"""Ask Lerni: answers stream in, history is kept short, and nothing personal goes to Claude."""

from lerni.student.conversation import (
    MAX_TURNS,
    SAFETY_RULES,
    Conversations,
    system_prompt,
)
from lerni.student.interests import MAP_HEADER


class FakeModel:
    def __init__(self):
        self.calls = []

    def stream(self, system, turns):
        self.calls.append((system, list(turns)))
        yield "Fast "
        yield "answer."


def test_a_question_gets_a_streamed_answer_and_history_stays_short():
    convos = Conversations(FakeModel())
    assert "".join(convos.ask("sam", "Why is the sky blue?")) == "Fast answer."
    assert [t.role for t in convos.history("sam")] == ["user", "assistant"]
    for i in range(30):
        list(convos.ask("sam", f"question {i}"))
    assert len(convos.history("sam")) == MAX_TURNS
    convos.clear("sam")
    assert convos.history("sam") == []


def test_the_map_is_information_before_the_rules_and_never_who_is_asking():
    block = MAP_HEADER + "\nThey love: cars"
    for voice in ("independent", "supervised"):  # map text never comes after the rules
        prompt = system_prompt(block, voice)
        assert prompt.index("They love: cars") < prompt.index(SAFETY_RULES)
    model, seen = FakeModel(), []
    convos = Conversations(model, context=lambda u: block, on_exchange=seen.append)
    list(convos.ask("zephyrine", "hi"))
    system, turns = model.calls[0]
    assert "They love: cars" in system
    assert "zephyrine" not in system and all("zephyrine" not in t.text for t in turns)
    assert seen[0].question == "hi" and seen[0].answer == "Fast answer." and not seen[0].stopped
    reply = convos.ask("zephyrine", "and trucks?")
    next(reply)
    reply.close()  # Stop
    assert seen[1].stopped and seen[1].previous == "Fast answer."


def test_clear_during_a_reply_is_not_undone_when_it_finishes():
    convos = Conversations(FakeModel())
    reply = convos.ask("sam", "Why?")
    next(reply)  # the answer has started
    convos.clear("sam")
    list(reply)  # ...and finishes after Clear
    assert convos.history("sam") == []


def test_a_broken_map_never_locks_the_student_out():
    # regression: an error building the prompt left them "still answering" until a restart
    import pytest

    from lerni.student.conversation import ConversationUnavailable

    def broken(username):
        raise ValueError("unreadable map")

    convos = Conversations(FakeModel(), context=broken)
    for _ in range(2):  # the second try must not say "Still answering"
        with pytest.raises(ConversationUnavailable):
            list(convos.ask("sam", "hi"))
