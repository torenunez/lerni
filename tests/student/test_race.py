"""Race rules: the finish depends only on how many were right; bad questions never race."""

import random
from datetime import date

import pytest

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
            "answer": 0, "why": "Half means 2 equal parts."}
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


class FakeQuizzer:
    """Returns ten good questions, or something useless, and counts its calls."""

    def __init__(self, good: bool = True, fail: bool = False):
        self.good, self.fail, self.calls = good, fail, 0

    def write(self, system, prompt):
        self.calls += 1
        if self.fail:
            raise RaceUnavailable("Lerni is resting until Mon 6:00 pm. 😴")
        item = {"goal": "Fractions", "question": "Half of 8 laps?", "choices": ["4", "2", "6"],
                "answer": 0, "why": "Half means 2 equal parts."}
        return {"questions": [item] * 10 if self.good else [{"goal": "x"}]}


def desk_for(tmp_path, quizzer):
    maps, points = MapStore(tmp_path), PointsStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    return RaceDesk(quizzer, maps, points), points


def test_a_race_awards_once_at_the_finish_and_ignores_stale_taps(tmp_path):
    desk, points = desk_for(tmp_path, FakeQuizzer())
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
