"""The Games screen: after a wrong answer, the question stays with its why until Next."""

from lerni.student.race import QUESTIONS_PER_RACE, Question, answer, new_race
from lerni.student.web.games import question_card

HALF = Question("Fractions", "Half of 8 laps?", ("4", "2", "6"), 0, "Half means 2 equal parts.")
QUARTER = Question("Fractions", "A quarter of 8 laps?", ("2", "4", "6"), 0, "4 equal parts.")


def test_a_wrong_answer_waits_for_next():
    race = new_race([HALF, QUARTER] + [HALF] * (QUESTIONS_PER_RACE - 2))
    text, choices = question_card(race)
    assert "Question 1 of 5" in text and "Half of 8 laps?" in text and choices
    turn = answer(race, 0, 1)  # wrong: "2"
    text, choices = question_card(race, (0, turn))
    assert "Question 1 of 5" in text and "Half of 8 laps?" in text  # the one just answered
    assert "it's **4**" in text and "Half means 2 equal parts." in text and not choices
    assert "A quarter" not in text  # the next question waits for Next
    text, choices = question_card(race)  # Next
    assert "Question 2 of 5" in text and "A quarter of 8 laps?" in text and choices
    turn = answer(race, 1, 0)  # right: straight on
    text, choices = question_card(race, (1, turn))
    assert "Question 3 of 5" in text and choices
