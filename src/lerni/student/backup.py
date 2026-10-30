"""Nightly backups: a whole copy of the data folder each night, the newest 30 kept.

``~/.lerni/backups/<data folder>/nightly-YYYY-MM-DD/`` (``student/`` for production, so a run
on development's data never replaces production's copy), made by ``lerni backup run``,
which a LaunchAgent runs at 03:00. Other folders there (copies made by hand) are never
touched. On the same disk: it covers a bad merge, edit, or deploy, not a broken disk
(``--to`` makes a second copy elsewhere). The keys stay out of every copy, each map is
copied with its journal under the map's lock, and ``restore`` puts a whole copy back.
Standard library only.
"""

from __future__ import annotations

import plistlib
import re
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path

from lerni.student.journal import map_lock
from lerni.student.jsonfiles import private
from lerni.student.service import (
    DATA_ENV,
    PORTS,
    Runner,
    ServiceError,
    _same_folder,
    _uid,
    agent_label,
    agent_path,
    agent_settings,
    log_path,
    restart,
    stop,
)
from lerni.student.students import AccountError, check_username

NAME = "backup"  # com.lerni.backup
KEEP = 30  # nightly copies kept
NIGHTLY = re.compile(r"^nightly-\d{4}-\d{2}-\d{2}$")
AT = {"Hour": 3, "Minute": 0}  # when the copy runs, while everyone's asleep
KEYS = ("secret.key", "https-key.pem")  # never copied: a copy must not let anyone sign in
CARRIED = (*KEYS, "https.pem")  # kept from the folder a restore replaces
SKIP = shutil.ignore_patterns(".tmp-*", "*.lock", *KEYS)
MAP_FILE = re.compile(r"^([a-z][a-z0-9-]{1,30})\.(json|events\.jsonl)$")


class BackupError(Exception):
    """A copy can't be restored; nothing was changed."""


def prune(backups: Path, keep: int = KEEP) -> list[str]:
    """Delete all but the newest ``keep`` nightly copies; returns the names deleted."""
    nights = sorted(p for p in backups.iterdir() if p.is_dir() and NIGHTLY.match(p.name))
    gone = nights[:-keep] if keep > 0 else nights
    for p in gone:
        shutil.rmtree(p)
    return [p.name for p in gone]


def run(data: Path, root: Path, today: date, keep: int = KEEP) -> Path:
    """Copy ``data`` to ``root/<its folder name>/nightly-<today>`` (replacing today's), then
    prune that folder only.

    Raises:
        OSError: The copy failed; any half copy is removed and older copies stay.
    """
    backups = root / data.name  # each data folder its own copies
    backups.mkdir(parents=True, exist_ok=True)
    dest = backups / f"nightly-{today.isoformat()}"
    half = backups / f".partial-{today.isoformat()}"  # never counted as a copy
    shutil.rmtree(half, ignore_errors=True)
    try:
        # every file is written whole; maps wait for their journals (below)
        shutil.copytree(data, half, ignore=lambda folder, names: {
            *SKIP(folder, names), *(["maps"] if Path(folder) == data else [])})
        _copy_maps(data / "maps", half / "maps")
    except OSError:
        shutil.rmtree(half, ignore_errors=True)
        raise
    shutil.rmtree(dest, ignore_errors=True)
    half.rename(dest)
    prune(backups, keep)
    private(backups)  # Lerni's copies only, never the rest of a drive
    return dest


def _copy_maps(src: Path, dest: Path) -> None:
    # each map with its journal, holding that map's lock, so the two always agree
    if not src.is_dir():
        return
    shutil.copytree(src, dest, ignore=lambda folder, names: {
        *SKIP(folder, names), *(n for n in names if Path(folder) == src and MAP_FILE.match(n))})
    users = sorted({m[1] for p in src.iterdir() if (m := MAP_FILE.match(p.name))})
    for user in users:
        try:
            check_username(user)
        except AccountError:  # a reserved name can't have a lock: copy it as it is
            for name in (f"{user}.json", f"{user}.events.jsonl"):
                if (src / name).is_file():
                    shutil.copy2(src / name, dest / name)
            continue
        with map_lock(src, user):
            for name in (f"{user}.json", f"{user}.events.jsonl"):
                if (src / name).is_file():
                    shutil.copy2(src / name, dest / name)


def server_for(data: Path, home: Path) -> str | None:
    """The installed server (prod or dev) whose agent uses this data folder, if any."""
    for name in PORTS:
        if agent_path(home, name).is_file():
            folder = agent_settings(home, name).get(DATA_ENV) or home / ".lerni" / "student"
            if _same_folder(Path(folder), data):
                return name
    return None


def restore(data: Path, copy: Path, home: Path | None = None, run_: Runner = subprocess.run,
            uid: int | None = None, now: datetime | None = None) -> tuple[Path, str | None]:
    """Put a whole copy back as ``data``: stop the server that uses it, swap the folders
    (keeping the keys and certificate), and start it again.

    Returns:
        The replaced folder, kept beside it, and the server started again (or None).

    Raises:
        BackupError: Not a copy of the data folder, or the server wouldn't stop or start;
            the message says whether anything changed.
        OSError: The copy failed; nothing was changed and the server runs again.
    """
    if not (copy / "students").is_dir():
        raise BackupError(f"{copy} isn't a copy of Lerni's data (it has no accounts).")
    home, now = home or Path.home(), now or datetime.now()
    server = server_for(data, home)
    try:
        running = stop(server, run_, uid) if server else False
    except ServiceError as exc:
        raise BackupError(f"{exc} Nothing changed; to start it: lerni service restart "
                          f"{server}.") from None
    half = data.parent / f".restoring-{data.name}"
    kept = data.parent / f"{data.name}.before-restore-{now:%Y%m%d-%H%M%S}"
    try:
        shutil.rmtree(half, ignore_errors=True)
        shutil.copytree(copy, half)
        for name in CARRIED:  # nobody signs out, and HTTPS keeps working
            if (data / name).is_file():
                shutil.copy2(data / name, half / name)
        private(half)
        if data.exists():
            data.rename(kept)
    except OSError as exc:
        shutil.rmtree(half, ignore_errors=True)
        if running and server:
            try:
                restart(server, run_, uid, home)
            except ServiceError as again:
                raise BackupError(f"Nothing changed ({exc}), but {again}") from exc
        raise
    try:
        half.rename(data)
    except OSError as exc:
        raise BackupError(f"Stopped halfway: the copy is {half} and the old folder {kept}; "
                          f"rename {kept.name} back to {data.name}.") from exc
    if running and server:
        try:
            restart(server, run_, uid, home)
        except ServiceError as exc:  # restored all the same: say where the old folder is
            raise BackupError(f"Restored; the folder it replaced is {kept}. But {exc}") from None
        return kept, server
    return kept, None


def backup_plist(lerni: Path, checkout: Path, home: Path, data: Path) -> bytes:
    """The LaunchAgent that runs ``lerni backup run`` every night on this data folder."""
    log = str(log_path(home, NAME))
    return plistlib.dumps({
        "Label": agent_label(NAME),
        "ProgramArguments": [str(lerni), "backup", "run"],
        "EnvironmentVariables": {DATA_ENV: str(data)},
        "WorkingDirectory": str(checkout),
        "StartCalendarInterval": AT,  # once a night; a missed night runs at the next wake
        "StandardOutPath": log,
        "StandardErrorPath": log,
    })


def install(lerni: Path, checkout: Path, data: Path, home: Path | None = None,
            run_: Runner = subprocess.run, uid: int | None = None) -> Path:
    """Write the backup agent and load it, replacing one already loaded.

    Raises:
        ServiceError: No such data folder, or macOS refused.
    """
    home = home or Path.home()
    if not (data / "students").is_dir():
        raise ServiceError(f"{data} has no accounts: point --data at production's data.")
    path = agent_path(home, NAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(backup_plist(lerni, checkout, home, data))
    log_path(home, NAME).parent.mkdir(parents=True, exist_ok=True)
    run_(["launchctl", "bootout", f"gui/{_uid(uid)}/{agent_label(NAME)}"], capture_output=True)
    try:
        run_(["launchctl", "bootstrap", f"gui/{_uid(uid)}", str(path)], check=True,
             capture_output=True)
    except subprocess.CalledProcessError as exc:
        raise ServiceError("macOS wouldn't load the backup agent: check you're logged in at "
                           "the Mac, then install again.") from exc
    return path


def status(root: Path, data: Path, home: Path | None = None) -> str:
    """One line: whether the nightly copy is set up, and this data folder's newest copy."""
    home = home or Path.home()
    backups = root / data.name
    nights = sorted(p.name for p in backups.glob("nightly-*") if NIGHTLY.match(p.name)) \
        if backups.is_dir() else []
    last = f"newest {nights[-1]}, {len(nights)} kept" if nights else "no copies yet"
    if not agent_path(home, NAME).is_file():
        return f"backup: not installed (lerni backup install); {last}"
    return f"backup: nightly at {AT['Hour']:02d}:{AT['Minute']:02d}; {last}"
