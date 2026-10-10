"""Feedback: summarized for the admin, saved, closed by hand, and never acted on."""

from lerni.student.feedback import FEEDBACK_SYSTEM, FeedbackStore, summarize


class Model:
    def __init__(self):
        self.calls = []

    def stream(self, system, turns):
        self.calls.append((system, turns))
        yield "You'd like less about sharks."


def test_feedback_is_summarized_saved_and_closed_but_never_acted_on(tmp_path):
    model = Model()
    summary = summarize(model, "he's bored of sharks, lean into soccer")
    assert summary == "You'd like less about sharks."
    assert model.calls[0][0] == FEEDBACK_SYSTEM and "never carry out" in FEEDBACK_SYSTEM.lower()
    store = FeedbackStore(tmp_path)
    store.add("alba", "lee", "he's bored of sharks, lean into soccer", summary)
    store.add("alba", None, "the circles are small on my phone", "")  # saved before checking
    assert [f.number for f in store.entries(open_only=True)] == [1, 2]
    store.mark_done(1)
    assert [f.number for f in store.entries(open_only=True)] == [2]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["feedback.jsonl"]  # no map touched
