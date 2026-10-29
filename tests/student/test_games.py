"""The Games screen: after a wrong answer, the question stays with its why until Next."""

from lerni.student.race import QUESTIONS_PER_RACE, Question, answer, miss_opener, new_race
from lerni.student.web.games import question_card, step_sound

HALF = Question("Fractions", "Half of 8 laps?", ("4", "2", "6"), 0, "Half means 2 equal parts.")
QUARTER = Question("Fractions", "A quarter of 8 laps?", ("2", "4", "6"), 0, "4 equal parts.")


def test_a_wrong_answer_waits_for_next():
    race = new_race([HALF, QUARTER] + [HALF] * (QUESTIONS_PER_RACE - 2))
    text, choices = question_card(race)
    assert "Question 1 of 5" in text and "Half of 8 laps?" in text and choices
    turn = answer(race, 0, 1)  # wrong: "2"
    text, choices = question_card(race, (0, turn))
    assert "Question 1 of 5" in text and "Half of 8 laps?" in text  # the one just answered
    assert "It's **4**" in text and miss_opener(race, 0) in text and not choices
    assert "Half means 2 equal parts." in text
    assert "A quarter" not in text  # the next question waits for Next
    text, choices = question_card(race)  # Next
    assert "Question 2 of 5" in text and "A quarter of 8 laps?" in text and choices
    turn = answer(race, 1, 0)  # right: straight on
    text, choices = question_card(race, (1, turn))
    assert "Question 3 of 5" in text and choices


def test_a_double_tap_on_a_wrong_answer_never_skips_the_why(tmp_path):
    # regression (review): the second tap of a double tap landed on Next, which had taken the
    # choice's place, and skipped the why
    from lerni.student.interests import MapStore, add_goal
    from lerni.student.points import PointsStore
    from lerni.student.race import RaceDesk

    class Quizzer:
        def write(self, system, prompt):
            return {"questions": [{"goal": "Fractions", "concept": f"idea {i}",
                                   "question": f"Half of {2 * i + 2} laps?",
                                   "choices": [str(i + 1), "0", "99"], "answer": 0, "why": "Half."}
                                  for i in range(QUESTIONS_PER_RACE)]}

    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Fractions"))
    desk = RaceDesk(Quizzer(), maps, PointsStore(tmp_path))
    desk.prefill = lambda *args: None
    now = [100.0]
    desk.clock = lambda: now[0]
    race = desk.start("sam", supervised=True)
    now[0] += 5
    desk.pick("sam", race.id, 0, (race.questions[0].answer + 1) % 3)  # wrong
    now[0] += 0.3
    assert desk.just_answered("sam")  # Next waits: this tap was meant for the choice
    now[0] += 2
    assert not desk.just_answered("sam")


def test_the_bonus_card_asks_then_shows_its_grade():
    from lerni.student.race import Bonus, bonus_move

    race = new_race([HALF] * QUESTIONS_PER_RACE)
    race.bonus = Bonus("Fractions", "halves", "Explain why two halves make a whole.",
                       ("two equal parts", "together they make one"))
    race.lucky = True  # the race drew a bonus
    for n in range(3):
        turn = answer(race, n, 1)
    # regression (review): a wrong third answer showed the bonus at once, never its why
    text, choices = question_card(race, (2, turn))
    assert "Question 3 of 5" in text and "It's **4**" in text and not choices  # then Next
    text, choices = question_card(race)  # Next
    assert "Bonus" in text and "two halves make a whole" in text and not choices
    assert "equal parts" not in text  # never the key ideas
    turn = bonus_move(race, "partly", "Good start: the missing idea is that they're equal.")
    text, choices = question_card(race, (3, turn))
    assert "two halves make a whole" in text and "Good start" in text and not choices  # Next


def test_the_sound_follows_the_score():
    # v3.32: an honest bonus try played the sputter
    from lerni.student.race import Bonus, bonus_move

    def at_bonus():
        race = new_race([HALF] * QUESTIONS_PER_RACE)
        race.bonus = Bonus("Fractions", "halves", "Explain halves.", ("a b", "c d"))
        race.lucky = True
        for n in range(3):
            answer(race, n, n % 2)  # right, wrong, right
        return race

    race = at_bonus()
    assert step_sound(race) == "roar"
    sounds = {}
    for tier in ("nailed", "partly", "tried", "none", "care"):
        race = at_bonus()
        bonus_move(race, tier, "Thanks!")
        sounds[tier] = step_sound(race)
    assert sounds == {"nailed": "zoom", "partly": "roar", "tried": "rev", "none": "", "care": ""}
    race = new_race([HALF] * QUESTIONS_PER_RACE)
    answer(race, 0, 1)
    assert step_sound(race) == "sputter"
    for n in range(1, QUESTIONS_PER_RACE):
        answer(race, n, 0)
    assert step_sound(race) == "finish"
