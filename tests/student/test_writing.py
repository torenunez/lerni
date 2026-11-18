"""v4.14: writing races: a paragraph after the day's reading race, a checklist graded by code
and Claude, one revision, the cars moved per item, misspellings suggested to the educator, and
the paragraph kept only in the conversation log."""

import pytest

from lerni.student.interests import MapStore, add_interest
from lerni.student.points import PointsStore
from lerni.student.race import QUESTIONS_PER_RACE, RaceDesk
from lerni.student.reading import READ_SCHEMA, ReadingDesk, ReadingStore
from lerni.student.results import ResultsLog
from lerni.student.spelling import SpellingDesk, SpellingStore
from lerni.student.writing import GRADE_SCHEMA, WritingDesk, WritingStore, capitals_ok, summary
from tests.student.test_race import FakeQuizzer
from tests.student.test_reading import PASSAGE, TODAY, FakeReader

pytestmark = pytest.mark.ci  # run on each PR by GitHub

DRAFT = ("I would be the tortoise. The tortoise kept walking zqx. The hare took a nap and "
         "lost. i like it becuase it is slow")  # no capital I, no last period, no wrap-up
BETTER = ("I would be the tortoise. The slow tortoise kept walking zqx. The fast hare took a "
          "nap and lost. I like it because it is steady. Slow and steady wins!")


class FakeWriter(FakeReader):
    """The reading race's passage with its two prompts, then a checklist grade: the draft
    misses describing words and a wrap-up, the revision meets everything."""

    def write(self, system, prompt, schema, timeout=0):
        if schema is READ_SCHEMA:  # the passage, with its two writing prompts
            return {**PASSAGE, "respond": "Would you rather be the tortoise or the hare?",
                    "create": "Write about a race car you'd build."}
        if schema is not GRADE_SCHEMA:
            return super().write(system, prompt, schema, timeout)
        first = "First try met" not in prompt  # a revision carries the first checklist
        return {"first": True, "details": True, "describing": 1 if first else 3,
                "wrap": not first, "well": "You picked a side.", "tip": "Add an ending.",
                "misspelled": ["because"] if first else [], "care": False}


class MemoryLog:
    """The conversation log, in memory: the one place a paragraph may go."""

    def __init__(self):
        self.rows = []

    def write(self, username, row):
        self.rows.append(row)


def test_a_writing_race_follows_reading_grades_twice_and_keeps_only_numbers(tmp_path):
    maps, points, results = MapStore(tmp_path), PointsStore(tmp_path), ResultsLog(tmp_path)
    maps.change("sam", lambda m: add_interest(m, "racing"))
    writer, log = FakeWriter(), MemoryLog()
    reading = ReadingDesk(ReadingStore(tmp_path), maps, writer=writer, fetch=lambda u: "")
    spelling = SpellingDesk(SpellingStore(tmp_path), maps)
    desk = RaceDesk(FakeQuizzer(), maps, points, results=results)
    desk.reading, desk.sources = reading, {"read": reading}
    desk.writing = WritingDesk(WritingStore(tmp_path), writer=writer, spelling=spelling, log=log)
    desk.prefill = lambda *args: None  # no writing ahead in the background
    ticks = iter(range(0, 1000, 10))
    desk.clock = lambda: float(next(ticks))  # each tap a moment after the last
    points.start_race("sam", TODAY)  # one race already: the 2nd is a reading race
    reading.store.hold("sam", reading.write("sam", supervised=True, today=TODAY))
    read = desk.start("sam", supervised=True, today=TODAY)
    desk.pick("sam", read.id, 0, read.questions[0].answer)  # into the reading race
    race = desk.start("sam", supervised=True, today=TODAY)  # the next: the paragraph
    # the draft: 2 items met, so a revision may come
    assert race.paragraph.kind == "respond" and race.passage is not None
    assert desk.pick("sam", race.id, 0, 0)[1] is None  # a tap never answers it
    _, graded, awarded = desk.paragraph_answer("sam", race.id, DRAFT, today=TODAY)
    assert graded.marks == (True, True, False, False, False) and not race.done and not awarded
    _, graded, awarded = desk.paragraph_answer("sam", race.id, BETTER, today=TODAY)
    assert graded.all_done and len(graded.better) == 3 and race.done and awarded > 0
    assert race.right == QUESTIONS_PER_RACE  # one right step per checklist item
    s = summary(desk.writing.store, "sam", TODAY)  # numbers only
    assert s["paragraphs"] == 1 and set(s["met"].values()) == {1} and s["better"] == 1
    assert len([r for r in results.read("sam") if r.get("kind") == "write"]) == 5
    assert desk.start("sam", True, today=TODAY).paragraph is None  # one a day
    # a misspelling reaches the educator as its right spelling, added only on a tap
    assert spelling.summary("sam")["suggested"] == ["because"]
    assert spelling.add_suggested("sam", ["because"]) == 1
    assert "because" in spelling.summary("sam")["practice"]
    # code checks capitals and periods
    assert capitals_ok(BETTER) and not capitals_ok(DRAFT)
    # rule 6: the paragraph only in the conversation log, never on disk elsewhere
    assert [r["tags"]["writing"] for r in log.rows] == ["draft", "revision"]
    files = [f for f in tmp_path.rglob("*") if f.is_file()]
    assert not any(b"zqx" in f.read_bytes() for f in files)
    assert not desk.writing.store.get("sam")["prompts"]  # raced: the prompts are gone
