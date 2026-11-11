"""v4.5: the admin's ratings in the checked bank steer the next write; a batch never writes."""

from datetime import date

from lerni.student.bank import BankStore
from lerni.student.batch import write_batch
from lerni.student.concepts import ConceptStore
from lerni.student.interests import MapStore, add_goal
from lerni.student.points import PointsStore
from lerni.student.race import WRITE_SIZE, RaceDesk, check_questions
from lerni.student.results import question_hash

TODAY = date(2026, 11, 11)
BAD = "Which is the odd one out: +, =, or 5?"


def item(goal: str, n: int, question: str = "") -> dict:
    return {"goal": goal, "question": question or f"Question {n} on {goal.lower()}?",
            "choices": ["4", "2", "6"], "answer": 0, "why": "Because.",
            "concept": f"{goal} idea {n}", "format": "how it works"}


class Quizzer:
    """Writes 15 on the goals it's given, one of them the question marked bad."""

    def __init__(self):
        self.prompts = []

    def write(self, system, prompt):
        self.prompts.append(prompt)
        goals = [g for g in ("Adding", "Nouns") if f"- {g} (" in prompt]
        n0 = 100 * len(self.prompts)  # every write's questions are new
        out = [item(goals[n % len(goals)], n0 + n) for n in range(WRITE_SIZE - 1)]
        return {"questions": [*out, item("Adding", n0 + 99, BAD)]}


def row(goal: str, question: str, rating: str, problem: str = "", notes: str = "") -> dict:
    return {"goal": goal, "question": question, "choices": ["8", "9", "10"], "answer": 1,
            "why": "6 + 3 = 9", "concept": "adding small numbers", "format": "closest guess",
            "interest": "trains", "rating": rating, "problem": problem, "notes": notes}


def setup(tmp_path):
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: [add_goal(m, g) for g in ("Adding", "Nouns")])
    return maps


def test_ratings_steer_the_next_write_and_a_bad_question_never_races(tmp_path):
    maps, bank = setup(tmp_path), BankStore(tmp_path)
    kept, skipped = bank.add_labels("sam", [
        row("Adding", "A train has 6 cars and 3 more join. How many now?", "Good"),
        row("Adding", BAD, "Bad", "Format doesn't fit", "Not about adding"),
        row("Gone", "A question on a goal that's gone?", "Good"),  # its goal was removed
        row("Nouns", "Not rated yet?", ""),  # unrated rows are left out
    ], maps.get("sam"), TODAY)
    assert (kept, skipped) == (2, 1)
    races = RaceDesk(Quizzer(), maps, PointsStore(tmp_path), ConceptStore(tmp_path), bank=bank)
    kept_qs = races._write("sam", supervised=True, today=TODAY)
    prompt = races.quizzer.prompts[0]
    good = prompt.split("Marked good")[1].splitlines()[1]
    assert "6 cars and 3 more join" in good and "9" in good  # with its right answer
    wrong = prompt.split("Marked wrong")[1].splitlines()[1]
    assert BAD in wrong and "Format doesn't fit" in wrong and "Not about adding" in wrong
    assert BAD not in [k.question for k in kept_qs]  # marked bad: never races


def test_a_blocked_question_is_dropped(tmp_path):
    m = setup(tmp_path).get("sam")
    raw = {"questions": [item("Adding", 1, BAD), item("Adding", 2)]}
    kept = check_questions(raw, m, blocked={question_hash(BAD)})
    assert [k.question for k in kept] == ["Question 2 on adding?"]


def test_a_batch_never_writes_the_real_data(tmp_path):
    setup(tmp_path)
    ConceptStore(tmp_path).add("sam", [("", "", "an old idea")], TODAY)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    rows = write_batch(tmp_path, "sam", Quizzer(), supervised=True, today=TODAY, per_goal=4)
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before  # nothing written, moved, or added
    by_goal = {g: sum(r["goal"] == g for r in rows) for g in ("Adding", "Nouns")}
    assert all(n >= 4 for n in by_goal.values())
    assert len({r["id"] for r in rows}) == len(rows)  # no question twice
    assert [r["goal"] for r in rows] == sorted(r["goal"] for r in rows)  # sorted by goal
