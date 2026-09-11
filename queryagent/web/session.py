"""Who may use the confirmation page, and whether a request came from it (T45, P06).

A local web server that can confirm queries is a target for three classic
attacks, and each check here answers one of them:

- **DNS rebinding.** A website points its own hostname at 127.0.0.1, and its
  script then talks to this server as if same-origin. The ``Host`` header
  still names the attacker's hostname, so any request whose Host is not this
  server's own address is refused, before anything else is looked at.
- **CSRF.** Another site's page submits a form here and the browser attaches
  the cookie. The session cookie is ``SameSite=Strict``; every POST must
  carry an ``Origin`` naming this server; and every form carries a token
  bound to the session, the action, and the draft version and hash that were
  on screen.
- **XSS.** Documents are untrusted text. ``page.py`` escapes every string it
  writes, and the server forbids scripts altogether with its
  Content-Security-Policy.

Logging in takes a random link printed on the terminal that started the
server, usable once. What this does not defend against is written in
SECURITY.md: an agent with a shell as the same OS user can confirm anyway.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from http.cookies import CookieError, SimpleCookie

COOKIE_NAME = "queryagent_session"


class Gate:
    """The login link, the sessions it opened, and the checks every request passes."""

    def __init__(self, port: int) -> None:
        self._port = port
        self._login_token: str | None = secrets.token_urlsafe(32)
        self._sessions: set[str] = set()
        self._form_key = secrets.token_bytes(32)

    @property
    def login_path(self) -> str:
        """The one-time login path, or '' once it has been used."""
        return f"/login?token={self._login_token}" if self._login_token else ""

    def host_ok(self, host: str | None) -> bool:
        """True when the request names this server's own address (DNS rebinding)."""
        return host in (f"127.0.0.1:{self._port}", f"localhost:{self._port}")

    def origin_ok(self, origin: str | None) -> bool:
        """True when a POST says it came from this server's own pages (CSRF)."""
        return origin in (f"http://127.0.0.1:{self._port}", f"http://localhost:{self._port}")

    def log_in(self, token: str) -> str | None:
        """Exchange the login token for a new session, once. None when it is wrong or spent."""
        expected = self._login_token
        if expected is None or not hmac.compare_digest(token.encode(), expected.encode()):
            return None
        self._login_token = None  # a link seen in history or a log opens nothing
        session = secrets.token_urlsafe(32)
        self._sessions.add(session)
        return session

    def session_of(self, cookie_header: str | None) -> str | None:
        """The session a request's cookie names, when it is one this server opened."""
        if not cookie_header:
            return None
        jar: SimpleCookie = SimpleCookie()
        try:
            jar.load(cookie_header)
        except CookieError:
            return None
        morsel = jar.get(COOKIE_NAME)
        if morsel is None or morsel.value not in self._sessions:
            return None
        return morsel.value

    def cookie(self, session: str) -> str:
        """The Set-Cookie value: no script can read it, no other site's request carries it."""
        return f"{COOKIE_NAME}={session}; HttpOnly; SameSite=Strict; Path=/"

    def form_token(
        self, session: str, action: str, draft_id: str, version: int, definition_hash: str
    ) -> str:
        """A token for one form: this session, this action, this version of this draft."""
        message = "\0".join((session, action, draft_id, str(version), definition_hash))
        return hmac.new(self._form_key, message.encode("utf-8"), hashlib.sha256).hexdigest()

    def form_token_ok(
        self,
        session: str,
        action: str,
        draft_id: str,
        version: int,
        definition_hash: str,
        token: str,
    ) -> bool:
        expected = self.form_token(session, action, draft_id, version, definition_hash)
        return hmac.compare_digest(expected.encode(), token.encode())
