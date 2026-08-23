# Explore Safe Slice — Lesson Domain, Content, and Deterministic State

## Goal

Implement a standard-library lesson core that:

- is independent of Study’s `Question`, `Answer`, `Review`, and `ConceptEdge` semantics;
- loads a strict, source-backed lesson snapshot from packaged TOML;
- exposes only child-safe presentation data;
- advances through deterministic application events;
- cannot be advanced by tutor output;
- remains testable without Gradio, a model, credentials, network access, or a database.

## File map

Create:

```text
src/lerni/explore/
├── __init__.py
├── canonical.py
├── domain.py
├── catalog.py
├── engine.py
└── lessons/
    ├── __init__.py
    ├── lesson_index.toml
    ├── chain_1_acceleration.toml
    └── assets/
        └── chain_1_acceleration.svg

tests/explore/
├── __init__.py
├── conftest.py
├── test_domain.py
├── test_catalog.py
├── test_chain_1_content.py
├── test_engine.py
└── test_distribution.py
```

Modify:

- `pyproject.toml` for package data.
- `MANIFEST.in` only if source-distribution verification proves setuptools package-data configuration alone is insufficient.

Do not modify:

- `src/lerni/models.py`;
- `src/lerni/db.py`;
- `src/lerni/sm2.py`;
- Study command modules.

## Public domain contract

Implement in `domain.py`.

```python
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


class ReviewScope(StrEnum):
    SCIENCE = "science"
    CHILD_CONTENT = "child_content"
    VISUAL_ACCESSIBILITY = "visual_accessibility"
    PARENT_APPROVAL = "parent_approval"


class StepKind(StrEnum):
    INTRO = "intro"
    TEACH = "teach"


class LessonPhase(StrEnum):
    INTRO = "intro"
    TEACH = "teach"
    CHECK = "check"
    HINT = "hint"
    COMPLETE = "complete"


class LessonAction(StrEnum):
    CONTINUE = "continue"
    SUBMIT_CHOICE = "submit_choice"
    RESTART = "restart"


class CompletionKind(StrEnum):
    CORRECT = "correct"
    ANSWER_REVEALED = "answer_revealed"


class TransitionOutcome(StrEnum):
    ADVANCED = "advanced"
    HINT_SHOWN = "hint_shown"
    COMPLETED_CORRECT = "completed_correct"
    COMPLETED_REVEALED = "completed_revealed"
    RESTARTED = "restarted"


@dataclass(frozen=True, slots=True)
class ReviewAttestation:
    id: str
    scope: ReviewScope
    reviewer_role: str
    reviewed_on: date
    evidence_ref: str | None
    reviewed_payload_sha256: str


@dataclass(frozen=True, slots=True)
class ReviewMetadata:
    status: ApprovalStatus
    attestations: tuple[ReviewAttestation, ...]


@dataclass(frozen=True, slots=True)
class SourceReference:
    id: str
    title: str
    publisher: str
    url: str
    retrieved_on: date


@dataclass(frozen=True, slots=True)
class GroundedFact:
    id: str
    canonical_text: str
    child_text: str
    source_ids: tuple[str, ...]
    allowed_numbers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GroundingBundle:
    scope: str
    fallback_text: str
    redirect_text: str
    facts: tuple[GroundedFact, ...]
    sources: tuple[SourceReference, ...]


@dataclass(frozen=True, slots=True)
class AssetRef:
    resource_name: str
    media_type: str
    alt_text: str
    sha256: str | None


@dataclass(frozen=True, slots=True)
class LessonStep:
    id: str
    kind: StepKind
    heading: str
    body: str
    visual: AssetRef | None
    fact_ids: tuple[str, ...]
    scope_terms: frozenset[str]


@dataclass(frozen=True, slots=True)
class CheckChoice:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class RetrievalCheck:
    id: str
    prompt: str
    choices: tuple[CheckChoice, ...]
    correct_choice_id: str
    hints: tuple[str, ...]
    success_text: str
    reveal_text: str
    fact_ids: tuple[str, ...]
    scope_terms: frozenset[str]
    allowed_short_replies: frozenset[str]


@dataclass(frozen=True, slots=True)
class Lesson:
    schema_version: int
    id: str
    content_version: int
    title: str
    locale: str
    audience: str
    max_turns: int
    review: ReviewMetadata
    sequence: tuple[str, ...]
    steps: tuple[LessonStep, ...]
    check: RetrievalCheck
    grounding: GroundingBundle


@dataclass(frozen=True, slots=True)
class LessonPackageIdentity:
    lesson_id: str
    content_version: int
    package_sha256: str
    lesson_payload_sha256: str


@dataclass(frozen=True, slots=True)
class LessonState:
    lesson_id: str
    lesson_content_version: int
    phase: LessonPhase
    step_index: int | None
    attempts: int
    hint_index: int | None
    completion: CompletionKind | None


@dataclass(frozen=True, slots=True)
class LessonEvent:
    action: LessonAction
    choice_id: str | None = None


@dataclass(frozen=True, slots=True)
class ChoiceView:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class LessonSnapshot:
    lesson_id: str
    lesson_content_version: int
    title: str
    phase: LessonPhase
    step_id: str | None
    heading: str
    body: str
    visual: AssetRef | None
    choices: tuple[ChoiceView, ...]
    hint_text: str | None
    completion: CompletionKind | None
    can_continue: bool
    can_submit_choice: bool
    can_restart: bool


@dataclass(frozen=True, slots=True)
class LessonTransition:
    before: LessonState
    event: LessonEvent
    after: LessonState
    outcome: TransitionOutcome


@dataclass(frozen=True, slots=True)
class LessonContext:
    grounding: GroundingBundle
    scope_terms: frozenset[str]
    allowed_short_replies: frozenset[str]
    redirect_text: str  # exact grounding.redirect_text
```

Exceptions:

```python
class LessonError(Exception):
    pass


class LessonContentError(LessonError, ValueError):
    pass


class LessonNotFoundError(LessonError):
    pass


class LessonNotApprovedError(LessonError):
    pass


class InvalidLessonStateError(LessonError, ValueError):
    pass


class InvalidTransitionError(LessonError, ValueError):
    pass


class UnknownChoiceError(LessonError, ValueError):
    pass
```

Domain exclusions:

- no provider, model, credential, prompt, or SDK fields;
- no raw child text;
- no database IDs;
- no `ConceptEdge`, relationship, hop, graph, or traversal fields;
- no mutable collection exposed by a frozen object.

Implement:

```python
def context_for_snapshot(
    lesson: Lesson,
    snapshot: LessonSnapshot,
) -> LessonContext:
    ...
```

It resolves the exact current step/check fact IDs, preserves source order, rejects missing references, and returns policy scope data. Tutor code never receives the full lesson-wide fact set when only a subset is current.

## Task 1 — Domain types through TDD

Write `tests/explore/test_domain.py`.

Required tests:

```python
def test_phase_values_are_stable():
    assert [phase.value for phase in LessonPhase] == [
        "intro",
        "teach",
        "check",
        "hint",
        "complete",
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
```

Add:

- `test_grounding_uses_ordered_immutable_tuples`;
- `test_state_contains_no_child_text`;
- `test_snapshot_has_no_correct_choice_id`;
- `test_event_requires_explicit_action`.

Red:

```bash
"$PYTHON" -m pytest tests/explore/test_domain.py -q
```

Before adding each test, scaffold an importable module with the public symbol and deliberately incomplete behavior. Each recorded red failure must be a behavior-specific assertion, not a missing-module or missing-symbol error.

Green:

- implement only the listed types and exceptions;
- run the same test file;
- do not add parsing, engine, UI, or adapter behavior yet.

## Catalog contract

Implement in `catalog.py`.

```python
from typing import Protocol


class LessonCatalog(Protocol):
    def load(self, lesson_id: str) -> Lesson:
        ...

    def read_asset(self, asset: AssetRef) -> bytes:
        ...

    def identity(self, lesson_id: str) -> LessonPackageIdentity:
        ...


def parse_lesson_toml(
    text: str,
    *,
    origin: str = "<memory>",
) -> Lesson:
    ...


class PackageLessonCatalog:
    def load(self, lesson_id: str) -> Lesson:
        ...

    def read_asset(self, asset: AssetRef) -> bytes:
        ...

    def identity(self, lesson_id: str) -> LessonPackageIdentity:
        ...
```

`PackageLessonCatalog.load()` is the child-safe approved boundary. It rejects missing, draft, hash-mismatched, or index-mismatched content.

The package index maps stable lesson IDs to resource names and SHA-256 hashes:

```toml
schema_version = 1

[[lessons]]
lesson_id = "chain-1-acceleration"
resource_name = "chain_1_acceleration.toml"
sha256 = "generated from the final reviewed bytes"
lesson_payload_sha256 = "generated from the canonical review-independent lesson payload"

[[assets]]
resource_name = "assets/chain_1_acceleration.svg"
media_type = "image/svg+xml"
sha256 = "generated from the exact reviewed SVG bytes"
```

Literal hashes are generated from actual files and then reviewed; the quoted values above describe the index schema and are never copied as literal hashes. Tests that need draft parsing call `parse_lesson_toml()` directly. There is no child-facing raw package loader.

`LessonPackageIdentity.package_sha256` is exactly the index `[[lessons]].sha256`: SHA-256 of the final lesson TOML bytes. Those bytes pin every referenced asset hash, so asset changes require a TOML/index update and change package identity transitively. It is not a directory/archive hash.

`lesson_payload_sha256` is SHA-256 of `canonical_json_bytes()` for one exact object:

```python
{
    "schema_version": lesson.schema_version,
    "id": lesson.id,
    "content_version": lesson.content_version,
    "title": lesson.title,
    "locale": lesson.locale,
    "audience": lesson.audience,
    "max_turns": lesson.max_turns,
    "sequence": [...],
    "steps": [
        {
            "id": ..., "kind": <enum value>, "heading": ..., "body": ...,
            "visual": None | {
                "resource_name": ..., "media_type": ...,
                "alt_text": ..., "sha256": ...
            },
            "fact_ids": [...],
            "scope_terms": <normalized UTF-8-byte-sorted list>
        }
    ],
    "check": {
        "id": ..., "prompt": ...,
        "choices": [{"id": ..., "label": ...}, ...],
        "correct_choice_id": ..., "hints": [...],
        "success_text": ..., "reveal_text": ..., "fact_ids": [...],
        "scope_terms": <normalized UTF-8-byte-sorted list>,
        "allowed_short_replies": <normalized UTF-8-byte-sorted list>
    },
    "grounding": {
        "scope": ..., "fallback_text": ..., "redirect_text": ...,
        "facts": [{
            "id": ..., "canonical_text": ..., "child_text": ...,
            "source_ids": [...], "allowed_numbers": [...]
        }, ...],
        "sources": [{
            "id": ..., "title": ..., "publisher": ..., "url": ...,
            "retrieved_on": <ISO local-date string>
        }, ...]
    },
    "referenced_assets": [
        {"resource_name": ..., "media_type": ..., "sha256": ...}, ...
    ]
}
```

`review` is the only omitted `Lesson` field. Approved visual objects retain their nested non-null SHA-256; `referenced_assets` intentionally repeats the identity tuple and is sorted by UTF-8 bytes of `(resource_name, media_type, sha256)`, with one entry per unique referenced visual. Sequence/tuple fields preserve declared order; only frozenset-backed scope/reply fields use the stated sort. PR-02 creates `canonical_json_bytes()` in `canonical.py` using sorted mapping keys, compact separators, UTF-8, `ensure_ascii=False`, finite numbers only, arrays for tuples, and no trailing bytes. Reject unknown/missing keys, duplicate assets, null approved hashes, or non-finite/noncanonical values. A single installed golden fixture is shared by PR-02 and PR-09. This identity changes for any child-visible or grounding/runtime behavior but not reviewer role/date/evidence metadata. `PackageLessonCatalog` independently reconstructs and verifies it before returning an approved lesson.

Package reads are bounded before full decode/allocation: lesson index `65_536` bytes, one lesson TOML `256_000` bytes, and one SVG asset `1_000_000` bytes. Read at most limit plus one from the `importlib.resources` binary stream, reject overage, then hash and parse those exact bytes.

Every approved lesson asset reference carries the same hash as the package index; a draft may omit it. `read_asset()` verifies:

1. resource exists in index;
2. media type matches;
3. `AssetRef.sha256` matches index;
4. SHA-256 of returned bytes matches index.

Any mismatch fails closed before bytes reach the visual renderer.

Use:

```python
importlib.resources.files("lerni.explore.lessons")
```

Do not convert package resources to `Path`; installed zipped resources need not have filesystem paths.

## Strict validation rules

`parse_lesson_toml()` raises:

```text
{origin}:{field-path}: {message}
```

Reject:

- malformed TOML;
- unknown keys at every level;
- `schema_version` other than `1`;
- IDs outside `^[a-z0-9]+(?:-[a-z0-9]+)*$`;
- `content_version < 1`;
- duplicate source, fact, step, or choice IDs;
- duplicate review-attestation IDs or review scopes;
- duplicate sequence IDs;
- a sequence reference to a missing step;
- an authored step absent from the sequence;
- first step not `intro`;
- any later authored step not `teach`;
- no teach step;
- non-HTTPS source URL;
- fact references to unknown sources;
- blank grounding scope, fallback text, or redirect text;
- unsupported asset media type;
- asset path outside `assets/`, absolute path, or `..`;
- malformed asset SHA-256;
- non-empty draft `visual_sha256` that does not match the package index;
- approved lesson asset without a SHA-256 matching its package index entry;
- repeated visual resource with inconsistent SHA-256;
- fewer than two check choices;
- missing correct choice;
- no hints;
- approved lesson with a blank reviewer role/date in any attestation;
- approved lesson with a missing, malformed, non-identical, or recomputation-mismatched `reviewed_payload_sha256`;
- approved lesson missing science, child-content, visual-accessibility, or parent-approval attestation;
- draft lesson with any attestation;
- step/check fact reference to an unknown fact;
- empty current-step fact set or scope terms;
- a `scope_terms`/`allowed_short_replies` item that is not already the exact canonical policy token: NFKC, policy apostrophe/dash folding, `casefold()`, then full-match of the appendix `TOKEN_RE`; reject duplicates after that canonicalization;
- `max_turns` outside 1–20;
- a fact with an empty source list;
- allowed number longer than 32 characters or containing unsupported characters.

Do not silently coerce types. A string `"1"` is not integer `1`.

The parser validates and stores only those canonical casefolded token strings before constructing each `frozenset`. PR-09 uses the identical function. Payload encoding sorts these canonical strings by UTF-8 bytes, so TOML and CSV compilation cannot differ by case or Unicode punctuation.

`grounding.redirect_text` is the sole source of `LessonContext.redirect_text`. `steps[].visual_sha256` is the sole TOML hash key: exact empty string maps to `None` only while lesson status is draft; approved content requires the lowercase package-index hash.

## Task 2 — Catalog parser through TDD

Create a complete valid TOML string fixture in `tests/explore/conftest.py`. The fixture may be approved with a fixed test-only review date because it is not production content.

Write:

- `test_parse_valid_toml_returns_exact_lesson`;
- `test_rejects_unknown_top_level_key`;
- `test_rejects_unsupported_schema_version`;
- `test_rejects_duplicate_sequence_id`;
- `test_rejects_missing_sequence_step`;
- `test_rejects_orphan_step`;
- `test_rejects_non_intro_first_step`;
- `test_rejects_dangling_fact_source`;
- `test_rejects_non_https_source`;
- `test_rejects_approved_without_attestation`;
- `test_rejects_attestation_for_different_payload`;
- `test_rejects_draft_with_attestation`;
- `test_rejects_asset_path_traversal`;
- `test_catalog_verifies_canonical_lesson_payload_hash`;
- `test_runtime_or_asset_change_changes_payload_hash`;
- `test_review_metadata_only_change_preserves_payload_hash`;
- `test_error_includes_origin_and_field_path`.

Every expectation is a literal derived independently from the parser.

Red:

```bash
"$PYTHON" -m pytest tests/explore/test_catalog.py -q
```

Expected: one specific validation assertion fails against the scaffolded parser. Do not count an import error as red evidence.

Green:

- parse with `tomllib.loads`;
- validate explicit mappings;
- reject unknown keys before constructing objects;
- convert lists to tuples only after validation.

## Production Chain-1 TOML

Create `chain_1_acceleration.toml` as `draft`.

Normative content:

```toml
schema_version = 1
lesson_id = "chain-1-acceleration"
content_version = 1
title = "What does 0–60 tell us?"
locale = "en-US"
audience = "ages-7-9"
max_turns = 8
sequence = ["hook-0-to-60", "teach-acceleration"]

[review]
status = "draft"

[grounding]
scope = "Straight-line 0-to-60 elapsed time, velocity change, and average acceleration. Excludes current car rankings, brand performance, crashes, and buying advice."
fallback_text = "That question goes beyond this lesson. Let's save it for a grown-up to check, and come back to 0–60 time and acceleration."
redirect_text = "Let's stay with 0–60 time and average acceleration. A grown-up can help save that other question for later."

[[grounding.sources]]
id = "nasa-acceleration"
title = "Displacement, Velocity, Acceleration"
publisher = "NASA Glenn Research Center"
url = "https://www.grc.nasa.gov/WWW/K-12/airplane/disvelac.html"
retrieved_on = 2026-08-22

[[grounding.facts]]
id = "zero-to-sixty-is-time"
canonical_text = "A 0-to-60 result reports the elapsed time for velocity to change from 0 miles per hour to 60 miles per hour."
child_text = "A 0–60 result tells how many seconds the speed change took."
source_ids = ["nasa-acceleration"]
allowed_numbers = ["0", "60"]

[[grounding.facts]]
id = "acceleration-definition"
canonical_text = "Average acceleration is change in velocity divided by elapsed time."
child_text = "Acceleration tells how quickly velocity changes."
source_ids = ["nasa-acceleration"]
allowed_numbers = []

[[grounding.facts]]
id = "shorter-time-greater-average"
canonical_text = "For two straight-line runs with the same initial and final velocities, the shorter elapsed time has the greater average acceleration."
child_text = "If both cars make the same speed change, the one that does it in less time has greater average acceleration."
source_ids = ["nasa-acceleration"]
allowed_numbers = ["0", "4", "8", "60"]

[[grounding.facts]]
id = "average-not-instant"
canonical_text = "A 0-to-60 elapsed time can support average acceleration over the interval but does not reveal acceleration at every instant."
child_text = "A car can accelerate differently during the run, so 0–60 supports an average."
source_ids = ["nasa-acceleration"]
allowed_numbers = ["0", "60"]

[[steps]]
id = "hook-0-to-60"
kind = "intro"
heading = "What does 0–60 measure?"
body = "A car card might say 0–60 in 4 seconds. The 4 seconds are elapsed time: how long the speed change took."
fact_ids = ["zero-to-sixty-is-time"]
scope_terms = ["0", "60", "car", "seconds", "time"]
visual_resource = "assets/chain_1_acceleration.svg"
visual_media_type = "image/svg+xml"
visual_alt = "Two hypothetical cars both go from 0 to 60 miles per hour. Car A takes 4 seconds and Car B takes 8 seconds."
visual_sha256 = ""

[[steps]]
id = "teach-acceleration"
kind = "teach"
heading = "Acceleration is a rate of change"
body = "Acceleration means how quickly velocity changes. If two cars make the same 0–60 change, the car with the shorter time has greater average acceleration."
fact_ids = [
  "acceleration-definition",
  "shorter-time-greater-average",
  "average-not-instant",
]
scope_terms = [
  "0",
  "60",
  "acceleration",
  "average",
  "car",
  "seconds",
  "time",
  "velocity",
]
visual_resource = "assets/chain_1_acceleration.svg"
visual_media_type = "image/svg+xml"
visual_alt = "The same speed change happens in less time for Car A, so Car A has greater average acceleration."
visual_sha256 = ""

[check]
id = "compare-average-acceleration"
prompt = "Car A goes from 0 to 60 in 4 seconds. Car B takes 8 seconds. Which car has greater average acceleration?"
correct_choice_id = "car-a"
hints = [
  "Both cars make the same speed change: 0 to 60 miles per hour.",
  "The same change in less time means greater average acceleration.",
]
success_text = "Yes. Car A makes the same speed change in less time, so its average acceleration is greater."
reveal_text = "It is Car A. Both cars go from 0 to 60, but Car A does it in less time."
fact_ids = [
  "zero-to-sixty-is-time",
  "acceleration-definition",
  "shorter-time-greater-average",
]
scope_terms = [
  "0",
  "60",
  "acceleration",
  "average",
  "car",
  "seconds",
  "time",
  "velocity",
]
allowed_short_replies = ["how", "no", "why", "yes"]

[[check.choices]]
id = "car-a"
label = "Car A — 4 seconds"

[[check.choices]]
id = "car-b"
label = "Car B — 8 seconds"

[[check.choices]]
id = "same"
label = "They have the same average acceleration"
```

The hypothetical 4- and 8-second values are lesson examples, not claims about real vehicles.

The catalog never fetches a source URL at runtime or during ordinary tests. Before approval, a reviewer must be able to inspect the source or a lawful repository-relative review artifact and record actual evidence. If source evidence is unavailable, the lesson remains draft and child use is blocked.

## Curated SVG requirements

Create a native SVG:

- `viewBox="0 0 800 360"`;
- `<title>` and `<desc>`;
- `role="img"`;
- no scripts, animation, event handlers, remote references, embedded photographs, tracking elements, brands, or logos;
- two lanes with the same 0 and 60 endpoints;
- Car A labeled 4 seconds;
- Car B labeled 8 seconds;
- instructional meaning duplicated in `visual_alt`;
- no meaning conveyed by color alone;
- readable high-contrast labels.

## Task 3 — Content tests and human approval gate

Tests:

- `test_chain_1_uses_explicit_sequence`;
- `test_chain_1_calls_zero_to_sixty_elapsed_time`;
- `test_chain_1_defines_average_acceleration_as_velocity_change_over_time`;
- `test_chain_1_distinguishes_average_from_instantaneous`;
- `test_chain_1_contains_no_brand_or_mutable_ranking`;
- `test_chain_1_contains_no_false_name_claim`;
- `test_chain_1_check_has_one_correct_choice`;
- `test_chain_1_has_exactly_two_progressive_hints`;
- `test_chain_1_references_reviewed_https_source`;
- `test_chain_1_has_no_graph_relationship_fields`;
- `test_chain_1_visual_is_packaged_and_accessible`;
- `test_child_catalog_rejects_test_fixture_draft`;
- `test_child_catalog_loads_approved_chain_1`.
- `test_context_for_each_snapshot_contains_only_bound_facts`;
- `test_chain_1_effective_turn_cap_is_reviewed_content`.

Red:

```bash
"$PYTHON" -m pytest tests/explore/test_chain_1_content.py -q
```

Create a parseable draft production resource first. Add each structural/content test against a deliberately incomplete or incorrect field and record its behavior-specific failure before correcting that field. The test-only draft fixture must always fail closed through the child catalog. The production approved-load test remains blocked/failing until the human gate is completed; do not satisfy it with fabricated attestations.

Human gate:

1. Finalize draft runtime/grounding text and SVG bytes.
2. Generate the exact SVG SHA-256, add it to every production asset reference/index entry, and compile the canonical review-independent lesson payload/hash.
3. A parent/educator reviews the exact payload for age fit and tone.
4. A scientifically competent reviewer verifies the exact payload, distinctions, and source.
5. A reviewer checks the exact SVG bytes/hash and alt text.
6. A parent records explicit approval for this family pilot.
7. Record four `[[review.attestations]]` entries. Each contains a stable `id`, one required scope, actual `reviewer_role`, actual TOML local-date `reviewed_on`, optional repository-relative `evidence_ref`, and the same exact `reviewed_payload_sha256`.
8. Use distinct IDs and the scopes `science`, `child_content`, `visual_accessibility`, and `parent_approval`; then change production review status to approved.
9. Generate the final lesson TOML/package hash and package index, verify that removing review metadata reproduces the attested payload hash, and review the final diff/hashes.
10. Rerun the content and package-index tests.

Do not automate approval and do not fabricate review metadata.

## Deterministic engine contract

Implement `DeterministicLessonEngine` in `engine.py`:

```python
class DeterministicLessonEngine:
    def initial_state(self, lesson: Lesson) -> LessonState:
        ...

    def transition(
        self,
        lesson: Lesson,
        state: LessonState,
        event: LessonEvent,
    ) -> LessonTransition:
        ...

    def snapshot(
        self,
        lesson: Lesson,
        state: LessonState,
    ) -> LessonSnapshot:
        ...
```

The class is stateless. Same lesson, state, and event produce the same result.

## Transition rules

Initial:

```python
LessonState(
    lesson_id=lesson.id,
    lesson_content_version=lesson.content_version,
    phase=LessonPhase.INTRO,
    step_index=0,
    attempts=0,
    hint_index=None,
    completion=None,
)
```

Rules:

1. `INTRO + CONTINUE` advances to the next authored step.
2. `TEACH + CONTINUE` advances to the next teach step or enters `CHECK`.
3. `CHECK + SUBMIT_CHOICE(correct)` completes with `CORRECT`.
4. `CHECK + SUBMIT_CHOICE(wrong)` enters `HINT` at hint `0`.
5. `HINT + SUBMIT_CHOICE(correct)` completes with `CORRECT`.
6. `HINT + SUBMIT_CHOICE(wrong)` advances to the next hint.
7. A wrong answer after the final hint completes with `ANSWER_REVEALED`.
8. `RESTART` from any valid phase returns the exact initial state.

Each choice submission increments attempts exactly once.

Reject without state mutation:

- choice missing for `SUBMIT_CHOICE`;
- choice supplied for `CONTINUE` or `RESTART`;
- unknown choice;
- submit during intro/teach/complete;
- continue during check/hint/complete;
- state from another lesson or content version;
- impossible combinations of phase, step, hint, completion, or attempts.

## Snapshot boundaries

- Intro/teach: authored step text and Continue.
- Check: prompt and choices.
- Hint: prompt, choices, and current hint.
- Complete/correct: success text.
- Complete/revealed: reveal text.
- Never expose `correct_choice_id`.
- Never expose grounding internals, review metadata, or source URLs to the child view.

## Task 4 — Engine TDD

Tests:

- `test_initial_state_points_to_intro`;
- `test_continue_moves_intro_to_teach`;
- `test_final_teach_continue_enters_check`;
- `test_correct_first_choice_completes_correct`;
- `test_first_wrong_choice_shows_first_hint`;
- `test_second_wrong_choice_shows_second_hint`;
- `test_wrong_after_final_hint_reveals_without_penalty_loop`;
- `test_correct_after_hint_completes_correct`;
- `test_attempts_increment_once_per_submission`;
- `test_restart_from_every_phase_returns_initial`;
- `test_unknown_choice_raises_without_mutating_input_state`;
- `test_invalid_payload_raises`;
- `test_mismatched_lesson_version_raises`;
- `test_current_context_never_contains_unbound_fact`;
- `test_replay_is_deterministic`;
- `test_snapshot_never_exposes_answer_key`.

Red:

```bash
"$PYTHON" -m pytest tests/explore/test_engine.py -q
```

Green:

- implement one transition branch at a time;
- run each new test red then green;
- run the full engine file after every branch group.

## Packaging

Add:

```toml
[tool.setuptools]
include-package-data = true

[tool.setuptools.package-data]
"lerni.explore.lessons" = [
  "*.toml",
  "assets/*.svg",
]
```

Build a wheel and source distribution using qualified environment commands. Install each into a clean environment and verify `PackageLessonCatalog` can load the approved lesson and SVG.

Distribution tests:

- `test_installed_wheel_loads_lesson_resource`;
- `test_installed_wheel_verifies_lesson_index_hash`;
- `test_installed_wheel_rejects_tampered_svg`;
- `test_installed_wheel_reads_svg_bytes`;
- `test_installed_sdist_loads_lesson_resource`;
- `test_installed_sdist_rejects_tampered_svg`;
- `test_runtime_does_not_depend_on_source_checkout_path`.

If source-distribution content is missing, add the minimal `MANIFEST.in` rule and rerun the red/green packaging check.

## Completion criteria

- Standard-library core passes without optional dependencies.
- Production lesson is explicitly approved by humans.
- Scientific distinction is correct.
- No brand/ranking claim is packaged.
- Lesson sequence is explicit and graph-independent.
- Engine behavior is deterministic.
- Child snapshots hide the answer key.
- Wheel and source distribution contain the lesson and visual.
- Existing Study tests still pass.
- No commit is made.
