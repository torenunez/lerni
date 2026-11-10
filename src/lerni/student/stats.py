"""A read-only copy of the student data in SQLite, for questions the app doesn't answer.

``<data root>/stats.sqlite``: labels and numbers only, rebuilt whole from the accounts, maps,
results, and concepts, so it's never the source of truth and has no migrations. Conversation
logs, feedback, goal notes, display names, and passwords are never read into it. Standard
library only.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from lerni.student.interests import Entry, InterestMap, MapStore, area_group
from lerni.student.students import USERNAME_RE

FILE = "stats.sqlite"
AIM = "50–75%"  # how often a student should be right (v3.16)
MIN_HARDEST = 5  # a goal with fewer answers says too little to call it hard
TOP = 5  # rows in the hardest and missed lists
WHO = "username = ? AND day >= ?"  # every report query: one student, from a first day
SCORED = "right IS NOT NULL AND probe IS NULL"  # a bonus has a tier, a probe its own line
BAD = (ValueError, TypeError, AttributeError, KeyError,  # a line or file not as written
       OverflowError, sqlite3.InterfaceError, sqlite3.ProgrammingError)  # a value SQLite refuses

TABLES = """
CREATE TABLE students (username TEXT PRIMARY KEY, kind TEXT, educator INTEGER, archived INTEGER);
CREATE TABLE entries (username TEXT, entry_id TEXT, kind TEXT, name TEXT, area TEXT,
    mentions INTEGER, days INTEGER, explained_days INTEGER, state TEXT);
CREATE TABLE answers (username TEXT, day TEXT, week TEXT, race TEXT, goal_id TEXT, goal TEXT,
    area TEXT, concept TEXT, question_hash TEXT, level INTEGER, attempt INTEGER, right INTEGER,
    seconds REAL, probe TEXT, bonus_tier TEXT, format TEXT, setting TEXT);
CREATE TABLE races (username TEXT, day TEXT, week TEXT, race TEXT, place INTEGER, points INTEGER);
CREATE TABLE probe_taps (username TEXT, day TEXT, topic TEXT);
CREATE TABLE concepts (username TEXT, goal_id TEXT, goal TEXT, concept TEXT, first TEXT,
    last TEXT, asked INTEGER, right INTEGER);
CREATE TABLE goal_levels (username TEXT, goal_id TEXT, level INTEGER, box INTEGER, due TEXT);
"""


@dataclass(frozen=True)
class Built:
    """What a rebuild made: the file, its counts, and the lines or files it had to skip."""

    path: Path
    students: int
    answers: int
    skipped: int


def monday(day: date) -> date:
    """The Monday of ``day``'s week."""
    return day - timedelta(days=day.weekday())


def wilson(right: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson 95% range of a share: honest about small counts, unlike plus or minus."""
    if n == 0:
        return 0.0, 1.0  # no answers: it could be anything
    p = right / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - spread), min(1.0, centre + spread)


def _lines(path: Path) -> tuple[list[dict[str, Any]], int]:
    # bytes, so a character cut in half loses its line and not the file
    try:
        raw = path.read_bytes().splitlines()
    except FileNotFoundError:
        return [], 0
    except OSError:
        return [], 1
    records, bad = [], 0
    for line in raw:
        try:
            record = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(record, dict):
            records.append(record)
        else:
            bad += 1
    return records, bad


def _object(path: Path) -> dict[str, Any]:
    # never read_json: this copy must not move a broken file aside
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(path.name)
    return data


def _goal(m: InterestMap, goal_id: str, name: str) -> Entry | None:
    # by id first, so a renamed goal keeps its rows; the oldest lines have only a name
    every = [*m.entries, *m.archived]
    e = next((x for x in every if x.id == goal_id), None) if goal_id else m.find(name)
    return e if e is not None and e.kind == "goal" else None


def _area(e: Entry | None) -> str:
    return (area_group(e.area) if e is not None else "") or "Other"


def _week(day: str) -> str:
    return monday(date.fromisoformat(day)).isoformat()


def _add_result(db: sqlite3.Connection, user: str, m: InterestMap, r: dict[str, Any]) -> bool:
    # one line of the results log into its table; False if it's no kind of line we know
    day = r["day"]
    week = _week(day)  # a line without a real day stops here
    if r.get("probe_tap"):
        db.execute("INSERT INTO probe_taps VALUES (?,?,?)", (user, day, str(r["probe_tap"])))
    elif "place" in r:
        db.execute("INSERT INTO races VALUES (?,?,?,?,?,?)",
                   (user, day, week, r.get("race"), int(r["place"]), r.get("points")))
    elif "right" in r or "bonus" in r:
        goal_id, name = str(r.get("goal_id") or ""), str(r.get("goal") or "")
        e = _goal(m, goal_id, name)
        right = int(bool(r["right"])) if "right" in r else None
        db.execute("INSERT INTO answers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            user, day, week, r.get("race"), goal_id or (e.id if e else None),
            e.name if e else name, _area(e), r.get("concept"), r.get("q"), r.get("level"),
            r.get("attempt"), right, r.get("seconds"), r.get("probe") or None, r.get("bonus"),
            r.get("format") or None, r.get("setting") or None))
    else:
        return False
    return True


def _add_student(db: sqlite3.Connection, root: Path, user: str, account: dict[str, Any]) -> int:
    # one student's rows; returns the lines and files skipped
    db.execute("INSERT INTO students VALUES (?,?,?,?)", (
        user, str(account.get("kind", "")), int(bool(account.get("educator"))),
        int(bool(account.get("archived")))))
    skipped = 0
    try:
        m = MapStore(root).get(user)
        rows = [(user, e.id, e.kind, e.name, _area(e) if e.kind == "goal" else None, e.mentions,
                 len(e.days), len(e.explained), state)
                for state, entries in (("active", m.entries), ("resting", m.archived))
                for e in entries]
        db.executemany("INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?)", rows)
    except (*BAD, OSError):  # a broken map adds no rows of its own
        m, skipped = InterestMap(), 1
    records, bad = _lines(root / "results" / f"{user}.jsonl")
    skipped += bad
    for r in records:
        try:
            skipped += not _add_result(db, user, m, r)
        except BAD:
            skipped += 1
    return skipped + _add_concepts(db, root / "concepts" / f"{user}.json", user)


def _add_concepts(db: sqlite3.Connection, path: Path, user: str) -> int:
    # the ledger and the levels; returns 1 for a broken file, which is written whole or not
    try:
        data = _object(path) if path.is_file() else {}
        concepts = [(user, c.get("goal_id"), c.get("goal"), c["concept"], c.get("first"),
                     c.get("last"), c.get("asked"), c.get("right"))
                    for c in data.get("concepts", [])]
        levels = [(user, goal_id, v.get("level"), v.get("box"), v.get("due"))
                  for goal_id, v in data.get("levels", {}).items()]
        db.executemany("INSERT INTO concepts VALUES (?,?,?,?,?,?,?,?)", concepts)
        db.executemany("INSERT INTO goal_levels VALUES (?,?,?,?,?)", levels)
    except (*BAD, OSError):
        return 1
    return 0


def build(root: Path) -> Built:
    """Rebuild ``root/stats.sqlite`` from the data folder, swapped in whole.

    Args:
        root: The data folder.

    Returns:
        The file, its counts, and how many cut-off lines or broken files were skipped.

    Raises:
        OSError: The file couldn't be written; any older copy stays.
        sqlite3.Error: The same, from SQLite.
    """
    path = root / FILE
    # a .tmp- name backups skip; mkstemp makes it this account's only
    fd, tmp = tempfile.mkstemp(dir=root, prefix=".tmp-stats-", suffix=".sqlite")
    os.close(fd)
    skipped = 0
    try:
        db = sqlite3.connect(tmp)
        try:
            db.executescript(TABLES)
            for file in sorted((root / "students").glob("*.json")):
                if not USERNAME_RE.match(file.stem):  # set-aside and temporary files
                    continue
                try:
                    account = _object(file)
                except (*BAD, OSError):
                    skipped += 1
                    continue
                skipped += _add_student(db, root, file.stem, account)
            db.commit()
            students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            answers = db.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        finally:
            db.close()
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return Built(path, students, answers, skipped)


def connect(path: Path) -> sqlite3.Connection:
    """A connection that can't change the file, however it's used."""
    db = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)  # no ATTACH: it could make a file elsewhere
    db.execute("PRAGMA query_only = ON")
    return db


def query(path: Path, sql: str, params: tuple[Any, ...] = ()
          ) -> tuple[list[str], list[tuple[Any, ...]]]:
    """Run one statement read-only: its column names and rows.

    Raises:
        sqlite3.Error: A bad query, or one that tries to write.
        sqlite3.Warning: More than one statement (on Python 3.11).
    """
    db = connect(path)
    try:
        cursor = db.execute(sql, params)
        return [c[0] for c in cursor.description or []], cursor.fetchall()
    finally:
        db.close()


def _table(rows: list[tuple[Any, ...]]) -> str:
    # columns padded to their widest cell
    widths = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(str(c).ljust(w) for c, w in zip(r, widths, strict=True)).rstrip()
                     for r in rows)


def _share(right: int, n: int) -> tuple[str, str, str]:
    # a share as "3/8", "38%", and its 95% range
    low, high = wilson(right, n)
    return f"{right}/{n}", f"{round(100 * right / n)}%", f"{round(100 * low)}–{round(100 * high)}"


def _ordinal(place: int) -> str:
    return str(place) + {1: "st", 2: "nd", 3: "rd"}.get(place, "th")


def _count(n: int, thing: str) -> str:
    return f"{n} {thing}" if n == 1 else f"{n} {thing}s"


def _total(db: sqlite3.Connection, who: tuple[str, str]) -> tuple[int, int]:
    # right and scored answers for (username, first day)
    return db.execute("SELECT COALESCE(SUM(right), 0), COUNT(*) FROM answers "
                      f"WHERE {WHO} AND {SCORED}", who).fetchone()


def overview(path: Path, start: str) -> str:
    """One line per student still active, from day ``start`` on."""
    db = connect(path)
    try:
        rows: list[tuple[Any, ...]] = [("Student", "Kind", "Goals", "Right", "%", "95% range",
                                        "Races", "Last race")]
        users = db.execute(
            "SELECT username, kind FROM students WHERE archived = 0 ORDER BY username").fetchall()
        for user, kind in users:
            goals = db.execute("SELECT COUNT(*) FROM entries WHERE username = ? AND kind = 'goal' "
                               "AND state = 'active'", (user,)).fetchone()[0]
            right, n = _total(db, (user, start))
            races, last = db.execute(f"SELECT COUNT(*), MAX(day) FROM races WHERE {WHO}",
                                     (user, start)).fetchone()
            rows.append((user, kind, goals, *(_share(right, n) if n else ("–", "–", "–")),
                         races, last or "–"))
    finally:
        db.close()
    return _table(rows)


def _head(db: sqlite3.Connection, who: tuple[str, str], window: str) -> str:
    right, n = _total(db, who)
    if not n:
        return f"{who[0]} · {window} · no answers"
    races = db.execute(f"SELECT COUNT(*) FROM races WHERE {WHO}", who).fetchone()[0]
    _, percent, spread = _share(right, n)
    return (f"{who[0]} · {window} · {_count(n, 'answer')} in {_count(races, 'race')} · "
            f"{percent} right (95% range {spread}; aim: {AIM})")


def _by(db: sqlite3.Connection, who: tuple[str, str], title: str, column: str,
        rest: str) -> str | None:
    # a table of right answers grouped by one column, or None when there are none
    rows = db.execute(f"SELECT {column}, SUM(right), COUNT(*) FROM answers WHERE {WHO} "
                      f"AND {SCORED} GROUP BY {column} {rest}", who).fetchall()
    return _table([(title, "Right", "%", "95% range"),
                   *((name, *_share(r, n)) for name, r, n in rows)]) if rows else None


def _weeks(db: sqlite3.Connection, who: tuple[str, str]) -> str | None:
    # each week's right answers, with its finishes
    finishes: dict[str, list[str]] = {}
    for week, place, count in db.execute(f"SELECT week, place, COUNT(*) FROM races WHERE {WHO} "
                                         "GROUP BY week, place ORDER BY week, place", who):
        finishes.setdefault(week, []).append(f"{_ordinal(place)} ×{count}")
    rows = db.execute(f"SELECT week, SUM(right), COUNT(*) FROM answers WHERE {WHO} AND {SCORED} "
                      "GROUP BY week ORDER BY week", who).fetchall()
    return _table([("Week of", "Right", "%", "95% range", "Races"), *(
        (w, *_share(r, n), ", ".join(finishes.get(w, [])) or "–") for w, r, n in rows)]) \
        if rows else None


def _missed(db: sqlite3.Connection, who: tuple[str, str]) -> str | None:
    # the ideas answered wrong most often, whatever their capitals
    rows = db.execute(f"SELECT concept, COUNT(*) - SUM(right), COUNT(*) FROM answers WHERE {WHO} "
                      f"AND {SCORED} AND concept != '' GROUP BY concept COLLATE NOCASE "
                      "HAVING COUNT(*) > SUM(right) "
                      f"ORDER BY COUNT(*) - SUM(right) DESC, COUNT(*), concept LIMIT {TOP}",
                      who).fetchall()
    return _table([("Ideas missed most", "Missed", "Asked"), *rows]) if rows else None


def _variety(db: sqlite3.Connection, who: tuple[str, str]) -> str | None:
    # how fresh the questions were (v3.42): ideas, repeats, formats, and settings
    n, ideas, before = db.execute(
        "SELECT COUNT(*), COUNT(DISTINCT COALESCE(goal_id, '') || '|' || lower(concept)), "
        f"COALESCE(SUM(attempt > 1), 0) FROM answers WHERE {WHO} AND {SCORED}", who).fetchone()
    if not n:
        return None
    line = f"Variety: {n} questions, {ideas} ideas, {before} asked before"
    for column in ("format", "setting"):  # the formats (v3.42) and settings (v3.43) used
        rows = db.execute(f"SELECT {column}, COUNT(*) FROM answers WHERE {WHO} AND {SCORED} "
                          f"AND {column} IS NOT NULL GROUP BY {column} COLLATE NOCASE "
                          f"ORDER BY COUNT(*) DESC, {column}", who).fetchall()
        line += f"; {column}s: " + ", ".join(f"{k} {v}" for v, k in rows) if rows else ""
    return line


def _extras(db: sqlite3.Connection, who: tuple[str, str]) -> str | None:
    # probes and bonus answers, kept apart from the percentages
    asked, right = db.execute("SELECT COUNT(*), COALESCE(SUM(right), 0) FROM answers "
                              f"WHERE {WHO} AND probe IS NOT NULL", who).fetchone()
    taps = db.execute(f"SELECT COUNT(*) FROM probe_taps WHERE {WHO}", who).fetchone()[0]
    tiers = db.execute(f"SELECT bonus_tier, COUNT(*) FROM answers WHERE {WHO} "
                       "AND bonus_tier IS NOT NULL GROUP BY bonus_tier "
                       "ORDER BY COUNT(*) DESC, bonus_tier", who).fetchall()
    lines = [f"Probes: {asked} asked, {right} right, {taps} tapped"] if asked or taps else []
    if tiers:
        lines.append("Bonus: " + ", ".join(f"{n} {tier}" for tier, n in tiers))
    return "\n".join(lines) or None


def report(path: Path, username: str, start: str, window: str) -> str:
    """One student's report from day ``start`` on: right answers by area and week, the
    hardest goals, the ideas missed most, how varied the questions were, then probes and bonus
    answers on their own lines."""
    db = connect(path)
    who = (username, start)
    try:
        parts = [
            _head(db, who, window),
            _by(db, who, "Area", "area", "ORDER BY COUNT(*) DESC, area"),
            _weeks(db, who),
            _by(db, who, f"Hardest goals ({MIN_HARDEST}+ answers)", "goal",
                f"HAVING COUNT(*) >= {MIN_HARDEST} AND goal != '' "
                f"ORDER BY 1.0 * SUM(right) / COUNT(*), COUNT(*) DESC LIMIT {TOP}"),
            _missed(db, who),
            _variety(db, who),
            _extras(db, who),
        ]
    finally:
        db.close()
    return "\n\n".join(p for p in parts if p)
