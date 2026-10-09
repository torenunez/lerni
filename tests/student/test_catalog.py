"""Strict lesson TOML parsing and the approved-content boundary.

Every rule here fails closed. Content a student can see must be exactly what a
human reviewed, so ambiguity, drift, and missing review are rejected rather than
tolerated.
"""

import re

import pytest

from lerni.student.catalog import (
    parse_lesson_toml,
)
from lerni.student.domain import ApprovalStatus, LessonContentError, ReviewScope


def test_parse_valid_toml_returns_exact_lesson(approved_lesson_toml):
    lesson = parse_lesson_toml(approved_lesson_toml)
    assert lesson.id == "test-lesson"
    assert lesson.schema_version == 1
    assert lesson.content_version == 1
    assert lesson.sequence == ("intro-step", "teach-step")
    assert tuple(step.id for step in lesson.steps) == ("intro-step", "teach-step")
    assert lesson.check.correct_choice_id == "choice-a"
    assert lesson.review.status is ApprovalStatus.APPROVED
    assert {a.scope for a in lesson.review.attestations} == set(ReviewScope)


























def test_rejects_approved_without_attestation(approved_lesson_toml):
    # Remove the science block outright. Rewriting its scope would instead trip
    # the duplicate-scope rule, and the test would pass for the wrong reason.
    bad = re.sub(
        r"\[\[review\.attestations\]\]\nid = \"att-science\".*?\n\n",
        "",
        approved_lesson_toml,
        flags=re.DOTALL,
    )
    assert "att-science" not in bad
    with pytest.raises(LessonContentError, match="missing scope"):
        parse_lesson_toml(bad)








def test_rejects_content_edited_after_approval(approved_lesson_toml):
    # The realistic drift: someone tweaks student-facing text without re-reviewing.
    bad = approved_lesson_toml.replace(
        'body = "Teach body."', 'body = "Edited after review."'
    )
    with pytest.raises(LessonContentError, match="approves payload"):
        parse_lesson_toml(bad)
