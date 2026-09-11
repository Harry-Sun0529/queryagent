"""The confirmation page server: standard library only, 127.0.0.1 only (T45, P06).

Routes:

- ``GET /login?token=…``: the one-time link printed on the terminal opens a
  session and redirects to the list.
- ``GET /``: drafts waiting on this person.
- ``GET /drafts/<id>``: the sheet, highlighted where an agent filled it in,
  with an amend form and, when complete, a confirm form.
- ``POST /drafts/<id>/amend`` and ``POST /drafts/<id>/confirm``.

Every request is checked in the same order: Host (DNS rebinding), then the
session, then for a POST the Origin and the form token (CSRF). A request that
fails a check changes nothing (H6). Confirming passes the version and hash
the form was rendered with, and the service refuses if the draft moved
since (H8).

``ConfirmationPage.handle`` takes a request and returns a response with no
sockets involved; the HTTP handler below only translates. That is what
makes every check testable without a network.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from queryagent.web.page import draft_page, message_page, pending_page
from queryagent.web.session import Gate
from queryagent.workflow.answers import Answers, answer_rules
from queryagent.workflow.errors import NotFound, PermissionDenied, StaleVersion, WorkflowError
from queryagent.workflow.models import ActorContext, Channel, DefinitionDraft, DraftProgress
from queryagent.workflow.render import render_result, sheet_lines
from queryagent.workflow.wiring import WorkflowWiring

MAX_BODY_BYTES = 64 * 1024

SECURITY_HEADERS = (
    # No script runs on this page, whatever reaches it (H7's second wall).
    (
        "Content-Security-Policy",
        "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'none'",
    ),
    ("X-Frame-Options", "DENY"),
    ("X-Content-Type-Options", "nosniff"),
    # Not no-referrer: under it a browser sends ``Origin: null`` even on a
    # same-origin form POST (Fetch, "serializing a request origin"), and the
    # CSRF check then refuses the person's own click. Found in a real browser.
    # same-origin still sends nothing to any other site.
    ("Referrer-Policy", "same-origin"),
    ("Cache-Control", "no-store"),
)

_DRAFT = re.compile(r"/drafts/([A-Za-z0-9_-]{1,64})")
_ACTION = re.compile(r"/drafts/([A-Za-z0-9_-]{1,64})/(amend|confirm)")
_TOKEN_IN_LOG = re.compile(r"token=[^&\s\"]+")


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    headers: Mapping[str, str]
    """Header names in lower case."""
    body: bytes = b""


@dataclass(frozen=True)
class Response:
    status: int
    body: str = ""
    headers: tuple[tuple[str, str], ...] = ()


class ConfirmationPage:
    """The routes, over one wired workflow and the one person the server was started for."""

    def __init__(self, wiring: WorkflowWiring, actor: ActorContext, gate: Gate) -> None:
        if actor.channel is not Channel.WEB:
            raise ValueError("the confirmation page acts for a person: use Channel.WEB")
        self._wiring = wiring
        self._workflow = wiring.workflow
        self._actor = actor
        self._gate = gate

    def handle(self, request: Request) -> Response:
        if not self._gate.host_ok(request.headers.get("host")):
            return _refused(403, "请求的主机名不是本机地址，已拒绝（防 DNS rebinding）。")
        url = urlsplit(request.path)
        if request.method == "GET" and url.path == "/login":
            return self._login(url.query)
        if url.path == "/favicon.ico":
            return Response(404)  # asked for by every browser; not worth a login page
        session = self._gate.session_of(request.headers.get("cookie"))
        if session is None:
            return _refused(401, "请用启动 queryagent web 时终端打印的登录链接打开本页。")
        if request.method == "GET":
            if url.path == "/":
                drafts = self._workflow.pending_drafts(self._actor)
                page = pending_page(
                    self._actor.subject_id, self._actor.workspace_id, drafts, self._wiring.zone
                )
                return Response(200, page)
            shown = _DRAFT.fullmatch(url.path)
            if shown:
                return self._show(shown[1], session)
            return _refused(404, "没有这个页面。")
        if request.method != "POST":
            return _refused(405, "不支持的请求方法。")
        if not self._gate.origin_ok(request.headers.get("origin")):
            return _refused(403, "这个提交不是来自本页，已拒绝（防跨站请求伪造）。")
        acted = _ACTION.fullmatch(url.path)
        if not acted:
            return _refused(404, "没有这个页面。")
        return self._act(acted[1], acted[2], session, request.body)

    def _login(self, query: str) -> Response:
        token = parse_qs(query).get("token", [""])[0]
        session = self._gate.log_in(token)
        if session is None:
            return _refused(
                403, "登录链接无效或已经用过。重启 queryagent web 可以得到一个新的登录链接。"
            )
        return Response(303, "", (("Location", "/"), ("Set-Cookie", self._gate.cookie(session))))

    def _own_draft(self, draft_id: str) -> DefinitionDraft:
        draft = self._workflow.get_draft(self._actor, draft_id)
        if draft.workspace_id != self._actor.workspace_id:
            raise PermissionDenied("not permitted")
        return draft

    def _show(self, draft_id: str, session: str) -> Response:
        try:
            draft = self._own_draft(draft_id)
        except (NotFound, PermissionDenied):
            return _refused(404, "没有这份草案。")
        progress = self._workflow.progress(self._actor, draft_id)
        citations = self._wiring.citations(self._actor, draft.question)
        run = self._workflow.last_run(self._actor, draft_id)
        result = (
            render_result(draft.definition, run, self._wiring.labels)
            if run is not None and progress is DraftProgress.EXECUTED
            else []
        )
        page = draft_page(
            draft,
            sheet_lines(draft, citations, self._wiring.labels),
            progress=progress,
            freshness=self._workflow.freshness_advisory(self._actor, draft_id),
            confirmation=self._workflow.human_confirmation(self._actor, draft_id),
            result=result,
            token=lambda action: self._gate.form_token(
                session, action, draft.draft_id, draft.version, draft.definition_hash
            ),
            zone=self._wiring.zone,
        )
        return Response(200, page)

    def _act(self, draft_id: str, action: str, session: str, body: bytes) -> Response:
        form = _form(body)
        try:
            version = int(form.get("version", ""))
        except ValueError:
            return _refused(400, "表单缺少版本号。")
        definition_hash = form.get("hash", "")
        token = form.get("token", "")
        if not self._gate.form_token_ok(session, action, draft_id, version, definition_hash, token):
            return _refused(403, "表单令牌无效或已过期：请回到草案页重新提交（防跨站请求伪造）。")
        back = f"/drafts/{draft_id}"
        try:
            draft = self._own_draft(draft_id)
            if action == "confirm":
                self._workflow.confirm(
                    self._actor, draft_id, version=version, definition_hash=definition_hash
                )
            else:
                rules = answer_rules(
                    draft.definition,
                    _answers(form),
                    source=self._actor.authoring_source,
                    today=self._wiring.today(),
                    dimensions=self._wiring.dimensions,
                )
                self._workflow.amend(self._actor, draft_id, expected_version=version, rules=rules)
        except (NotFound, PermissionDenied):
            return _refused(404, "没有这份草案。")
        except StaleVersion:
            return _refused(
                409, "这份口径在你查看之后被改动过，没有确认也没有修改。请重新查看当前版本。", back
            )
        except (ValueError, WorkflowError) as exc:
            return _refused(400, str(exc), back)
        return Response(303, "", (("Location", back),))


def _answers(form: Mapping[str, str]) -> Answers:
    return Answers(
        variant=form.get("variant", "").strip(),
        adopt=tuple(v for k, v in form.items() if k.startswith("adopt:") and v.strip()),
        rules=tuple(
            (k.removeprefix("rule:"), v)
            for k, v in form.items()
            if k.startswith("rule:") and v.strip()
        ),
        period=form.get("period", "").strip(),
        group_by=form.get("group_by", "").strip(),
        value_filter=form.get("filter", "").strip(),
    )


def _form(body: bytes) -> dict[str, str]:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    return {key: values[-1] for key, values in parse_qs(text, keep_blank_values=True).items()}


def _refused(status: int, text: str, back: str = "/") -> Response:
    return Response(status, message_page("未执行", text, back=back))


class _Handler(BaseHTTPRequestHandler):
    """Translates HTTP to ``ConfirmationPage.handle`` and back; decides nothing."""

    server: ConfirmationServer
    server_version = "queryagent"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802 - the standard library's naming
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def _dispatch(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            self._send(_refused(413, "提交的内容过大。"))
            return
        body = self.rfile.read(length) if length > 0 else b""
        headers = {name.lower(): value for name, value in self.headers.items()}
        self._send(self.server.page.handle(Request(self.command, self.path, headers, body)))

    def _send(self, response: Response) -> None:
        encoded = response.body.encode("utf-8")
        self.send_response(response.status)
        for name, value in (*SECURITY_HEADERS, *response.headers):
            self.send_header(name, value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # The login link's token must not outlive its one use in a log.
        print(f"[web] {_TOKEN_IN_LOG.sub('token=***', format % args)}", file=sys.stderr)


class ConfirmationServer(HTTPServer):
    """One person's confirmation page, bound to 127.0.0.1 and nowhere else."""

    def __init__(self, wiring: WorkflowWiring, actor: ActorContext, port: int) -> None:
        super().__init__(("127.0.0.1", port), _Handler)
        self.gate = Gate(self.server_address[1])
        self.page = ConfirmationPage(wiring, actor, self.gate)

    @property
    def login_url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}{self.gate.login_path}"
