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


VALID_LESSON_TOML = """
schema_version = 1
lesson_id = "test-lesson"
content_version = 1
title = "Test lesson"
locale = "en-US"
audience = "ages-7-9"
max_turns = 8
sequence = ["intro-step", "teach-step"]

[review]
status = "approved"

[[review.attestations]]
id = "att-science"
scope = "science"
reviewer_role = "test-reviewer"
reviewed_on = 2026-01-01
evidence_ref = "tests/explore/conftest.py"
reviewed_payload_sha256 = "PAYLOAD_HASH"

[[review.attestations]]
id = "att-child"
scope = "child_content"
reviewer_role = "test-reviewer"
reviewed_on = 2026-01-01
reviewed_payload_sha256 = "PAYLOAD_HASH"

[[review.attestations]]
id = "att-visual"
scope = "visual_accessibility"
reviewer_role = "test-reviewer"
reviewed_on = 2026-01-01
reviewed_payload_sha256 = "PAYLOAD_HASH"

[[review.attestations]]
id = "att-parent"
scope = "parent_approval"
reviewer_role = "test-reviewer"
reviewed_on = 2026-01-01
reviewed_payload_sha256 = "PAYLOAD_HASH"

[grounding]
scope = "Test scope."
fallback_text = "Fallback."
redirect_text = "Redirect."

[[grounding.sources]]
id = "test-source"
title = "Test Source"
publisher = "Test Publisher"
url = "https://example.org/test"
retrieved_on = 2026-01-01

[[grounding.facts]]
id = "fact-one"
canonical_text = "Canonical one."
child_text = "Child one."
source_ids = ["test-source"]
allowed_numbers = ["0", "60"]

[[grounding.facts]]
id = "fact-two"
canonical_text = "Canonical two."
child_text = "Child two."
source_ids = ["test-source"]
allowed_numbers = []

[[steps]]
id = "intro-step"
kind = "intro"
heading = "Intro heading"
body = "Intro body."
fact_ids = ["fact-one"]
scope_terms = ["car", "time"]

[[steps]]
id = "teach-step"
kind = "teach"
heading = "Teach heading"
body = "Teach body."
fact_ids = ["fact-two"]
scope_terms = ["acceleration", "time"]

[check]
id = "test-check"
prompt = "Which one?"
correct_choice_id = "choice-a"
hints = ["First hint.", "Second hint."]
success_text = "Correct."
reveal_text = "It was A."
fact_ids = ["fact-one", "fact-two"]
scope_terms = ["car", "time"]
allowed_short_replies = ["no", "yes"]

[[check.choices]]
id = "choice-a"
label = "Choice A"

[[check.choices]]
id = "choice-b"
label = "Choice B"
"""


@pytest.fixture
def valid_lesson_toml() -> str:
    """Approved TOML with a placeholder payload hash.

    The placeholder is replaced with the real recomputed hash by
    :func:`approved_lesson_toml`. A fixed test-only review date is acceptable
    here because this is a fixture, never production content.
    """
    return VALID_LESSON_TOML


@pytest.fixture
def draft_lesson_toml() -> str:
    """The same lesson as draft, with no attestations."""
    head, _, tail = VALID_LESSON_TOML.partition("[review]")
    _, _, rest = tail.partition("[grounding]")
    return head + '[review]\nstatus = "draft"\n\n[grounding]' + rest


@pytest.fixture
def approved_lesson_toml(draft_lesson_toml) -> str:
    """Approved TOML carrying the real recomputed payload hash.

    The payload hash excludes review metadata, so it can be computed from the
    draft form of the same lesson and then substituted into the approved form.
    """
    from lerni.explore.catalog import lesson_payload_sha256, parse_lesson_toml

    digest = lesson_payload_sha256(parse_lesson_toml(draft_lesson_toml))
    return VALID_LESSON_TOML.replace("PAYLOAD_HASH", digest)
