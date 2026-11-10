"""Fresher races (v3.42): each goal's own memory, the dice, and the 10 most different of 15."""

import uuid
from datetime import date, timedelta

from lerni.student.concepts import ConceptStore
from lerni.student.interests import MapStore, add_goal
from lerni.student.points import PointsStore
from lerni.student.race import FORMATS, SET_SIZE, WRITE_SIZE, RaceDesk, check_questions

TODAY = date(2026, 11, 10)


class TopicEmbedder:
    """A fake: texts sharing a topic word match fully; every other text is its own direction."""

    TOPICS = ("pizza", "speed")

    def __init__(self, fail: bool = False):
        self.fail, self.dims = fail, {}

    def embed(self, texts):
        if self.fail:
            raise OSError("no model")
        keys = [next((k for k in self.TOPICS if k in t.casefold()), t.casefold()) for t in texts]
        for key in keys:
            self.dims.setdefault(key, len(self.dims))
        return [[1.0 if i == self.dims[key] else 0.0 for i in range(len(self.dims))]
                for key in keys]


def q(goal: str, n: int, concept: str = "", fmt: str = "") -> dict:
    words = uuid.uuid5(uuid.NAMESPACE_OID, str(n)).hex  # unlike every other question's words
    return {"goal": goal, "question": f"Question {words} {goal}?", "choices": ["4", "2", "6"],
            "answer": 0, "why": "Because.", "concept": concept or f"{goal} idea {n}",
            "format": fmt or FORMATS[n % len(FORMATS)]}


class Quizzer:
    """Writes 15: one rewords an old idea; keeps the prompts it was sent."""

    def __init__(self):
        self.prompts = []

    def write(self, system, prompt):
        self.prompts.append(prompt)
        plain = [q("Fractions" if n % 2 else "Nouns", n) for n in range(WRITE_SIZE - 1)]
        return {"questions": [*plain, q("Fractions", 99, "a pizza cut in half")]}


def desk(tmp_path, embedder):
    maps, concepts = MapStore(tmp_path), ConceptStore(tmp_path)
    ids = {}
    maps.change("sam", lambda m: ids.update(
        {name: add_goal(m, name).id for name in ("Fractions", "Nouns")}))
    month = TODAY - timedelta(days=20)  # beyond today's 14 days and 40 labels, inside 30
    concepts.add("sam", [(ids["Fractions"], "Fractions", "halves of a pizza"),
                         (ids["Nouns"], "Nouns", "naming words")], month)
    return RaceDesk(Quizzer(), maps, PointsStore(tmp_path), concepts, embedder=embedder)


def test_each_goal_remembers_its_ideas_and_the_ten_most_different_race(tmp_path, capsys):
    races = desk(tmp_path, TopicEmbedder())
    kept = races._write("sam", supervised=True, today=TODAY)
    prompt = races.quizzer.prompts[0]
    fractions = next(line for line in prompt.splitlines() if line.startswith("- Fractions"))
    assert "halves of a pizza" in fractions and "naming words" not in fractions  # its own ideas
    plan = prompt.split("Question plan")[1]
    assert sum(f in plan for f in FORMATS) >= 4  # the dice: several formats rolled
    assert len(kept) == SET_SIZE  # 15 written, the 10 most different kept
    assert "a pizza cut in half" not in [k.concept for k in kept]  # an old idea, reworded
    assert len({k.format for k in kept}) >= 4
    out = capsys.readouterr().out
    assert f"Race set: {WRITE_SIZE} written, {SET_SIZE} kept" in out and "Question" not in out
    # at most one question a set compares two of their cars
    raw = {"questions": [{**q("Fractions", n), "question": f"Is the Zoom GT or Bolt RS faster {n}?"}
                         for n in range(3)]}
    spare = []
    one = check_questions(raw, races.maps.get("sam"), cars=["Zoom GT", "Bolt RS"], spare=spare)
    assert len(one) == 1 and len(spare) == 2


def test_without_the_meaning_model_ten_still_race_dealt_by_format(tmp_path):
    kept = desk(tmp_path, TopicEmbedder(fail=True))._write("sam", supervised=True, today=TODAY)
    assert len(kept) == SET_SIZE and len({k.format for k in kept}) >= 4


def test_the_morning_write_ahead_holds_a_few_races(tmp_path):
    from datetime import datetime

    from lerni.student.race import AHEAD_RACES, QUESTIONS_PER_RACE, seconds_until

    class Fresh(Quizzer):  # new ideas every call
        def write(self, system, prompt):
            self.prompts.append(prompt)
            start = 100 * len(self.prompts)
            return {"questions": [q("Fractions" if n % 2 else "Nouns", n)
                                  for n in range(start, start + WRITE_SIZE)]}

    races = desk(tmp_path, None)
    races.quizzer = Fresh()
    races.prefill("sam", supervised=True, races=AHEAD_RACES).wait(10)  # in the background
    held = races._held("sam", date.today())
    assert len(held) >= AHEAD_RACES * QUESTIONS_PER_RACE and len(races.quizzer.prompts) == 2
    assert seconds_until(5, datetime(2026, 11, 10, 23, 0)) == 6 * 3600  # next 5:00, tomorrow


def test_a_race_never_waits_for_the_write_ahead_to_finish(tmp_path, monkeypatch):
    # regression (v3.42 build): a tap during the morning write waited for its second write too
    import threading
    import time

    import lerni.student.race as race

    gate = threading.Event()

    class SlowSecond(Quizzer):  # the first set comes at once, the second waits for the gate
        def write(self, system, prompt):
            self.prompts.append(prompt)
            if len(self.prompts) > 1:
                gate.wait(10)
            start = 100 * len(self.prompts)
            return {"questions": [q("Fractions" if n % 2 else "Nouns", n)
                                  for n in range(start, start + WRITE_SIZE)]}

    monkeypatch.setattr(race, "QUIZ_WAIT_SECONDS", 5)
    races = desk(tmp_path, None)
    races.quizzer = SlowSecond()
    done = races.prefill("sam", supervised=True, races=race.AHEAD_RACES)
    while len(races.quizzer.prompts) < 2:  # the second write has begun
        time.sleep(0.01)
    began = time.monotonic()
    races.start("sam", supervised=True)
    assert time.monotonic() - began < 1  # raced on the first set, not after the second
    gate.set()
    done.wait(10)
