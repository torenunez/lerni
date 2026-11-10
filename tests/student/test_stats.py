"""The read-only stats copy: labels and numbers in SQLite, rebuilt from the data folder."""

import json
import sqlite3

import pytest
from typer.testing import CliRunner

from lerni.cli import app
from lerni.student.interests import MapStore, add_goal, add_interest, rename, set_area
from lerni.student.results import ResultsLog
from lerni.student.stats import build, query, wilson
from lerni.student.students import Kind, StudentStore


def _answer(day: str, goal_id: str, goal: str, right: bool, concept: str = "an idea",
            **more) -> dict:
    return {"day": day, "race": "r1", "goal_id": goal_id, "goal": goal, "concept": concept,
            "q": "abc123", "right": right, "seconds": 2.5, **more}


def _folder(root):
    # one student: two goals (one renamed), an interest, and a mix of result lines
    StudentStore(root).add("sam", "Secret Display Name", Kind.SUPERVISED, "pass")
    maps = MapStore(root)

    def fill(m):
        fractions = add_goal(m, "Fractions", "secret goal note")
        set_area(m, fractions.id, "Math")
        add_goal(m, "Verbs")
        add_interest(m, "sharks")
        return None

    maps.change("sam", fill, by="person:sam")
    m = maps.get("sam")
    fractions, verbs = (next(e for e in m.entries if e.name == n) for n in ("Fractions", "Verbs"))
    log = ResultsLog(root)
    for right in (True, True, False):
        log.add("sam", _answer("2026-10-26", fractions.id, "Fractions", right, level=2, attempt=1,
                               format="odd one out", setting="trains"))
    log.add("sam", _answer("2026-10-27", verbs.id, "Verbs", False))  # older line: no level
    log.add("sam", _answer("2026-10-27", fractions.id, "Fractions", True, probe="earthquakes"))
    log.add("sam", {"day": "2026-10-27", "race": "r1", "goal_id": fractions.id,
                    "goal": "Fractions", "concept": "an idea", "q": "def", "bonus": "nailed"})
    log.add("sam", {"day": "2026-10-27", "race": "r1", "place": 2, "points": 12, "version": "3"})
    log.add("sam", {"day": "2026-10-27", "probe_tap": "earthquakes"})
    with (root / "results" / "sam.jsonl").open("ab") as handle:
        handle.write(b'{"day": "2026-10-2')  # cut off by a write in progress
    maps.change("sam", lambda m: rename(m, fractions.id, "Halves") and None, by="person:sam")
    (root / "concepts").mkdir()
    (root / "concepts" / "sam.json").write_text(json.dumps({
        "schema": 4,
        "concepts": [{"goal_id": fractions.id, "goal": "Halves", "concept": "an idea",
                      "first": "2026-10-26", "last": "2026-10-27", "asked": 4, "right": 3}],
        "levels": {fractions.id: {"level": 3, "right": 1, "asked": 2, "box": 1,
                                  "due": "2026-10-30"}}}))
    return root


def test_the_copy_has_every_table_and_a_renamed_goal_keeps_its_rows(tmp_path):
    built = build(_folder(tmp_path / "data"))
    assert (built.students, built.answers, built.skipped) == (1, 6, 1)

    def rows(sql):
        return query(built.path, sql)[1]

    assert rows("SELECT username, kind, educator FROM students") == [("sam", "supervised", 0)]
    assert rows("SELECT name, kind, area, state FROM entries ORDER BY name") == [
        ("Halves", "goal", "Math", "active"), ("Verbs", "goal", "Other", "active"),
        ("sharks", "interest", None, "active")]
    # the old name's lines sit under the goal's name and area today
    assert rows("SELECT goal, area, COUNT(*) FROM answers GROUP BY goal ORDER BY goal") == [
        ("Halves", "Math", 5), ("Verbs", "Other", 1)]
    assert rows("SELECT week, level, attempt FROM answers WHERE goal = 'Verbs'") == [
        ("2026-10-26", None, None)]  # the week's Monday; an older line isn't guessed
    assert rows("SELECT right, seconds, bonus_tier FROM answers WHERE bonus_tier IS NOT NULL") == [
        (None, None, "nailed")]
    assert rows("SELECT probe, right FROM answers WHERE probe IS NOT NULL") == [("earthquakes", 1)]
    assert rows("SELECT place, points FROM races") == [(2, 12)]
    assert rows("SELECT day, topic FROM probe_taps") == [("2026-10-27", "earthquakes")]
    assert rows("SELECT goal, concept, asked, right FROM concepts") == [
        ("Halves", "an idea", 4, 3)]
    assert rows("SELECT level, box, due FROM goal_levels") == [(3, 1, "2026-10-30")]


def test_hand_edited_values_are_skipped_and_counted(tmp_path):
    root = _folder(tmp_path / "data")
    with (root / "results" / "sam.jsonl").open("a") as handle:  # after the cut-off line's newline
        handle.write("\n" + json.dumps(_answer("2026-10-27", "", "x", True, level=10**30)) + "\n")
    path = root / "maps" / "sam.json"
    data = json.loads(path.read_text())
    data["entries"][0]["days"] = None
    path.write_text(json.dumps(data))
    built = build(root)  # the map (no rows from it), the cut-off line, and the huge number
    assert (built.students, built.skipped) == (1, 3)


def test_the_report_keeps_probes_and_bonus_answers_out_of_the_percentages(tmp_path):
    root = _folder(tmp_path / "data")
    args = ["stats", "--data", str(root)]
    report = CliRunner().invoke(app, [*args, "sam", "--all"])
    assert report.exit_code == 0, report.output
    # 4 scored answers: not the probe (right) or the bonus
    assert "4 answers in 1 race · 50% right" in report.output
    assert "Probes: 1 asked, 1 right, 1 tapped" in report.output
    assert "Bonus: 1 nailed" in report.output
    assert ("Variety: 4 questions, 2 ideas, 0 asked before; formats: 3 odd one out; "
            "settings: 3 trains") in report.output
    assert "2nd ×1" in report.output
    assert "Hardest" not in report.output  # no goal has 5 scored answers
    overview = CliRunner().invoke(app, args)
    assert overview.exit_code == 0 and "sam" in overview.output
    assert CliRunner().invoke(app, [*args, "nobody"]).exit_code == 1


def test_private_text_never_reaches_the_copy(tmp_path):
    root = _folder(tmp_path / "data")
    (root / "logs" / "sam").mkdir(parents=True)
    (root / "logs" / "sam" / "2026-10-27.jsonl").write_text('{"text": "secret conversation"}\n')
    (root / "feedback.jsonl").write_text('{"text": "secret feedback"}\n')
    built = build(root)
    assert built.path.stat().st_mode & 0o777 == 0o600  # this account's only
    raw = built.path.read_bytes()
    for marker in (b"secret", b"Secret", b"scrypt", b"salt"):
        assert marker not in raw
    assert not list(root.glob(".tmp-*"))


def test_a_query_can_never_change_the_copy(tmp_path):
    root = _folder(tmp_path / "data")
    built = build(root)
    for sql in ("DELETE FROM answers", f"ATTACH '{tmp_path}/other.db' AS other"):
        with pytest.raises(sqlite3.OperationalError):
            query(built.path, sql)
    assert not (tmp_path / "other.db").exists()
    out = CliRunner().invoke(app, ["stats", "--data", str(root), "--sql",
                                   "DROP TABLE answers"])
    assert out.exit_code == 1
    out = CliRunner().invoke(app, ["stats", "--data", str(root), "--sql",
                                   "SELECT COUNT(*) AS n FROM answers"])
    assert out.exit_code == 0 and out.stdout.split() == ["n", "6"]  # the note goes to stderr


def test_wilson_range_matches_a_known_value():
    low, high = wilson(8, 10)
    assert round(low, 3) == 0.490 and round(high, 3) == 0.943
