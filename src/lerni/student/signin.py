"""Signing in: check a password, issue a signed cookie, and resolve it on every request.

The cookie carries the username, when it was issued, and the account's
session version, signed with a server secret. Resolving it re-reads the
account, so an archive or password reset (which bump the version) signs out
every device at once. Standard library only.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from lerni.student.students import (
    USERNAME_RE,
    AccountError,
    Kind,
    StudentStore,
    hash_password,
    verify_password,
)

COOKIE_NAME = "lerni_session"
SESSION_SECONDS = 30 * 24 * 3600
FREE_FAILURES = 3  # wrong passwords before delays start
MAX_WAIT = 30.0
MAX_TRACKED = 1000  # usernames with recent wrong passwords kept in memory
SECRET_BYTES = 32


class Role(StrEnum):
    SUPERVISED = "supervised"
    INDEPENDENT = "independent"


@dataclass(frozen=True, slots=True)
class Viewer:
    """Who a request belongs to, resolved on the server."""

    username: str
    display_name: str
    role: Role
    educator: bool = False  # may manage students and the family's plans


def load_secret(root: Path) -> bytes:
    """Read the signing secret, creating it (readable only by this user) on first start.

    Raises:
        RuntimeError: The file is damaged (too short), so cookies would be forgeable.
    """
    path = root / "secret.key"
    if not path.exists():
        root.mkdir(parents=True, exist_ok=True)
        # write a temp file, then swap it in, so a crash never leaves an empty secret
        tmp = root / f".secret-{secrets.token_hex(4)}.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(secrets.token_hex(SECRET_BYTES))
        os.replace(tmp, path)
    try:
        secret = bytes.fromhex(path.read_text().strip())
    except ValueError:
        secret = b""
    if len(secret) < SECRET_BYTES:
        raise RuntimeError(f"{path} is damaged; delete it to make a new one (signs everyone out).")
    return secret


@dataclass
class _Failures:
    count: int = 0
    until: float = 0.0  # refuse attempts before this time


class SignIn:
    """Checks passwords and cookies for the student app.

    Args:
        students: The account store.
        secret: The cookie-signing secret.
        clock: Seconds since the epoch; injectable for tests.
    """

    def __init__(
        self,
        students: StudentStore,
        secret: bytes,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.students = students
        self._secret = secret
        self._clock = clock
        self._failures: dict[str, _Failures] = {}
        self._lock = threading.Lock()  # one sign-in check at a time, so waits can't be raced
        self._dummy = hash_password("not-a-real-password", Kind.INDEPENDENT)

    # --- cookies -------------------------------------------------------------

    def _sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    def _version(self, username: str) -> str | None:
        """The current session version, or None if the account can't sign in."""
        try:
            student = self.students.get(username)
        except AccountError:
            return None
        return None if student.archived else str(student.session_version)

    def _cookie(self, username: str, version: str) -> str:
        payload = f"{username}.{int(self._clock())}.{version}"
        return f"{payload}.{self._sign(payload)}"

    def viewer(self, username: str | None) -> Viewer | None:
        """Re-read who ``username`` is right now; None if missing or archived."""
        if not username or not USERNAME_RE.fullmatch(username):
            return None
        try:
            s = self.students.get(username)
        except AccountError:
            return None
        if s.archived:
            return None
        role = Role.SUPERVISED if s.kind is Kind.SUPERVISED else Role.INDEPENDENT
        return Viewer(s.username, s.display_name, role, s.educator)

    def viewer_from_cookie(self, value: str | None) -> Viewer | None:
        """Resolve a cookie: valid signature, not expired, and the same session version."""
        parts = (value or "").split(".")
        if len(parts) != 4:
            return None
        username, issued, version, signature = parts
        if not hmac.compare_digest(signature, self._sign(f"{username}.{issued}.{version}")):
            return None
        if not issued.isdigit() or self._clock() - int(issued) > SESSION_SECONDS:
            return None
        if version != self._version(username):
            return None
        return self.viewer(username)

    # --- passwords -------------------------------------------------------------

    def _check(self, username: str, password: str) -> bool:
        try:
            student = self.students.get(username)
        except AccountError:
            # same work as a real account, so timing doesn't reveal who exists
            verify_password(password, self._dummy)
            return False
        return not student.archived and verify_password(password, student.password)

    def attempt(self, username: str, password: str) -> tuple[str | None, str]:
        """Try to sign in.

        Returns:
            ``(cookie, "")`` on success, or ``(None, message)``.
        """
        # every well-formed name is tracked alike, known or not, so nothing reveals who exists
        tracked = bool(USERNAME_RE.fullmatch(username))
        with self._lock:
            f = self._failures.get(username) if tracked else None
            now = self._clock()
            if f and now < f.until:
                # refused without checking; waiting doesn't extend the delay
                wait = int(f.until - now) + 1
                return None, f"Too many tries. Wait {wait} second{'s' if wait > 1 else ''}."
            if self._check(username, password):
                self._failures.pop(username, None)
                return self._cookie(username, self._version(username) or ""), ""
            if tracked:
                if username not in self._failures and len(self._failures) >= MAX_TRACKED:
                    self._failures.pop(next(iter(self._failures)))  # forget the oldest
                f = self._failures.setdefault(username, _Failures())
                f.count += 1
                if f.count >= FREE_FAILURES:
                    f.until = now + min(2.0 ** (f.count - FREE_FAILURES), MAX_WAIT)
            return None, "That username and password don't match."
