"""Domain contract tests for the Explore lesson core.

These assert the shape of the public domain: stable enum values, immutability,
and the boundary that keeps child-facing data free of answer keys and raw text.
"""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from lerni.explore.domain import (
    AssetRef,
    CheckChoice,
    GroundedFact,
    GroundingBundle,
    Lesson,
    LessonAction,
    LessonEvent,
    LessonPhase,
    LessonSnapshot,
    LessonState,
    ReviewMetadata,
    ReviewScope,
    SourceReference,
    StepKind,
    context_for_snapshot,
)


def test_phase_values_are_stable():
    assert [phase.value for phase in LessonPhase] == [
        "intro",
        "teach",
        "check",
        "hint",
        "complete",
    ]


def test_review_scope_values_are_stable():
    assert [scope.value for scope in ReviewScope] == [
        "science",
        "child_content",
        "visual_accessibility",
        "parent_approval",
    ]


def test_domain_models_are_frozen(valid_lesson):
    with pytest.raises(FrozenInstanceError):
        valid_lesson.title = "Changed"


def test_lesson_sequence_is_explicit_data(valid_lesson):
    assert valid_lesson.sequence == (
        "hook-0-to-60",
        "teach-acceleration",
    )
    assert not hasattr(valid_lesson, "edges")
    assert not hasattr(valid_lesson, "relationship")


def test_grounding_uses_ordered_immutable_tuples(valid_lesson):
    grounding = valid_lesson.grounding
    assert isinstance(grounding.facts, tuple)
    assert isinstance(grounding.sources, tuple)
    assert [fact.id for fact in grounding.facts] == [
        "zero-to-sixty-is-time",
        "acceleration-definition",
        "shorter-time-greater-average",
    ]
    with pytest.raises(FrozenInstanceError):
        grounding.scope = "other"


def test_state_contains_no_child_text():
    fields = set(LessonState.__dataclass_fields__)
    assert fields == {
        "lesson_id",
        "lesson_content_version",
        "phase",
        "step_index",
        "attempts",
        "hint_index",
        "completion",
    }


def test_snapshot_has_no_correct_choice_id():
    fields = set(LessonSnapshot.__dataclass_fields__)
    assert "correct_choice_id" not in fields
    assert "grounding" not in fields
    assert "review" not in fields


def test_event_requires_explicit_action():
    event = LessonEvent(action=LessonAction.SUBMIT_CHOICE, choice_id="car-a")
    assert event.action is LessonAction.SUBMIT_CHOICE
    with pytest.raises(TypeError):
        LessonEvent()


def test_step_kind_and_action_values_are_stable():
    assert [kind.value for kind in StepKind] == ["intro", "teach"]
    assert [action.value for action in LessonAction] == [
        "continue",
        "submit_choice",
        "restart",
    ]


def test_context_for_snapshot_binds_only_current_facts(valid_lesson):
    snapshot = LessonSnapshot(
        lesson_id=valid_lesson.id,
        lesson_content_version=valid_lesson.content_version,
        title=valid_lesson.title,
        phase=LessonPhase.INTRO,
        step_id="hook-0-to-60",
        heading="h",
        body="b",
        visual=None,
        choices=(),
        hint_text=None,
        completion=None,
        can_continue=True,
        can_submit_choice=False,
        can_restart=True,
    )
    context = context_for_snapshot(valid_lesson, snapshot)
    assert [fact.id for fact in context.grounding.facts] == ["zero-to-sixty-is-time"]
    assert context.redirect_text == valid_lesson.grounding.redirect_text


def test_context_for_snapshot_rejects_unknown_step(valid_lesson):
    snapshot = LessonSnapshot(
        lesson_id=valid_lesson.id,
        lesson_content_version=valid_lesson.content_version,
        title=valid_lesson.title,
        phase=LessonPhase.TEACH,
        step_id="no-such-step",
        heading="h",
        body="b",
        visual=None,
        choices=(),
        hint_text=None,
        completion=None,
        can_continue=True,
        can_submit_choice=False,
        can_restart=True,
    )
    with pytest.raises(ValueError):
        context_for_snapshot(valid_lesson, snapshot)


def test_domain_exposes_no_provider_or_credential_fields(valid_lesson):
    forbidden = {"provider", "model", "credential", "api_key", "prompt", "endpoint"}
    for cls in (Lesson, GroundedFact, GroundingBundle, SourceReference, AssetRef):
        assert not (forbidden & set(cls.__dataclass_fields__))


def test_choice_and_source_types_are_frozen():
    choice = CheckChoice(id="car-a", label="Car A")
    with pytest.raises(FrozenInstanceError):
        choice.label = "x"
    source = SourceReference(
        id="s",
        title="t",
        publisher="p",
        url="https://example.org/",
        retrieved_on=date(2026, 1, 1),
    )
    with pytest.raises(FrozenInstanceError):
        source.url = "https://other.example/"


def test_review_metadata_holds_attestations_as_tuple(valid_lesson):
    review = valid_lesson.review
    assert isinstance(review, ReviewMetadata)
    assert isinstance(review.attestations, tuple)
