"""Race rules: the finish depends only on how many were right; bad questions never race."""

import random
import time
import uuid
from datetime import date, timedelta

import pytest

from lerni.student.concepts import ConceptStore, normalize
from lerni.student.interests import InterestMap, MapStore, add_goal, add_interest, remove
from lerni.student.points import RACES_PER_DAY, PointsError, PointsStore
from lerni.student.race import (
    QUESTIONS_PER_RACE,
    Question,
    RaceDesk,
    RaceUnavailable,
    answer,
    check_questions,
    new_race,
    place,
    public,
    quiz_input,
    race_points,
)

TODAY = date(2026, 10, 13)
Q = Question("Fractions", "Half of 8 laps?", ("4", "2", "6"), 0, "Half means 2 equal parts.")


def finish(rights: list[bool]):
    race = new_race([Q] * QUESTIONS_PER_RACE)
    for n, ok in enumerate(rights):
        answer(race, n, 0 if ok else 1)
    return race


def test_places_depend_only_on_how_many_were_right():
    for rights, expected in [([True] * 5, 1), ([False] + [True] * 4, 1), ([True] * 4 + [False], 1),
                             ([True] * 3 + [False] * 2, 2), ([False] * 2 + [True] * 3, 2),
                             ([True] * 2 + [False] * 3, 3), ([False] * 5, 3)]:
        race = finish(rights)
        assert race.done and place(race) == expected, rights
    assert race_points(finish([True] * 5)) == 15 + 5 and race_points(finish([False] * 5)) == 5


def test_a_repeat_tap_is_ignored_and_the_page_never_sees_the_answer():
    race = new_race([Q] * QUESTIONS_PER_RACE)
    assert answer(race, 0, 0) is not None and answer(race, 0, 0) is None  # the same question twice
    assert race.answered == 1
    shown = public(race)
    assert set(shown) == {"race", "number", "question", "choices"} and "why" not in str(shown)


def test_bad_or_off_map_questions_are_dropped_and_shuffling_keeps_the_right_answer():
    m = InterestMap()
    add_goal(m, "Fractions")
    remove(m, add_interest(m, "sharks").id)  # set aside: never in a question
    good = {"goal": "Fractions", "question": "Half of 8 laps?", "choices": ["4", "2", "6"],
            "answer": 0, "why": "Half means 2 equal parts.", "concept": "halves"}
    raw = {"questions": [
        good,
        {**good, "choices": ["4", "4", "6"]},  # not three different choices
        {**good, "answer": 3},  # no such choice
        {**good, "goal": "Spelling"},  # not a goal on the map
        {**good, "question": "How fast do sharks swim? " + "x" * 10},  # set aside
        {**good, "question": "y" * 141},  # too long
    ]}
    kept = check_questions(raw, m, random.Random(1))
    assert len(kept) == 1 and kept[0].choices[kept[0].answer] == "4"
    text = quiz_input(m, TODAY, supervised=True)
    assert "Fractions" in text and "sharks" in text  # listed only as never to use


def fresh(goal: str, why: str = "Half means 2 equal parts.", **extra) -> dict:
    """One good question unlike any other: its own text and concept."""
    tag = uuid.uuid4().hex
    return {"goal": goal, "concept": tag[:12], "question": f"What is {tag}?",
            "choices": ["4", "2", "6"], "answer": 0, "why": why, **extra}


class FakeQuizzer:
    """Returns ten good questions, or something useless, and counts its calls."""

    def __init__(self, good: bool = True, fail: bool = False,
                 why: str = "Half means 2 equal parts."):
        self.good, self.fail, self.why, self.calls = good, fail, why, 0

    def write(self, system, prompt):
        self.calls += 1
        if self.fail:
            raise RaceUnavailable("Lerni is resting until Mon 6:00 pm. 😴")
        items = [fresh("Fractions", self.why) for _ in range(10)]
        return {"questions": items if self.good else [{"goal": "x"}]}


def desk_for(tmp_path, quizzer):
    maps, points = MapStore(tmp_path), PointsStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    return RaceDesk(quizzer, maps, points), points


def test_a_race_awards_once_at_the_finish_and_ignores_stale_taps(tmp_path):
    desk, points = desk_for(tmp_path, FakeQuizzer())
    ticks = iter(range(0, 1000, 10))
    desk.clock = lambda: float(next(ticks))  # a student reads each question first
    race = desk.start("sam", supervised=True, today=TODAY)
    for n in range(QUESTIONS_PER_RACE):
        q = race.questions[n]
        assert desk.pick("sam", "old-race", n, q.answer)[1] is None  # another screen's race
        _, turn, awarded = desk.pick("sam", race.id, n, q.answer)
        assert turn is not None and turn.right
        assert desk.pick("sam", race.id, n, q.answer)[1] is None  # a double tap
    assert awarded == 20 and points.get("sam").balance == 20
    assert desk.start("sam", supervised=True, today=TODAY).questions  # the second race of the set


def test_no_questions_means_no_race_and_no_race_used(tmp_path):
    for n, quizzer in enumerate((FakeQuizzer(good=False), FakeQuizzer(fail=True))):
        desk, points = desk_for(tmp_path / str(n), quizzer)
        with pytest.raises(RaceUnavailable):
            desk.start("sam", supervised=True, today=TODAY)
        assert points.races_left("sam", TODAY) == RACES_PER_DAY


def test_the_day_limit_stops_before_asking_claude(tmp_path):
    quizzer = FakeQuizzer()
    desk, points = desk_for(tmp_path, quizzer)
    for _ in range(RACES_PER_DAY):
        points.start_race("sam", TODAY)
    with pytest.raises(PointsError):
        desk.start("sam", supervised=True, today=TODAY)
    assert quizzer.calls == 0


class SlowQuizzer(FakeQuizzer):
    """Takes a moment, like Claude, and writes five questions per goal."""

    def write(self, system, prompt):
        import time

        self.calls += 1
        time.sleep(0.3)
        return {"questions": [fresh("Fractions") for _ in range(5)]
                + [fresh("Acceleration") for _ in range(5)]}


def test_a_race_waits_for_questions_being_written_and_mixes_the_goals(tmp_path):
    quizzer = SlowQuizzer()
    desk, _ = desk_for(tmp_path, quizzer)
    desk.maps.change("sam", lambda m: add_goal(m, "Acceleration"))
    desk.prefill("sam", supervised=True)  # opening Games starts writing
    race = desk.start("sam", supervised=True)  # a quick tap on Race
    assert quizzer.calls == 1  # regression: the tap asked Claude a second time
    assert {q.goal for q in race.questions} == {"Fractions", "Acceleration"}  # not five of one


def test_a_goal_named_with_its_notes_still_counts():
    m = InterestMap()
    add_goal(m, "Fractions", "halves and quarters")
    item = {"goal": "Fractions (halves and quarters)", "question": "Half of 8 laps?",
            "choices": ["4", "2", "6"], "answer": 0, "why": "Half means 2 equal parts.",
            "concept": "halves"}
    kept = check_questions({"questions": [item]}, m)  # regression: every one was dropped
    assert [q.goal for q in kept] == ["Fractions"]


def test_quick_second_taps_never_answer_unseen_or_start_a_second_race(tmp_path):
    now = [100.0]
    desk, points = desk_for(tmp_path, FakeQuizzer())
    desk.clock = lambda: now[0]
    race = desk.start("sam", supervised=True, today=TODAY)
    assert desk.start("sam", supervised=True, today=TODAY) is race  # regression: a second tap
    assert points.races_left("sam", TODAY) == RACES_PER_DAY - 1  # counted once
    assert desk.pick("sam", race.id, 0, 0)[1] is not None
    # regression: a second button 0.2 s later answered question 2 unseen
    assert desk.pick("sam", race.id, 1, 0)[1] is None
    now[0] += 1.0
    assert desk.pick("sam", race.id, 1, 0)[1] is not None


def test_matched_rivals_place_by_right_answers_in_any_car():
    def finish_with(boost, right):
        race = new_race([Q] * QUESTIONS_PER_RACE, boost=boost)
        for n in range(QUESTIONS_PER_RACE):
            answer(race, n, 0 if n < right else 1)
        return place(race)

    for boost in (1.0, 1.2, 1.4):  # a faster car brings new rivals, not easier wins
        assert [finish_with(boost, r) for r in range(6)] == [3, 3, 3, 2, 1, 1], boost
    race = new_race([Q] * QUESTIONS_PER_RACE, rivals=(("Mustang", "m"), ("Bolt", "muscle")))
    assert answer(race, 0, 0).slowed == "Mustang"  # everyone starts level: the fast one is named
    answer(race, 1, 0)
    assert place(race) == 1 and answer(race, 2, 0).slowed == ""  # leading: no rival is ahead


def test_set_aside_matches_whole_words_and_the_why_too():
    # regression: "car" dropped a question about cards; a set-aside name slipped in through "why"
    m = InterestMap()
    add_goal(m, "Fractions")
    remove(m, add_interest(m, "great white").id)
    remove(m, add_interest(m, "car").id)
    good = {"goal": "Fractions", "question": "Half of 8 cards?", "choices": ["4", "2", "6"],
            "answer": 0, "why": "Half means 2 equal parts.", "concept": "halves"}
    raw = {"questions": [good, {**good, "why": "Like 2 cars in 4."},
                         {**good, "question": "Half of a Great White's 8 fins?"}]}
    kept = check_questions(raw, m, random.Random(1))
    assert [q.question for q in kept] == ["Half of 8 cards?"]


def test_no_questions_are_written_once_the_days_races_are_used(tmp_path):
    # regression: opening Games at the limit still asked Claude
    quizzer = FakeQuizzer()
    desk, points = desk_for(tmp_path, quizzer)
    for _ in range(RACES_PER_DAY):
        points.start_race("sam")
    desk.prefill("sam", supervised=True)
    time.sleep(0.2)  # prefill writes in the background
    assert quizzer.calls == 0


def test_a_question_written_before_a_set_aside_never_races(tmp_path):
    # regression: a shark question written ahead raced after "sharks" was set aside
    quizzer = FakeQuizzer(why="Like 4 sharks in 8.")
    desk, _ = desk_for(tmp_path, quizzer)
    desk.maps.change("sam", lambda m: add_interest(m, "sharks"))
    desk.start("sam", supervised=True)  # ten written, five held
    desk.maps.change("sam", lambda m: remove(m, m.find("sharks").id))
    desk.drop("sam")
    quizzer.why = "Half means 2 equal parts."
    race = desk.start("sam", supervised=True)
    assert all("shark" not in q.why for q in race.questions) and quizzer.calls == 2


def test_two_race_taps_at_once_start_one_race(tmp_path):
    # regression: two starts at once both asked Claude and both counted
    import threading

    quizzer = SlowQuizzer()
    desk, points = desk_for(tmp_path, quizzer)
    desk.prefill = lambda *args: None  # the next set, written ahead, would be a second call
    races = []
    taps = [threading.Thread(target=lambda: races.append(desk.start("sam", supervised=True)))
            for _ in range(2)]
    for t in taps:
        t.start()
    for t in taps:
        t.join()
    assert races[0] is races[1] and quizzer.calls == 1
    assert points.races_left("sam") == RACES_PER_DAY - 1


def test_opening_games_while_a_race_starts_asks_claude_once(tmp_path):
    # regression: a second device opening Games during a start wrote a set nobody could use
    import threading

    quizzer = SlowQuizzer()
    desk, _ = desk_for(tmp_path, quizzer)
    desk.maps.change("sam", lambda m: add_goal(m, "Acceleration"))  # all ten questions count
    tap = threading.Thread(target=lambda: desk.start("sam", supervised=True))
    tap.start()
    time.sleep(0.1)  # the start is waiting on Claude
    desk.prefill("sam", supervised=True)
    tap.join()
    time.sleep(0.4)
    assert quizzer.calls == 1


def test_repeats_are_dropped_and_recent_concepts_reach_claude(tmp_path):
    # regression: production raced the same or nearly the same questions again and again
    class Repeater(FakeQuizzer):
        def __init__(self):
            super().__init__()
            self.prompts, self.first = [], None

        def write(self, system, prompt):
            self.calls += 1
            self.prompts.append(prompt)
            if self.first is None:  # five fresh questions, plus a twin of the first
                self.first = [fresh("Fractions") for _ in range(5)]
                return {"questions": [*self.first, {**self.first[0], "concept": "other"}]}
            old = self.first[0]
            return {"questions": [
                fresh("Fractions", concept=old["concept"]),  # an idea asked last race
                fresh("Fractions", question=old["question"].replace("?", " now?")),  # near copy
                *[fresh("Fractions") for _ in range(5)]]}

    quizzer = Repeater()
    maps, points = MapStore(tmp_path), PointsStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    desk = RaceDesk(quizzer, maps, points, ConceptStore(tmp_path))
    desk.prefill = lambda *args: None  # only the starts ask Claude here
    ticks = iter(range(0, 1000, 10))
    desk.clock = lambda: float(next(ticks))  # the second start isn't a quick second tap
    first = desk.start("sam", supervised=True, today=TODAY)
    second = desk.start("sam", supervised=True, today=TODAY + timedelta(days=1))  # a new set
    assert len({q.question for q in first.questions}) == QUESTIONS_PER_RACE  # no twin in a race
    assert quizzer.first[1]["concept"] in quizzer.prompts[1]  # Claude hears what was asked
    asked = {normalize(q.question) for q in first.questions}
    assert not any(normalize(q.question) in asked or "now" in q.question
                   for q in second.questions)
    assert not {q.concept for q in first.questions} & {q.concept for q in second.questions}
    saved = (tmp_path / "concepts" / "sam.json").read_text()
    assert "What is" not in saved and quizzer.first[1]["concept"] in saved  # labels, never text


def test_a_race_still_starts_when_claude_can_only_repeat_or_the_concepts_file_fails(tmp_path):
    # regression: a narrow goal's near-repeats locked out every race until a restart, and a
    # failed concepts write counted a race that never showed
    class Same(FakeQuizzer):
        def __init__(self):
            super().__init__()
            self.items = [fresh("Fractions") for _ in range(10)]

        def write(self, system, prompt):
            self.calls += 1
            return {"questions": self.items}

    class Broken(ConceptStore):
        def add(self, *args, **kwargs):
            raise OSError("disk full")

    maps, points = MapStore(tmp_path), PointsStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    desk = RaceDesk(Same(), maps, points, Broken(tmp_path))
    desk.prefill = lambda *args: None
    ticks = iter(range(0, 1000, 10))
    desk.clock = lambda: float(next(ticks))
    for day in range(3):  # each day a new set, and every question already asked
        race = desk.start("sam", supervised=True, today=TODAY + timedelta(days=day))
        assert len(race.questions) == QUESTIONS_PER_RACE
        assert len({q.question for q in race.questions}) == QUESTIONS_PER_RACE
    assert points.races_left("sam", TODAY + timedelta(days=2)) == RACES_PER_DAY - 1  # counted once


def test_a_set_aside_while_questions_are_written_refuses_the_race(tmp_path):
    # regression: an educator set "sharks" aside during the Claude call, and shark questions raced
    class SetsAside(FakeQuizzer):
        def write(self, system, prompt):
            self.calls += 1
            desk.maps.change("sam", lambda m: remove(m, m.find("sharks").id))
            return {"questions": [fresh("Fractions", "Like 4 sharks in 8.") for _ in range(10)]}

    desk, points = desk_for(tmp_path, SetsAside())
    desk.maps.change("sam", lambda m: add_interest(m, "sharks"))
    with pytest.raises(RaceUnavailable):
        desk.start("sam", supervised=True, today=TODAY)
    assert points.races_left("sam", TODAY) == RACES_PER_DAY  # not counted
    # regression (review): questions that still fit were thrown away with the refusal
    good = fresh("Fractions")
    desk.maps.change("sam", lambda m: add_interest(m, "whales"))

    def whales(system, prompt):  # set aside again while Claude writes
        desk.maps.change("sam", lambda m: remove(m, m.find("whales").id))
        return {"questions": [good, *[fresh("Fractions", "Like 4 whales.") for _ in range(9)]]}

    desk.quizzer.write = whales
    with pytest.raises(RaceUnavailable):
        desk.start("sam", supervised=True, today=TODAY)
    assert [q.question for q in desk._held("sam", TODAY)] == [good["question"]]


def test_the_concept_ledger_keeps_every_idea_with_its_answers(tmp_path):
    # long-term memory: an idea asked months ago is still known, with how it went
    maps, points = MapStore(tmp_path), PointsStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    concepts = ConceptStore(tmp_path)
    desk = RaceDesk(FakeQuizzer(), maps, points, concepts)
    desk.prefill = lambda *args: None
    ticks = iter(range(0, 1000, 10))
    desk.clock = lambda: float(next(ticks))
    race = desk.start("sam", supervised=True, today=TODAY)
    first = race.questions[0]
    desk.pick("sam", race.id, 0, first.answer)  # right
    desk.pick("sam", race.id, 1, (race.questions[1].answer + 1) % 3)  # wrong
    later = TODAY + timedelta(days=20)
    assert first.concept not in concepts.recent("sam", later)  # not "asked lately" any more
    ledger = {c["concept"]: c for c in concepts.ledger("sam")}
    assert ledger[first.concept]["asked"] == 1 and ledger[first.concept]["right"] == 1
    assert ledger[race.questions[1].concept]["right"] == 0 and len(ledger) == QUESTIONS_PER_RACE
    old = tmp_path / "concepts" / "kim.json"  # a v3.9 file still loads
    old.write_text('{"schema": 1, "recent": [{"concept": "halves", "goal": "Fractions", '
                   '"day": "2026-10-12"}]}')
    assert concepts.recent("kim", TODAY) == ["halves"]


def test_a_wrong_key_never_races(tmp_path):
    # the admin's decision (2026-10-19): a race question never teaches a wrong answer
    import re

    wrong_sum = fresh("Fractions", question="Half of a 400-meter lap, in meters?", math="400 / 2",
                      choices=["100 meters", "200 meters", "800 meters"], answer=0)
    right_sum = fresh("Fractions", question="A quarter of 8 laps, in laps?", math="8 * 1/4",
                      choices=["4", "2", "6"], answer=1)
    doubted = fresh("Fractions", question="Which is more, a half or a third? DOUBT")

    class Writer(FakeQuizzer):
        def write(self, system, prompt, schema=None):
            return {"questions": [wrong_sum, right_sum, doubted,
                                  *[fresh("Fractions") for _ in range(4)]]}

    class Checker:  # answers blind: the "4" or "2" it would pick, wrong on the doubted one
        def __init__(self):
            self.prompts = []

        def write(self, system, prompt, schema=None, **kwargs):
            self.prompts.append(prompt)
            picks = []
            for block in prompt.strip().split("\n\n"):  # one question, a choice per line
                choices = re.findall(r"^([ABC]): (.*)$", block, flags=re.M)
                want = "2" if "DOUBT" in block or "quarter" in block else "4"
                picks.append(next(letter for letter, c in choices if c.strip() == want))
            return {"picks": picks}

    maps, points = MapStore(tmp_path), PointsStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    checker = Checker()
    desk = RaceDesk(Writer(), maps, points, checker=checker)
    desk.prefill = lambda *args: None
    race = desk.start("sam", supervised=True, today=TODAY)
    raced = {q.question for q in [*race.questions, *desk._held("sam", TODAY)]}
    assert right_sum["question"] in raced  # its sum and its key agree, and so does the check
    assert wrong_sum["question"] not in raced and doubted["question"] not in raced
    assert "DOUBT" in checker.prompts[0] and "math" not in checker.prompts[0].casefold()


def test_answers_are_logged_as_labels_and_numbers(tmp_path):
    # the results log, kept for good: what was practiced and how it went, never any text
    import json

    from lerni.student.results import ResultsLog

    maps, points, results = MapStore(tmp_path), PointsStore(tmp_path), ResultsLog(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    desk = RaceDesk(FakeQuizzer(), maps, points, results=results)
    desk.prefill = lambda *args: None
    ticks = iter(range(0, 1000, 10))
    desk.clock = lambda: float(next(ticks))
    race = desk.start("sam", supervised=True)
    for n, ok in enumerate([True, True, False, True, False]):
        q = race.questions[n]
        desk.pick("sam", race.id, n, q.answer if ok else (q.answer + 1) % 3)
    lines = [json.loads(x) for x in (tmp_path / "results" / "sam.jsonl").read_text().splitlines()]
    answers, finish = lines[:5], lines[5]
    assert [a["right"] for a in answers] == [True, True, False, True, False]
    assert all(a["goal"] == "Fractions" and a["seconds"] > 0 and len(a["q"]) == 12 for a in answers)
    assert "What is" not in json.dumps(lines)  # never the question's words
    assert finish["place"] in (1, 2, 3) and finish["points"] > 0
    assert results.week("sam", date.today()) == [("Fractions", 3, 5)]
    # a goal's Practice line: read from the log each time, never stored
    today, goal_id = date.today(), maps.get("sam").find("Fractions").id
    practice = results.practice("sam", goal_id, today)
    assert (practice.last, practice.right, practice.asked) == (today.isoformat(), 3, 5)
    for concept, ok in (("halves of odd numbers", False), ("thirds", False),
                        ("halves of odd numbers", True)):  # a later right answer clears a miss
        results.add("sam", {"day": today.isoformat(), "goal_id": goal_id, "goal": "Fractions",
                            "concept": concept, "right": ok})
    missed = results.practice("sam", goal_id, today).missed
    assert missed[0] == "thirds" and "halves of odd numbers" not in missed and len(missed) <= 3
    assert results.practice("sam", "e999", today) is None  # never raced
    results.add("sam", {"day": today.isoformat(), "goal_id": goal_id, "goal": "Fractions",
                        "concept": "Thirds", "right": True})  # the same idea, capitalized
    assert "thirds" not in results.practice("sam", goal_id, today).missed



def test_the_check_never_refuses_a_race_by_itself(tmp_path):
    # regression (review): a check that disagreed with everything (say, an off-by-one) left
    # no race at all; a sum written loosely ("400 / 2 = 200") dropped a good question; a huge
    # number crashed the sum check
    from lerni.student.race import _arith

    assert _arith("9" * 400 + " * 2") is None and _arith("1e400 - 1e400") is None
    loose = fresh("Fractions", question="Half of 400?", math="400 / 2 = 200",
                  choices=["200", "100", "800"], answer=0)

    class Writer(FakeQuizzer):
        def write(self, system, prompt, schema=None):
            return {"questions": [loose, *[fresh("Fractions") for _ in range(6)]]}

    class Contrary:  # never agrees (a fixed letter would match a shuffled answer now and then)
        def write(self, system, prompt, schema=None, **kwargs):
            return {"picks": [{"work": "", "pick": "D"}] * prompt.count("\nA: ")}

    maps, points = MapStore(tmp_path), PointsStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    desk = RaceDesk(Writer(), maps, points, checker=Contrary())
    desk.prefill = lambda *args: None
    race = desk.start("sam", supervised=True, today=TODAY)
    raced = {q.question for q in [*race.questions, *desk._held("sam", TODAY)]}
    assert len(race.questions) == QUESTIONS_PER_RACE and loose["question"] in raced


def test_a_goals_level_follows_its_last_five_answers(tmp_path):
    # pitched right: 4 or 5 right of a goal's last 5 goes one harder, 2 or fewer one easier
    import json

    class Recording(FakeQuizzer):  # five questions a call, so every race writes and is heard
        prompts: list = []

        def write(self, system, prompt):
            self.prompts.append(prompt)
            return {"questions": [fresh("Fractions") for _ in range(QUESTIONS_PER_RACE)]}

    maps, points, concepts = MapStore(tmp_path), PointsStore(tmp_path), ConceptStore(tmp_path)
    goal_id = maps.change("sam", lambda m: add_goal(m, "Fractions", "halves")).id
    (tmp_path / "concepts").mkdir()
    (tmp_path / "concepts" / "sam.json").write_text(json.dumps({"schema": 2, "concepts": [
        {"concept": "old idea", "goal": "Fractions", "first": "2026-10-01", "last": "2026-10-01",
         "asked": 1, "right": 0}]}))  # a file from before levels
    quizzer = Recording()
    desk = RaceDesk(quizzer, maps, points, concepts)
    desk.prefill = lambda *args: None
    ticks = iter(range(0, 10_000, 10))
    desk.clock = lambda: float(next(ticks))

    def race(rights):
        r = desk.start("sam", supervised=True)
        for n, ok in enumerate(rights):
            q = r.questions[n]
            desk.pick("sam", r.id, n, q.answer if ok else (q.answer + 1) % 3)

    assert concepts.levels("sam") == {} and "- Fractions (level 3; notes: halves)" in (
        quiz_input(maps.get("sam"), TODAY, True))  # every goal starts at 3
    race([True, True, True, True, False])
    assert concepts.levels("sam") == {goal_id: 4}
    assert "old idea" in [c["concept"] for c in concepts.ledger("sam")]  # the ledger survives
    race([True, True, False, False, False])
    assert "- Fractions (level 4; notes: halves)" in quizzer.prompts[-1]  # Claude heard the level
    assert concepts.levels("sam") == {goal_id: 3}
    # regression (review): a broken map or a hand-edited level never stops a race or its award
    r = desk.start("sam", supervised=True)
    for n in range(QUESTIONS_PER_RACE - 1):
        desk.pick("sam", r.id, n, r.questions[n].answer)
    (tmp_path / "maps" / "sam.json").write_text("{broken")
    _, _, awarded = desk.pick("sam", r.id, 4, r.questions[4].answer)
    assert awarded > 0
    data = json.loads((tmp_path / "concepts" / "sam.json").read_text())
    data["levels"] = {"a": {"level": "x", "asked": "y"}, "b": {"level": 99}, "c": None}
    (tmp_path / "concepts" / "sam.json").write_text(json.dumps(data))
    assert concepts.levels("sam") == {"a": 3, "b": 5}
    concepts.practiced("sam", "a", True)  # counts from a clean start, never a crash


def test_a_missed_idea_comes_back_on_schedule(tmp_path):
    # spaced review: a miss is due tomorrow, then 3 days, then 7, then retired
    d0 = date(2026, 10, 22)
    day = lambda n: d0 + timedelta(days=n)  # noqa: E731
    maps, points, concepts = MapStore(tmp_path), PointsStore(tmp_path), ConceptStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    idea = "halves of odd numbers"
    concepts.add("sam", [("Fractions", idea)], d0)
    concepts.answered("sam", idea, False, d0)
    assert concepts.due("sam", d0) == [] and concepts.due("sam", day(1)) == [("Fractions", idea)]

    class Recording(FakeQuizzer):  # asks the due idea again, labelled a little differently
        prompts: list = []

        def write(self, system, prompt):
            self.prompts.append(prompt)
            return {"questions": [fresh("Fractions", concept="half of odd numbers"),
                                  *(fresh("Fractions") for _ in range(QUESTIONS_PER_RACE))]}

    quizzer = Recording()
    desk = RaceDesk(quizzer, maps, points, concepts)
    written = desk._write("sam", True, day(1))
    assert "Due for review" in quizzer.prompts[-1] and idea in quizzer.prompts[-1]
    assert idea in [q.concept for q in written]  # asked again within 14 days, under its label

    for n, after in ((1, day(4)), (4, day(11))):  # each right answer pushes it out
        concepts.answered("sam", idea, True, day(n))
        assert concepts.due("sam", after) == [("Fractions", idea)]
        assert concepts.due("sam", after - timedelta(days=1)) == []
    concepts.answered("sam", idea, True, day(11))
    assert concepts.due("sam", day(60)) == []  # three right in a row: retired

    # regression (review): a right answer before the idea is due again doesn't move it, so two
    # questions on one idea in a day never step it twice
    concepts.answered("sam", idea, False, day(20))
    concepts.answered("sam", idea, True, day(21))  # due: step 1, back on day 24
    concepts.answered("sam", idea, True, day(21))  # the same day again: no change
    assert concepts.due("sam", day(24)) == [("Fractions", idea)]
    # regression (review): a different idea with a similar label never takes the due one's,
    # and one question at most takes it
    from lerni.student.race import Question, _as_due

    q = lambda c: Question("Fractions", f"About {c}?", ("1", "2", "3"), 0, "", c)  # noqa: E731
    asked = _as_due([q("halves of even numbers"), q("dividing by 3"), q("half of odd number"),
                     q("halves of odd numbers")],
                    [("Fractions", idea), ("Fractions", "dividing by 2")])
    assert [x.concept for x in asked] == ["halves of even numbers", "dividing by 3", idea,
                                          "halves of odd numbers"]


def test_a_right_key_written_as_a_mixed_number_races(tmp_path):
    # regression (eval): "3 and a half", "3 1/2" and "3½" were read as 3, so a right key worked
    # out as 7 / 2 was dropped as wrong, and half of an odd number was never asked
    from lerni.student.race import _number

    assert [_number(c) for c in ("3 and a half scoops", "3 1/2 cones", "3½", "2 wheels")] == [
        3.5, 3.5, 3.5, 2.0]
    assert _number("3 and a bit") is None  # a mixed number it can't read: the check is skipped
    m = InterestMap()
    add_goal(m, "Fractions")
    odd = fresh("Fractions", question="Half of 7 scoops?", math="7 / 2",
                choices=["3 and a half scoops", "2 scoops", "7 scoops"], answer=0)
    assert len(check_questions({"questions": [odd]}, m)) == 1


def test_the_bonus_comes_when_behind_or_lucky_and_counts_once():
    from lerni.student.race import Bonus, bonus_move, check_bonus

    b = Bonus("Fractions", "why two halves make a whole", "Explain why two halves make a whole.",
              ("two equal parts", "together they make one"))
    m = InterestMap()
    add_goal(m, "Fractions")
    good = {"goal": "Fractions", "concept": b.concept, "question": b.question,
            "key_ideas": list(b.key_ideas)}
    raw = {"bonus": [good, {**good, "key_ideas": ["a"]}, {**good, "goal": "Spelling"}]}
    assert check_bonus(raw, m) == [b]  # one key idea, or a goal not on the map: dropped

    def race_with(rights, lucky=False):
        race = new_race([Q] * QUESTIONS_PER_RACE)
        race.bonus, race.lucky = b, lucky
        for n, ok in enumerate(rights):
            answer(race, n, 0 if ok else 1)
        return race

    behind = race_with([False] * 3)  # last after question 3: question 4 is the bonus
    assert behind.bonus_live and public(behind)["bonus"] == b.question
    assert "equal parts" not in str(public(behind))  # the page never sees the key ideas
    assert answer(behind, 3, 0) is None  # multiple choice waits for the bonus
    me = behind.me
    turn = bonus_move(behind, "nailed", "Nailed it!")
    assert turn.right and behind.me > me and behind.answered == 4 and behind.right == 1
    assert bonus_move(behind, "nailed", "again") is None and not behind.bonus_live  # once only
    assert race_with([True] * 3, lucky=True).bonus_live  # or a lucky draw at the start
    ahead = race_with([True] * 3)
    assert not ahead.bonus_live and answer(ahead, 3, 0) is not None  # otherwise, as before
    tried = race_with([False] * 3)
    me = tried.me
    assert not bonus_move(tried, "tried", "Good try.").right and tried.me - me == pytest.approx(0.7)


def test_a_bonus_answer_is_graded_safely(tmp_path):
    from lerni.student.race import BONUS_POINTS, CARE_LINE
    from lerni.student.results import ResultsLog

    class Writer(FakeQuizzer):  # five questions and one bonus a call, so each race writes
        def write(self, system, prompt):
            self.calls += 1
            return {"questions": [fresh("Fractions") for _ in range(QUESTIONS_PER_RACE)],
                    "bonus": [{"goal": "Fractions", "concept": f"why halves {self.calls}",
                               "question": "Explain why two halves make a whole.",
                               "key_ideas": ["two equal parts", "together they make one"]}]}

    class Grader:
        def __init__(self):
            self.calls, self.reply = [], {"tier": "nailed", "line": "Nailed it!", "care": False}

        def write(self, system, prompt, schema=None, timeout=None):
            self.calls.append(prompt)
            if self.reply is None:
                raise TimeoutError("too slow")
            return self.reply

    maps, points = MapStore(tmp_path), PointsStore(tmp_path)
    goal = maps.change("sam", lambda m: add_goal(m, "Fractions"))
    grader = Grader()
    from lerni.student.logs import ConversationLog as Log

    desk = RaceDesk(Writer(), maps, points, ConceptStore(tmp_path), results=ResultsLog(tmp_path),
                    grader=grader, log=Log(tmp_path))
    desk.prefill = lambda *args: None
    ticks = iter(range(0, 10_000, 10))
    desk.clock = lambda: float(next(ticks))

    def at_bonus():
        race = desk.start("sam", supervised=True)
        for n in range(3):  # three wrong: last, so question 4 is the bonus
            desk.pick("sam", race.id, n, (race.questions[n].answer + 1) % 3)
        assert race.bonus_live
        return race

    race = at_bonus()  # blank or emojis: nothing to grade, never called wrong
    _, turn, awarded = desk.answer_bonus("sam", race.id, 3, " 🙂🙂 ")
    assert (race.bonus_tier, awarded, grader.calls) == ("none", 0, []) and not turn.right

    race = at_bonus()
    secret = "Because 2 equal parts fit together into 1 whole pizza, xyzzy"
    _, turn, awarded = desk.answer_bonus("sam", race.id, 3, secret)
    assert turn.right and awarded == BONUS_POINTS["nailed"] and len(grader.calls) == 1
    assert desk.answer_bonus("sam", race.id, 3, secret)[2] == 0  # a double send: once only
    assert date.today().isoformat() in maps.get("sam").get(goal.id).explained
    assert not any("xyzzy" in p.read_text(errors="ignore")  # the answer is never on disk
                   for p in tmp_path.rglob("*") if p.is_file())

    grader.reply = None  # the grader fails: a real try, never a zero
    race = at_bonus()
    _, turn, awarded = desk.answer_bonus("sam", race.id, 3, "halves are the same size")
    assert race.bonus_tier == "tried" and awarded == BONUS_POINTS["tried"]
    assert "couldn't read" in turn.why and "+2" not in turn.why  # the ⭐ is said once, below

    grader.reply = {"tier": "nailed", "line": "Great!", "care": True}  # worry comes first
    race = at_bonus()
    _, turn, awarded = desk.answer_bonus("sam", race.id, 3, "someone keeps hurting me")
    assert race.bonus_tier == "care" and turn.why == CARE_LINE and awarded == 0  # no reward
    # regression (review): a worry left no trace; like Chat's, it's kept in the conversation log
    from lerni.student.logs import ConversationLog

    assert any("hurting me" in r.get("answer", "") for r in ConversationLog(tmp_path).read("sam"))
    assert '"care": true' in (tmp_path / "results" / "sam.jsonl").read_text()


def test_held_questions_last_past_midnight(tmp_path):
    # regression: held questions were dropped at midnight, so a day's first race waited a minute
    quizzer = FakeQuizzer()
    desk, _ = desk_for(tmp_path, quizzer)
    desk.prefill = lambda *args: None
    ticks = iter(range(0, 1000, 10))
    desk.clock = lambda: float(next(ticks))
    desk.start("sam", supervised=True, today=TODAY)  # ten written: five race, five held
    desk.start("sam", supervised=True, today=TODAY + timedelta(days=1))
    assert quizzer.calls == 1
    desk.start("sam", supervised=True, today=TODAY + timedelta(days=2))  # none held: a new set
    assert quizzer.calls == 2
    desk.maps.change("sam", lambda m: [add_goal(m, "Decimals"),  # Fractions gone overnight
                                       remove(m, m.find("Fractions").id)])
    with pytest.raises(RaceUnavailable):
        desk.start("sam", supervised=True, today=TODAY + timedelta(days=3))
