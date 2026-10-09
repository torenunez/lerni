"""Domain contract tests for the student app lesson core.

These assert the shape of the public domain: stable enum values, immutability,
and the boundary that keeps student-facing data free of answer keys and raw text.
"""



from lerni.student.domain import (
    LessonSnapshot,
)


def test_snapshot_has_no_correct_choice_id():
    fields = set(LessonSnapshot.__dataclass_fields__)
    assert "correct_choice_id" not in fields
    assert "grounding" not in fields
    assert "review" not in fields
