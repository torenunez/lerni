"""Chain-1 content tests.

Two kinds of assertion live here. Most check properties of the authored content
that tooling can verify: the science is stated correctly, no brand or mutable
ranking is packaged, the visual is accessible. Two check the human review gate,
and they are expected to fail until real people actually review this lesson.
That failure is the gate working, not a defect to route around.
"""

import hashlib
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest

from lerni.explore.catalog import (
    PackageLessonCatalog,
    lesson_payload_sha256,
    parse_lesson_toml,
)
from lerni.explore.domain import (
    ApprovalStatus,
    LessonNotApprovedError,
    LessonPhase,
    LessonSnapshot,
    StepKind,
    context_for_snapshot,
)

LESSON_ID = "chain-1-acceleration"
LESSONS_DIR = pathlib.Path(__file__).resolve().parents[2] / "src/lerni/explore/lessons"


@pytest.fixture
def chain_1():
    """The production lesson parsed directly, bypassing the approval boundary."""
    path = LESSONS_DIR / "chain_1_acceleration.toml"
    return parse_lesson_toml(path.read_text(encoding="utf-8"), origin=path.name)


@pytest.fixture
def all_child_text(chain_1) -> str:
    """Every string the child can actually read, lowercased."""
    parts = [chain_1.title]
    for step in chain_1.steps:
        parts += [step.heading, step.body]
        if step.visual:
            parts.append(step.visual.alt_text)
    check = chain_1.check
    parts += [check.prompt, check.success_text, check.reveal_text, *check.hints]
    parts += [c.label for c in check.choices]
    parts += [f.child_text for f in chain_1.grounding.facts]
    return " ".join(parts).lower()


def test_chain_1_uses_explicit_sequence(chain_1):
    assert chain_1.sequence == ("hook-0-to-60", "teach-acceleration")
    assert [s.kind for s in chain_1.steps] == [StepKind.INTRO, StepKind.TEACH]


def test_chain_1_calls_zero_to_sixty_elapsed_time(chain_1):
    fact = next(f for f in chain_1.grounding.facts if f.id == "zero-to-sixty-is-time")
    assert "elapsed time" in fact.canonical_text
    assert "seconds" in fact.child_text


def test_chain_1_defines_average_acceleration_as_velocity_change_over_time(chain_1):
    fact = next(f for f in chain_1.grounding.facts if f.id == "acceleration-definition")
    assert "change in velocity" in fact.canonical_text
    assert "elapsed time" in fact.canonical_text


def test_chain_1_distinguishes_average_from_instantaneous(chain_1):
    fact = next(f for f in chain_1.grounding.facts if f.id == "average-not-instant")
    assert "does not reveal acceleration at every instant" in fact.canonical_text


def test_chain_1_qualifies_the_comparison_claim(chain_1):
    # Without the same-endpoints qualifier the comparison claim is simply false.
    fact = next(f for f in chain_1.grounding.facts if f.id == "shorter-time-greater-average")
    assert "same initial and final velocities" in fact.canonical_text
    assert "same speed change" in fact.child_text


def test_chain_1_contains_no_false_name_claim(all_child_text):
    # The rejected draft line was "that 0-60 number has a name: acceleration".
    # A 0-60 figure is elapsed time; naming it acceleration is wrong.
    assert not re.search(r"(has a name|is called|called)\s*:?\s*acceleration", all_child_text)


def test_chain_1_contains_no_brand_or_mutable_ranking(all_child_text):
    brands = ("tesla", "ferrari", "porsche", "bugatti", "lamborghini", "corvette", "bmw")
    for brand in brands:
        assert brand not in all_child_text
    for phrase in ("fastest", "quickest", "world record", "best car", "top speed"):
        assert phrase not in all_child_text


def test_chain_1_presents_seconds_as_hypothetical(chain_1):
    # 4 and 8 seconds are lesson examples. They must not be attached to a
    # real vehicle, which would be an unsourced and perishable claim.
    fact = next(f for f in chain_1.grounding.facts if f.id == "shorter-time-greater-average")
    assert set(fact.allowed_numbers) == {"0", "4", "8", "60"}


def test_chain_1_check_has_one_correct_choice(chain_1):
    check = chain_1.check
    assert len(check.choices) == 3
    assert check.correct_choice_id == "car-a"
    assert sum(c.id == check.correct_choice_id for c in check.choices) == 1


def test_chain_1_has_exactly_two_progressive_hints(chain_1):
    assert len(chain_1.check.hints) == 2
    assert chain_1.check.hints[0] != chain_1.check.hints[1]


def test_chain_1_references_reviewed_https_source(chain_1):
    sources = chain_1.grounding.sources
    assert len(sources) == 1
    assert sources[0].id == "nasa-acceleration"
    assert sources[0].url.startswith("https://")
    for fact in chain_1.grounding.facts:
        assert fact.source_ids == ("nasa-acceleration",)


def test_chain_1_has_no_graph_relationship_fields(chain_1):
    for attr in ("edges", "relationship", "prerequisites", "hops", "concept_ids"):
        assert not hasattr(chain_1, attr)
    for step in chain_1.steps:
        assert not hasattr(step, "edge_id")


def test_chain_1_effective_turn_cap_is_reviewed_content(chain_1):
    assert chain_1.max_turns == 8


def test_context_for_each_snapshot_contains_only_bound_facts(chain_1):
    intro = LessonSnapshot(
        lesson_id=chain_1.id,
        lesson_content_version=chain_1.content_version,
        title=chain_1.title,
        phase=LessonPhase.INTRO,
        step_id="hook-0-to-60",
        heading="",
        body="",
        visual=None,
        choices=(),
        hint_text=None,
        completion=None,
        can_continue=True,
        can_submit_choice=False,
        can_restart=True,
    )
    context = context_for_snapshot(chain_1, intro)
    assert [f.id for f in context.grounding.facts] == ["zero-to-sixty-is-time"]
    # The intro must not leak the teach step's facts, which the child has not
    # reached, nor the check's, which would hand a tutor the answer's grounding.
    assert "acceleration-definition" not in {f.id for f in context.grounding.facts}


# --- Visual --------------------------------------------------------------


def test_chain_1_visual_is_packaged_and_accessible(chain_1):
    svg_path = LESSONS_DIR / "assets/chain_1_acceleration.svg"
    assert svg_path.exists()
    root = ET.parse(svg_path).getroot()
    ns = "{http://www.w3.org/2000/svg}"
    assert root.get("viewBox") == "0 0 800 360"
    assert root.get("role") == "img"
    assert root.find(f"{ns}title") is not None
    assert root.find(f"{ns}desc") is not None

    for step in chain_1.steps:
        assert step.visual is not None
        assert step.visual.resource_name == "assets/chain_1_acceleration.svg"
        assert step.visual.alt_text.strip()


def test_chain_1_visual_carries_no_active_or_remote_content():
    text = (LESSONS_DIR / "assets/chain_1_acceleration.svg").read_text(encoding="utf-8")
    for forbidden in (
        "<script",
        "<animate",
        "onload",
        "onclick",
        "xlink:href",
        "<image",
        "<foreignObject",
        "url(",
    ):
        assert forbidden not in text

    # The SVG namespace URI is an identifier, not a fetch; it is the only URL
    # permitted here. Anything else would make rendering reach the network.
    urls = set(re.findall(r'https?://[^\s"\')<]+', text))
    assert urls == {"http://www.w3.org/2000/svg"}, f"unexpected URL(s): {urls - {'http://www.w3.org/2000/svg'}}"


def test_chain_1_visual_meaning_survives_without_color():
    # Both bars use the same fill; the distinction is length and text labels.
    text = (LESSONS_DIR / "assets/chain_1_acceleration.svg").read_text(encoding="utf-8")
    fills = set(re.findall(r'fill="(#[0-9a-fA-F]{6})"', text))
    assert len(fills) <= 3, f"too many distinct fills to be color-independent: {fills}"
    assert "4 seconds" in text and "8 seconds" in text


def test_chain_1_index_matches_actual_bytes():
    index = parse_index()
    lesson_bytes = (LESSONS_DIR / "chain_1_acceleration.toml").read_bytes()
    assert index["lesson_sha256"] == hashlib.sha256(lesson_bytes).hexdigest()
    svg_bytes = (LESSONS_DIR / "assets/chain_1_acceleration.svg").read_bytes()
    assert index["asset_sha256"] == hashlib.sha256(svg_bytes).hexdigest()


def parse_index() -> dict[str, str]:
    import tomllib

    data = tomllib.loads((LESSONS_DIR / "lesson_index.toml").read_text(encoding="utf-8"))
    return {
        "lesson_sha256": data["lessons"][0]["sha256"],
        "payload_sha256": data["lessons"][0]["lesson_payload_sha256"],
        "asset_sha256": data["assets"][0]["sha256"],
    }


def test_chain_1_payload_hash_matches_index(chain_1):
    assert lesson_payload_sha256(chain_1) == parse_index()["payload_sha256"]


# --- The human review gate ----------------------------------------------


def test_chain_1_is_still_draft(chain_1):
    """Guards the gate itself.

    If this starts failing, either real reviews were recorded (delete this test
    and let the two below carry the contract) or an attestation was fabricated.
    """
    assert chain_1.review.status is ApprovalStatus.DRAFT
    assert chain_1.review.attestations == ()


def test_child_catalog_refuses_draft_chain_1():
    with pytest.raises(LessonNotApprovedError):
        PackageLessonCatalog().load(LESSON_ID)


@pytest.mark.xfail(
    reason="Blocked on the human review gate: four real attestations are required. "
    "See plans/runbooks/chain-1-source-review.md. Do not satisfy this by "
    "fabricating review metadata.",
    strict=True,
)
def test_child_catalog_loads_approved_chain_1():
    lesson = PackageLessonCatalog().load(LESSON_ID)
    assert lesson.review.status is ApprovalStatus.APPROVED
    assert {a.scope for a in lesson.review.attestations} == {
        "science",
        "child_content",
        "visual_accessibility",
        "parent_approval",
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
