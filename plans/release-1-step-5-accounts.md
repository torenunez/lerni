# Release 1, step 5: accounts and one sign-in — implementation plan

> **Superseded in part (history).** Built and merged in PR #8, with one change: there is no `educator` login or passcode. Educator access is a permission on an independent account, set with `lerni student educator`. The [spec](specs/03-student-accounts.md) and the code are current.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Everyone signs in to one Lerni app on the home server, with a sign-in form Safari can save, re-checked on every request, and tabs that depend on who signed in.

**Architecture:** Two new standard-library core modules: `students.py` (accounts and password hashes, stored as JSON) and `signin.py` (password checks with wrong-password delays, a signed cookie, and resolving a request to a viewer). A small FastAPI sign-in page sets the cookie; Gradio's `auth_dependency` re-checks it on every request. One Gradio app at `/app/` shows tabs by role; every handler re-resolves the viewer on the server.

**Tech Stack:** Python 3.11+, standard library (`hashlib.scrypt`, `hmac`, `secrets`), FastAPI (already a Gradio dependency, with `python-multipart` for forms), Gradio 6.30.

**Spec:** [plans/specs/03-student-accounts.md](specs/03-student-accounts.md) (sections "Who can do what", "Sign-in", "Accounts and passwords", "Data", "Tabs"). The step: [Release 1 plan, step 5](release-1-mvp.md#to-build).

## Global Constraints

- Core modules (`students.py`, `signin.py`, `jsonfiles.py`) import only the standard library and `lerni.student` (ARCHITECTURE boundary 8; `tests/student/test_core_imports.py` enforces it).
- Usernames match `^[a-z][a-z0-9-]{1,30}$`; never normalize-and-accept. Reserved: `educator`, `admin`. Never reused (archive in place).
- Passwords: at least 8 characters for independent accounts, 4 for supervised; educator passcode at least 8, checked when the server starts.
- scrypt: `n=2**15, r=8, p=3`, 16-byte salt from `os.urandom`, `maxmem=64 * 1024 * 1024`; compare with `hmac.compare_digest`.
- Wrong passwords: after 3 in a row for a known username (or `educator`), further attempts are refused without checking for 1, 2, 4, … up to 30 seconds; attempts during a wait don't extend it; success resets. Unknown usernames: no tracking. Signed-in sessions are never affected.
- Cookie `lerni_session`: `HttpOnly`, `SameSite=Lax`, `Max-Age` 30 days, `path=/`, not `Secure` (plain HTTP until Release 3). Value: `username.issued.version.signature`, HMAC-SHA256 with the secret in `<data root>/secret.key` (mode 600).
- Archive and password reset bump `session_version`, so every device signs out at once. A student's own password change doesn't (other devices stay signed in).
- Every event `api_visibility="private"`; every handler resolves the viewer from `request.username` by re-reading the record; nothing per-user is built into the layout.
- Tests use fakes, no network, minimal (CLAUDE.md rule 4). Vocabulary rule 1; no private details (rule 8). Update `docs/code-manifest.md` for every new code or test file (rule 9).

## Review Focus

- **A wrong account on the shared iPad:** the header must always say who is signed in, and Sign out must work from every tab. (Covered in Task 4's manual check and the header test.)
- **A signed-out page load:** `/app/` without a cookie must land on `/signin`, not a raw 401 JSON page. (Task 3 test.)
- **Uppercase or spaced usernames typed on an iPad keyboard** (iOS capitalizes the first letter): the form sets `autocapitalize="none"` and `autocorrect="off"`, and a refused username says why. (Task 3 form markup; Task 1 test refuses `Sam`.)
- **A queued action after archive:** a handler that runs after the account was archived must refuse, not act. Handlers re-read the record. (Task 4 test calls a handler for an archived viewer.)
- **The first start with no accounts:** only `educator` can sign in, and the Students tab must work with an empty list. (Task 4 test.)

---

### Task 1: Accounts (`students.py`) and the shared JSON writer

**Files:**
- Create: `src/lerni/student/jsonfiles.py`
- Create: `src/lerni/student/students.py`
- Modify: `src/lerni/student/plans.py` (use `write_json_atomic` in `PlanStore.save`)
- Modify: `tests/student/test_core_imports.py` (add the new core modules to its list)
- Test: `tests/student/test_students.py`
- Modify: `docs/code-manifest.md`

**Interfaces:**
- Produces: `write_json_atomic(path: Path, data: dict[str, Any]) -> None`; `Kind` (`SUPERVISED`, `INDEPENDENT`); `Student`; `AccountError`; `check_username(username: str) -> str`; `verify_password(password: str, stored: PasswordHash) -> bool`; `StudentStore(root: Path | None = None)` with `list_students() -> list[Student]`, `get(username) -> Student`, `add(username, display_name, kind, password) -> Student`, `reset_password(username, new) -> Student`, `change_password(username, current, new) -> Student`, `rename(username, display_name) -> Student`, `archive(username) -> Student`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/student/test_students.py
"""Student accounts: saved, checked, and refused when the username isn't canonical."""

import pytest

from lerni.student.students import AccountError, Kind, StudentStore, verify_password


def test_account_saves_loads_and_checks_its_password(tmp_path):
    store = StudentStore(tmp_path)
    store.add("sam", "Sam", Kind.INDEPENDENT, "correct horse")
    sam = store.get("sam")
    assert sam.kind is Kind.INDEPENDENT and sam.display_name == "Sam"
    assert verify_password("correct horse", sam.password)
    assert not verify_password("wrong", sam.password)
    reset = store.reset_password("sam", "another pass")
    assert reset.session_version == sam.session_version + 1  # signs out every device


@pytest.mark.parametrize("username", ["Sam", "../x", "", "educator", "admin", "s", "9lives"])
def test_bad_or_reserved_usernames_are_refused(tmp_path, username):
    with pytest.raises(AccountError):
        StudentStore(tmp_path).add(username, "X", Kind.SUPERVISED, "1234")


def test_archived_username_is_never_reused(tmp_path):
    store = StudentStore(tmp_path)
    store.add("sam", "Sam", Kind.SUPERVISED, "1234")
    store.archive("sam")
    assert store.get("sam").archived
    with pytest.raises(AccountError):
        store.add("sam", "Sam again", Kind.SUPERVISED, "1234")
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/student/test_students.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'lerni.student.students'`.

- [ ] **Step 3: Write the shared writer**

```python
# src/lerni/student/jsonfiles.py
"""Atomic JSON writes shared by the plan and student stores. Standard library only."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Write ``data`` as pretty JSON to ``path`` without ever leaving half a file.

    Args:
        path: The destination; its folder is created if needed.
        data: A JSON-ready dict.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # write to a temp file in the same folder, then swap it in
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
```

In `plans.py`, replace the body of `PlanStore.save` after `path = self._path(saved.plan_id)` with `write_json_atomic(path, data)` and `return saved`; drop the now-unused `tempfile` import (keep `os` and `secrets`, still used by `archive`).

- [ ] **Step 4: Write the accounts module**

```python
# src/lerni/student/students.py
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
        students = [self.get(p.stem) for p in sorted(self.root.glob("*.json"))]
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

    def add(self, username: str, display_name: str, kind: Kind, password: str) -> Student:
        """Create an account. Archived usernames stay taken."""
        if self._path(username).exists():
            raise AccountError(f"{username!r} is taken.")
        student = Student(
            username=username,
            display_name=_display_name(display_name),
            kind=Kind(kind),
            password=hash_password(password, Kind(kind)),
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

    def archive(self, username: str) -> Student:
        """Archive in place: no more sign-ins, every device signs out, the username stays taken."""
        s = self.get(username)
        return self._save(replace(s, archived=True, session_version=s.session_version + 1))
```

Add `"jsonfiles"` and `"students"` to the module list in `tests/student/test_core_imports.py`.

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m pytest tests/student/test_students.py tests/student/test_plans.py tests/student/test_core_imports.py -q`
Expected: all pass.

- [ ] **Step 6: Manifest and commit**

Add to `docs/code-manifest.md`, core table: `src/lerni/student/students.py` — "Student accounts: usernames, kinds, scrypt password hashes, and `StudentStore` (one JSON file per student; archived in place, never reused)." and `src/lerni/student/jsonfiles.py` — "Writes a JSON file atomically; shared by the plan and student stores." Tests table: `tests/student/test_students.py` — "An account saves and checks its password; bad, reserved, and archived usernames are refused."

```bash
git add src/lerni/student/jsonfiles.py src/lerni/student/students.py src/lerni/student/plans.py tests/student/test_students.py tests/student/test_core_imports.py docs/code-manifest.md
git commit -m "Step 5: student accounts and the shared JSON writer"
```

---

### Task 2: Sign-in logic (`signin.py`): password checks, delays, signed cookie, viewer

**Files:**
- Create: `src/lerni/student/signin.py`
- Modify: `tests/student/test_core_imports.py` (add `"signin"`)
- Test: `tests/student/test_signin.py`
- Modify: `docs/code-manifest.md`

**Interfaces:**
- Consumes: `StudentStore`, `Student`, `Kind`, `AccountError`, `verify_password`, `USERNAME_RE` (Task 1).
- Produces: `COOKIE_NAME = "lerni_session"`, `SESSION_SECONDS`, `EDUCATOR = "educator"`, `Role` (`EDUCATOR`, `SUPERVISED`, `INDEPENDENT`), `Viewer(username, display_name, role)`, `load_secret(root: Path) -> bytes`, `SignIn(students, passcode, secret, clock=time.time)` with `attempt(username, password) -> tuple[str | None, str]` (cookie value or `None`, and a message), `viewer_from_cookie(value: str | None) -> Viewer | None`, `viewer(username: str | None) -> Viewer | None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/student/test_signin.py
"""Sign-in: cookies are re-checked against the account, and wrong passwords slow down."""

from lerni.student.signin import Role, SignIn
from lerni.student.students import Kind, StudentStore


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


def make(tmp_path):
    store = StudentStore(tmp_path)
    store.add("sam", "Sam", Kind.INDEPENDENT, "correct horse")
    clock = Clock()
    return store, SignIn(store, "educator-pass", b"k" * 32, clock=clock), clock


def test_cookie_works_until_reset_or_archive(tmp_path):
    store, signin, _ = make(tmp_path)
    cookie, _ = signin.attempt("sam", "correct horse")
    assert signin.viewer_from_cookie(cookie).role is Role.INDEPENDENT
    store.reset_password("sam", "new password")
    assert signin.viewer_from_cookie(cookie) is None  # every device signed out
    assert signin.viewer_from_cookie("sam.1.1.forged") is None
    educator, _ = signin.attempt("educator", "educator-pass")
    assert signin.viewer_from_cookie(educator).role is Role.EDUCATOR


def test_wrong_passwords_wait_without_touching_signed_in_sessions(tmp_path):
    _, signin, clock = make(tmp_path)
    cookie, _ = signin.attempt("sam", "correct horse")
    for _ in range(3):
        assert signin.attempt("sam", "nope")[0] is None
    refused, message = signin.attempt("sam", "correct horse")  # inside the wait
    assert refused is None and "wait" in message.lower()
    assert signin.viewer_from_cookie(cookie) is not None  # existing session unaffected
    clock.now += 2
    assert signin.attempt("sam", "correct horse")[0] is not None
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/student/test_signin.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'lerni.student.signin'`.

- [ ] **Step 3: Write the module**

```python
# src/lerni/student/signin.py
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
        """Resolve a cookie: valid signature, not expired, and the account's version still matches."""
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
```

Add `"signin"` to the module list in `tests/student/test_core_imports.py`.

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/student/test_signin.py tests/student/test_core_imports.py -q`
Expected: pass.

- [ ] **Step 5: Manifest and commit**

Manifest, core table: `src/lerni/student/signin.py` — "Signing in: checks passwords (with growing waits after wrong ones), issues a signed cookie, and re-reads the account on every request, so archive and reset sign out every device." Tests table: `tests/student/test_signin.py` — "A cookie stops working after a reset; wrong passwords wait without signing anyone out."

```bash
git add src/lerni/student/signin.py tests/student/test_signin.py tests/student/test_core_imports.py docs/code-manifest.md
git commit -m "Step 5: sign-in checks, signed cookie, wrong-password delays"
```

---

### Task 3: The sign-in page, one app at `/app/`, and the server

**Files:**
- Create: `src/lerni/student/web/signin_page.py`
- Modify: `src/lerni/student/web/app.py` (one mount at `/app` with `auth_dependency`; the sign-in routes; drop `passcode_checker` and the `/educator` mount)
- Modify: `src/lerni/student/web/serve.py` (passcode at least 8; print the new URLs)
- Delete: `tests/student/test_web_skeleton.py`
- Test: `tests/student/test_web_signin.py`
- Modify: `docs/code-manifest.md`

**Interfaces:**
- Consumes: `SignIn`, `COOKIE_NAME`, `SESSION_SECONDS`, `load_secret` (Task 2); `StudentStore` (Task 1).
- Produces: `APP_PATH = "/app"`; `add_signin_routes(app: FastAPI, signin: SignIn) -> None`; `build_app(passcode: str, *, data_root: Path | None = None, store: PlanStore | None = None, catalog: PackageLessonCatalog | None = None, drafter: PlanDrafter | None = None) -> FastAPI`; `build_main_view(signin, store, catalog, students, drafter) -> gr.Blocks` (stubbed here, filled in Task 4).

- [ ] **Step 1: Write the failing tests**

```python
# tests/student/test_web_signin.py
"""The one app: signed-out visits go to the sign-in form; a cookie opens the app."""

import pytest

pytest.importorskip("gradio")

from fastapi.testclient import TestClient  # noqa: E402

from lerni.student.students import Kind, StudentStore  # noqa: E402
from lerni.student.web.app import build_app  # noqa: E402

PASSCODE = "test-passcode"


@pytest.fixture
def client(tmp_path):
    StudentStore(tmp_path).add("sam", "Sam", Kind.SUPERVISED, "1234")
    return TestClient(build_app(PASSCODE, data_root=tmp_path), follow_redirects=False)


def sign_in(client, username, password):
    return client.post("/signin", data={"username": username, "password": password})


def test_signed_out_visits_go_to_the_sign_in_form(client):
    assert client.get("/app/").headers["location"] == "/signin"
    form = client.get("/signin").text
    assert 'autocomplete="current-password"' in form and "<form" in form
    assert client.get("/app/config").status_code == 401


def test_a_right_password_opens_the_app_and_sign_out_ends_it(client):
    assert sign_in(client, "sam", "nope").status_code == 401
    response = sign_in(client, "sam", "1234")
    assert response.status_code == 303 and response.headers["location"] == "/app/"
    assert client.get("/app/config").status_code == 200
    client.get("/signout")
    assert client.get("/app/config").status_code == 401


def test_short_educator_passcode_is_refused(tmp_path):
    with pytest.raises(ValueError):
        build_app("short", data_root=tmp_path)
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/student/test_web_signin.py -q`
Expected: FAIL (`build_app()` has no `data_root`, and `/signin` returns 404).

- [ ] **Step 3: Write the sign-in page**

```python
# src/lerni/student/web/signin_page.py
"""The sign-in page: a plain HTML form Safari and Keychain can save.

It posts normally (no script), sets the signed ``lerni_session`` cookie, and
sends the browser to the app. Signed-out visits to the app come here.
"""

from __future__ import annotations

from html import escape

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from lerni.student.signin import COOKIE_NAME, SESSION_SECONDS, SignIn

APP_PATH = "/app"

# System fonts and inline CSS only, so the iPad loads nothing from outside.
_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lerni: sign in</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; margin: 0; min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #ffe17a 0%, #ff9fb2 45%, #8fd3ff 100%); color: #1b1340; }}
form {{ background: rgba(255,255,255,.85); padding: 2rem; border-radius: 24px;
  width: min(90vw, 360px); display: flex; flex-direction: column; gap: .8rem; }}
h1 {{ margin: 0 0 .5rem; font-size: 2.2rem; }}
label {{ font-weight: 600; }}
input {{ font-size: 1.3rem; padding: .6rem; border-radius: 12px; border: 1px solid #999; }}
button {{ font-size: 1.3rem; padding: .7rem; border-radius: 999px; border: 0;
  background: #1b1340; color: white; font-weight: 700; }}
.error {{ color: #a10000; }}
</style></head><body>
<form method="post" action="/signin">
  <h1>👋 Lerni</h1>
  <p class="error" role="alert">{message}</p>
  <label for="username">Username</label>
  <input id="username" name="username" autocomplete="username" autocapitalize="none"
    autocorrect="off" spellcheck="false" required>
  <label for="password">Password</label>
  <input id="password" name="password" type="password" autocomplete="current-password" required>
  <button type="submit">Sign in</button>
  <p>No account yet? Ask your educator.</p>
</form></body></html>"""


def _page(message: str = "", status: int = 200) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(message=escape(message)), status_code=status)


def add_signin_routes(app: FastAPI, signin: SignIn) -> None:
    """Add ``/``, ``/signin``, ``/signout``, and the signed-out redirect for the app page."""

    @app.middleware("http")
    async def signed_out_to_signin(request: Request, call_next):  # type: ignore[no-untyped-def]
        # only the app's page itself redirects; its API calls get Gradio's 401
        if request.method == "GET" and request.url.path in (APP_PATH, APP_PATH + "/"):
            if signin.viewer_from_cookie(request.cookies.get(COOKIE_NAME)) is None:
                return RedirectResponse("/signin", status_code=303)
        return await call_next(request)

    @app.get("/")
    def root(request: Request) -> Response:
        signed_in = signin.viewer_from_cookie(request.cookies.get(COOKIE_NAME))
        return RedirectResponse(APP_PATH + "/" if signed_in else "/signin", status_code=303)

    @app.get("/signin")
    def signin_form() -> HTMLResponse:
        return _page()

    @app.post("/signin")
    def signin_submit(username: str = Form(""), password: str = Form("")) -> Response:
        cookie, message = signin.attempt(username, password)
        if cookie is None:
            return _page(message, status=401)
        response = RedirectResponse(APP_PATH + "/", status_code=303)
        response.set_cookie(
            COOKIE_NAME, cookie, max_age=SESSION_SECONDS, httponly=True, samesite="lax", path="/"
        )
        return response

    @app.get("/signout")
    def signout() -> Response:
        # this device only; other devices stay signed in
        response = RedirectResponse("/signin", status_code=303)
        response.delete_cookie(COOKIE_NAME, path="/")
        return response
```

- [ ] **Step 4: Rewire `app.py`**

Replace the module docstring, `EDUCATOR_PATH`, `EDUCATOR_USERNAME`, `passcode_checker`, `_student_screen`, and `build_app` with the following (keep `_SYSTEM_FONTS`, `_MONO_FONTS`, `_CSS`, `_WELCOME_HTML`, `_MOUNT_OPTIONS`, `_theme`):

```python
"""Build the student app: a sign-in page and one Gradio app with tabs by role.

Signed-out visits go to ``/signin``; the app lives at ``/app/``. Gradio's
``auth_dependency`` re-checks the signed cookie on every request, and every
handler re-resolves the viewer. See the trust boundaries in
``docs/ARCHITECTURE.md``.
"""
```

```python
MIN_PASSCODE = 8


def build_app(
    passcode: str,
    *,
    data_root: Path | None = None,
    store: PlanStore | None = None,
    catalog: PackageLessonCatalog | None = None,
    drafter: PlanDrafter | None = None,
) -> FastAPI:
    """Build the server: the sign-in page and the app at ``/app/``.

    Args:
        passcode: The educator passcode, already read from the environment.
        data_root: The home server's data folder; defaults to ``$LERNI_STUDENT_DATA``
            or ``~/.lerni/student``.
        store: Learning plans; defaults to the plan folder under ``data_root``.
        catalog: Packaged activities; defaults to the ones shipped with Lerni.
        drafter: Claude behind an adapter for imports; ``None`` turns imports off.

    Raises:
        ValueError: The passcode is shorter than 8 characters.
    """
    if len(passcode) < MIN_PASSCODE:
        raise ValueError(f"The educator passcode needs at least {MIN_PASSCODE} characters.")
    root = data_root or default_data_dir()
    students = StudentStore(root)
    signin = SignIn(students, passcode, load_secret(root))
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    add_signin_routes(app, signin)

    def current_user(request: Request) -> str | None:
        # runs on every request: no valid cookie, no access
        viewer = signin.viewer_from_cookie(request.cookies.get(COOKIE_NAME))
        return viewer.username if viewer else None

    view = build_main_view(
        signin, store or PlanStore(root), catalog or PackageLessonCatalog(), students, drafter
    )
    return gr.mount_gradio_app(
        app, view, path=APP_PATH, auth_dependency=current_user,
        theme=_theme(), css=_CSS, **_MOUNT_OPTIONS,
    )
```

Imports to add: `from pathlib import Path`, `from fastapi import FastAPI, Request`, `from lerni.student.plans import PlanStore, default_data_dir`, `from lerni.student.signin import COOKIE_NAME, SignIn, load_secret`, `from lerni.student.students import StudentStore`, `from lerni.student.web.main import build_main_view`, `from lerni.student.web.signin_page import APP_PATH, add_signin_routes`. Remove `hmac`, `TYPE_CHECKING`/`Callable`, and the `build_educator_view` import.

Create `src/lerni/student/web/main.py` with a stub so this task runs on its own (Task 4 fills it in):

```python
"""The one app's page: a header, then tabs by role. Filled in by Task 4."""

from __future__ import annotations

import gradio as gr


def build_main_view(signin, store, catalog, students, drafter) -> gr.Blocks:  # type: ignore[no-untyped-def]
    """Build the app's page (temporary: a header only)."""
    with gr.Blocks(title="Lerni", analytics_enabled=False) as blocks:
        gr.Markdown("Lerni")
    return blocks
```

- [ ] **Step 5: Update `serve.py`**

In `serve()`: after `passcode = resolve_passcode(passcode_env)`, build with `app = build_app(passcode, drafter=drafter)` (it raises `ValueError` for a short passcode; let `commands/serve.py` show it: wrap its call in `except ValueError as exc: typer.echo(str(exc), err=True); raise typer.Exit(1)`). Replace the two URL lines with:

```python
    print(f"Sign in:  http://<this-computer>:{port}/", flush=True)
    print("Educator: username 'educator' and the passcode. Students: their own username.", flush=True)
```

and drop the `EDUCATOR_PATH` import.

- [ ] **Step 6: Run the tests, delete the old skeleton test**

```bash
git rm tests/student/test_web_skeleton.py
.venv/bin/python -m pytest tests/student -q
```
Expected: all pass (the new web tests included).

- [ ] **Step 7: Manifest and commit**

Manifest: update the `app.py` and `serve.py` rows to describe the one app at `/app/` behind the sign-in page; add `web/signin_page.py` — "The sign-in page: a plain HTML form Safari can save, the signed cookie, Sign out (this device only), and sending signed-out visits to it." and `web/main.py` — "The one app's page: the header and the tabs by role." Replace the `test_web_skeleton.py` row with `tests/student/test_web_signin.py` — "Signed-out visits go to the sign-in form; a right password opens the app; Sign out ends it; a short passcode is refused."

```bash
git add -A src/lerni/student/web src/lerni/commands/serve.py tests/student docs/code-manifest.md
git commit -m "Step 5: sign-in page and one app at /app/"
```

---

### Task 4: Tabs by role, the Students tab, My account, and role checks

**Files:**
- Modify: `src/lerni/student/web/main.py` (the real page)
- Create: `src/lerni/student/web/accounts.py` (Students and My account handlers and tabs)
- Modify: `src/lerni/student/web/educator.py` (tabs built inside the main page; handlers check the educator role; lists load per request; "kids'" removed from `IMPORT_TIPS`)
- Test: `tests/student/test_web_roles.py`
- Modify: `docs/code-manifest.md`

**Interfaces:**
- Consumes: `SignIn.viewer`, `Viewer`, `Role` (Task 2); `StudentStore`, `Kind`, `AccountError` (Task 1).
- Produces:
  - `web/accounts.py`: `NotAllowed(Exception)`; `require(viewer: Viewer | None, *roles: Role) -> Viewer`; `student_rows(students: StudentStore) -> list[list[str]]`; `add_student(students, viewer, username, display_name, kind, password) -> str`; `reset_student(students, viewer, username, password) -> str`; `archive_student(students, viewer, username) -> str`; `change_own_password(students, viewer, current, new) -> str`; `rename_self(students, viewer, display_name) -> str`; `students_tab(signin, students) -> tuple[gr.Tab, gr.Dataframe]` and `account_tab(signin, students) -> gr.Tab` (Gradio wiring, called inside a `gr.Tabs()` block).
  - `web/educator.py`: `educator_tabs(signin, store, catalog, drafter) -> tuple[list[gr.Tab], gr.Dropdown, gr.Markdown]` (builds Guide, Sessions, Learning plans inside the caller's `gr.Tabs()`; returns the three tabs plus the plan dropdown and the Sessions text, which `main.py` fills on load). The old `build_educator_view` goes away.
  - `web/main.py`: `build_main_view(signin, store, catalog, students, drafter) -> gr.Blocks`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/student/test_web_roles.py
"""Tabs by role: educator actions refuse students, and the page config carries no user data."""

import pytest

pytest.importorskip("gradio")

from fastapi.testclient import TestClient  # noqa: E402

from lerni.student.signin import Role, Viewer  # noqa: E402
from lerni.student.students import Kind, StudentStore  # noqa: E402
from lerni.student.web.accounts import NotAllowed, add_student, archive_student  # noqa: E402
from lerni.student.web.app import build_app  # noqa: E402

EDUCATOR = Viewer("educator", "Educator", Role.EDUCATOR)
SAM = Viewer("sam", "Sam", Role.INDEPENDENT)


def test_students_can_not_manage_accounts(tmp_path):
    students = StudentStore(tmp_path)
    assert "Added" in add_student(students, EDUCATOR, "sam", "Sam", "independent", "long enough")
    with pytest.raises(NotAllowed):
        add_student(students, SAM, "eve", "Eve", "independent", "long enough")
    with pytest.raises(NotAllowed):
        archive_student(students, None, "sam")  # an archived or unknown viewer resolves to None
    assert students.list_students()[0].username == "sam"


def test_page_config_carries_no_plans_or_usernames(tmp_path):
    students = StudentStore(tmp_path)
    students.add("sam", "Sam", Kind.SUPERVISED, "1234")
    students.add("eve", "Eve", Kind.INDEPENDENT, "long enough")
    client = TestClient(build_app("test-passcode", data_root=tmp_path))
    client.post("/signin", data={"username": "sam", "password": "1234"})
    config = client.get("/app/config").text  # Gradio adds the viewer's own username; fine
    for leaked in ("cars-", "sharks-", "eve", "Eve"):
        assert leaked not in config
```

(The seeded example plans have ids starting `cars-` and `sharks-`; today `plan_choices(store)` is built into the layout, so they'd leak.)

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/student/test_web_roles.py -q`
Expected: FAIL (`lerni.student.web.accounts` doesn't exist).

- [ ] **Step 3: Write `web/accounts.py`**

```python
"""Accounts in the app: the educator's Students tab and an independent student's My account.

Handlers are plain functions that take the viewer, resolved on the server,
so role checks can be tested without a browser.
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import AccountError, Kind, StudentStore

PRIVATE = {"api_visibility": "private"}
STUDENT_COLUMNS = ["Username", "Display name", "Kind", "Status"]


class NotAllowed(Exception):
    """The signed-in viewer may not do this."""


def require(viewer: Viewer | None, *roles: Role) -> Viewer:
    """Return ``viewer`` if it has one of ``roles``; refuse a missing or archived one."""
    if viewer is None or viewer.role not in roles:
        raise NotAllowed("You can't do that from this account.")
    return viewer


def student_rows(students: StudentStore) -> list[list[str]]:
    """The Students table: names and kinds only, never plans or sessions."""
    return [
        [s.username, s.display_name, s.kind.value, "archived" if s.archived else "active"]
        for s in students.list_students()
    ] or [["", "No students yet.", "", ""]]


def add_student(
    students: StudentStore, viewer: Viewer | None, username: str, display_name: str,
    kind: str, password: str,
) -> str:
    require(viewer, Role.EDUCATOR)
    s = students.add(username, display_name, Kind(kind), password)
    return f"✅ Added {s.display_name} ({s.kind.value})."


def reset_student(students: StudentStore, viewer: Viewer | None, username: str, password: str) -> str:
    require(viewer, Role.EDUCATOR)
    students.reset_password(username, password)
    return f"✅ New password set for {username}. Their devices are signed out."


def archive_student(students: StudentStore, viewer: Viewer | None, username: str) -> str:
    require(viewer, Role.EDUCATOR)
    students.archive(username)
    return f"✅ Archived {username}. They can't sign in, and the username stays taken."


def change_own_password(
    students: StudentStore, viewer: Viewer | None, current: str, new: str
) -> str:
    v = require(viewer, Role.INDEPENDENT)
    students.change_password(v.username, current, new)
    return "✅ Password changed."


def rename_self(students: StudentStore, viewer: Viewer | None, display_name: str) -> str:
    v = require(viewer, Role.INDEPENDENT)
    students.rename(v.username, display_name)
    return "✅ Name changed."


def _run(fn: Any, *args: Any) -> str:
    """Call a handler and turn refusals into a message for the screen."""
    try:
        return fn(*args)
    except (NotAllowed, AccountError) as exc:
        return f"⚠️ {exc}"


def students_tab(signin: SignIn, students: StudentStore) -> tuple[gr.Tab, gr.Dataframe]:
    """The educator's Students tab (hidden for everyone else)."""
    with gr.Tab("Students", visible=False) as tab:
        table = gr.Dataframe(headers=STUDENT_COLUMNS, interactive=False, type="array")
        gr.Markdown("### Add a student")
        username = gr.Textbox(label="Username (lowercase, e.g. sam)")
        display = gr.Textbox(label="Display name (a nickname is fine)")
        kind = gr.Radio(["supervised", "independent"], value="supervised", label="Kind")
        password = gr.Textbox(label="Starting password (4+ for supervised, 8+ for independent)",
                              type="password")
        add_btn = gr.Button("Add student", variant="primary")
        gr.Markdown("### Reset a password or archive")
        who = gr.Textbox(label="Username")
        new_password = gr.Textbox(label="New password", type="password")
        with gr.Row():
            reset_btn = gr.Button("Reset password")
            archive_btn = gr.Button("Archive", variant="stop")
        status = gr.Markdown()

        def viewer(request: gr.Request) -> Viewer | None:
            return signin.viewer(request.username)

        def on_add(u: str, d: str, k: str, p: str, request: gr.Request) -> list[Any]:
            message = _run(add_student, students, viewer(request), u.strip(), d, k, p)
            return [message, student_rows(students)]

        def on_reset(u: str, p: str, request: gr.Request) -> list[Any]:
            return [_run(reset_student, students, viewer(request), u.strip(), p), student_rows(students)]

        def on_archive(u: str, request: gr.Request) -> list[Any]:
            return [_run(archive_student, students, viewer(request), u.strip()), student_rows(students)]

        add_btn.click(on_add, [username, display, kind, password], [status, table], **PRIVATE)
        reset_btn.click(on_reset, [who, new_password], [status, table], **PRIVATE)
        archive_btn.click(on_archive, who, [status, table], **PRIVATE)
    return tab, table  # main.py fills the table on page load


def account_tab(signin: SignIn, students: StudentStore) -> gr.Tab:
    """An independent student's My account tab (hidden for everyone else)."""
    with gr.Tab("My account", visible=False) as tab:
        name = gr.Textbox(label="Display name")
        name_btn = gr.Button("Change name")
        current = gr.Textbox(label="Current password", type="password")
        new = gr.Textbox(label="New password (8+ characters)", type="password")
        pw_btn = gr.Button("Change password", variant="primary")
        status = gr.Markdown()

        def on_name(d: str, request: gr.Request) -> str:
            return _run(rename_self, students, signin.viewer(request.username), d)

        def on_password(c: str, n: str, request: gr.Request) -> str:
            return _run(change_own_password, students, signin.viewer(request.username), c, n)

        name_btn.click(on_name, name, status, **PRIVATE)
        pw_btn.click(on_password, [current, new], status, **PRIVATE)
    return tab
```

- [ ] **Step 4: Change `educator.py`**

1. Rename `build_educator_view(store, catalog, drafter)` to `educator_tabs(signin, store, catalog, drafter) -> list[gr.Tab]`. Remove its `with gr.Blocks(...)`, `gr.Markdown("## Educator view")`, and `with gr.Tabs():` wrappers; the three `gr.Tab(...)` blocks are now created directly inside the caller's `gr.Tabs()`. Give `Sessions` and `Learning plans` `visible=False`; `Guide` stays visible (both educator and independent students see it; supervised students get it hidden by `main.py`). Bind each tab (`with gr.Tab("Guide") as guide_tab:` and so on).
2. Build nothing from data into the layout: `plan_dd = gr.Dropdown(label="Plan", choices=[], scale=3)` and `sessions = gr.Markdown()` (filled on load by `main.py`, see Step 5).
3. Add `request: gr.Request` as the last parameter of every handler (`on_import`, `on_keep`, `on_drop`, `show_plan`, `on_new`, `on_copy`, `on_archive`, `on_save`, `show_card`, `refresh_answer`, `on_save_card`) and make each start with:

```python
            if not _is_educator(signin, request):
                return _refuse(n)  # n = the number of outputs of this handler
```

with these two helpers defined at module level:

```python
def _is_educator(signin: SignIn, request: gr.Request) -> bool:
    """True only for the educator, re-read from the server on every call."""
    viewer = signin.viewer(request.username)
    return viewer is not None and viewer.role is Role.EDUCATOR


def _refuse(outputs: int) -> Any:
    """Leave every output unchanged when a non-educator calls an educator handler."""
    return gr.update() if outputs == 1 else [gr.update()] * outputs
```

(Step 6 of the spec opens Learning plans to independent students, scoped by owner; until then only the educator passes.)
4. In `IMPORT_TIPS`, replace "kids' ocean encyclopedia" with "an ocean encyclopedia".
5. Return the tabs and two load targets: change the return to `return [guide_tab, sessions_tab, plans_tab], plan_dd, sessions` and add `-> tuple[list[gr.Tab], gr.Dropdown, gr.Markdown]`.

- [ ] **Step 5: Write `web/main.py`**

```python
"""The one app's page: who's signed in, then tabs by role.

Tabs start hidden and are shown on load for the signed-in viewer; nothing
per-user or from the data is built into the layout, because Gradio sends
every signed-in browser the same page config.
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from lerni.student.catalog import PackageLessonCatalog
from lerni.student.plan_import import PlanDrafter
from lerni.student.plans import PlanStore
from lerni.student.signin import Role, SignIn
from lerni.student.students import StudentStore
from lerni.student.web.accounts import account_tab, student_rows, students_tab
from lerni.student.web.educator import educator_tabs, plan_choices, sessions_text


def build_main_view(
    signin: SignIn,
    store: PlanStore,
    catalog: PackageLessonCatalog,
    students: StudentStore,
    drafter: PlanDrafter | None,
    welcome_html: str = "",
    independent_html: str = "",
) -> gr.Blocks:
    """Build the page; the tabs each viewer sees are set on load."""
    store.seed_if_empty()  # first run: copy in the example plans
    with gr.Blocks(title="Lerni", analytics_enabled=False) as blocks:
        header = gr.Markdown()
        with gr.Tabs():
            with gr.Tab("Learn", visible=False) as learn_tab:
                waiting = gr.HTML(welcome_html, visible=False)
                independent = gr.HTML(independent_html, visible=False)
            (guide_tab, sessions_tab, plans_tab), plan_dd, sessions = educator_tabs(
                signin, store, catalog, drafter
            )
            students_tab_, students_table = students_tab(signin, students)
            account = account_tab(signin, students)

        def on_load(request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            role = viewer.role if viewer else None
            is_edu, is_ind = role is Role.EDUCATOR, role is Role.INDEPENDENT
            show = lambda flag: gr.update(visible=flag)  # noqa: E731
            name = f"{viewer.display_name} · {viewer.role.value}" if viewer else "nobody"
            return [
                f"Signed in as **{name}** · [Sign out](/signout)",
                show(role in (Role.SUPERVISED, Role.INDEPENDENT)),  # Learn
                show(role is Role.SUPERVISED),  # waiting screen
                show(is_ind),  # independent's empty Learn
                show(is_edu or is_ind),  # Guide
                show(is_edu),  # Sessions
                show(is_edu),  # Learning plans (independent students get it in step 6)
                show(is_edu),  # Students
                show(is_ind),  # My account
                gr.update(choices=plan_choices(store) if is_edu else [], value=None),
                sessions_text(catalog) if is_edu else "",
                student_rows(students) if is_edu else [],
            ]

        blocks.load(
            on_load,
            None,
            [header, learn_tab, waiting, independent, guide_tab, sessions_tab, plans_tab,
             students_tab_, account, plan_dd, sessions, students_table],
            api_visibility="private",
        )
    return blocks
```

In `app.py`, pass the looks in: `build_main_view(signin, ..., drafter, welcome_html=_WELCOME_HTML, independent_html=_INDEPENDENT_HTML)` with

```python
_INDEPENDENT_HTML = """
<div class="lerni-welcome" role="main">
  <span class="lerni-wave" aria-hidden="true">👋</span>
  <h1>Your activities will appear here</h1>
  <p>Planning your own learning arrives in the next update.</p>
</div>
"""
```.

- [ ] **Step 6: Run all tests and lint**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src/lerni/student tests/student
```
Expected: all pass; ruff clean on the changed files.

- [ ] **Step 7: Manifest and commit**

Manifest: `web/educator.py` row becomes "The educator's Guide, Sessions, and Learning plans tabs (plan table, activity-card form, Claude import). Handlers are plain functions; each Gradio handler re-checks that the viewer is the educator." Add `web/accounts.py` — "The Students tab (add, reset password, archive) and an independent student's My account (name, password with the current one); handlers take the server-resolved viewer and refuse other roles." Tests: `tests/student/test_web_roles.py` — "Students can't manage accounts; the page config carries no plans or usernames."

```bash
git add -A src/lerni/student/web tests/student docs/code-manifest.md
git commit -m "Step 5: tabs by role, Students tab, My account, educator-only handlers"
```

---

### Task 5: Guide, docs, and the check on real devices

**Files:**
- Modify: `src/lerni/student/web/guide.md`
- Modify: `docs/ARCHITECTURE.md`, `docs/reference/admin.md`, `docs/progress.md`, `docs/todo.md`, `plans/release-1-mvp.md`
- Modify (private, gitignored): `CLAUDE.local.md`

- [ ] **Step 1: Guide.** In `guide.md`, under "How it works", add a first step before "Pick an interest and a goal":

```markdown
1. **Add the students** in the **Students** tab. Pick **supervised** for a student you plan for and sit beside (a short password, 4+ characters), or **independent** for someone who plans their own learning (8+ characters). Sign in on the student's iPad once as that student and let Safari save the password; never save your own password there.
```

Renumber the following steps, and change "The admin turns your card into an activity for the app." to "A complete card becomes an activity in the app once you approve it (coming in a later update)."

- [ ] **Step 2: Docs.**
  - `docs/ARCHITECTURE.md`: in Bird's-eye view, change "Today (built)" to describe the sign-in page and the one app at `/app/` with tabs by role (Learn, Guide, Sessions, Learning plans, Students, My account); move "Everyone signs in" in Trust boundaries from planned to built; mark the context diagram's sign-in edges built ("HTTP, sign-in"); in the data table mark student accounts and sign-in built.
  - `docs/reference/admin.md`: replace the "Until step 5 lands" block with: the iPad and other devices open `http://<home-server>:7860/`, sign in at `/signin`; the educator uses username `educator` and the passcode (at least 8 characters); the first time, the educator adds accounts in Students.
  - `plans/release-1-mvp.md`: mark step 5 *(Built.)*.
  - `docs/todo.md`: delete the Upcoming PRs row for step 5 after merge (per its rules); add any follow-ups found.
  - `docs/progress.md`: a dated log entry with what was built, the test count, and the device check results; update Current state.
  - `CLAUDE.local.md` (private): change the URLs to `http://<server name>:7860/` and the sign-in note; keep it out of tracked files.

- [ ] **Step 3: Check on real devices (the admin, by hand).**
  1. Start the server on the home server (`lerni serve`, passcode exported).
  2. On the admin's own device (or a private tab): sign in as `educator`; add an independent account for yourself and a supervised test account.
  3. Sign out; sign in as yourself. Expected: Safari offers to save the password; the header says "Signed in as … · independent"; tabs are Guide, Learn, My account.
  4. Reload, then force-quit Safari and reopen. Expected: still signed in.
  5. On a second device, sign in as the same account; on the first, as `educator`, reset its password. Expected: the second device is sent to `/signin` on its next action or reload.
  6. Type a wrong password 3 times. Expected: "Too many tries. Wait N seconds."; the educator's signed-in session keeps working.
  7. Record the results (pass/fail per item, no private details) in the progress entry.

- [ ] **Step 4: Commit**

```bash
git add src/lerni/student/web/guide.md docs plans/release-1-mvp.md
git commit -m "Step 5: guide, docs, and device check"
```

---

## Self-review notes

- **Spec coverage:** accounts and username/password rules (Task 1); session version, cookie, delays, educator version (Task 2); sign-in page, `/app/`, signed-out redirect, Sign out this device only, passcode minimum (Task 3); tabs by role, Students, My account, "Signed in as", role checks on every handler, nothing per-user in the layout, step-5-safe independent tabs (Task 4); guide, docs, device check (Task 5). Explore freely, plan ownership, and the import changes are step 6.
- **Deliberate choice:** a student's own password change doesn't sign out their other devices; the educator's reset does (spec: reset and archive).
- **Known gap, accepted:** Gradio serves cached files to any signed-in user by URL (spec "Files").
