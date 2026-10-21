"""Nightly backups: a whole copy of the data folder each night, the newest 30 kept."""

import plistlib
from datetime import date
from pathlib import Path

from lerni.student.backup import backup_plist, run


def test_nightly_backups_copy_everything_and_keep_thirty(tmp_path):
    data, backups = tmp_path / "student", tmp_path / "backups"
    (data / "maps").mkdir(parents=True)
    (data / "maps" / "sam.json").write_text("{}")
    (data / "maps" / "sam.events.jsonl").write_text("{}\n")
    for day in range(1, 31):  # 32 older nights, and a copy the admin made by hand
        (backups / "student" / f"nightly-2026-09-{day:02d}").mkdir(parents=True)
    for day in (1, 2):
        (backups / "student" / f"nightly-2026-08-{day:02d}").mkdir()
    (backups / "student-before-x").mkdir()
    (tmp_path / "student-dev").mkdir()
    run(tmp_path / "student-dev", backups, date(2026, 10, 21))  # never replaces production's
    copy = run(data, backups, date(2026, 10, 21))
    assert (copy / "maps" / "sam.events.jsonl").read_text() == "{}\n"  # the journals too
    nights = sorted(p.name for p in (backups / "student").glob("nightly-*"))
    assert len(nights) == 30 and nights[-1] == "nightly-2026-10-21"
    assert "nightly-2026-08-01" not in nights and "nightly-2026-09-01" not in nights
    assert (backups / "student-before-x").is_dir()  # never touched
    agent = plistlib.loads(backup_plist(Path("/x/lerni"), Path("/x"), tmp_path, data))
    assert agent["ProgramArguments"] == ["/x/lerni", "backup", "run"]
    assert agent["StartCalendarInterval"] == {"Hour": 3, "Minute": 0}
    assert agent["EnvironmentVariables"]["LERNI_STUDENT_DATA"] == str(data)
    assert "KeepAlive" not in agent  # runs once a night, never restarted
