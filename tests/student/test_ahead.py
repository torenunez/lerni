"""v4.6.1: questions written ahead survive a restart, and go once their day ends."""

import json
from datetime import date

from lerni.student.ahead import AheadStore
from lerni.student.interests import MapStore, add_goal
from lerni.student.points import PointsStore
from lerni.student.race import RaceDesk
from tests.student.test_race import FakeQuizzer

TODAY = date.today()  # the desk loads today's file at start-up


def test_a_restart_keeps_the_questions_written_ahead(tmp_path):
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    first = FakeQuizzer()
    desk = RaceDesk(first, maps, PointsStore(tmp_path), ahead=AheadStore(tmp_path))
    desk.prefill("sam", supervised=True, races=2).wait(5)  # the morning write-ahead
    assert first.calls >= 1 and desk._held("sam", TODAY)
    later = FakeQuizzer()  # a deploy restarts the server
    again = RaceDesk(later, maps, PointsStore(tmp_path), ahead=AheadStore(tmp_path))
    race = again.start("sam", supervised=True)  # the next race needs no write
    assert race is not None and later.calls == 0
    kept = json.loads((tmp_path / "ahead" / "sam.json").read_text())["questions"]
    assert len(kept) == len(again._held("sam", TODAY))  # the raced ones left the file


def test_an_earlier_days_questions_are_deleted(tmp_path):
    store = AheadStore(tmp_path)
    store.save("sam", date(2026, 1, 1), [{"question": "Old?"}], [])  # a day that has ended
    assert store.load(TODAY) == {}  # never held again
    assert store.purge(TODAY) == 1 and not (tmp_path / "ahead" / "sam.json").exists()
