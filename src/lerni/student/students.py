"""Student accounts on the home server: who can sign in, and their password hashes.

One JSON file per student in ``<data root>/students/``. Passwords are stored
only as scrypt hashes. Accounts are archived in place, never deleted, so a
username is never reused. Standard library only.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

from lerni.student.jsonfiles import write_json_atomic
from lerni.student.plans import default_data_dir

USERNAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
RESERVED = frozenset({"educator", "admin"})
MAX_DISPLAY_NAME = 40
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**15, 8, 3
SCRYPT_MAXMEM = 64 * 1024 * 1024  # above OpenSSL's 32 MiB default


class AccountError(ValueError):
    """An account request is invalid (bad username, short password, unknown account)."""


class Kind(StrEnum):
    SUPERVISED = "supervised"
    INDEPENDENT = "independent"


MIN_PASSWORD = {Kind.SUPERVISED: 4, Kind.INDEPENDENT: 8}


@dataclass(frozen=True, slots=True)
class PasswordHash:
    """An scrypt hash and the parameters to check against it."""

    salt: str  # base64
    hash: str  # base64
    n: int = SCRYPT_N
    r: int = SCRYPT_R
    p: int = SCRYPT_P


@dataclass(frozen=True, slots=True)
class Student:
    """One student account."""

    username: str
    display_name: str
    kind: Kind
    password: PasswordHash
    session_version: int = 1
    explore_freely: date | None = None
    educator: bool = False  # may manage students and the family's plans
    archived: bool = False


def check_username(username: str) -> str:
    """Return ``username`` if it is canonical and not reserved.

    Raises:
        AccountError: Anything else; it is never lowercased or trimmed to fit.

    Example:
        >>> check_username("sam-2")
        'sam-2'
    """
    if not isinstance(username, str) or not USERNAME_RE.fullmatch(username):
        raise AccountError(
            "Usernames are 2–31 lowercase letters, digits, or hyphens, starting with a letter."
        )
    if username in RESERVED:
        raise AccountError(f"{username!r} is reserved.")
    return username


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=SCRYPT_MAXMEM, dklen=32
    )


def hash_password(password: str, kind: Kind) -> PasswordHash:
    """Hash a new password after checking its length for this kind of account.

    Raises:
        AccountError: The password is too short.
    """
    if len(password) < MIN_PASSWORD[kind]:
        raise AccountError(f"Use at least {MIN_PASSWORD[kind]} characters.")
    salt = os.urandom(16)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return PasswordHash(
        salt=base64.b64encode(salt).decode(), hash=base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored: PasswordHash) -> bool:
    """Check ``password`` against a stored hash in constant time."""
    digest = _scrypt(password, base64.b64decode(stored.salt), stored.n, stored.r, stored.p)
    return hmac.compare_digest(digest, base64.b64decode(stored.hash))


def _to_dict(student: Student) -> dict[str, Any]:
    p = student.password
    return {
        "username": student.username,
        "display_name": student.display_name,
        "kind": student.kind.value,
        "password": {"salt": p.salt, "hash": p.hash, "n": p.n, "r": p.r, "p": p.p},
        "session_version": student.session_version,
        "explore_freely": student.explore_freely.isoformat() if student.explore_freely else None,
        "educator": student.educator,
        "archived": student.archived,
    }


def _from_dict(data: dict[str, Any]) -> Student:
    try:
        explore = data.get("explore_freely")
        return Student(
            username=check_username(data["username"]),
            display_name=str(data["display_name"]),
            kind=Kind(data["kind"]),
            password=PasswordHash(**data["password"]),
            session_version=int(data["session_version"]),
            explore_freely=date.fromisoformat(explore) if explore else None,
            educator=bool(data.get("educator", False)),
            archived=bool(data["archived"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AccountError("unreadable account file") from exc


def _display_name(name: str) -> str:
    name = (name or "").strip()
    if not name or len(name) > MAX_DISPLAY_NAME:
        raise AccountError(f"Give a display name of 1–{MAX_DISPLAY_NAME} characters.")
    return name


class StudentStore:
    """Student accounts on disk, one JSON file each, written atomically."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "students"

    def _path(self, username: str) -> Path:
        # canonical usernames only, so a name can never point outside the folder
        return self.root / f"{check_username(username)}.json"

    def _save(self, student: Student) -> Student:
        write_json_atomic(self._path(student.username), _to_dict(student))
        return student

    def list_students(self) -> list[Student]:
        """All accounts, archived last, then by display name."""
        if not self.root.is_dir():
            return []
        students = []
        for path in sorted(self.root.glob("*.json")):
            if not USERNAME_RE.fullmatch(path.stem):
                continue  # temp files (".tmp-*") and anything else that isn't an account
            try:
                students.append(self.get(path.stem))
            except AccountError:
                continue  # one damaged file mustn't hide everyone else
        return sorted(students, key=lambda s: (s.archived, s.display_name.lower()))

    def get(self, username: str) -> Student:
        """Load one account.

        Raises:
            AccountError: Unknown username or an unreadable file.
        """
        path = self._path(username)
        if not path.is_file():
            raise AccountError(f"{username}: no such account")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AccountError(f"{username}: unreadable account file") from exc
        return _from_dict(data)

    def add(
        self, username: str, display_name: str, kind: Kind, password: str, educator: bool = False
    ) -> Student:
        """Create an account. Archived usernames stay taken; only independent accounts educate."""
        if self._path(username).exists():
            raise AccountError(f"{username!r} is taken.")
        if educator and Kind(kind) is not Kind.INDEPENDENT:
            raise AccountError("Only an independent account can be an educator.")
        student = Student(
            username=username,
            display_name=_display_name(display_name),
            kind=Kind(kind),
            password=hash_password(password, Kind(kind)),
            educator=educator,
        )
        return self._save(student)

    def reset_password(self, username: str, new: str) -> Student:
        """The educator's reset: new password, and every device signs out."""
        s = self.get(username)
        return self._save(
            replace(s, password=hash_password(new, s.kind), session_version=s.session_version + 1)
        )

    def change_password(self, username: str, current: str, new: str) -> Student:
        """A student's own change: needs the current password; other devices stay signed in."""
        s = self.get(username)
        if not verify_password(current, s.password):
            raise AccountError("Your current password doesn't match.")
        return self._save(replace(s, password=hash_password(new, s.kind)))

    def rename(self, username: str, display_name: str) -> Student:
        """Change the display name."""
        return self._save(replace(self.get(username), display_name=_display_name(display_name)))

    def set_educator(self, username: str, educator: bool) -> Student:
        """Give or take away educator access (independent accounts only)."""
        s = self.get(username)
        if educator and s.kind is not Kind.INDEPENDENT:
            raise AccountError("Only an independent account can be an educator.")
        return self._save(replace(s, educator=educator, session_version=s.session_version + 1))

    def archive(self, username: str) -> Student:
        """Archive in place: no more sign-ins, every device signs out, the username stays taken."""
        s = self.get(username)
        return self._save(replace(s, archived=True, session_version=s.session_version + 1))
