"""Ask Lerni: answers stream in, history is kept short, and nothing personal goes to Claude."""

from lerni.student.conversation import (
    MAX_TURNS,
    Conversations,
    system_prompt,
)
from lerni.student.plans import LearningPlan, PlannedActivity


class FakeModel:
    def __init__(self):
        self.calls = []

    def stream(self, system, turns):
        self.calls.append((system, list(turns)))
        yield "Fast "
        yield "answer."


def test_a_question_gets_a_streamed_answer_and_history_stays_short():
    convos = Conversations(FakeModel())
    assert "".join(convos.ask("sam", "Why is the sky blue?", None)) == "Fast answer."
    assert [t.role for t in convos.history("sam")] == ["user", "assistant"]
    for i in range(30):
        list(convos.ask("sam", f"question {i}", None))
    assert len(convos.history("sam")) == MAX_TURNS
    convos.clear("sam")
    assert convos.history("sam") == []


def test_a_topic_shares_the_plan_ideas_but_never_who_is_asking():
    plan = LearningPlan(
        plan_id="cars-1",
        interest="Cars",
        goal="Speed and time",
        activities=(PlannedActivity(idea="Acceleration", big_question="What does 0-60 mean?"),),
    )
    assert "Acceleration" in system_prompt(plan) and "What does 0-60 mean?" in system_prompt(plan)
    model = FakeModel()
    list(Conversations(model).ask("zephyrine", "hi", plan))
    system, turns = model.calls[0]
    assert "zephyrine" not in system and all("zephyrine" not in t.text for t in turns)
