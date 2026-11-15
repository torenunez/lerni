"""v4.6.3: goal priorities and a fair share; the morning write-ahead tries again."""

from collections import Counter
from types import SimpleNamespace

from lerni.student.adapters.claude_code import _failed
from lerni.student.interests import InterestMap, add_goal, rank_of, set_area_rank, set_rank
from lerni.student.race import pick_goals
from lerni.student.students import Kind
from lerni.student.web.app import morning_tries


def test_shares_follow_priorities_and_a_goal_can_differ_from_its_area():
    m = InterestMap()
    goals = {}
    for name, area in (("Fractions", "Math"), ("Decimals", "Math"), ("Rain", "Science"),
                       ("Plants", "Science"), ("Rhythm", "Music")):
        goals[name] = add_goal(m, name)
        goals[name].area = area
    set_area_rank(m, "math", 1)  # High
    set_area_rank(m, "Music", 1)
    set_rank(m, goals["Rhythm"].id, 3)  # its own: Low, though Music is High
    assert rank_of(m, goals["Fractions"]) == 1 and rank_of(m, goals["Rhythm"]) == 3
    assert rank_of(m, goals["Rain"]) == 2  # an area nobody set is Medium
    tally: dict[str, tuple[int, int]] = {}
    count = Counter()
    for _ in range(90):  # one goal a set, each answered about 3 in 4 right (no nudge)
        e = pick_goals(m, tally, k=1)[0]
        asked, _ = tally.get(e.id, (0, 0))
        tally[e.id] = (asked + 1, round(0.75 * (asked + 1)))
        count[e.name] += 1
    high = count["Fractions"] + count["Decimals"]
    medium = count["Rain"] + count["Plants"]
    assert 1.8 <= high / medium <= 2.2  # High gets twice Medium
    assert 0.4 <= count["Rhythm"] / count["Rain"] <= 0.6  # Low gets half


def test_a_failed_morning_is_tried_again():
    # 2026-11-13 and 14: the 5:00 calls failed, and nothing tried again that day
    calls = []

    def morning(username):
        calls.append(username)
        if len(calls) == 1:
            raise RuntimeError("Claude was busy")  # the first try fails

    races = SimpleNamespace(purge_ahead=lambda day: 0, prefill=lambda *a, **k: None)
    sam = SimpleNamespace(username="sam", kind=Kind.SUPERVISED, archived=False)
    students = SimpleNamespace(list_students=lambda: [sam])
    morning_tries(races, students, morning, wait=lambda seconds: None)
    assert len(calls) >= 2  # tried again after the failure


def test_a_failed_call_logs_why_without_its_text(capsys):
    # 2026-11-13: the log said only "ResultError", so no one could tell why
    class ResultError(Exception):
        terminal_reason, api_error_status = "api_error", 529

    _failed(None, "small model", ResultError("API Error: the prompt's private words"))
    out = capsys.readouterr().out
    assert "ResultError (api_error, 529)" in out and "private" not in out
