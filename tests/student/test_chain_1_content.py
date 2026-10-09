"""Chain-1 content tests.

Two kinds of assertion live here. Most check properties of the authored content
that tooling can verify: the science is stated correctly, no brand or mutable
ranking is packaged, the visual is accessible. Two check the human review gate,
and they are expected to fail until real people actually review this lesson.
That failure is the gate working, not a defect to route around.
"""

import pathlib

import pytest

from lerni.student.catalog import (
    PackageLessonCatalog,
    parse_lesson_toml,
)
from lerni.student.domain import (
    ApprovalStatus,
    LessonNotApprovedError,
)

LESSON_ID = "chain-1-acceleration"
LESSONS_DIR = pathlib.Path(__file__).resolve().parents[2] / "src/lerni/student/lessons"


@pytest.fixture
def chain_1():
    """The production lesson parsed directly, bypassing the approval boundary."""
    path = LESSONS_DIR / "chain_1_acceleration.toml"
    return parse_lesson_toml(path.read_text(encoding="utf-8"), origin=path.name)
































# --- Visual --------------------------------------------------------------














# --- The human review gate ----------------------------------------------




def test_student_catalog_refuses_draft_chain_1():
    with pytest.raises(LessonNotApprovedError):
        PackageLessonCatalog().load(LESSON_ID)


@pytest.mark.xfail(
    reason="Blocked on the human review gate: four real attestations are required. "
    "See plans/runbooks/chain-1-source-review.md. Do not satisfy this by "
    "fabricating review metadata.",
    strict=True,
)
def test_student_catalog_loads_approved_chain_1():
    lesson = PackageLessonCatalog().load(LESSON_ID)
    assert lesson.review.status is ApprovalStatus.APPROVED
    assert {a.scope for a in lesson.review.attestations} == {
        "science",
        "student_content",
        "visual_accessibility",
        "educator_approval",
    }


@pytest.mark.xfail(
    reason="Blocked on the human review gate: the approved lesson must pin the "
    "reviewed SVG hash, which only exists once the visual is reviewed.",
    strict=True,
)
def test_approved_chain_1_pins_reviewed_asset_hash():
    catalog = PackageLessonCatalog()
    lesson = catalog.load(LESSON_ID)
    visual = lesson.steps[0].visual
    assert visual is not None and visual.sha256 is not None
    assert catalog.read_asset(visual)
