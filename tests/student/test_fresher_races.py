"""Fresher races (v3.42): each goal's own memory, the dice, and the 10 most different of 15;
the race fixes (v4.2): math identity, repeats per goal, review ids, fewer theme repeats."""

import random
import uuid
from datetime import date, timedelta

from lerni.student.concepts import ConceptStore, normalize
from lerni.student.interests import MapStore, add_goal, add_interest
from lerni.student.points import PointsStore
from lerni.student.race import (
    FORMATS,
    QUANTITY,
    QUESTIONS_PER_RACE,
    SET_SIZE,
    WRITE_SIZE,
    RaceDesk,
    check_questions,
    deal,
)
from lerni.student.results import question_hash

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
    month = TODAY - timedelta(days=20)  # inside each goal's 30 days of ideas
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


def test_a_goal_with_a_long_history_still_gets_its_turn():
    # review (v3.42): scoring by the closest of 30 old ideas left the most-asked goal out entirely
    from lerni.student.meaning import Meaning
    from lerni.student.race import Question, pick_varied

    def one(goal_id, concept):
        return Question("", f"About {concept}?", ("a", "b", "c"), 0, "Why.", concept, goal_id)

    vectors = {"old a": [1, 0, 0, 0, 0], "a1": [0.8, 0.6, 0, 0, 0], "a2": [0.8, 0, 0.6, 0, 0],
               "b1": [0, 0, 0, 1, 0], "b2": [0, 0, 0, 0, 1]}
    picked = pick_varied([one("A", "a1"), one("A", "a2"), one("B", "b1"), one("B", "b2")], 2,
                         Meaning(vectors), {"A": ["old a"], "B": []})
    assert {q.goal_id for q in picked} == {"A", "B"}  # each goal keeps its most novel one


def test_the_morning_write_ahead_survives_a_broken_account_list():
    # review (v3.42): one error stopped the 5:00 thread for good
    from lerni.student.web.app import write_ahead

    class Broken:
        def list_students(self):
            raise OSError("disk")

    write_ahead(object(), Broken())  # logs the kind and returns


def test_every_interest_gets_a_turn_and_new_bridges_come_first(tmp_path):
    import random

    from lerni.student.interests import add_interest, group, remove
    from lerni.student.race import deal, quiz_input

    maps = MapStore(tmp_path)
    made = {}

    def fill(m):
        made["Fractions"], made["Nouns"] = add_goal(m, "Fractions"), add_goal(m, "Nouns")
        for name in ("pizza", "trains", "baking", "volcanoes", "dogs", "space"):
            made[name] = add_interest(m, name)
        for kind in ("rockets", "planets"):  # kinds of space: one group with it
            made[kind] = add_interest(m, kind)
            group(m, made[kind].id, made["space"].id)
        remove(m, add_interest(m, "spiders").id)  # set aside: never a setting
        from lerni.student.interests import Link
        m.links.append(Link(made["pizza"].id, made["Fractions"].id, "bridge", "2026-11-01"))

    maps.change("sam", fill)
    m = maps.get("sam")
    used = {"trains": 2}  # trains framed the most questions lately
    slots = deal(m, ["Fractions", "Nouns"], used, random.Random(1))
    assert {s.goal for s in slots} == {"Fractions", "Nouns"} and all(s.setting for s in slots)
    firsts = [s.setting for s in slots]
    assert "spiders" not in " ".join(f"{s.setting} {s.second}" for s in slots)
    groups = {"rockets": "space", "planets": "space"}
    assert sum(groups.get(x, x) == "space" for x in firsts) <= 4  # one group, not three
    assert firsts.index("trains") >= 5  # the most used comes after the rest have had turns
    fractions = [s.setting for s in slots if s.goal == "Fractions"][:3]
    assert "pizza" not in fractions  # already bridged to Fractions: the others first
    prompt = quiz_input(m, TODAY, True, goals=["Fractions", "Nouns"], plan=slots)
    assert "1. Fractions, set in " in prompt or "1. Nouns, set in " in prompt
    assert "bridged from: pizza" in prompt
    # the setting Claude used reaches the ledger
    races = desk(tmp_path / "desk", None)

    class Setting(Quizzer):
        def write(self, system, prompt):
            return {"questions": [{**q("Fractions", n), "setting": "nowhere"} if n == 0 else
                                  q("Fractions", n) for n in range(WRITE_SIZE)]}

    races.quizzer = Setting()
    races.maps.change("sam", lambda m: add_interest(m, "trains") and None)
    unknown = check_questions({"questions": [{**q("Fractions", 1), "setting": "nowhere"}]},
                              races.maps.get("sam"))
    assert unknown[0].setting == ""  # not an interest on the map: left blank
    kept_named = check_questions({"questions": [{**q("Fractions", 1), "setting": "Trains"}]},
                                 races.maps.get("sam"))
    assert kept_named[0].setting == "trains"  # the map's spelling
    races._sets["sam"] = (TODAY.isoformat(), kept_named * QUESTIONS_PER_RACE)
    race = races.start("sam", supervised=True, today=TODAY)
    ledger = races.concepts.ledger("sam")
    assert race and any(c.get("setting") == "trains" for c in ledger)  # it reaches the ledger


def test_sets_written_ahead_rotate_and_due_goals_lead(tmp_path):
    # review (v3.43): held sets all started from the same counts; due goals were dealt last
    from dataclasses import replace

    from lerni.student.interests import add_interest

    races = desk(tmp_path, None)
    races.maps.change("sam", lambda m: [add_interest(m, n) for n in ("trains", "baking")] and None)
    fresh = races._write("sam", supervised=True, today=TODAY)
    held = [replace(k, setting="trains") for k in fresh]  # a set written ahead, all in trains
    races._sets["sam"] = (TODAY.isoformat(), held)
    nouns = races.maps.get("sam").find("Nouns")
    races.concepts.answered("sam", nouns.id, "naming words", False, TODAY - timedelta(days=1))
    races._write("sam", supervised=True, today=TODAY)
    plan = races.quizzer.prompts[-1].split("Question plan: ")[1]
    assert plan.startswith("1. Nouns, set in baking")  # the due goal first, the other interest


def test_math_labels_keep_their_operators_and_signs(tmp_path):
    # review (2026-11-10): "1/2 + 1/4" and "1/2 - 1/4" were one idea and one hash
    assert normalize("1/2 + 1/4") != normalize("1/2 - 1/4")
    assert normalize("-3") != normalize("3") and normalize("0.5") != normalize("0 5")
    assert normalize("top-speed vs 0–60") == normalize("top speed vs 0-60")  # words unchanged
    assert question_hash("What is 1/2 + 1/4?") != question_hash("What is 1/2 - 1/4?")
    concepts = ConceptStore(tmp_path)
    concepts.add("sam", [("g1", "Fractions", "1/2 + 1/4"), ("g1", "Fractions", "1/2 - 1/4")],
                 TODAY)
    assert len(concepts.ledger("sam")) == 2


def test_an_idea_asked_on_one_goal_is_new_on_another(tmp_path):
    # review (2026-11-10): the repeat check pooled every picked goal's history
    races = desk(tmp_path, None)

    class Shared(Quizzer):
        def write(self, system, prompt):
            return {"questions": [q("Nouns", 1, "halves of a pizza"),  # Fractions asked it
                                  q("Fractions", 2, "halves of a pizza"),  # its own repeat
                                  *(q("Fractions" if n % 2 else "Nouns", n)
                                    for n in range(3, WRITE_SIZE))]}

    races.quizzer = Shared()
    kept = races._write("sam", supervised=True, today=TODAY)
    ideas = {(k.goal, k.concept) for k in kept}
    assert ("Nouns", "halves of a pizza") in ideas
    assert ("Fractions", "halves of a pizza") not in ideas


def test_a_reworded_review_with_its_id_moves_that_review(tmp_path):
    # review (2026-11-10): a new label left the review due for good
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: [add_goal(m, "Fractions"), add_goal(m, "Nouns")] and None)
    raw = {"questions": [{**q("Fractions", 1, "sharing an odd count equally"), "review": "R1"},
                         {**q("Nouns", 2, "naming things you share"), "review": "R1"}]}
    kept = check_questions(raw, maps.get("sam"), reviews=[("Fractions", "halves of odd numbers")])
    assert [k.concept for k in kept] == ["halves of odd numbers", "naming things you share"]


def test_a_goal_spreads_its_interests_formats_and_records():
    # review (2026-11-10): goals and interests fell into step; quantity frames piled up
    from lerni.student.interests import InterestMap

    m = InterestMap()
    goals = [add_goal(m, name).name for name in ("Fractions", "Nouns", "Volume")]
    for name in ("pizza", "trains", "dogs"):  # 3 groups for 3 goals: in step before
        add_interest(m, name)
    for seed in range(40):
        slots = deal(m, goals, {}, random.Random(seed), n=9)
        for g in goals:
            mine = [s for s in slots if s.goal == g]
            assert len({s.setting for s in mine}) == len(mine) == 3
            assert sum(s.fmt in QUANTITY for s in mine) <= 1
        assert sum(s.twist.startswith("a record") for s in slots) <= 1


def test_one_car_comparison_across_both_tries(tmp_path):
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Speed") and None)
    two = {**q("Speed", 1), "question": "Which is quicker, the Mini or the Beetle?"}
    spare: list = []
    kept = check_questions({"questions": [two]}, maps.get("sam"), cars=["Mini", "Beetle"],
                           spare=spare, compared=1)
    assert kept == [] and len(spare) == 1  # the first try already compared two cars



def test_review_v42_a_rejected_question_leaves_its_review_id_free(tmp_path):
    # review (v4.2): a first question with "R1" and a wrong sum used up the id
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions") and None)
    wrong = {**q("Fractions", 1, "odd halves"), "review": "R1", "math": "7 / 2"}  # keys 4
    good = {**q("Fractions", 2, "sharing an odd count equally"), "review": "R1"}
    kept = check_questions({"questions": [wrong, good]}, maps.get("sam"),
                           reviews=[("Fractions", "halves of odd numbers")])
    assert [k.concept for k in kept] == ["halves of odd numbers"]


def test_review_v42_one_sum_written_two_ways_is_one_idea():
    for a, b in [("1/2 − 1/4", "1/2 - 1/4"), ("6 / 2", "6/2"), ("7-3", "7 - 3"),
                 ("3 × 4", "3 * 4"), ("x=-3", "x = -3")]:
        assert normalize(a) == normalize(b), (a, b)
    assert normalize("(-3)") != normalize("3") and normalize("top-speed") == "top speed"


def test_review_v42_a_connection_still_spreads_a_goals_interests():
    from lerni.student.interests import InterestMap

    m = InterestMap()
    goal = add_goal(m, "Fractions")
    for name in ("pizza", "trains", "dogs"):
        add_interest(m, name)
    for seed in range(60):
        slots = deal(m, ["Fractions"], {}, random.Random(seed), n=3,
                     targets={goal.id: ("trains", "a hook")})
        assert [s.setting for s in slots][:2] == ["trains", "trains"]  # it leads 2 of 3 (v3.44)
        assert slots[2].setting != "trains", seed  # the third goes elsewhere


def test_review_v42_a_sets_car_number_is_one_two_cars_have(tmp_path):
    from lerni.student.garage import Car

    races = desk(tmp_path, None)
    cars = [Car("a", "Mini", 10, "red", "", usd=20000, zero_to_60=9.0),
            Car("b", "Beetle", 10, "blue", "", usd=15000, zero_to_60=12.0, power_hp=80)]
    races.garage = type("G", (), {"in_reach": lambda self, owned, balance: cars})()
    for _ in range(6):
        races._write("sam", supervised=True, today=TODAY)
        assert "uses only: horsepower" not in races.quizzer.prompts[-1]  # only one has hp


def test_review_v43_a_review_never_races_twice_through_the_spare_fill(tmp_path):
    # review (v4.3): a spare already carried the review's label, so a short race asked it twice
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions") and None)
    first = {**q("Fractions", 1, "odd halves"), "review": "R1"}  # its words were asked: spare
    second = {**q("Fractions", 2, "sharing odd counts"), "review": "R1"}
    spare: list = []
    kept = check_questions({"questions": [first, second]}, maps.get("sam"), spare=spare,
                           texts=[normalize(first["question"])],
                           reviews=[("Fractions", "halves of odd numbers")])
    assert [k.concept for k in kept] == ["halves of odd numbers"]
    assert [s.concept for s in spare] == ["halves of odd numbers"]  # the review's own label
    from lerni.student.race import fill
    assert len(fill(kept, spare)) == 1  # the fill never races that idea twice


def test_review_v43_minus_signs_and_old_duplicate_reviews(tmp_path):
    assert normalize("x<-3") != normalize("x<3") and normalize("2^-3") != normalize("2^3")
    assert normalize("−x") != normalize("x") and normalize("x+-3") != normalize("x+3")
    assert normalize("top-speed") == "top speed"
    concepts = ConceptStore(tmp_path)
    old = TODAY - timedelta(days=3)
    concepts._change("sam", lambda ledger: ledger.extend(  # two spellings v4.2 kept apart
        {"concept": c, "goal_id": "g1", "goal": "Sums", "first": str(old), "last": str(old),
         "asked": 1, "right": 0, "due": str(old), "step": 0} for c in ("7-3", "7 - 3")))
    assert len(concepts.due("sam", TODAY)) == 1
