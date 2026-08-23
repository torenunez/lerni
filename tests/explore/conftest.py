"""Shared fixtures for Explore tests.

Fixtures build domain objects directly. Nothing here reaches the packaged
production lesson, which must stay draft until human review is recorded.
"""

from datetime import date

import pytest

from lerni.explore.domain import (
    ApprovalStatus,
    AssetRef,
    CheckChoice,
    GroundedFact,
    GroundingBundle,
    Lesson,
    LessonStep,
    RetrievalCheck,
    ReviewMetadata,
    SourceReference,
    StepKind,
)


@pytest.fixture
def valid_source() -> SourceReference:
    return SourceReference(
        id="nasa-acceleration",
        title="Displacement, Velocity, Acceleration",
        publisher="NASA Glenn Research Center",
        url="https://www.grc.nasa.gov/WWW/K-12/airplane/disvelac.html",
        retrieved_on=date(2026, 8, 23),
    )


@pytest.fixture
def valid_facts() -> tuple[GroundedFact, ...]:
    return (
        GroundedFact(
            id="zero-to-sixty-is-time",
            canonical_text=(
                "A 0-to-60 result reports the elapsed time for velocity to change "
                "from 0 miles per hour to 60 miles per hour."
            ),
            child_text="A 0-60 result tells how many seconds the speed change took.",
            source_ids=("nasa-acceleration",),
            allowed_numbers=("0", "60"),
        ),
        GroundedFact(
            id="acceleration-definition",
            canonical_text="Average acceleration is change in velocity divided by elapsed time.",
            child_text="Acceleration tells how quickly velocity changes.",
            source_ids=("nasa-acceleration",),
            allowed_numbers=(),
        ),
        GroundedFact(
            id="shorter-time-greater-average",
            canonical_text=(
                "For two straight-line runs with the same initial and final velocities, "
                "the shorter elapsed time has the greater average acceleration."
            ),
            child_text=(
                "If both cars make the same speed change, the one that does it in less "
                "time has greater average acceleration."
            ),
            source_ids=("nasa-acceleration",),
            allowed_numbers=("0", "4", "8", "60"),
        ),
    )


@pytest.fixture
def valid_lesson(valid_source, valid_facts) -> Lesson:
    visual = AssetRef(
        resource_name="assets/chain_1_acceleration.svg",
        media_type="image/svg+xml",
        alt_text="Two cars both go from 0 to 60. Car A takes 4 seconds, Car B takes 8.",
        sha256=None,
    )
    return Lesson(
        schema_version=1,
        id="chain-1-acceleration",
        content_version=1,
        title="What does 0-60 tell us?",
        locale="en-US",
        audience="ages-7-9",
        max_turns=8,
        review=ReviewMetadata(status=ApprovalStatus.DRAFT, attestations=()),
        sequence=("hook-0-to-60", "teach-acceleration"),
        steps=(
            LessonStep(
                id="hook-0-to-60",
                kind=StepKind.INTRO,
                heading="What does 0-60 measure?",
                body="The seconds are elapsed time: how long the speed change took.",
                visual=visual,
                fact_ids=("zero-to-sixty-is-time",),
                scope_terms=frozenset({"0", "60", "car", "seconds", "time"}),
            ),
            LessonStep(
                id="teach-acceleration",
                kind=StepKind.TEACH,
                heading="Acceleration is a rate of change",
                body="Acceleration means how quickly velocity changes.",
                visual=visual,
                fact_ids=("acceleration-definition", "shorter-time-greater-average"),
                scope_terms=frozenset({"acceleration", "average", "time", "velocity"}),
            ),
        ),
        check=RetrievalCheck(
            id="compare-average-acceleration",
            prompt="Car A goes 0 to 60 in 4 seconds. Car B takes 8. Which accelerates more?",
            choices=(
                CheckChoice(id="car-a", label="Car A - 4 seconds"),
                CheckChoice(id="car-b", label="Car B - 8 seconds"),
                CheckChoice(id="same", label="They have the same average acceleration"),
            ),
            correct_choice_id="car-a",
            hints=(
                "Both cars make the same speed change: 0 to 60 miles per hour.",
                "The same change in less time means greater average acceleration.",
            ),
            success_text="Yes. Car A makes the same speed change in less time.",
            reveal_text="It is Car A. Both go 0 to 60, but Car A does it in less time.",
            fact_ids=("acceleration-definition", "shorter-time-greater-average"),
            scope_terms=frozenset({"acceleration", "average", "car", "time"}),
            allowed_short_replies=frozenset({"how", "no", "why", "yes"}),
        ),
        grounding=GroundingBundle(
            scope="Straight-line 0-to-60 elapsed time, velocity change, and average acceleration.",
            fallback_text="That question goes beyond this lesson.",
            redirect_text="Let's stay with 0-60 time and average acceleration.",
            facts=valid_facts,
            sources=(valid_source,),
        ),
    )
