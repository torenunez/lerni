"""Student accounts on the home server: who can sign in, and their password hashes.

One JSON file per student in ``<data root>/students/``. Passwords are stored
only as scrypt hashes. Accounts are archived in place, never deleted, so a
username is never reused. Standard library only.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import hmac
import json
import os
import re
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from lerni.student.jsonfiles import write_json_atomic

DATA_ENV = "LERNI_STUDENT_DATA"
_WRITE_LOCK = threading.Lock()  # account changes in this process, one at a time

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
    educator: bool = False  # may manage students and the family's plans
    archived: bool = False


def default_data_dir() -> Path:
    """The student app's data folder: ``$LERNI_STUDENT_DATA`` or ``~/.lerni/student``."""
    override = os.environ.get(DATA_ENV)
    return Path(override) if override else Path.home() / ".lerni" / "student"


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
        "educator": student.educator,
        "archived": student.archived,
    }


def _from_dict(data: dict[str, Any]) -> Student:
    try:
        return Student(
            username=check_username(data["username"]),
            display_name=str(data["display_name"]),
            kind=Kind(data["kind"]),
            password=PasswordHash(**data["password"]),
            session_version=int(data["session_version"]),
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

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """One account change at a time, across threads and processes (server and CLI)."""
        self.root.mkdir(parents=True, exist_ok=True)
        with _WRITE_LOCK, open(self.root / ".lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)  # released when the file closes
            yield

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
        with self._locked():  # two adds of one name can't both succeed
            return self._add(username, display_name, kind, password, educator)

    def _add(
        self, username: str, display_name: str, kind: Kind, password: str, educator: bool
    ) -> Student:
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

    def _update(self, username: str, change: Callable[[Student], Student]) -> Student:
        """Read, change, and write one account with no other write in between."""
        with self._locked():  # so a rename can't undo an archive or reset made meanwhile
            return self._save(change(self.get(username)))

    def reset_password(self, username: str, new: str) -> Student:
        """The educator's reset: new password, and every device signs out."""
        return self._update(username, lambda s: replace(
            s, password=hash_password(new, s.kind), session_version=s.session_version + 1
        ))

    def change_password(self, username: str, current: str, new: str) -> Student:
        """A student's own change: needs the current password; other devices stay signed in."""
        def change(s: Student) -> Student:
            if not verify_password(current, s.password):
                raise AccountError("Your current password doesn't match.")
            return replace(s, password=hash_password(new, s.kind))

        return self._update(username, change)

    def rename(self, username: str, display_name: str) -> Student:
        """Change the display name."""
        name = _display_name(display_name)
        return self._update(username, lambda s: replace(s, display_name=name))

    def set_educator(self, username: str, educator: bool) -> Student:
        """Give or take away educator access (independent accounts only)."""
        def change(s: Student) -> Student:
            if educator and s.kind is not Kind.INDEPENDENT:
                raise AccountError("Only an independent account can be an educator.")
            if educator and s.archived:
                raise AccountError(f"{username} is archived.")
            return replace(s, educator=educator, session_version=s.session_version + 1)

        return self._update(username, change)

    def archive(self, username: str) -> Student:
        """Archive in place: no more sign-ins, every device signs out, the username stays taken."""
        return self._update(
            username, lambda s: replace(s, archived=True, session_version=s.session_version + 1)
        )
