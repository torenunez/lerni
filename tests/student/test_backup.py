"""Nightly backups: a whole copy of the data folder each night, the newest 30 kept."""

import json
import plistlib
import subprocess
import threading
import time
from datetime import date, datetime
from pathlib import Path

import pytest

from lerni.student.backup import BackupError, backup_plist, restore, run
from lerni.student.interests import MapStore, add_goal
from lerni.student.journal import MapJournal, replay
from lerni.student.service import DATA_ENV, agent_path


def test_nightly_backups_copy_everything_and_keep_thirty(tmp_path):
    data, backups = tmp_path / "student", tmp_path / "backups"
    (data / "maps").mkdir(parents=True)
    (data / "maps" / "sam.json").write_text("{}")
    (data / "maps" / "sam.events.jsonl").write_text("{}\n")
    for name in ("secret.key", "https-key.pem", "https.pem"):
        (data / name).write_text("x")
    for day in range(1, 31):  # 32 older nights, and a copy the admin made by hand
        (backups / "student" / f"nightly-2026-09-{day:02d}").mkdir(parents=True)
    for day in (1, 2):
        (backups / "student" / f"nightly-2026-08-{day:02d}").mkdir()
    (backups / "student-before-x").mkdir()
    (tmp_path / "student-dev").mkdir()
    run(tmp_path / "student-dev", backups, date(2026, 10, 21))  # never replaces production's
    copy = run(data, backups, date(2026, 10, 21))
    assert (copy / "maps" / "sam.events.jsonl").read_text() == "{}\n"  # the journals too
    # v3.34: the keys stay out, and the copies are private to this account
    assert not (copy / "secret.key").exists() and not (copy / "https-key.pem").exists()
    assert (copy / "https.pem").is_file()
    assert (backups.stat().st_mode & 0o777, copy.stat().st_mode & 0o777) == (0o700, 0o700)
    assert (copy / "maps" / "sam.json").stat().st_mode & 0o777 == 0o600
    nights = sorted(p.name for p in (backups / "student").glob("nightly-*"))
    assert len(nights) == 30 and nights[-1] == "nightly-2026-10-21"
    assert "nightly-2026-08-01" not in nights and "nightly-2026-09-01" not in nights
    assert (backups / "student-before-x").is_dir()  # never touched
    agent = plistlib.loads(backup_plist(Path("/x/lerni"), Path("/x"), tmp_path, data))
    assert agent["ProgramArguments"] == ["/x/lerni", "backup", "run"]
    assert agent["StartCalendarInterval"] == {"Hour": 3, "Minute": 0}
    assert agent["EnvironmentVariables"]["LERNI_STUDENT_DATA"] == str(data)
    assert "KeepAlive" not in agent  # runs once a night, never restarted


def test_a_backup_copies_a_map_and_its_journal_as_a_pair(tmp_path):
    data = tmp_path / "student"
    store = MapStore(data)
    store.change("sam", lambda m: add_goal(m, "Fractions"), by="person:ann")
    started = threading.Event()

    def slow(m):  # a change in progress while the copy starts
        started.set()
        time.sleep(0.3)
        add_goal(m, "Volcanoes")

    writer = threading.Thread(target=store.change, args=("sam", slow))
    writer.start()
    started.wait()
    copy = run(data, tmp_path / "backups", date(2026, 10, 30))
    writer.join()
    saved = json.loads((copy / "maps" / "sam.json").read_text())
    assert [e["name"] for e in saved["entries"]] == ["Fractions", "Volcanoes"]  # waited for it
    assert replay(MapJournal(copy).read("sam")) == saved  # and the journal agrees


def _launchctl(calls):
    # a fake launchctl: prod is loaded until booted out, and bootstrap loads it again
    state = {"loaded": True}

    def run_(cmd, check=False, capture_output=False):
        calls.append(cmd[1])
        code = 113 if cmd[1] in ("print", "kickstart") and not state["loaded"] else 0
        state["loaded"] = {"bootout": False, "bootstrap": True}.get(cmd[1], state["loaded"])
        if check and code:
            raise subprocess.CalledProcessError(code, cmd)
        return subprocess.CompletedProcess(cmd, code)
    return run_


def _setup(tmp_path):
    data, home = tmp_path / "student", tmp_path / "home"
    (data / "students").mkdir(parents=True)
    (data / "students" / "sam.json").write_text("{}")
    (data / "secret.key").write_text("old")
    copy = run(data, tmp_path / "backups", date(2026, 10, 29))
    agent = agent_path(home, "prod")
    agent.parent.mkdir(parents=True)
    agent.write_bytes(plistlib.dumps({"EnvironmentVariables": {DATA_ENV: str(data)}}))
    return data, home, copy


def test_restore_puts_a_copy_back_and_keeps_what_it_replaced(tmp_path):
    data, home, copy = _setup(tmp_path)
    (data / "students" / "ann.json").write_text("{}")  # added since the copy
    (data / "secret.key").write_text("new")
    calls = []
    kept, server = restore(data, copy, home=home, run_=_launchctl(calls), uid=501,
                           now=datetime(2026, 10, 30, 10, 15))
    assert server == "prod" and "bootout" in calls and calls[-1] == "bootstrap"  # stopped, started
    assert sorted(p.name for p in (data / "students").iterdir()) == ["sam.json"]
    assert (data / "secret.key").read_text() == "new"  # nobody signs out
    assert kept == tmp_path / "student.before-restore-20261030-101500"
    assert (kept / "students" / "ann.json").is_file()  # set aside, not deleted
    assert data.stat().st_mode & 0o777 == 0o700


def test_restore_refuses_a_copy_with_no_accounts(tmp_path):
    data, home, _ = _setup(tmp_path)
    empty = tmp_path / "backups" / "student" / "nightly-2026-10-28"
    empty.mkdir()
    calls = []
    with pytest.raises(BackupError):
        restore(data, empty, home=home, run_=_launchctl(calls), uid=501)
    assert calls == [] and (data / "secret.key").read_text() == "old"  # nothing changed
