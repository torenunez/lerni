"""v4.13: reading races: a passage, five questions of three kinds (a tap, an order, an open
answer with one nudge), the reading level, and nothing said or typed kept."""

from datetime import date

import pytest

from lerni.student.interests import MapStore, add_interest
from lerni.student.points import PointsStore
from lerni.student.race import CHECK_SCHEMA, QUESTIONS_PER_RACE, RaceDesk
from lerni.student.reading import (
    GRADE_OPEN_SCHEMA,
    READ_SCHEMA,
    ReadingDesk,
    ReadingStore,
    check_passage,
    fk_grade,
)
from lerni.student.results import ResultsLog
from tests.student.test_race import FakeQuizzer

pytestmark = pytest.mark.ci  # run on each PR by GitHub

TODAY = date(2026, 11, 17)
TEXT = (
    'A hare liked to brag. "I am the fastest!" he said. A tortoise said, "Let us race." '
    "The hare ran far ahead. He sat down by a tree. Soon he fell asleep.\n\n"
    "The tortoise did not stop. Step by step, he went on. He passed the sleeping hare. "
    "The hare woke up and ran. But it was too late. The tortoise won the race. Slow and "
    "steady can win. The hare was sad, and the tortoise was glad. They both learned a lot "
    "that day."
)
PASSAGE = {  # as Claude would write it; the order sentences come back shuffled
    "title": "The Tortoise and the Hare", "text": TEXT, "question": "Who won the race?",
    "choices": ["The hare", "The tortoise", "A tree"], "answer": 1,
    "why": "The tortoise passed the sleeping hare.",
    "order": ["The tortoise won the race.", "The hare ran far ahead.", "Soon he fell asleep."],
    "open_question": "Describe the hare with 2 describing words.",
    "key_ideas": ["fast", "boastful", "sleepy"],
}


class FakeReader:
    """Writes the passage, agrees with it blind, and grades open answers by a word in them."""

    def write(self, system, prompt, schema, timeout=0):
        if schema is READ_SCHEMA:
            return PASSAGE
        if schema is CHECK_SCHEMA:  # a story (A), and the tortoise (B)
            return {"picks": [{"work": "", "pick": "A"}, {"work": "", "pick": "B"}]}
        assert schema is GRADE_OPEN_SCHEMA
        if "bold zqx" in prompt:  # describing words: right
            return {"right": True, "line": "Great describing words!", "describing": 2,
                    "bare": "", "care": False}
        if "zqxrabbit" in prompt:  # a bare noun: the nudge
            return {"right": True, "line": "Yes!", "describing": 0, "bare": "rabbit",
                    "care": False}
        return {"right": True, "line": "Yes, it has characters.", "describing": 0, "bare": "",
                "care": False}


def test_a_reading_race_asks_five_kinds_nudges_once_and_keeps_nothing_said(tmp_path):
    maps, points, results = MapStore(tmp_path), PointsStore(tmp_path), ResultsLog(tmp_path)
    maps.change("sam", lambda m: add_interest(m, "racing"))
    reading = ReadingDesk(ReadingStore(tmp_path), maps, writer=FakeReader(), fetch=lambda u: "")
    desk = RaceDesk(FakeQuizzer(), maps, points, results=results)
    desk.reading, desk.sources = reading, {"read": reading}
    desk.prefill = lambda *args: None  # no writing ahead in the background
    ticks = iter(range(0, 1000, 10))
    desk.clock = lambda: float(next(ticks))  # each answer a moment after the last
    points.start_race("sam", TODAY)  # one race already today: the 2nd is a reading race
    p = reading.write("sam", supervised=True, today=TODAY)
    assert p.order == ("The hare ran far ahead.", "Soon he fell asleep.",
                       "The tortoise won the race.")  # the text's order, not Claude's
    reading.store.hold("sam", p)
    race = desk.start("sam", supervised=True, today=TODAY)
    assert race.passage == p and not (tmp_path / "reading" / "ahead" / "sam.json").exists()
    assert [race.typed[n].label.split(":")[1] for n in (1, 3, 4)] == ["why", "order", "open"]
    desk.pick("sam", race.id, 0, race.questions[0].answer)  # a story
    assert desk.answer_bonus("sam", race.id, 1, "zqx it has characters")[1].right  # said aloud
    desk.pick("sam", race.id, 2, race.questions[2].answer)  # the tortoise
    assert desk.typed_answer("sam", race.id, 3, race.typed[3].key, TODAY)[1].right  # in order
    _, turn, _ = desk.answer_bonus("sam", race.id, 4, "a zqxrabbit")  # a bare noun
    assert turn is None and race.nudge.startswith("What kind of rabbit") and race.answered == 4
    _, turn, awarded = desk.answer_bonus("sam", race.id, 4, "a bold zqxrabbit")
    assert turn.right and race.done and race.right == QUESTIONS_PER_RACE and awarded > 0
    assert reading.store.get("sam")["level"] == 2  # five right: the level moves up
    # regression (review): a nudged answer counts once, and question 2 not at all
    assert [r["n"] for r in reading.store.get("sam")["open"]] == [2]
    rows = [r for r in results.read("sam") if r.get("kind") == "read"]
    assert len(rows) == QUESTIONS_PER_RACE  # every answer logged as a label
    # rule 6: nothing said or typed is on disk
    files = [f for f in tmp_path.rglob("*") if f.is_file()]
    assert not any(b"zqx" in f.read_bytes() for f in files)


def test_the_checks_drop_a_passage_whose_order_sentences_arent_in_it():
    made_up = {**PASSAGE, "order": ["The hare ran far ahead.", "Soon he fell asleep.",
                                    "The hare flew home on a kite."]}
    assert check_passage(made_up, "narrative", 1, "Aesop", TODAY) is None
    assert check_passage(PASSAGE, "narrative", 1, "Aesop", TODAY) is not None


def test_harder_text_measures_a_higher_grade():
    easy = "The cat sat on the mat. The dog ran to the cat. They had fun."
    hard = ("Paleontologists meticulously investigate fossilized organisms, reconstructing "
            "evolutionary relationships between extinct marine reptiles and modern species.")
    assert fk_grade(easy) < 2 < 10 < fk_grade(hard)


def test_a_failed_write_waits_an_hour_and_none_comes_after_the_last_reading_race(tmp_path):
    # regression (review): Claude was asked again on every race start while writes failed
    calls = []

    class Failing:
        def write(self, *args, **kwargs):
            calls.append(1)
            raise TimeoutError

    reading = ReadingDesk(ReadingStore(tmp_path), MapStore(tmp_path), writer=Failing(),
                          fetch=lambda u: "")
    reading.prefill("sam", True, TODAY, started=0)  # before the 1st race: nothing
    assert not reading._busy and not calls
    for _ in range(2):  # the 2nd try comes within the hour: skipped
        reading.prefill("sam", True, TODAY, started=1)
        for worker in list(reading._busy.values()):
            worker.join()
    assert len(calls) == 1
    reading.store._change("sam", lambda d: d.update(day=TODAY.isoformat(), today=3))
    reading._failed.clear()
    reading.prefill("sam", True, TODAY, started=8)  # all 3 reading races raced today
    assert not reading._busy and len(calls) == 1
