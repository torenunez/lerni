"""Importing a rough plan: notes in, a proposed plan out, nothing saved until approved."""

import pytest

pytest.importorskip("gradio")

from lerni.student.plan_import import DraftResult  # noqa: E402
from lerni.student.plans import PlanError, PlanStore  # noqa: E402
from lerni.student.web.educator import import_preview  # noqa: E402

PROPOSAL = {
    "interest": "Soccer",
    "goal": "Understand that a harder kick means more force.",
    "activities": [
        {"start_from": "Soccer", "idea": "Force", "why": "Kicks are pushes.",
         "big_question": "What makes the ball go farther?", "card": None},
        {"start_from": "Force", "idea": "Direction", "why": "", "big_question": "", "card": None},
        {"start_from": "Direction", "idea": "Distance", "why": "", "big_question": "",
         "card": None},
    ],
    "notes": ["Renamed a person to 'the student'."],
}


class FakeDrafter:
    def __init__(self):
        self.sources = []

    def draft(self, source):
        self.sources.append(source)
        return DraftResult(proposal=PROPOSAL)


def test_rough_notes_become_an_unsaved_plan(tmp_path):
    upload = tmp_path / "notes.txt"
    upload.write_text("kicks -> force -> direction")
    drafter = FakeDrafter()
    plan, notes = import_preview(drafter, "soccer stuff", str(upload), agreed=True)
    assert plan.interest == "Soccer" and len(plan.activities) == 3
    assert not plan.is_example
    assert notes == ["Renamed a person to 'the student'."]
    assert "soccer stuff" in drafter.sources[0].text
    assert "kicks -> force" in drafter.sources[0].text
    assert not upload.exists()  # uploads aren't kept
    assert PlanStore(tmp_path).list_plans() == []  # nothing saved before approval


def test_nothing_is_sent_without_consent():
    drafter = FakeDrafter()
    with pytest.raises(PlanError):
        import_preview(drafter, "notes", None, agreed=False)
    assert drafter.sources == []
