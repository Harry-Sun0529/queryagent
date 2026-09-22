"""Acceptance harness: scriptable local checks for the v1.0 human-acceptance list.

Each check runs the real CLI/MCP/web code paths against the demo config —
no live model, no sealed benchmarks — and prints PASS/FAIL with evidence.
Usage: python scripts/acceptance_check.py [--config PATH] [check ...]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CHECKS: list[Check] = []


class Check:
    def __init__(self, name: str, run) -> None:  # type: ignore[no-untyped-def]
        self.name = name
        self.run = run
        CHECKS.append(self)


@contextlib.contextmanager
def _temp_env() -> Iterator[Path]:
    """A scratch directory with a demo-shaped config, metrics and mappings."""
    import sqlite3

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        db = root / "shop.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE users (id INTEGER, first_order_at TEXT, channel TEXT)")
        conn.executemany(
            "INSERT INTO users VALUES (?,?,?)",
            [
                (1, "2026-01-01", "ads"),
                (2, None, "organic"),
                (3, "2026-01-02", "ads"),
            ],
        )
        conn.commit()
        conn.close()
        (root / "metrics.yaml").write_text(
            "metrics:\n"
            "  - name: new_users\n"
            "    display_name: 新增用户\n"
            "    definition: 统计新加入的用户数。\n"
            "    tables: [users]\n"
            "    required_rules: [period]\n"
            "    variants:\n"
            "      - key: registered\n"
            "        label: 注册口径\n"
            "        definition: 按 created_at 归属日期计数\n"
            "      - key: first_order\n"
            "        label: 首单口径\n"
            "        definition: 按 first_order_at 归属日期计数\n",
            encoding="utf-8",
        )
        (root / "mappings.yaml").write_text(
            "mappings:\n"
            "  - metric: new_users\n"
            "    variant: registered\n"
            "    from: users\n"
            "    measure: COUNT(*)\n"
            "    label: n\n"
            "    time_column: first_order_at\n"
            "  - metric: new_users\n"
            "    variant: first_order\n"
            "    from: users\n"
            "    measure: COUNT(*)\n"
            "    label: n\n"
            "    where: [\"first_order_at IS NOT NULL\"]\n"
            "    time_column: first_order_at\n"
            "dimensions:\n"
            "  - key: channel\n"
            "    label: 渠道\n"
            "    columns: {users: channel}\n"
            "    values: {ads: [广告], organic: [自然流量]}\n",
            encoding="utf-8",
        )
        (root / "config.yaml").write_text(
            "llm:\n"
            "  backend: openai_compatible\n"
            "  model: m\n"
            "  base_url: http://127.0.0.1:9\n"
            "database:\n"
            f"  type: sqlite\n  path: {db}\n"
            f"metrics_path: {root / 'metrics.yaml'}\n"
            "workflow:\n"
            f"  mappings_path: {root / 'mappings.yaml'}\n"
            f"  state_path: {root / 'wf.db'}\n"
            "trace: false\n",
            encoding="utf-8",
        )
        yield root


def _flow(root: Path, question: str, stdin: str, *flags: str) -> tuple[int, str, str]:
    """Run the real CLI with scripted stdin; return (exit, stdout, stderr)."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "queryagent.cli",
            "flow",
            question,
            "--config",
            str(root / "config.yaml"),
            "--workspace",
            "ops",
            "--subject",
            "alice",
            *flags,
        ],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


# --------------------------------------------------------------- CLI checks


def check(name: str) -> Any:  # type: ignore[no-any-return] # decorator
    def wrap(fn):  # type: ignore[no-untyped-def]
        Check(name, fn)
        return fn

    return wrap


@check("cli-natural-language-adopt")
def _() -> None:
    """The variant prompt accepts a number and a plain-language label."""
    with _temp_env() as root:
        # Period is asked first, then the variant: feed both.
        code, out, err = _flow(root, "新增用户有多少？", "2026-01-01..2026-01-02\n1\nn\n")
        assert code == 2, (code, out, err)
        assert "选定口径：注册口径" in out, out
        assert "你的选择" in out, out
        assert "[无效]" not in err, err
        code, out, err = _flow(root, "新增用户有多少？", "2026-01-01..2026-01-02\n注册口径\nn\n")
        assert "选定口径：注册口径" in out, out


@check("cli-invalid-then-valid-answer")
def _() -> None:
    """A wrong answer re-prompts instead of exiting with a config complaint."""
    with _temp_env() as root:
        # A wrong period answer at the prompt shows [无效] and asks again.
        code, out, err = _flow(root, "新增用户有多少？", "zzz\n2026-01-01..2026-01-02\nn\n")
        assert "[无效]" in err, err
        assert "配置有问题" not in err, err


@check("cli-near-two-months-offers-choices")
def _() -> None:
    """近两个月 lists interpretations with absolute dates and accepts a number."""
    with _temp_env() as root:
        code, out, err = _flow(root, "近两个月新增用户有多少？", "1\nn\n")
        assert code == 2, (code, out, err)
        assert "滚动到今天" in out, out
        assert "个完整自然月" in out, out
        assert "请输入编号" in out, out


@check("cli-undeclared-dimension-fails-fast")
def _() -> None:
    """A split by an undeclared dimension refuses before any prompt."""
    with _temp_env() as root:
        code, out, err = _flow(root, "上个月按城市拆分的新增用户数", "", "--yes")
        assert code == 2, (code, out, err)
        assert "没有声明这个维度" in err, err
        assert "你的选择" not in out, out  # no adopt/variant prompt was shown


@check("cli-undeclared-value-retries")
def _() -> None:
    """抖音 is refused; a subsequent declared value is accepted."""
    with _temp_env() as root:
        code, out, err = _flow(
            root, "上个月抖音渠道的新增用户有多少？", "1\n渠道=广告\nn\n", "--variant", "registered"
        )
        assert code == 2, (code, out, err)
        assert "不是维护者声明的取值" in err, err


# --------------------------------------------------------------- MCP checks


def _mcp(root: Path) -> subprocess.Popen[Any]:
    """A real stdio MCP server subprocess, as a host would launch it."""
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "queryagent.cli",
            "mcp",
            "--config",
            str(root / "config.yaml"),
            "--subject",
            "alice",
            "--workspace",
            "ops",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )


def _rpc(proc: subprocess.Popen[Any], payload: dict[str, Any]) -> dict[str, Any]:
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write((json.dumps(payload) + "\n").encode())
    proc.stdin.flush()
    line = proc.stdout.readline()
    assert line, "MCP server closed stdout"
    return json.loads(line)


@check("mcp-five-tools-no-confirm")
def _() -> None:
    with _temp_env() as root:
        proc = _mcp(root)
        try:
            reply = _rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            names = {t["name"] for t in reply["result"]["tools"]}
            assert names == {
                "list_metrics",
                "prepare_query",
                "amend_query",
                "query_status",
                "execute_query",
            }, names
            frame = _rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "confirm_query", "arguments": {}},
                },
            )
            # The protocol may answer with an error object (unknown tool) or an
            # isError result; either way the call must not succeed.
            rejected = frame.get("error") is not None or frame["result"].get("isError") is True
            assert rejected, frame
        finally:
            proc.kill()


@check("mcp-execute-without-confirmation-runs-nothing")
def _() -> None:
    with _temp_env() as root:
        proc = _mcp(root)
        try:
            prepared = _rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "prepare_query",
                        "arguments": {"question": "新增用户有多少？"},
                    },
                },
            )["result"]["structuredContent"]
            draft_id = prepared["draft_id"]
            amend = _rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "amend_query",
                        "arguments": {
                            "draft_id": draft_id,
                            "expected_version": prepared["version"],
                            "variant": "registered",
                            "period": "2026-01-01..2026-01-02",
                        },
                    },
                },
            )
            assert amend["result"]["isError"] is False, amend
            refused = _rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "execute_query", "arguments": {"draft_id": draft_id}},
                },
            )
            assert refused["result"]["isError"] is True, refused
        finally:
            proc.kill()


@check("mcp-forged-identity-is-refused")
def _() -> None:
    with _temp_env() as root:
        proc = _mcp(root)
        try:
            frame = _rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "list_metrics",
                        "arguments": {"subject": "bob", "workspace": "finance"},
                    },
                },
            )
            assert frame["result"]["isError"] is True, frame
        finally:
            proc.kill()


# --------------------------------------------------------------- Web checks


def _web_proc(root: Path) -> tuple[subprocess.Popen[Any], int]:
    """A real confirmation-page server subprocess on an OS-assigned free port."""
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "queryagent.cli",
            "web",
            "--config",
            str(root / "config.yaml"),
            "--subject",
            "alice",
            "--workspace",
            "ops",
            "--port",
            str(port),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    return proc, port


def _login_url(proc: subprocess.Popen[Any], port: int, timeout: float = 10.0) -> str:
    """The one-time login URL the server prints on stdout at startup.

    The startup line glues the URL to a full-width colon, so the URL is found
    as a substring, not as a whitespace-separated word.
    """
    deadline = time.time() + timeout
    assert proc.stdout is not None
    prefix = f"http://127.0.0.1:{port}"
    while time.time() < deadline:
        line = proc.stdout.readline().decode()
        if not line and proc.poll() is not None:
            break
        found = line.find(prefix)
        if found >= 0:
            tail = line[found:].strip()
            return tail.rstrip("。：")
    raise AssertionError(f"no login URL printed on stdout for port {port}")


def _get(url: str, headers: dict[str, str] | None = None) -> Any:
    """Fetch a URL, returning the response or the HTTPError object."""
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with contextlib.closing(urllib.request.urlopen(req, timeout=5)) as resp:
            return resp
    except urllib.error.HTTPError as exc:
        return exc


class _NoRedirect(urllib.request.HTTPRedirectHandler):  # type: ignore[no-untyped-def]
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@check("web-negative-http-checks")
def _() -> None:
    """Forged Host, missing session, one-time login and session cookie."""
    with _temp_env() as root:
        proc, port = _web_proc(root)
        try:
            login = _login_url(proc, port)
            base = f"http://127.0.0.1:{port}"
            # Forged Host (DNS rebinding).
            assert _get(base, {"Host": "evil.example"}).status == 403
            # No session yet: the root refuses before any draft is shown.
            assert _get(base).status == 401
            # The login link answers 303 with an HttpOnly SameSite session
            # cookie, and never serves the page itself.
            opener = urllib.request.build_opener(_NoRedirect)
            try:
                with contextlib.closing(opener.open(login, timeout=5)) as resp:
                    raise AssertionError(f"login link served a page: {resp.status}")
            except urllib.error.HTTPError as exc:
                assert exc.status == 303
                cookie = exc.headers.get("Set-Cookie", "")
                assert "HttpOnly" in cookie and "SameSite=Strict" in cookie, cookie
                assert exc.headers.get("Location") == "/"
            # The link cannot be reused (H6: one-time link).
            assert _get(login).status == 403
            # The session it opened does reach the list.
            with contextlib.closing(
                opener.open(
                    urllib.request.Request(
                        base + "/", headers={"Cookie": cookie.split(";")[0]}
                    ),
                    timeout=5,
                )
            ) as resp:
                assert resp.status == 200
        finally:
            proc.kill()


@check("web-security-headers-present")
def _() -> None:
    with _temp_env() as root:
        proc, port = _web_proc(root)
        try:
            _login_url(proc, port)
            exc = _get(f"http://127.0.0.1:{port}/")
            assert isinstance(exc, urllib.error.HTTPError), "expected 401 without a session"
            status_headers = tuple(exc.headers.items())
            names = {name for name, _ in status_headers}
            assert {
                "Content-Security-Policy",
                "X-Frame-Options",
                "X-Content-Type-Options",
                "Referrer-Policy",
            } <= names, names
            csp = dict(status_headers).get("Content-Security-Policy", "")
            assert "default-src 'none'" in csp, csp
        finally:
            proc.kill()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checks", nargs="*", help="check names (default: all)")
    args = parser.parse_args(argv)
    selected = [c for c in CHECKS if not args.checks or c.name in args.checks]
    if args.checks and len(selected) != len(args.checks):
        known = {c.name for c in CHECKS}
        unknown = [c for c in args.checks if c not in known]
        print(f"unknown checks: {unknown}")
        return 2
    failures = 0
    for check in selected:
        try:
            check.run()
            print(f"PASS {check.name}")
        except Exception as exc:  # noqa: BLE001 - a harness reports, never dies
            failures += 1
            print(f"FAIL {check.name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(selected) - failures}/{len(selected)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
