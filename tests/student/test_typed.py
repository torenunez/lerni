"""v4.11: typed questions in races: one of each kind, the neediest gets more, the cars move as
for a choice, and nothing typed is kept."""

import random
from datetime import date, timedelta

from lerni.student.blocks import MAX_LEVEL, BlocksDesk, BlocksStore, question, typed_number
from lerni.student.interests import MapStore, add_goal, add_interest
from lerni.student.points import PointsStore
from lerni.student.race import BONUS_AT, QUESTIONS_PER_RACE, RaceDesk, mix, need, public
from lerni.student.results import ResultsLog
from lerni.student.spelling import SpellingDesk, SpellingStore
from tests.student.test_race import FakeQuizzer

TODAY = date(2026, 11, 17)


class Voice:
    """Says anything; spelling words come slowly."""

    def speak(self, text):
        return b"audio"

    def dictate(self, pieces):
        return b"slow audio"


def math_map(m):
    add_goal(m, "Fractions").area = "Math"  # the fake writes for it; a Math goal: blocks come
    add_interest(m, "dinosaurs")  # drawn as 🦕


def test_a_race_mixes_kinds_and_a_typed_answer_moves_the_cars(tmp_path):
    maps, points, results = MapStore(tmp_path), PointsStore(tmp_path), ResultsLog(tmp_path)
    maps.change("sam", math_map)
    spelling = SpellingDesk(SpellingStore(tmp_path), maps, speech=Voice())  # no Claude
    spelling.set_class_list("sam", "because", TODAY)
    desk = RaceDesk(FakeQuizzer(), maps, points, results=results)
    desk.sources = {"spell": spelling, "picture": BlocksDesk(BlocksStore(tmp_path), maps)}
    desk.prefill = lambda *args: None  # no writing ahead in the background
    ticks = iter(range(0, 1000, 10))
    desk.clock = lambda: float(next(ticks))  # each answer a moment after the last
    race = desk.start("sam", supervised=True, today=TODAY)
    kinds = [t.kind for t in race.typed.values()]
    assert set(kinds) == {"picture", "spell"} and len(kinds) < QUESTIONS_PER_RACE  # and choices
    for n in range(QUESTIONS_PER_RACE):
        t = race.typed.get(n)
        if t is None:  # a choice
            assert desk.typed_answer("sam", race.id, n, "4", TODAY)[1] is None  # typing: ignored
            desk.pick("sam", race.id, n, race.questions[n].answer)
            continue
        view = public(race)
        assert view["typed"] == t.kind and t.key not in str(view.get("prompt"))  # no answer
        assert desk.pick("sam", race.id, n, 0)[1] is None  # a tap on a typed slot: ignored
        typed = "Because " if t.kind == "spell" else "zqx 999"  # the word right, a number wrong
        _, turn, awarded = desk.typed_answer("sam", race.id, n, typed, TODAY)
        assert turn.right is (t.kind == "spell") and turn.answer == t.key
    assert race.done and points.get("sam").balance == awarded > 0  # pays at the finish
    assert desk.read_aloud("sam", race.id, 0) is None  # the race is over: nothing to read
    words = {w["word"]: w for w in SpellingStore(tmp_path).get("sam")["words"]}
    assert words["because"]["due"] == (TODAY + timedelta(days=1)).isoformat()  # box 1
    assert BlocksStore(tmp_path).get("sam")["recent"] == [False] * kinds.count("picture")
    rows = results.read("sam")
    assert {r.get("kind") for r in rows if "right" in r} >= {"spell", "picture"}
    # rule 6: what was typed is never on disk
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert not any(b"zqx" in p.read_bytes() for p in files)


def test_the_neediest_kind_gets_the_spare_slots_and_the_bonus_spot_stays_a_choice():
    order = mix({"choice": 0.1, "spell": 0.9, "picture": 0.2})
    assert sorted(order) == ["choice", "picture", "spell", "spell", "spell"]
    assert all(a != b for a, b in zip(order, order[1:], strict=False))  # spread out
    assert mix({"choice": 0.5}) == ["choice"] * QUESTIONS_PER_RACE  # nothing else available
    lucky = mix({"choice": 0.0, "spell": 1.0, "picture": 1.0}, lucky=True)
    assert lucky[BONUS_AT] == "choice" and lucky.count("choice") == 1
    assert need(0, 0, 0) == 0.5 and need(3, 10, 10) == 0.8  # no history; misses plus due


def test_each_blocks_answer_matches_its_drawing():
    rng = random.Random(7)
    for level in range(1, MAX_LEVEL + 1):
        for _ in range(20):
            _, answer, draw, _ = question(level, rng)
            if draw["empty"]:  # the missing piece: the pile shared into the rows
                assert answer * draw["rows"] == draw["total"]
            else:
                assert answer == draw["rows"] * draw["cols"]
    assert typed_number(" 1 2 ") == 12 and typed_number("12a") is None
