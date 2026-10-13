"""Race rules: the finish depends only on how many were right; bad questions never race."""

import random
from datetime import date

from lerni.student.interests import InterestMap, add_goal, add_interest, remove
from lerni.student.race import (
    QUESTIONS_PER_RACE,
    Question,
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
