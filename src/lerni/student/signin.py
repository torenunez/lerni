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
    verify_password,
)

COOKIE_NAME = "lerni_session"
SESSION_SECONDS = 30 * 24 * 3600
EDUCATOR = "educator"
FREE_FAILURES = 3  # wrong passwords before delays start
MAX_WAIT = 30.0


class Role(StrEnum):
    EDUCATOR = "educator"
    SUPERVISED = "supervised"
    INDEPENDENT = "independent"


@dataclass(frozen=True, slots=True)
class Viewer:
    """Who a request belongs to, resolved on the server."""

    username: str
    display_name: str
    role: Role


def load_secret(root: Path) -> bytes:
    """Read the signing secret, creating it (readable only by this user) on first start."""
    path = root / "secret.key"
    if not path.exists():
        root.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(secrets.token_hex(32))
    return bytes.fromhex(path.read_text().strip())


@dataclass
class _Failures:
    count: int = 0
    until: float = 0.0  # refuse attempts before this time


class SignIn:
    """Checks passwords and cookies for the student app.

    Args:
        students: The account store.
        passcode: The educator passcode (already checked for length by the caller).
        secret: The cookie-signing secret.
        clock: Seconds since the epoch; injectable for tests.
    """

    def __init__(
        self,
        students: StudentStore,
        passcode: str,
        secret: bytes,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.students = students
        self._passcode = passcode.encode("utf-8")
        self._secret = secret
        self._clock = clock
        self._failures: dict[str, _Failures] = {}
        # changing the passcode changes this, which signs the educator out everywhere
        self._educator_version = hashlib.sha256(self._passcode).hexdigest()[:12]

    # --- cookies -------------------------------------------------------------

    def _sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    def _version(self, username: str) -> str | None:
        """The current session version, or None if the account can't sign in."""
        if username == EDUCATOR:
            return self._educator_version
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
        if username == EDUCATOR:
            return Viewer(EDUCATOR, "Educator", Role.EDUCATOR)
        if not username or not USERNAME_RE.fullmatch(username):
            return None
        try:
            s = self.students.get(username)
        except AccountError:
            return None
        if s.archived:
            return None
        role = Role.SUPERVISED if s.kind is Kind.SUPERVISED else Role.INDEPENDENT
        return Viewer(s.username, s.display_name, role)

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
        if username == EDUCATOR:
            return hmac.compare_digest(password.encode("utf-8"), self._passcode)
        try:
            student = self.students.get(username)
        except AccountError:
            return False
        return not student.archived and verify_password(password, student.password)

    def attempt(self, username: str, password: str) -> tuple[str | None, str]:
        """Try to sign in.

        Returns:
            ``(cookie, "")`` on success, or ``(None, message)``.
        """
        known = username == EDUCATOR or self._version(username) is not None
        f = self._failures.get(username) if known else None
        now = self._clock()
        if f and now < f.until:
            # refused without checking; waiting doesn't extend the delay
            return None, f"Too many tries. Wait {int(f.until - now) + 1} seconds."
        if self._check(username, password):
            self._failures.pop(username, None)
            return self._cookie(username, self._version(username) or ""), ""
        if known:
            f = self._failures.setdefault(username, _Failures())
            f.count += 1
            if f.count >= FREE_FAILURES:
                f.until = now + min(2.0 ** (f.count - FREE_FAILURES), MAX_WAIT)
        return None, "That username and password don't match."
