"""Nightly backups: a whole copy of the data folder each night, the newest 30 kept.

``~/.lerni/backups/<data folder>/nightly-YYYY-MM-DD/`` (``student/`` for production, so a run
on development's data never replaces production's copy), made by ``lerni backup run``,
which a LaunchAgent runs at 03:00. Other folders there (copies made by hand) are never
touched. On the same disk: it covers a bad merge, edit, or deploy, not a broken disk
(``--to`` makes a second copy elsewhere). Standard library only.
"""

from __future__ import annotations

import plistlib
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

from lerni.student.service import (
    DATA_ENV,
    Runner,
    ServiceError,
    _uid,
    agent_label,
    agent_path,
    log_path,
)

NAME = "backup"  # com.lerni.backup
KEEP = 30  # nightly copies kept
NIGHTLY = re.compile(r"^nightly-\d{4}-\d{2}-\d{2}$")
AT = {"Hour": 3, "Minute": 0}  # when the copy runs, while everyone's asleep


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
        # maps and journals are written whole, so each copied file is whole
        shutil.copytree(data, half, ignore=shutil.ignore_patterns(".tmp-*", "*.lock"))
    except OSError:
        shutil.rmtree(half, ignore_errors=True)
        raise
    shutil.rmtree(dest, ignore_errors=True)
    half.rename(dest)
    prune(backups, keep)
    return dest


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
