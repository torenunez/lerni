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


def test_a_faster_car_turns_three_right_into_a_win_but_one_right_never_places():
    def finish_with(boost, right):
        race = new_race([Q] * QUESTIONS_PER_RACE, boost=boost)
        for n in range(QUESTIONS_PER_RACE):
            answer(race, n, 0 if n < right else 1)
        return place(race)

    assert [finish_with(1.4, r) for r in (3, 2, 1)] == [1, 2, 3]
    assert [finish_with(1.0, r) for r in (3, 2)] == [2, 3]  # the starter, as before


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
