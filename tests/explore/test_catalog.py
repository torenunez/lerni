"""Strict lesson TOML parsing and the approved-content boundary.

Every rule here fails closed. Content a child can see must be exactly what a
human reviewed, so ambiguity, drift, and missing review are rejected rather than
tolerated.
"""

import re

import pytest

from lerni.explore.catalog import (
    lesson_payload_sha256,
    parse_lesson_toml,
)
from lerni.explore.domain import ApprovalStatus, LessonContentError, ReviewScope


def _without(toml_text: str, block: str) -> str:
    return toml_text.replace(block, "")


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


def test_rejects_unknown_top_level_key(draft_lesson_toml):
    with pytest.raises(LessonContentError, match="unknown key"):
        parse_lesson_toml(draft_lesson_toml + '\nsurprise = "x"\n')


def test_rejects_unsupported_schema_version(draft_lesson_toml):
    bad = draft_lesson_toml.replace("schema_version = 1", "schema_version = 2")
    with pytest.raises(LessonContentError, match="schema_version"):
        parse_lesson_toml(bad)


def test_rejects_string_where_integer_required(draft_lesson_toml):
    bad = draft_lesson_toml.replace("content_version = 1", 'content_version = "1"')
    with pytest.raises(LessonContentError, match="content_version"):
        parse_lesson_toml(bad)


def test_rejects_duplicate_sequence_id(draft_lesson_toml):
    bad = draft_lesson_toml.replace(
        'sequence = ["intro-step", "teach-step"]',
        'sequence = ["intro-step", "intro-step", "teach-step"]',
    )
    with pytest.raises(LessonContentError, match="duplicate"):
        parse_lesson_toml(bad)


def test_rejects_missing_sequence_step(draft_lesson_toml):
    bad = draft_lesson_toml.replace(
        'sequence = ["intro-step", "teach-step"]',
        'sequence = ["intro-step", "teach-step", "ghost-step"]',
    )
    with pytest.raises(LessonContentError, match="ghost-step"):
        parse_lesson_toml(bad)


def test_rejects_orphan_step(draft_lesson_toml):
    bad = draft_lesson_toml.replace(
        'sequence = ["intro-step", "teach-step"]',
        'sequence = ["intro-step"]',
    )
    with pytest.raises(LessonContentError, match="teach-step"):
        parse_lesson_toml(bad)


def test_rejects_non_intro_first_step(draft_lesson_toml):
    bad = draft_lesson_toml.replace('kind = "intro"', 'kind = "teach"')
    with pytest.raises(LessonContentError, match="intro"):
        parse_lesson_toml(bad)


def test_rejects_second_intro_step(draft_lesson_toml):
    bad = draft_lesson_toml.replace('kind = "teach"', 'kind = "intro"')
    with pytest.raises(LessonContentError, match="teach"):
        parse_lesson_toml(bad)


def test_rejects_dangling_fact_source(draft_lesson_toml):
    bad = draft_lesson_toml.replace('source_ids = ["test-source"]', 'source_ids = ["ghost"]')
    with pytest.raises(LessonContentError, match="ghost"):
        parse_lesson_toml(bad)


def test_rejects_step_reference_to_unknown_fact(draft_lesson_toml):
    bad = draft_lesson_toml.replace(
        'fact_ids = ["fact-one"]\nscope_terms', 'fact_ids = ["ghost"]\nscope_terms'
    )
    with pytest.raises(LessonContentError, match="ghost"):
        parse_lesson_toml(bad)


def test_rejects_non_https_source(draft_lesson_toml):
    bad = draft_lesson_toml.replace("https://example.org/test", "http://example.org/test")
    with pytest.raises(LessonContentError, match="https"):
        parse_lesson_toml(bad)


def test_rejects_invalid_id_format(draft_lesson_toml):
    bad = draft_lesson_toml.replace('lesson_id = "test-lesson"', 'lesson_id = "Test_Lesson"')
    with pytest.raises(LessonContentError, match="lesson_id"):
        parse_lesson_toml(bad)


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


def test_rejects_duplicate_review_scope(approved_lesson_toml):
    bad = approved_lesson_toml.replace('scope = "science"', 'scope = "child_content"')
    with pytest.raises(LessonContentError, match="duplicate review scope"):
        parse_lesson_toml(bad)


def test_rejects_attestation_for_different_payload(approved_lesson_toml):
    # Replace *every* occurrence, so the "all attestations agree" rule still
    # passes and the failure can only come from the payload recomputation.
    digest = lesson_payload_sha256(parse_lesson_toml(approved_lesson_toml))
    bad = approved_lesson_toml.replace(digest, "0" * 64)
    with pytest.raises(LessonContentError, match="approves payload"):
        parse_lesson_toml(bad)


def test_rejects_attestations_disagreeing_on_payload(approved_lesson_toml):
    digest = lesson_payload_sha256(parse_lesson_toml(approved_lesson_toml))
    bad = approved_lesson_toml.replace(digest, "0" * 64, 1)
    with pytest.raises(LessonContentError, match="same reviewed_payload_sha256"):
        parse_lesson_toml(bad)


def test_rejects_content_edited_after_approval(approved_lesson_toml):
    # The realistic drift: someone tweaks child-facing text without re-reviewing.
    bad = approved_lesson_toml.replace(
        'body = "Teach body."', 'body = "Edited after review."'
    )
    with pytest.raises(LessonContentError, match="approves payload"):
        parse_lesson_toml(bad)


def test_rejects_draft_with_attestation(approved_lesson_toml):
    bad = approved_lesson_toml.replace('status = "approved"', 'status = "draft"')
    with pytest.raises(LessonContentError, match="draft"):
        parse_lesson_toml(bad)


def test_rejects_asset_path_traversal(draft_lesson_toml):
    bad = draft_lesson_toml.replace(
        'body = "Intro body."',
        'body = "Intro body."\n'
        'visual_resource = "../secrets.svg"\n'
        'visual_media_type = "image/svg+xml"\n'
        'visual_alt = "x"\n'
        'visual_sha256 = ""',
    )
    with pytest.raises(LessonContentError, match="assets/"):
        parse_lesson_toml(bad)


def test_rejects_too_few_check_choices(draft_lesson_toml):
    bad = draft_lesson_toml.replace(
        '[[check.choices]]\nid = "choice-b"\nlabel = "Choice B"\n', ""
    )
    with pytest.raises(LessonContentError, match="choices"):
        parse_lesson_toml(bad)


def test_rejects_missing_correct_choice(draft_lesson_toml):
    bad = draft_lesson_toml.replace('correct_choice_id = "choice-a"', 'correct_choice_id = "ghost"')
    with pytest.raises(LessonContentError, match="ghost"):
        parse_lesson_toml(bad)


def test_rejects_no_hints(draft_lesson_toml):
    bad = draft_lesson_toml.replace('hints = ["First hint.", "Second hint."]', "hints = []")
    with pytest.raises(LessonContentError, match="hints"):
        parse_lesson_toml(bad)


def test_rejects_max_turns_out_of_range(draft_lesson_toml):
    for value in (0, 21):
        bad = draft_lesson_toml.replace("max_turns = 8", f"max_turns = {value}")
        with pytest.raises(LessonContentError, match="max_turns"):
            parse_lesson_toml(bad)


def test_rejects_noncanonical_scope_term(draft_lesson_toml):
    bad = draft_lesson_toml.replace(
        'scope_terms = ["car", "time"]', 'scope_terms = ["Car", "time"]'
    )
    with pytest.raises(LessonContentError, match="canonical"):
        parse_lesson_toml(bad)


def test_rejects_duplicate_scope_term(draft_lesson_toml):
    bad = draft_lesson_toml.replace(
        'scope_terms = ["car", "time"]', 'scope_terms = ["car", "car"]'
    )
    with pytest.raises(LessonContentError, match="duplicate"):
        parse_lesson_toml(bad)


def test_rejects_fact_with_no_source(draft_lesson_toml):
    bad = draft_lesson_toml.replace(
        'source_ids = ["test-source"]\nallowed_numbers = []',
        "source_ids = []\nallowed_numbers = []",
    )
    with pytest.raises(LessonContentError, match="source"):
        parse_lesson_toml(bad)


def test_rejects_blank_grounding_text(draft_lesson_toml):
    bad = draft_lesson_toml.replace('redirect_text = "Redirect."', 'redirect_text = "  "')
    with pytest.raises(LessonContentError, match="redirect_text"):
        parse_lesson_toml(bad)


def test_rejects_oversized_allowed_number(draft_lesson_toml):
    oversized = "9" * 33
    bad = draft_lesson_toml.replace(
        'allowed_numbers = ["0", "60"]', f'allowed_numbers = ["{oversized}"]'
    )
    with pytest.raises(LessonContentError, match="allowed_numbers"):
        parse_lesson_toml(bad)


def test_error_includes_origin_and_field_path(draft_lesson_toml):
    bad = draft_lesson_toml.replace("max_turns = 8", "max_turns = 99")
    with pytest.raises(LessonContentError) as exc:
        parse_lesson_toml(bad, origin="lesson.toml")
    assert str(exc.value).startswith("lesson.toml:max_turns:")


def test_rejects_malformed_toml():
    with pytest.raises(LessonContentError, match="TOML"):
        parse_lesson_toml("this is not = = toml")


def test_review_metadata_only_change_preserves_payload_hash(approved_lesson_toml):
    baseline = lesson_payload_sha256(parse_lesson_toml(approved_lesson_toml))
    changed = approved_lesson_toml.replace(
        'reviewer_role = "test-reviewer"', 'reviewer_role = "other-role"'
    )
    assert lesson_payload_sha256(parse_lesson_toml(changed)) == baseline


def test_runtime_change_changes_payload_hash(draft_lesson_toml):
    baseline = lesson_payload_sha256(parse_lesson_toml(draft_lesson_toml))
    changed = draft_lesson_toml.replace('body = "Teach body."', 'body = "Different body."')
    assert lesson_payload_sha256(parse_lesson_toml(changed)) != baseline


def test_payload_hash_is_stable_across_calls(draft_lesson_toml):
    lesson = parse_lesson_toml(draft_lesson_toml)
    assert lesson_payload_sha256(lesson) == lesson_payload_sha256(lesson)
