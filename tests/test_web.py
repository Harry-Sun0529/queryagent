"""v1.0 T45: the person's doors — the local confirmation page, `drafts` and `confirm`.

H6-H9. Every refusal here is paired with its side effect, because a refusal
that confirmed something anyway is the failure this page exists to prevent:
nothing confirmed, nothing amended, nothing run.
"""

from __future__ import annotations

import http.client
import re
import sqlite3
import threading
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pytest

from queryagent.cli import main
from queryagent.web.server import (
    _TOKEN_IN_LOG,
    SECURITY_HEADERS,
    ConfirmationPage,
    ConfirmationServer,
    Request,
    Response,
)
from queryagent.web.session import Gate
from queryagent.workflow.models import (
    BusinessDefinition,
    Candidate,
    Channel,
    DefinitionDraft,
    DraftProgress,
    DraftStatus,
    Rule,
    RuleSource,
)
from tests.wired import ALICE, ALICE_WEB, Parts

PORT = 8765
HOST = f"127.0.0.1:{PORT}"
ORIGIN = f"http://127.0.0.1:{PORT}"
_FORM = re.compile(
    r'action="/drafts/([^"]+)/(confirm|amend)"><input type="hidden" name="version" '
    r'value="(\d+)"><input type="hidden" name="hash" value="([0-9a-f]+)">'
    r'<input type="hidden" name="token" value="([0-9a-f]+)">'
)


class Browser:
    """A logged-in client of one page, without sockets."""

    def __init__(self, page: ConfirmationPage, gate: Gate) -> None:
        self.page = page
        response = page.handle(Request("GET", gate.login_path, {"host": HOST}))
        assert response.status == 303
        self.cookie = dict(response.headers)["Set-Cookie"].split(";")[0]

    def get(self, path: str, *, host: str = HOST, cookie: bool = True) -> Response:
        headers = {"host": host}
        if cookie:
            headers["cookie"] = self.cookie
        return self.page.handle(Request("GET", path, headers))

    def post(
        self,
        path: str,
        fields: dict[str, Any],
        *,
        origin: str | None = ORIGIN,
        host: str = HOST,
        cookie: bool = True,
    ) -> Response:
        headers = {"host": host}
        if origin is not None:
            headers["origin"] = origin
        if cookie:
            headers["cookie"] = self.cookie
        body = urlencode(fields).encode("utf-8")
        return self.page.handle(Request("POST", path, headers, body))

    def form(self, draft_id: str, action: str) -> dict[str, str]:
        """The hidden fields of one form, exactly as the page rendered them."""
        page = self.get(f"/drafts/{draft_id}")
        for match in _FORM.finditer(page.body):
            if (match[1], match[2]) == (draft_id, action):
                return {"version": match[3], "hash": match[4], "token": match[5]}
        raise AssertionError(f"no {action} form on the page")


class Site:
    def __init__(self, tmp_path: Path) -> None:
        self.parts = Parts(tmp_path)
        self.gate = Gate(PORT)
        self.page = ConfirmationPage(self.parts.wiring, ALICE_WEB, self.gate)
        self.browser = Browser(self.page, self.gate)


@pytest.fixture
def site(tmp_path: Path) -> Iterator[Site]:
    built = Site(tmp_path)
    yield built
    built.parts.close()


# ------------------------------------------------------------------ login


def test_the_login_link_opens_one_session_once(tmp_path: Path) -> None:
    parts = Parts(tmp_path)
    gate = Gate(PORT)
    page = ConfirmationPage(parts.wiring, ALICE_WEB, gate)
    path = gate.login_path
    first = page.handle(Request("GET", path, {"host": HOST}))
    assert first.status == 303
    headers = dict(first.headers)
    assert headers["Location"] == "/"  # the token leaves the address bar
    assert "HttpOnly" in headers["Set-Cookie"]
    assert "SameSite=Strict" in headers["Set-Cookie"]
    assert page.handle(Request("GET", path, {"host": HOST})).status == 403
    parts.close()


def test_every_page_needs_a_session(site: Site) -> None:
    assert site.browser.get("/", cookie=False).status == 401
    assert site.browser.get("/drafts/abc", cookie=False).status == 401
    forged = site.page.handle(
        Request("GET", "/", {"host": HOST, "cookie": "queryagent_session=guess"})
    )
    assert forged.status == 401


# -------------------------------------------------------------- H6: Host


def test_a_foreign_host_is_refused_before_anything_else(tmp_path: Path) -> None:
    """H6, DNS rebinding: a request naming another host is refused, even with the login token."""
    parts = Parts(tmp_path)
    gate = Gate(PORT)
    page = ConfirmationPage(parts.wiring, ALICE_WEB, gate)
    path = gate.login_path
    rebound = page.handle(Request("GET", path, {"host": f"attacker.example:{PORT}"}))
    assert rebound.status == 403
    assert gate.login_path == path  # the refusal did not spend the link
    browser = Browser(page, gate)
    assert browser.get("/", host=f"attacker.example:{PORT}").status == 403
    assert browser.get("/", host="127.0.0.1:9999").status == 403
    parts.close()


# ---------------------------------------------------------- H6: CSRF


def test_confirming_without_a_form_token_changes_nothing(site: Site) -> None:
    draft = site.parts.agent_prepares()
    fields = {"version": draft["version"], "hash": draft["definition_hash"]}
    response = site.browser.post(f"/drafts/{draft['draft_id']}/confirm", fields)
    assert response.status == 403
    assert site.parts.confirmations() == []


def test_a_forged_or_misbound_token_changes_nothing(site: Site) -> None:
    """The token names the session, the action, the draft, the version and the hash."""
    draft = site.parts.agent_prepares()
    draft_id = draft["draft_id"]
    amend_form = site.browser.form(draft_id, "amend")
    for fields in (
        {**amend_form},  # a real token, for the other action
        {**amend_form, "token": "0" * 64},
        {**amend_form, "version": "1"},
    ):
        assert site.browser.post(f"/drafts/{draft_id}/confirm", fields).status == 403
    assert site.parts.confirmations() == []


def test_a_cross_site_or_missing_origin_changes_nothing(site: Site) -> None:
    """H6, CSRF: another site's form rides the cookie but cannot name this origin."""
    draft = site.parts.agent_prepares()
    form = site.browser.form(draft["draft_id"], "confirm")
    path = f"/drafts/{draft['draft_id']}/confirm"
    assert site.browser.post(path, form, origin="https://attacker.example").status == 403
    assert site.browser.post(path, form, origin="null").status == 403
    assert site.browser.post(path, form, origin=None).status == 403
    assert site.browser.post(path, form, cookie=False).status == 401
    assert site.parts.confirmations() == []


def test_an_amendment_needs_the_same_checks(site: Site) -> None:
    draft = site.parts.agent_prepares()
    path = f"/drafts/{draft['draft_id']}/amend"
    form = site.browser.form(draft["draft_id"], "amend")
    assert site.browser.post(path, {**form, "variant": "first_order"}, origin=None).status == 403
    assert site.browser.post(path, {"variant": "first_order", "version": "2"}).status == 403
    assert site.parts.workflow.get_draft(ALICE, draft["draft_id"]).version == 2


# ------------------------------------------------------------- H7: escaping


def test_document_and_question_text_is_escaped(site: Site) -> None:
    """H7: documents and questions are untrusted; nothing they contain becomes markup."""
    now = datetime(2026, 9, 11, tzinfo=timezone.utc)
    definition = BusinessDefinition(
        metric="new_users",
        display_name="新增用户",
        rules=(
            Rule(
                "counting_basis",
                "<script>alert('rule')</script>按注册",
                RuleSource.DOC,
                evidence_ref="d1#c1@0:9",
            ),
        ),
        missing=("variant",),
        candidates=(
            Candidate("registered", "注册口径", '"><img src=x onerror=alert(1)>'),
            Candidate("first_order", "首单口径", "按首单"),
        ),
    )
    site.parts.store.create_draft(
        DefinitionDraft(
            draft_id="evil1",
            request_id="r",
            subject_id="alice",
            workspace_id="ops",
            question="新增用户<script>alert('question')</script>",
            version=1,
            status=DraftStatus.NEEDS_INPUT,
            definition=definition,
            created_at=now,
            updated_at=now,
        )
    )
    for body in (site.browser.get("/drafts/evil1").body, site.browser.get("/").body):
        assert "<script" not in body.lower()
        assert "<img" not in body.lower()
    shown = site.browser.get("/drafts/evil1").body
    assert "&lt;script&gt;alert(&#x27;rule&#x27;)&lt;/script&gt;" in shown
    assert "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;" in shown


# ------------------------------------------------------- H8: what was on screen


def test_a_confirmation_of_a_version_that_moved_on_is_refused(site: Site) -> None:
    """H8: the page confirms what it showed; the agent amending in between voids the click."""
    draft = site.parts.agent_prepares()
    form = site.browser.form(draft["draft_id"], "confirm")
    site.parts.call(
        "amend_query",
        {"draft_id": draft["draft_id"], "expected_version": 2, "variant": "first_order"},
    )
    response = site.browser.post(f"/drafts/{draft['draft_id']}/confirm", form)
    assert response.status == 409
    assert "被改动过" in response.body
    assert site.parts.confirmations() == []
    progress = site.parts.workflow.progress(ALICE, draft["draft_id"])
    assert progress is DraftProgress.AWAITING_CONFIRMATION


# ----------------------------------------------- H9 and the whole handshake


def test_a_person_confirms_on_the_page_and_the_agent_runs_it(site: Site) -> None:
    """H3 + H9 end to end: page confirmation is recorded as web; the agent then runs it once."""
    draft = site.parts.agent_prepares(variant="first_order")
    draft_id = draft["draft_id"]
    page = site.browser.get(f"/drafts/{draft_id}").body
    assert '<mark class="agent">' in page  # P05: the agent's pick is highlighted
    assert "Agent 代填" in page
    form = site.browser.form(draft_id, "confirm")
    response = site.browser.post(f"/drafts/{draft_id}/confirm", form)
    assert (response.status, dict(response.headers)["Location"]) == (303, f"/drafts/{draft_id}")
    assert site.parts.confirmations() == [(draft_id, "web")]
    assert site.parts.executed == []  # confirming is not executing
    run = site.parts.call("execute_query", {"draft_id": draft_id})["result"]
    assert run["structuredContent"]["rows"] == [[1]]
    shown = site.browser.get(f"/drafts/{draft_id}").body
    assert "已执行" in shown
    assert "结果（执行口径" in shown
    assert "<form" not in shown  # nothing left to confirm or amend


def test_an_amendment_on_the_page_is_the_persons_own(site: Site) -> None:
    draft = site.parts.agent_prepares(variant="registered")
    draft_id = draft["draft_id"]
    form = site.browser.form(draft_id, "amend")
    response = site.browser.post(f"/drafts/{draft_id}/amend", {**form, "variant": "first_order"})
    assert response.status == 303
    rule = site.parts.workflow.get_draft(ALICE, draft_id).definition.rule("variant")
    assert rule is not None
    assert (rule.value, rule.source) == ("first_order", RuleSource.USER)
    assert rule.note == "覆盖 Agent 代填"


def test_an_empty_or_unreadable_amendment_is_explained(site: Site) -> None:
    draft = site.parts.agent_prepares()
    form = site.browser.form(draft["draft_id"], "amend")
    empty = site.browser.post(f"/drafts/{draft['draft_id']}/amend", form)
    assert empty.status == 400
    assert "没有内容" in empty.body
    bad = site.browser.post(f"/drafts/{draft['draft_id']}/amend", {**form, "period": "某天"})
    assert bad.status == 400
    assert site.parts.workflow.get_draft(ALICE, draft["draft_id"]).version == 2


def test_the_list_shows_only_what_waits_in_this_workspace(site: Site) -> None:
    waiting = site.parts.agent_prepares()
    done = site.parts.agent_prepares()
    site.parts.workflow.confirm(
        ALICE, done["draft_id"], version=2, definition_hash=done["definition_hash"]
    )
    finance = site.parts.workflow.prepare(
        ALICE.__class__("alice", "finance"), "新增用户有多少？", request_id="f"
    )
    listing = site.browser.get("/").body
    assert waiting["draft_id"] in listing
    assert done["draft_id"] not in listing
    assert finance.draft_id not in listing
    assert site.browser.get(f"/drafts/{finance.draft_id}").status == 404


def test_the_referrer_policy_still_lets_the_browser_name_this_origin() -> None:
    """Found in a real browser: under no-referrer, a same-origin form POST carries
    ``Origin: null`` and the CSRF check refused the person's own confirmation."""
    policy = dict(SECURITY_HEADERS)["Referrer-Policy"]
    assert policy == "same-origin"


def test_the_log_never_carries_the_login_token() -> None:
    line = '"GET /login?token=abc-DEF_123 HTTP/1.1" 303 -'
    assert "abc-DEF_123" not in _TOKEN_IN_LOG.sub("token=***", line)


def test_the_page_refuses_an_actor_that_is_not_on_the_web_channel(site: Site) -> None:
    with pytest.raises(ValueError, match="Channel.WEB"):
        ConfirmationPage(site.parts.wiring, ALICE, Gate(PORT))


# ----------------------------------------------------------- a real server


def test_the_real_server_sends_its_headers_and_confirms_over_http(tmp_path: Path) -> None:
    """The handler only translates; this proves it translates every part of a confirmation."""
    ready = threading.Event()
    box: dict[str, Any] = {}

    def serve() -> None:
        parts = Parts(tmp_path)  # SQLite objects stay on the thread that made them
        box["draft"] = parts.agent_prepares()
        server = ConfirmationServer(parts.wiring, ALICE_WEB, 0)
        box["server"] = server
        ready.set()
        server.serve_forever(poll_interval=0.05)
        server.server_close()
        parts.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    assert ready.wait(10)
    server: ConfirmationServer = box["server"]
    port = server.server_address[1]
    draft_id = box["draft"]["draft_id"]

    def request(method: str, path: str, **kwargs: Any) -> tuple[http.client.HTTPResponse, str]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        connection.request(method, path, **kwargs)
        response = connection.getresponse()
        return response, response.read().decode("utf-8")

    try:
        login, _ = request("GET", server.gate.login_path)
        assert login.status == 303
        cookie = login.getheader("Set-Cookie", "").split(";")[0]
        shown, body = request("GET", f"/drafts/{draft_id}", headers={"Cookie": cookie})
        assert shown.status == 200
        assert (shown.getheader("Content-Security-Policy") or "").startswith("default-src 'none'")
        assert shown.getheader("X-Frame-Options") == "DENY"
        match = next(m for m in _FORM.finditer(body) if m[2] == "confirm")
        fields = urlencode({"version": match[3], "hash": match[4], "token": match[5]})
        confirmed, _ = request(
            "POST",
            f"/drafts/{draft_id}/confirm",
            body=fields,
            headers={
                "Cookie": cookie,
                "Origin": f"http://127.0.0.1:{port}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        assert confirmed.status == 303
    finally:
        server.shutdown()
        thread.join(10)
    with sqlite3.connect(tmp_path / "wf.db") as connection:
        assert list(connection.execute("SELECT channel FROM confirmations")) == [("web",)]


# ------------------------------------------------------ the terminal door


def test_drafts_lists_what_waits_on_you(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parts = Parts(tmp_path)
    draft = parts.agent_prepares()
    config = parts.write_config()
    alice = ["--subject", "alice", "--workspace", "ops"]
    assert main(["drafts", "--config", str(config), *alice]) == 0
    out = capsys.readouterr().out
    assert f"#{draft['draft_id'][:8]}  v2  待确认" in out
    assert main(["drafts", "--config", str(config), "--subject", "bob", "--workspace", "ops"]) == 0
    assert "没有等待" in capsys.readouterr().out
    parts.close()


def test_confirming_in_the_terminal_records_the_cli_channel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    parts = Parts(tmp_path)
    draft = parts.agent_prepares()
    config = parts.write_config()
    monkeypatch.setattr("builtins.input", lambda _prompt="": "y")
    code = main(
        ["confirm", draft["draft_id"][:8], "--config", str(config),
         "--subject", "alice", "--workspace", "ops"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "[Agent 代填]" in out  # the person saw what the agent filled in
    assert "execute_query" in out
    assert parts.confirmations() == [(draft["draft_id"], Channel.CLI.value)]
    assert parts.executed == []
    parts.close()


def test_declining_in_the_terminal_confirms_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parts = Parts(tmp_path)
    draft = parts.agent_prepares()
    config = parts.write_config()
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    code = main(
        ["confirm", draft["draft_id"], "--config", str(config),
         "--subject", "alice", "--workspace", "ops"]
    )
    assert code == 2
    assert parts.confirmations() == []
    parts.close()


def test_the_terminal_asks_for_what_is_open_before_confirming(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parts = Parts(tmp_path)
    draft = parts.agent_prepares(variant="")
    config = parts.write_config()
    answers = iter(["first_order", "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    code = main(
        ["confirm", draft["draft_id"], "--config", str(config),
         "--subject", "alice", "--workspace", "ops"]
    )
    assert code == 0
    rule = parts.workflow.get_draft(ALICE, draft["draft_id"]).definition.rule("variant")
    assert rule is not None and rule.source is RuleSource.USER
    assert len(parts.confirmations()) == 1
    parts.close()


def test_someone_elses_draft_cannot_be_confirmed_in_the_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    parts = Parts(tmp_path)
    draft = parts.agent_prepares()
    config = parts.write_config()
    monkeypatch.setattr("builtins.input", lambda _prompt="": "y")
    code = main(
        ["confirm", draft["draft_id"], "--config", str(config),
         "--subject", "mallory", "--workspace", "ops"]
    )
    assert code == 2
    assert parts.confirmations() == []
    parts.close()
