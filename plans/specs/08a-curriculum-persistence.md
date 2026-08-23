# Explore Safe Slice — Curriculum Import and Persistence Contract

## Goal

Make spreadsheet import implementation-ready with:

- immutable typed rows;
- deterministic validation reports;
- a full-snapshot batch model;
- exact SQLite keys and constraints;
- monotonic content versions;
- staged import separate from activation;
- one transactional active-snapshot pointer;
- immutable lesson-to-curriculum bindings;
- no Study or telemetry tables.

The database path is the derived curriculum path from the runtime profile. It uses and verifies the shared Explore SQLite connection pragmas from the telemetry contract; it does not introduce WAL mode, disk-backed temp state, or extension loading.

## Milestone and bootstrap boundary

Implement this plan only after plans 00–07 pass the first-slice pilot gate. This milestone modifies `bootstrap.py`, `ApplicationBundle`, readiness tests, and bootstrap tests; no graph type or conditional schema discovery belongs in the original first-slice bootstrap.

The graph-enabled bundle adds:

```python
curriculum_repository: CurriculumRepository
active_curriculum: ActiveCurriculumView | None
```

The importer/curation command initializes and mutates the curriculum database. Child-app startup opens the supported schema, reads the active pointer, and verifies publication approval/installed hashes without staging, publishing, or activating. A genuinely new empty store yields explicit `curated-lesson-only` mode; a verified active snapshot yields `active-curriculum`. Hash/schema/corruption mismatch, missing pointer after prior activation, or explicit installed-lesson revocation blocks child launch instead of silently using stale packaged approval. Recommendation and parent-state services remain absent until plan 08b.

The graph extension upgrades `readiness_schema_version` from base `1` to exact `2` and adds `graph_mode`, `active_batch_id`, `active_manifest_sha256`, `active_artifact_set_sha256`, `curriculum_state_sha256`, and nullable `content_quarantine_sha256` to `LaunchReadinessReport`; the strict encoder/decoder rejects fields from another version. Null active fields are allowed only for a genuinely new/empty curated-only store; the quarantine hash is null only when the file is absent. Activation, supersession, revocation/quarantine, publication approval, or any installed-hash change invalidates the acknowledged digest.

Implement an explicit v2 typed extension rather than an untyped dictionary:

```python
@dataclass(frozen=True, slots=True)
class GraphLaunchReadinessReport(LaunchReadinessReport):
    graph_mode: str
    active_batch_id: str | None
    active_manifest_sha256: str | None
    active_artifact_set_sha256: str | None
    curriculum_state_sha256: str | None
    content_quarantine_sha256: str | None
```

Its constructor requires `readiness_schema_version == 2`; base v1 construction rejects these fields. Plan 08b similarly owns the concrete v3 extension.

`curriculum_state_sha256` is also persisted in the singleton active pointer and verified at every open. Compute it with PR-02 `canonical_json_bytes()` over: content schema version, SQL migration hash, and content-schema resource hash; singleton ID/batch/activation time; the selected `import_batches` row; publication approval; sorted published `(path, kind, sha256)` tuples; and every active-batch row from the fixed v1 curriculum/content/relation/review/binding table allowlist, represented by exact column names and values and sorted by declared primary key. Replace asset BLOB values with their verified SHA-256 and omit only `active_content_snapshot.curriculum_state_sha256` itself. Unknown tables/columns, duplicate primary keys, non-canonical values, or a recomputation mismatch block child startup. This hash is database state identity; it is distinct from manifest, lesson payload, package, and artifact-set hashes.

The exact top-level hash object is:

```python
{
    "schema_version": 1,
    "migration_sha256": ...,
    "content_schema_resource_sha256": ...,
    "active_pointer": {
        "singleton_id": 1, "batch_id": ..., "activated_at": ...
    },
    "import_batch": {<every declared import_batches column>: ...},
    "publication_approval": {
        <every declared curriculum_publication_approvals column>: ...
    },
    "published_artifacts": [
        {"relative_path": ..., "artifact_kind": ..., "sha256": ...}, ...
    ],
    "tables": [
        {
            "table": <fixed allowlisted table name>,
            "columns": [<DDL order, excluding asset BLOB bytes>],
            "rows": [[<canonical SQL scalar or asset blob_sha256>, ...], ...]
        }, ...
    ]
}
```

Artifact paths sort by UTF-8 bytes. Tables use the fixed order in installed `curriculum_data/content-schema-v1.json`; columns use its DDL order; rows sort by its declared primary-key values encoded as typed canonical scalars. SQL null→JSON null, integer→JSON integer, and canonical stored text remains exact text. The pointer’s own `curriculum_state_sha256` and raw asset BLOB are the only omitted values. `migration_sha256` hashes exact SQL migration bytes; `content_schema_resource_sha256` hashes the exact JSON resource, preventing implementation-selected enumeration.

## Batch semantics

Every manifest describes a complete candidate curriculum snapshot, not a patch.

For every stable entity present in the active snapshot, the new batch must contain:

- the same version and identical canonical row hash;
- a higher version with changed content/status; or
- a higher version whose status is `retired`.

Silent omission is an error. This prevents accidental deletion.

Within a batch:

- one row per stable entity ID and content version;
- all references resolve within the same batch;
- no row is updated after staging;
- observations are rejected from curriculum manifests/imports and are not stored in the curriculum database; the separate neutralized export remains operator review material only.

## Exact immutable types

Implement in `curation_models.py`.

```python
class ContentStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAUSED = "paused"
    RETIRED = "retired"


class InterestLifecycle(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"


class BatchState(StrEnum):
    STAGED = "staged"
    PUBLISHED = "published"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: IssueSeverity
    code: str
    relative_path: str
    row_number: int | None
    entity_id: str | None
    field: str | None
    message: str


@dataclass(frozen=True, slots=True)
class CurationManifest:
    schema_version: int
    batch_id: str
    exported_at: datetime
    exported_by_role: str
    formula_free_attested: bool
    file_hashes: Mapping[str, str]
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class InterestRow:
    interest_id: str
    lifecycle_status: InterestLifecycle
    approval_status: ContentStatus
    label: str
    category: str
    anchor_concept_ids: tuple[str, ...]
    child_phrase_sanitized: str | None
    parent_observation_sanitized: str | None
    engagement_strength: int
    first_observed_on: date
    last_observed_on: date
    locale: str
    entered_by_role: str
    notes_sanitized: str | None
    content_version: int
    row_sha256: str


@dataclass(frozen=True, slots=True)
class ConceptRow:
    concept_id: str
    status: ContentStatus
    label: str
    kind: str
    track: str
    aliases: tuple[str, ...]
    description_child: str
    description_parent: str
    locale: str
    content_version: int
    row_sha256: str


@dataclass(frozen=True, slots=True)
class SourceRow:
    source_id: str
    status: ContentStatus
    title: str
    publisher: str
    url: str
    retrieved_on: date
    license_or_use_notes: str
    content_version: int
    row_sha256: str


@dataclass(frozen=True, slots=True)
class FactRow:
    fact_id: str
    status: ContentStatus
    concept_id: str
    canonical_text: str
    child_text: str
    source_ids: tuple[str, ...]
    allowed_numbers: tuple[str, ...]
    scope_note: str
    content_version: int
    row_sha256: str


@dataclass(frozen=True, slots=True)
class NudgeRow:
    nudge_id: str
    status: ContentStatus
    from_interest_id: str | None
    from_concept_id: str | None
    target_concept_id: str
    nudge_kind: str
    parent_goal: str
    child_prompt: str
    expected_signal: str
    hints: tuple[str, str]
    reveal_text: str
    priority: int
    prerequisite_concept_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    locale: str
    content_version: int
    row_sha256: str


@dataclass(frozen=True, slots=True)
class EdgeRow:
    edge_id: str
    status: ContentStatus
    from_concept_id: str
    to_concept_id: str
    relationship_type: str
    rationale: str
    source_ids: tuple[str, ...]
    content_version: int
    row_sha256: str


@dataclass(frozen=True, slots=True)
class AssetRow:
    asset_id: str
    status: ContentStatus
    resource_name: str
    media_type: str
    sha256: str
    title: str
    description: str
    alt_text: str
    source_id: str | None
    license_or_use_notes: str
    content_version: int
    row_sha256: str


@dataclass(frozen=True, slots=True)
class LessonRow:
    lesson_id: str
    status: ContentStatus
    title: str
    interest_id: str
    locale: str
    audience: str
    goal: str
    grounding_scope: str
    fallback_text: str
    redirect_text: str
    max_turns: int
    content_version: int
    row_sha256: str


@dataclass(frozen=True, slots=True)
class LessonStepRow:
    lesson_id: str
    lesson_content_version: int
    status: ContentStatus
    step_index: int
    step_id: str
    step_kind: StepKind
    concept_id: str
    nudge_id: str | None
    asset_id: str
    heading: str
    body: str
    fact_ids: tuple[str, ...]
    scope_terms: tuple[str, ...]
    required: bool
    row_sha256: str


@dataclass(frozen=True, slots=True)
class LessonCheckRow:
    lesson_id: str
    lesson_content_version: int
    status: ContentStatus
    check_id: str
    nudge_id: str
    prompt: str
    success_text: str
    reveal_text: str
    fact_ids: tuple[str, ...]
    scope_terms: tuple[str, ...]
    allowed_short_replies: tuple[str, ...]
    row_sha256: str


@dataclass(frozen=True, slots=True)
class CheckChoiceRow:
    lesson_id: str
    lesson_content_version: int
    check_id: str
    choice_index: int
    choice_id: str
    label: str
    is_correct: bool
    row_sha256: str


@dataclass(frozen=True, slots=True)
class CheckHintRow:
    lesson_id: str
    lesson_content_version: int
    check_id: str
    hint_index: int
    hint_text: str
    row_sha256: str


@dataclass(frozen=True, slots=True)
class ReviewAttestationRow:
    attestation_id: str
    attestation_version: int
    entity_type: str
    entity_id: str
    entity_version: int
    review_scope: ReviewScope
    reviewer_role: str
    reviewed_on: date
    evidence_ref: str | None
    reviewed_payload_sha256: str | None
    review_status: str
    row_sha256: str


@dataclass(frozen=True, slots=True)
class ValidatedCurationRows:
    manifest: CurationManifest
    validated_rows_sha256: str
    interests: tuple[InterestRow, ...]
    concepts: tuple[ConceptRow, ...]
    sources: tuple[SourceRow, ...]
    facts: tuple[FactRow, ...]
    nudges: tuple[NudgeRow, ...]
    edges: tuple[EdgeRow, ...]
    assets: tuple[AssetRow, ...]
    lessons: tuple[LessonRow, ...]
    lesson_steps: tuple[LessonStepRow, ...]
    lesson_checks: tuple[LessonCheckRow, ...]
    check_choices: tuple[CheckChoiceRow, ...]
    check_hints: tuple[CheckHintRow, ...]
    attestations: tuple[ReviewAttestationRow, ...]
    asset_bytes: Mapping[str, bytes]
    warnings: tuple[ValidationIssue, ...]


@dataclass(frozen=True, slots=True)
class StageableCurationBundle:
    rows: ValidatedCurationRows
    staging_plan: "CompiledStagingPlan"
    stageable_bundle_sha256: str
```

Use immutable mappings for `file_hashes` and `asset_bytes`.

`manifest_sha256` is computed from exact validated raw `manifest.json` bytes, never from a reserialized mapping.

The strict parser maps the wire key `manifest.json["files"]` to `CurationManifest.file_hashes`; there is no accepted wire key named `file_hashes`, and canonical regeneration always emits `files`.

PR-09 produces `ValidatedCurationRows`: a path-free immutable snapshot of exact bounded bytes/typed rows. Its digest uses `canonical_json_bytes()` over validator schema/policy resource hashes, exact manifest SHA-256, stable-sorted manifested file/hash pairs, stable ordered table row hashes, and asset byte hashes. It has no final artifact plan and remains read-only.

PR-10's pure `compile_stageable_bundle(rows)` independently derives `CompiledStagingPlan` outside the mutation gate and returns `StageableCurationBundle`. Compile intermediates for every approved lesson that passes exact-version review checks include the review-section-free payload/hash and exact review decisions; the stored plan contains final attestation-bearing TOML/assets/index artifacts and derived bindings. The compiler first computes payload identity, validates every exact-version review against it, then emits final artifacts. This is not publication: it writes nothing and grants no active status.

## Report and snapshot types

```python
@dataclass(frozen=True, slots=True)
class ImportCounts:
    interests: int
    concepts: int
    sources: int
    facts: int
    nudges: int
    edges: int
    assets: int
    lessons: int
    steps: int
    checks: int
    choices: int
    hints: int
    attestations: int


@dataclass(frozen=True, slots=True)
class ImportReport:
    batch_id: str
    manifest_sha256: str
    staged: bool
    counts: ImportCounts
    issues: tuple[ValidationIssue, ...]


@dataclass(frozen=True, slots=True)
class CurriculumBinding:
    binding_id: str
    batch_id: str
    lesson_id: str
    lesson_content_version: int
    lesson_package_sha256: str
    lesson_payload_sha256: str
    interest_id: str
    nudge_id: str | None
    concept_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompiledStagingArtifact:
    relative_path: str
    artifact_kind: str
    sha256: str
    content: bytes


@dataclass(frozen=True, slots=True)
class CompiledStagingPlan:
    validated_rows_sha256: str
    bindings: tuple[CurriculumBinding, ...]
    artifacts: tuple[CompiledStagingArtifact, ...]
    artifact_set_sha256: str
    plan_sha256: str


@dataclass(frozen=True, slots=True)
class ActiveCurriculumSnapshot:
    batch_id: str
    manifest_sha256: str
    curriculum_state_sha256: str
    activated_at: datetime
    bindings: tuple[CurriculumBinding, ...]


@dataclass(frozen=True, slots=True)
class CurriculumAdjacency:
    parent: Mapping[str, tuple[str, ...]]
    prerequisite: Mapping[str, tuple[str, ...]]
    related: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class ActiveCurriculumView:
    snapshot: ActiveCurriculumSnapshot
    interests: tuple[InterestRow, ...]
    concepts: tuple[ConceptRow, ...]
    sources: tuple[SourceRow, ...]
    facts: tuple[FactRow, ...]
    nudges: tuple[NudgeRow, ...]
    edges: tuple[EdgeRow, ...]
    assets: tuple[AssetRow, ...]
    lessons: tuple[LessonRow, ...]
    lesson_steps: tuple[LessonStepRow, ...]
    lesson_checks: tuple[LessonCheckRow, ...]
    check_choices: tuple[CheckChoiceRow, ...]
    check_hints: tuple[CheckHintRow, ...]
    attestations: tuple[ReviewAttestationRow, ...]
    adjacency: CurriculumAdjacency
```

`validated_rows_sha256` hashes this exact `canonical_json_bytes()` v1 mapping, with no digest field:

```json
{
  "schema_version": 1,
  "validator_resources": [
    {"resource_id": "curation-schema-v1.json", "sha256": "..."},
    {"resource_id": "policy-cases-v1.toml", "sha256": "..."},
    {"resource_id": "svg-policy-v1.json", "sha256": "..."}
  ],
  "manifest_sha256": "...",
  "manifest_files": [
    {"relative_path": "...", "sha256": "..."}
  ],
  "tables": [
    {"table": "INTERESTS", "row_sha256s": ["..."]}
  ],
  "assets": [
    {"asset_id": "...", "relative_path": "...", "sha256": "..."}
  ]
}
```

The three validator-resource IDs and order are fixed. `manifest_files` sort by UTF-8 relative path. `tables` use exact order `INTERESTS`, `CONCEPTS`, `SOURCES`, `FACTS`, `NUDGES`, `EDGES`, `ASSETS`, `LESSONS`, `LESSON_STEPS`, `LESSON_CHECKS`, `CHECK_CHOICES`, `CHECK_HINTS`, `REVIEWS`; within each, row hashes sort by that table's declared composite primary key (never display label or file order). Assets sort by `(asset_id, relative_path)`. Every manifested curriculum CSV/asset appears exactly once in the applicable list; README/LISTS/OBSERVATIONS are excluded by the manifest contract.

Staging digests use `canonical_json_bytes()` with exact v1 mappings:

- artifact-set input: `{"schema_version": 1, "artifacts": [...]}` where records contain only `relative_path`, `artifact_kind`, and verified content `sha256`, sorted by UTF-8 relative path; paths are unique;
- plan input: `{"schema_version": 1, "validated_rows_sha256": ..., "bindings": [...], "artifact_set_sha256": ...}` where each binding includes every scalar plus its ordered `concept_ids`, sorted by `(lesson_id, lesson_content_version, binding_id)`; `plan_sha256` is omitted from its own input;
- stageable-bundle input: `{"schema_version": 1, "validated_rows_sha256": ..., "plan_sha256": ...}`.

Every hex digest is lowercase and independently recomputed from bytes immediately before use. Unknown/missing keys, duplicate paths/bindings, ordering drift, content/hash mismatch, a plan rows hash unequal to `rows.validated_rows_sha256`, or a stageable digest mismatch rejects before any write.

Graph integration converts a `CurriculumBinding` to the graph-neutral telemetry `BindingAttachment` using binding ID, lesson ID, lesson content version, compiled package hash, and canonical lesson-payload hash. Telemetry never imports curriculum-persistence types.

Schema version 1 requires exactly one distinct non-null nudge reference across an approved lesson’s steps/check. `CurriculumBinding.nudge_id` is that exact value; zero or multiple values fail compilation rather than being collapsed.

Binding derivation is normative:

1. Order lesson steps by `step_index`.
2. Append each `concept_id` on first occurrence.
3. Resolve the sole nudge; if its approved `target_concept_id` is absent, append it once after all step concepts.
4. Persist that tuple through `curriculum_binding_concepts.concept_index`; no graph traversal or lexical sort changes it.
5. Compute `binding_id` as lowercase SHA-256 of `b"curriculum-binding-v1\n"` followed by the eight-lowercase-hex-byte-length, LF, and exact UTF-8 bytes for `batch_id`, `lesson_id`, base-10 `lesson_content_version`, and lowercase `lesson_payload_sha256`, in that order.

The final package hash is deliberately excluded from binding ID because PR-02's exact review status/attestation block may change while canonical child/runtime payload stays fixed; publication approval metadata is never packaged. The binding still stores and verifies the exact final package hash separately.

All mappings are immutable and adjacency values are stable-ID sorted. The view contains active/approved usable entities plus review rows needed to explain approval; paused/rejected/retired/draft entities are excluded from usable tuples.

Curation row hashes retain authored tuple/list order. The lesson compiler converts validated scope/reply tuples to runtime `frozenset` only after row hashes are fixed; canonical lesson-payload JSON then discards authored order for those set-valued fields and sorts normalized values by UTF-8 bytes exactly as PR-02 specifies. No other tuple is reordered.

## Canonical row hash

For each parsed row:

1. Build a mapping in exact CSV-header order.
2. Reject CR/LF in every cell; normalize Unicode/text/value types by the shared CSV rules.
3. Render integers as base-10 ASCII, booleans as lowercase `true`/`false`, dates/timestamps in their exact schema forms, and missing optional value as empty string.
4. Join ID, token, label, or normalized-number lists with `|` in their validated authored order; apply each field class’s normalization before joining.
5. Use `csv.writer` with `delimiter=","`, `quotechar='"'`, `quoting=csv.QUOTE_ALL`, `doublequote=True`, `escapechar=None`, `lineterminator="\n"`, and `strict=True` to encode exactly one record in header order.
6. Encode exactly `b"curation-row-v1\n" + table_name.encode("ascii") + b"\n" + record.encode("utf-8")`; no BOM or trailing bytes beyond the record LF.
7. SHA-256 those bytes.

The row hash excludes source row number and batch ID.

Same entity/version with a different row hash is invalid across batches.

For review attestations, `attestation_version` is the monotonic row version. Same attestation ID/version with a changed hash is invalid; revocation requires version increment. `entity_version` identifies the reviewed content and does not serve as the attestation row version.

Review eligibility is exact-version and current-decision only:

- content status/lifecycle changes require a higher content version, including retire/pause/reject and any later reactivation;
- every required scope must have exactly one `active` attestation in the candidate batch targeting that exact entity type, stable ID, and current content version;
- for each stable `attestation_id`, the candidate row must be the greatest seen `attestation_version`; if that row is `revoked`, its earlier active version cannot satisfy anything;
- lesson/asset attestations must also match the exact current reviewed payload/asset hash;
- attestations for older content versions remain history only and never satisfy a reactivated or changed row.

Thus retiring and later reactivating an entity always requires fresh exact-version attestations for every required scope; copying prior active review rows cannot restore eligibility.

## SQLite schema

Use schema version `1`.

Common constraints are intentionally repeated so the database defends the importer boundary.

```sql
PRAGMA foreign_keys = ON;
PRAGMA secure_delete = ON;

CREATE TABLE content_schema_version (
    version INTEGER PRIMARY KEY CHECK (version = 1)
);

CREATE TABLE import_batches (
    batch_id TEXT PRIMARY KEY,
    manifest_sha256 TEXT NOT NULL UNIQUE
        CHECK (length(manifest_sha256) = 64),
    manifest_schema_version INTEGER NOT NULL CHECK (
        manifest_schema_version = 1
    ),
    exported_at TEXT NOT NULL,
    exported_by_role TEXT NOT NULL CHECK (
        exported_by_role IN ('parent', 'educator')
    ),
    formula_free_attested INTEGER NOT NULL CHECK (
        formula_free_attested = 1
    ),
    state TEXT NOT NULL CHECK (
        state IN ('staged', 'published', 'active', 'superseded')
    ),
    staged_at TEXT NOT NULL,
    published_at TEXT,
    activated_at TEXT,
    CHECK (
        (state = 'staged' AND published_at IS NULL AND activated_at IS NULL)
        OR (
            state = 'published'
            AND published_at IS NOT NULL
            AND activated_at IS NULL
        )
        OR (
            state IN ('active', 'superseded')
            AND published_at IS NOT NULL
            AND activated_at IS NOT NULL
        )
    )
);

CREATE UNIQUE INDEX one_active_import_batch
    ON import_batches(state)
    WHERE state = 'active';

CREATE TABLE active_content_snapshot (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    batch_id TEXT NOT NULL UNIQUE,
    activated_at TEXT NOT NULL,
    curriculum_state_sha256 TEXT NOT NULL CHECK (
        length(curriculum_state_sha256) = 64
    ),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);
```

### Core content

```sql
CREATE TABLE interests (
    batch_id TEXT NOT NULL,
    interest_id TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL CHECK (
        lifecycle_status IN ('candidate', 'active', 'paused', 'retired')
    ),
    approval_status TEXT NOT NULL CHECK (
        approval_status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    label TEXT NOT NULL CHECK (length(label) BETWEEN 1 AND 120),
    category TEXT NOT NULL CHECK (length(category) BETWEEN 1 AND 80),
    child_phrase_sanitized TEXT CHECK (
        child_phrase_sanitized IS NULL
        OR length(child_phrase_sanitized) BETWEEN 1 AND 500
    ),
    parent_observation_sanitized TEXT CHECK (
        parent_observation_sanitized IS NULL
        OR length(parent_observation_sanitized) BETWEEN 1 AND 500
    ),
    engagement_strength INTEGER NOT NULL CHECK (
        engagement_strength BETWEEN 1 AND 5
    ),
    first_observed_on TEXT NOT NULL,
    last_observed_on TEXT NOT NULL,
    locale TEXT NOT NULL CHECK (length(locale) BETWEEN 2 AND 16),
    entered_by_role TEXT NOT NULL CHECK (
        entered_by_role IN ('parent', 'educator')
    ),
    notes_sanitized TEXT CHECK (
        notes_sanitized IS NULL
        OR length(notes_sanitized) BETWEEN 1 AND 500
    ),
    content_version INTEGER NOT NULL CHECK (content_version >= 1),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(batch_id, interest_id),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE TABLE interest_anchor_concepts (
    batch_id TEXT NOT NULL,
    interest_id TEXT NOT NULL,
    anchor_index INTEGER NOT NULL CHECK (anchor_index >= 0),
    concept_id TEXT NOT NULL,
    PRIMARY KEY(batch_id, interest_id, anchor_index),
    UNIQUE(batch_id, interest_id, concept_id),
    FOREIGN KEY(batch_id, interest_id)
        REFERENCES interests(batch_id, interest_id)
        ON DELETE CASCADE,
    FOREIGN KEY(batch_id, concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id)
);

CREATE TABLE curriculum_concepts (
    batch_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    label TEXT NOT NULL CHECK (length(label) BETWEEN 1 AND 120),
    kind TEXT NOT NULL CHECK (
        kind IN ('anchor', 'bridge', 'mechanism', 'fundamental', 'application')
    ),
    track TEXT NOT NULL CHECK (track IN ('interest', 'learning')),
    description_child TEXT NOT NULL CHECK (
        length(description_child) BETWEEN 1 AND 500
    ),
    description_parent TEXT NOT NULL CHECK (
        length(description_parent) BETWEEN 1 AND 1000
    ),
    locale TEXT NOT NULL CHECK (length(locale) BETWEEN 2 AND 16),
    content_version INTEGER NOT NULL CHECK (content_version >= 1),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(batch_id, concept_id),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE TABLE concept_aliases (
    batch_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    alias_index INTEGER NOT NULL CHECK (alias_index >= 0),
    alias TEXT NOT NULL CHECK (length(alias) BETWEEN 1 AND 120),
    PRIMARY KEY(batch_id, concept_id, alias_index),
    UNIQUE(batch_id, concept_id, alias),
    FOREIGN KEY(batch_id, concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id)
        ON DELETE CASCADE
);

CREATE TABLE curriculum_sources (
    batch_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 300),
    publisher TEXT NOT NULL CHECK (length(publisher) BETWEEN 1 AND 200),
    url TEXT NOT NULL CHECK (
        length(url) BETWEEN 9 AND 2000
        AND substr(url, 1, 8) = 'https://'
    ),
    retrieved_on TEXT NOT NULL,
    license_or_use_notes TEXT NOT NULL CHECK (
        length(license_or_use_notes) BETWEEN 1 AND 1000
    ),
    content_version INTEGER NOT NULL CHECK (content_version >= 1),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(batch_id, source_id),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE TABLE curriculum_facts (
    batch_id TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    concept_id TEXT NOT NULL,
    canonical_text TEXT NOT NULL CHECK (
        length(canonical_text) BETWEEN 1 AND 2000
    ),
    child_text TEXT NOT NULL CHECK (length(child_text) BETWEEN 1 AND 1000),
    scope_note TEXT NOT NULL CHECK (length(scope_note) BETWEEN 1 AND 1000),
    content_version INTEGER NOT NULL CHECK (content_version >= 1),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(batch_id, fact_id),
    FOREIGN KEY(batch_id, concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE TABLE fact_sources (
    batch_id TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    source_index INTEGER NOT NULL CHECK (source_index >= 0),
    source_id TEXT NOT NULL,
    PRIMARY KEY(batch_id, fact_id, source_index),
    UNIQUE(batch_id, fact_id, source_id),
    FOREIGN KEY(batch_id, fact_id)
        REFERENCES curriculum_facts(batch_id, fact_id)
        ON DELETE CASCADE,
    FOREIGN KEY(batch_id, source_id)
        REFERENCES curriculum_sources(batch_id, source_id)
);

CREATE TABLE fact_allowed_numbers (
    batch_id TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    number_index INTEGER NOT NULL CHECK (number_index >= 0),
    normalized_number TEXT NOT NULL CHECK (
        length(normalized_number) BETWEEN 1 AND 32
    ),
    PRIMARY KEY(batch_id, fact_id, number_index),
    UNIQUE(batch_id, fact_id, normalized_number),
    FOREIGN KEY(batch_id, fact_id)
        REFERENCES curriculum_facts(batch_id, fact_id)
        ON DELETE CASCADE
);
```

### Nudges, edges, and assets

```sql
CREATE TABLE curriculum_nudges (
    batch_id TEXT NOT NULL,
    nudge_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    from_interest_id TEXT,
    from_concept_id TEXT,
    target_concept_id TEXT NOT NULL,
    nudge_kind TEXT NOT NULL CHECK (
        nudge_kind IN (
            'question', 'comparison', 'prediction',
            'demonstration', 'analogy', 'retrieval', 'activity'
        )
    ),
    parent_goal TEXT NOT NULL CHECK (length(parent_goal) BETWEEN 1 AND 1000),
    child_prompt TEXT NOT NULL CHECK (length(child_prompt) BETWEEN 1 AND 1000),
    expected_signal TEXT NOT NULL CHECK (
        length(expected_signal) BETWEEN 1 AND 1000
    ),
    hint_1 TEXT NOT NULL CHECK (length(hint_1) BETWEEN 1 AND 1000),
    hint_2 TEXT NOT NULL CHECK (length(hint_2) BETWEEN 1 AND 1000),
    reveal_text TEXT NOT NULL CHECK (
        length(reveal_text) BETWEEN 1 AND 1000
    ),
    priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
    locale TEXT NOT NULL CHECK (length(locale) BETWEEN 2 AND 16),
    content_version INTEGER NOT NULL CHECK (content_version >= 1),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    CHECK (
        (from_interest_id IS NOT NULL) !=
        (from_concept_id IS NOT NULL)
    ),
    PRIMARY KEY(batch_id, nudge_id),
    FOREIGN KEY(batch_id, from_interest_id)
        REFERENCES interests(batch_id, interest_id),
    FOREIGN KEY(batch_id, from_concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id),
    FOREIGN KEY(batch_id, target_concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE TABLE nudge_prerequisites (
    batch_id TEXT NOT NULL,
    nudge_id TEXT NOT NULL,
    prerequisite_index INTEGER NOT NULL CHECK (prerequisite_index >= 0),
    concept_id TEXT NOT NULL,
    PRIMARY KEY(batch_id, nudge_id, prerequisite_index),
    UNIQUE(batch_id, nudge_id, concept_id),
    FOREIGN KEY(batch_id, nudge_id)
        REFERENCES curriculum_nudges(batch_id, nudge_id)
        ON DELETE CASCADE,
    FOREIGN KEY(batch_id, concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id)
);

CREATE TABLE nudge_sources (
    batch_id TEXT NOT NULL,
    nudge_id TEXT NOT NULL,
    source_index INTEGER NOT NULL CHECK (source_index >= 0),
    source_id TEXT NOT NULL,
    PRIMARY KEY(batch_id, nudge_id, source_index),
    UNIQUE(batch_id, nudge_id, source_id),
    FOREIGN KEY(batch_id, nudge_id)
        REFERENCES curriculum_nudges(batch_id, nudge_id)
        ON DELETE CASCADE,
    FOREIGN KEY(batch_id, source_id)
        REFERENCES curriculum_sources(batch_id, source_id)
);

CREATE TABLE curriculum_edges (
    batch_id TEXT NOT NULL,
    edge_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    from_concept_id TEXT NOT NULL,
    to_concept_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL CHECK (
        relationship_type IN ('parent', 'prerequisite', 'related')
    ),
    rationale TEXT NOT NULL CHECK (length(rationale) BETWEEN 1 AND 1000),
    content_version INTEGER NOT NULL CHECK (content_version >= 1),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    CHECK (from_concept_id != to_concept_id),
    PRIMARY KEY(batch_id, edge_id),
    FOREIGN KEY(batch_id, from_concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id),
    FOREIGN KEY(batch_id, to_concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE TABLE edge_sources (
    batch_id TEXT NOT NULL,
    edge_id TEXT NOT NULL,
    source_index INTEGER NOT NULL CHECK (source_index >= 0),
    source_id TEXT NOT NULL,
    PRIMARY KEY(batch_id, edge_id, source_index),
    UNIQUE(batch_id, edge_id, source_id),
    FOREIGN KEY(batch_id, edge_id)
        REFERENCES curriculum_edges(batch_id, edge_id)
        ON DELETE CASCADE,
    FOREIGN KEY(batch_id, source_id)
        REFERENCES curriculum_sources(batch_id, source_id)
);

CREATE TABLE curriculum_assets (
    batch_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    resource_name TEXT NOT NULL,
    media_type TEXT NOT NULL CHECK (media_type = 'image/svg+xml'),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 300),
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 1000),
    alt_text TEXT NOT NULL CHECK (length(alt_text) BETWEEN 1 AND 1000),
    source_id TEXT,
    license_or_use_notes TEXT NOT NULL CHECK (
        length(license_or_use_notes) BETWEEN 1 AND 1000
    ),
    content_version INTEGER NOT NULL CHECK (content_version >= 1),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(batch_id, asset_id),
    UNIQUE(batch_id, resource_name),
    FOREIGN KEY(batch_id, source_id)
        REFERENCES curriculum_sources(batch_id, source_id),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE TABLE curriculum_asset_bytes (
    batch_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    content BLOB NOT NULL CHECK (length(content) BETWEEN 1 AND 1000000),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    PRIMARY KEY(batch_id, asset_id),
    FOREIGN KEY(batch_id, asset_id)
        REFERENCES curriculum_assets(batch_id, asset_id)
        ON DELETE CASCADE
);

CREATE TABLE published_artifacts (
    batch_id TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    artifact_kind TEXT NOT NULL CHECK (
        artifact_kind IN ('lesson_toml', 'asset', 'package_index')
    ),
    content BLOB NOT NULL CHECK (length(content) BETWEEN 1 AND 2000000),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    PRIMARY KEY(batch_id, relative_path),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);
```

### Lessons and authored order

```sql
CREATE TABLE curriculum_lessons (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    interest_id TEXT NOT NULL,
    locale TEXT NOT NULL CHECK (length(locale) BETWEEN 2 AND 16),
    audience TEXT NOT NULL CHECK (length(audience) BETWEEN 1 AND 80),
    goal TEXT NOT NULL CHECK (length(goal) BETWEEN 1 AND 1000),
    grounding_scope TEXT NOT NULL CHECK (
        length(grounding_scope) BETWEEN 1 AND 2000
    ),
    fallback_text TEXT NOT NULL CHECK (
        length(fallback_text) BETWEEN 1 AND 1200
    ),
    redirect_text TEXT NOT NULL CHECK (
        length(redirect_text) BETWEEN 1 AND 1200
    ),
    max_turns INTEGER NOT NULL CHECK (max_turns BETWEEN 1 AND 20),
    content_version INTEGER NOT NULL CHECK (content_version >= 1),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(batch_id, lesson_id),
    UNIQUE(batch_id, lesson_id, content_version),
    FOREIGN KEY(batch_id, interest_id)
        REFERENCES interests(batch_id, interest_id),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE TABLE curriculum_lesson_steps (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    step_index INTEGER NOT NULL CHECK (step_index >= 0),
    step_id TEXT NOT NULL,
    step_kind TEXT NOT NULL CHECK (step_kind IN ('intro', 'teach')),
    concept_id TEXT NOT NULL,
    nudge_id TEXT,
    asset_id TEXT NOT NULL,
    heading TEXT NOT NULL CHECK (length(heading) BETWEEN 1 AND 300),
    body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 1200),
    required INTEGER NOT NULL CHECK (required = 1),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(batch_id, lesson_id, lesson_content_version, step_index),
    UNIQUE(batch_id, lesson_id, lesson_content_version, step_id),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version)
        REFERENCES curriculum_lessons(batch_id, lesson_id, content_version),
    FOREIGN KEY(batch_id, concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id),
    FOREIGN KEY(batch_id, nudge_id)
        REFERENCES curriculum_nudges(batch_id, nudge_id),
    FOREIGN KEY(batch_id, asset_id)
        REFERENCES curriculum_assets(batch_id, asset_id)
);

CREATE TABLE lesson_step_facts (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    step_id TEXT NOT NULL,
    fact_index INTEGER NOT NULL CHECK (fact_index >= 0),
    fact_id TEXT NOT NULL,
    PRIMARY KEY(
        batch_id, lesson_id, lesson_content_version, step_id, fact_index
    ),
    UNIQUE(
        batch_id, lesson_id, lesson_content_version, step_id, fact_id
    ),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version, step_id)
        REFERENCES curriculum_lesson_steps(
            batch_id, lesson_id, lesson_content_version, step_id
        )
        ON DELETE CASCADE,
    FOREIGN KEY(batch_id, fact_id)
        REFERENCES curriculum_facts(batch_id, fact_id)
);

CREATE TABLE lesson_step_scope_terms (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    step_id TEXT NOT NULL,
    term_index INTEGER NOT NULL CHECK (term_index >= 0),
    term TEXT NOT NULL CHECK (length(term) BETWEEN 1 AND 64),
    PRIMARY KEY(
        batch_id, lesson_id, lesson_content_version, step_id, term_index
    ),
    UNIQUE(
        batch_id, lesson_id, lesson_content_version, step_id, term
    ),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version, step_id)
        REFERENCES curriculum_lesson_steps(
            batch_id, lesson_id, lesson_content_version, step_id
        )
        ON DELETE CASCADE
);

CREATE TABLE curriculum_lesson_checks (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'draft', 'proposed', 'approved',
            'rejected', 'paused', 'retired'
        )
    ),
    check_id TEXT NOT NULL,
    nudge_id TEXT NOT NULL,
    prompt TEXT NOT NULL CHECK (length(prompt) BETWEEN 1 AND 1200),
    success_text TEXT NOT NULL CHECK (
        length(success_text) BETWEEN 1 AND 1200
    ),
    reveal_text TEXT NOT NULL CHECK (
        length(reveal_text) BETWEEN 1 AND 1200
    ),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(batch_id, lesson_id, lesson_content_version, check_id),
    UNIQUE(batch_id, lesson_id, lesson_content_version),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version)
        REFERENCES curriculum_lessons(batch_id, lesson_id, content_version),
    FOREIGN KEY(batch_id, nudge_id)
        REFERENCES curriculum_nudges(batch_id, nudge_id)
);

CREATE TABLE check_facts (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    check_id TEXT NOT NULL,
    fact_index INTEGER NOT NULL CHECK (fact_index >= 0),
    fact_id TEXT NOT NULL,
    PRIMARY KEY(
        batch_id, lesson_id, lesson_content_version, check_id, fact_index
    ),
    UNIQUE(
        batch_id, lesson_id, lesson_content_version, check_id, fact_id
    ),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version, check_id)
        REFERENCES curriculum_lesson_checks(
            batch_id, lesson_id, lesson_content_version, check_id
        )
        ON DELETE CASCADE,
    FOREIGN KEY(batch_id, fact_id)
        REFERENCES curriculum_facts(batch_id, fact_id)
);

CREATE TABLE check_scope_terms (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    check_id TEXT NOT NULL,
    term_index INTEGER NOT NULL CHECK (term_index >= 0),
    term TEXT NOT NULL CHECK (length(term) BETWEEN 1 AND 64),
    PRIMARY KEY(
        batch_id, lesson_id, lesson_content_version, check_id, term_index
    ),
    UNIQUE(
        batch_id, lesson_id, lesson_content_version, check_id, term
    ),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version, check_id)
        REFERENCES curriculum_lesson_checks(
            batch_id, lesson_id, lesson_content_version, check_id
        )
        ON DELETE CASCADE
);

CREATE TABLE check_allowed_short_replies (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    check_id TEXT NOT NULL,
    reply_index INTEGER NOT NULL CHECK (reply_index >= 0),
    reply TEXT NOT NULL CHECK (length(reply) BETWEEN 1 AND 32),
    PRIMARY KEY(
        batch_id, lesson_id, lesson_content_version, check_id, reply_index
    ),
    UNIQUE(
        batch_id, lesson_id, lesson_content_version, check_id, reply
    ),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version, check_id)
        REFERENCES curriculum_lesson_checks(
            batch_id, lesson_id, lesson_content_version, check_id
        )
        ON DELETE CASCADE
);

CREATE TABLE curriculum_check_choices (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    check_id TEXT NOT NULL,
    choice_index INTEGER NOT NULL CHECK (choice_index >= 0),
    choice_id TEXT NOT NULL,
    label TEXT NOT NULL CHECK (length(label) BETWEEN 1 AND 300),
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(
        batch_id, lesson_id, lesson_content_version, check_id, choice_index
    ),
    UNIQUE(
        batch_id, lesson_id, lesson_content_version, check_id, choice_id
    ),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version, check_id)
        REFERENCES curriculum_lesson_checks(
            batch_id, lesson_id, lesson_content_version, check_id
        )
);

CREATE TABLE curriculum_check_hints (
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    check_id TEXT NOT NULL,
    hint_index INTEGER NOT NULL CHECK (hint_index >= 0),
    hint_text TEXT NOT NULL CHECK (length(hint_text) BETWEEN 1 AND 1000),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(
        batch_id, lesson_id, lesson_content_version, check_id, hint_index
    ),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version, check_id)
        REFERENCES curriculum_lesson_checks(
            batch_id, lesson_id, lesson_content_version, check_id
        )
);
```

The importer validates contiguity and exactly one correct choice; SQLite alone does not express those aggregate constraints.

### Reviews and bindings

```sql
CREATE TABLE curriculum_review_attestations (
    batch_id TEXT NOT NULL,
    attestation_id TEXT NOT NULL,
    attestation_version INTEGER NOT NULL CHECK (attestation_version >= 1),
    entity_type TEXT NOT NULL CHECK (
        entity_type IN (
            'interest', 'concept', 'source', 'fact',
            'nudge', 'edge', 'asset', 'lesson'
        )
    ),
    entity_id TEXT NOT NULL,
    entity_version INTEGER NOT NULL CHECK (entity_version >= 1),
    review_scope TEXT NOT NULL CHECK (
        review_scope IN (
            'science', 'child_content',
            'visual_accessibility', 'parent_approval'
        )
    ),
    reviewer_role TEXT NOT NULL CHECK (
        length(reviewer_role) BETWEEN 1 AND 120
    ),
    reviewed_on TEXT NOT NULL,
    evidence_ref TEXT CHECK (
        evidence_ref IS NULL OR length(evidence_ref) BETWEEN 1 AND 500
    ),
    reviewed_payload_sha256 TEXT CHECK (
        reviewed_payload_sha256 IS NULL
        OR length(reviewed_payload_sha256) = 64
    ),
    CHECK (
        (entity_type IN ('lesson', 'asset')
            AND reviewed_payload_sha256 IS NOT NULL)
        OR
        (entity_type NOT IN ('lesson', 'asset')
            AND reviewed_payload_sha256 IS NULL)
    ),
    review_status TEXT NOT NULL CHECK (
        review_status IN ('active', 'revoked')
    ),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    PRIMARY KEY(batch_id, attestation_id),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE UNIQUE INDEX one_active_review_scope
    ON curriculum_review_attestations(
        batch_id, entity_type, entity_id, entity_version, review_scope
    )
    WHERE review_status = 'active';

CREATE TABLE curriculum_publication_approvals (
    batch_id TEXT PRIMARY KEY,
    manifest_sha256 TEXT NOT NULL CHECK (length(manifest_sha256) = 64),
    artifact_set_sha256 TEXT NOT NULL CHECK (
        length(artifact_set_sha256) = 64
    ),
    confirmed_by_role TEXT NOT NULL CHECK (
        confirmed_by_role IN ('parent', 'educator')
    ),
    confirmed_at TEXT NOT NULL,
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE TABLE curriculum_bindings (
    binding_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    lesson_package_sha256 TEXT NOT NULL CHECK (
        length(lesson_package_sha256) = 64
    ),
    lesson_payload_sha256 TEXT NOT NULL CHECK (
        length(lesson_payload_sha256) = 64
    ),
    interest_id TEXT NOT NULL,
    nudge_id TEXT,
    UNIQUE(binding_id, batch_id),
    UNIQUE(batch_id, lesson_id, lesson_content_version),
    FOREIGN KEY(batch_id, lesson_id, lesson_content_version)
        REFERENCES curriculum_lessons(batch_id, lesson_id, content_version),
    FOREIGN KEY(batch_id, interest_id)
        REFERENCES interests(batch_id, interest_id),
    FOREIGN KEY(batch_id, nudge_id)
        REFERENCES curriculum_nudges(batch_id, nudge_id)
);

CREATE TABLE curriculum_binding_concepts (
    binding_id TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    concept_index INTEGER NOT NULL CHECK (concept_index >= 0),
    concept_id TEXT NOT NULL,
    PRIMARY KEY(binding_id, concept_index),
    UNIQUE(binding_id, concept_id),
    FOREIGN KEY(binding_id, batch_id)
        REFERENCES curriculum_bindings(binding_id, batch_id)
        ON DELETE CASCADE,
    FOREIGN KEY(batch_id, concept_id)
        REFERENCES curriculum_concepts(batch_id, concept_id)
);
```

Application validation resolves polymorphic attestation entity references before insertion because SQLite cannot express one foreign key across multiple entity tables. All non-polymorphic relationships have explicit foreign keys and are inspected with `PRAGMA foreign_key_list`.

## Staging transaction

### Validation and mutation-lock split

Never hold the shared application mutation gate while reading CSV/assets, decoding UTF-8, parsing, hashing, compiling previews, contacting a helper/service, or waiting for operator input:

1. Under the curation source-directory no-follow rules, pin/copy each exact manifested regular file into an owner-private bounded staging snapshot and hash it; reject source identity changes during copy.
2. Close source descriptors and perform privacy scan, parse, referential checks, review-payload compilation, exact-version review validation, final attestation-bearing artifact compilation, asset validation, graph/binding derivation, and all canonical hashes outside the application mutation gate.
3. Produce immutable `ValidatedCurationRows`, then a `StageableCurationBundle`/`CompiledStagingPlan` with canonical digests; neither contains source paths, and the latter pins the exact package/artifact bytes later publication must reproduce.
4. Before lock/DB work, `stage` independently reruns `compile_stageable_bundle(bundle.rows)` and requires byte-for-byte plan/digest equality with the supplied stageable bundle. Only then acquire the shared mutation gate with a short fixed deadline, re-read active curriculum/precondition hashes, and perform the bounded SQLite transaction below. On mismatch/busy/timeout, write nothing, so an invalid plan cannot burn its batch ID.
5. Prepare publication bytes outside the gate from immutable staged rows/assets. Reacquire the gate only to revalidate expected batch/manifest/artifact-set/current-state hashes and perform the bounded approval/output transaction.
6. Activation likewise acquires the gate only for fresh installed-hash/current-state verification and its short pointer transaction.

Strict file/row/asset/count limits make each mutation section bounded. If measured worst-case stage/publication/activation cannot meet the qualified local callback-stop budget, those mutations are disabled while the server is running and must use the offline operator command under the exclusive runtime lifetime lock. Stop/Reset/Delete/wipe never wait behind bundle parsing or external work.

```python
def stage(
    self,
    bundle: StageableCurationBundle,
) -> ImportReport:
    ...
```

Algorithm:

1. Outside the gate, require zero validation errors and exact independent recompilation equality for the complete stageable bundle; failure opens no DB transaction.
2. Open connection, enable foreign keys and secure delete.
3. `BEGIN IMMEDIATE`.
4. If batch ID exists:
   - identical manifest hash and complete counts → return idempotent report;
   - different hash → fail.
5. Compare every stable entity to active snapshot:
   - lower version → fail;
   - same version/different row hash → fail;
   - missing stable entity → fail;
   - changed status/content without higher version → fail.
   - for attestations, apply the same rules using `attestation_version`.
6. Insert batch as `staged`.
7. Insert main rows, link rows, attestations, and verified asset bytes.
8. Verify inserted counts and foreign keys.
9. Verify the precomputed staging-plan digest/counts and that every binding/artifact identity is covered by the validated bundle; perform no compilation or file decoding.
10. Insert the precomputed immutable curriculum bindings/concept rows, including final TOML package hashes and canonical payload hashes.
11. Verify inserted binding/hash identities exactly equal the staging plan.
12. Commit.

On any exception:

- rollback;
- remove any compiler temporary files;
- active pointer unchanged;
- no partial batch remains.

Staging does not write packaged lesson files, but it persists verified immutable source asset bytes in the content database.

## Publication transaction

```python
@dataclass(frozen=True, slots=True)
class PublishedArtifact:
    relative_path: str
    artifact_kind: str
    sha256: str
    content: bytes


@dataclass(frozen=True, slots=True)
class PublicationPreview:
    batch_id: str
    manifest_sha256: str
    artifacts: tuple[PublishedArtifact, ...]
    artifact_set_sha256: str


def prepare_publication(
    self,
    batch_id: str,
    *,
    expected_manifest_sha256: str,
) -> PublicationPreview:
    ...


def publish(
    self,
    batch_id: str,
    *,
    expected_manifest_sha256: str,
    expected_artifact_set_sha256: str,
    confirmed_by_role: str,
    confirmed_at: datetime,
) -> tuple[PublishedArtifact, ...]:
    ...
```

Algorithm:

`prepare_publication` requires a staged batch/manifest, re-reads immutable rows/assets, reruns the same two-pass payload-review/final-artifact compiler outside the mutation gate, and requires every artifact, package/payload hash, binding ID, and binding concept row to equal the staged identities. It returns those exact final bytes plus a canonical sorted path/kind/hash artifact manifest and its SHA-256. It writes nothing.

After the parent/educator inspects those bytes/diff/hash, the token-guarded operator service calls `publish`:

1. Recompute the complete preview from persisted rows outside the mutation gate and require both expected hashes.
2. Require UTC aware confirmation and valid role.
3. Acquire the mutation gate, `BEGIN IMMEDIATE`, and re-read the canonical staged-row/binding state digest; a mismatch rejects the preview without writing.
4. Re-require every final lesson TOML hash to equal its immutable binding `lesson_package_sha256` and every payload hash to equal its binding payload identity.
5. Insert immutable `published_artifacts` bytes/hashes.
6. Insert one `curriculum_publication_approvals` row binding manifest and final artifact-set hashes.
7. Set batch state `published` and `published_at`.
8. Commit.

The application/operator service never writes into a source checkout or installed package. It may write a parent-token-protected, atomic no-replace publication bundle only beneath the pinned derived `curation-private/publications/` root, containing exact artifacts plus the canonical path/kind/hash manifest and no sheet-only fields. This root is registered with managed family-data wipe. A developer then reviews and applies those exact bytes through the ordinary source-control/build workflow, builds wheel/sdist, installs in a clean environment, and supplies independently measured installed hashes to activation. A restart can reproduce the private publication bundle because source and published bytes persist in SQLite.

## Activation transaction

```python
def activate(
    self,
    batch_id: str,
    *,
    expected_manifest_sha256: str,
    installed_artifact_hashes: Mapping[str, str],
    confirmed_by_role: str,
    confirmed_at: datetime,
) -> ActiveCurriculumSnapshot:
    ...
```

Algorithm:

1. Require UTC aware timestamp and role `parent` or `educator`.
2. Outside the mutation gate, prepare a path-free activation plan: re-read/compile the immutable staged rows, reviews, graph, bindings, published bytes, and independently measured installed artifact hashes; require exact binding/package/payload/artifact equality and hash the complete source state.
3. Acquire the mutation gate and `BEGIN IMMEDIATE`.
4. Load batch and revalidate the activation plan's complete source-state hash before any insert/update:
   - if it is already the singleton active batch, verify the same manifest, installed artifact hashes, and recomputed persisted curriculum-state hash, then return the existing snapshot idempotently;
   - if it is not `published`, fail before any mutation;
   - if state/pointer disagree, report corruption.
5. Compare expected manifest hash.
6. Require the exact publication-approval manifest/artifact-set hashes.
7. Compare every supplied installed artifact path/hash to `published_artifacts`; require exact complete set and the prevalidated plan.
8. Mark previous active batch `superseded`.
9. Mark selected batch `active` and set activation time.
10. Compute the exact curriculum-state hash from the prospective active state.
11. Insert/update the singleton pointer with that hash and independently recompute it before commit.
12. Commit.
13. Return immutable snapshot.

Exactly one active batch exists after commit.

Activation only reads existing review attestations; it never inserts or replaces them. Application startup never calls stage, publish, or activate. Bootstrap performs read-only active-snapshot and installed-hash verification, so repeated starts cannot collide with attestation or publication uniqueness constraints.

An activation audit category may be written to an operator execution log. Do not store a person’s name in the content database.

Activation is impossible until publication and installed-package hash verification succeed.

At application startup, bootstrap compares the active batch’s publication approval and published artifact hashes with the installed package index. A mismatch, corrupt previously used curriculum DB, or explicit revoked/retired status for the installed lesson blocks child launch; it does not silently fall back to stale packaged approval. Revocation/retirement of an installed lesson writes an atomic strict non-child `content-quarantine.json` containing only schema version, lesson ID/version, package and canonical payload hashes, fixed reason code, manifest hash, and timestamp. Its hash enters readiness; managed family-data wipe preserves it. Curated-only packaged fallback is allowed only when the curriculum store is genuinely new/empty and no quarantine record exists.

Quarantine is sticky and never disappears on startup, managed wipe, or ordinary activation. A separate parent-token operator action may clear it only with the expected quarantine-file hash and expected current curriculum-state hash, while holding the runtime lock, after a different/newer active approved publication and installed package both pass full verification and no active row revokes/retires that lesson. It unlinks only the pinned regular one-link derived file, fsyncs the parent directory, and verifies absence; after a crash, startup revalidates the replacement regardless of whether the durable unlink completed. Clearing merely to reuse the exact quarantined package identity is rejected.

```python
def clear_content_quarantine(
    *,
    expected_quarantine_sha256: str,
    expected_curriculum_state_sha256: str,
    parent_token: str,
) -> None:
    ...
```

## Repository API

```python
class CurriculumRepository(Protocol):
    def stage(
        self,
        bundle: StageableCurationBundle,
    ) -> ImportReport:
        ...

    def prepare_publication(
        self,
        batch_id: str,
        *,
        expected_manifest_sha256: str,
    ) -> PublicationPreview:
        ...

    def publish(
        self,
        batch_id: str,
        *,
        expected_manifest_sha256: str,
        expected_artifact_set_sha256: str,
        confirmed_by_role: str,
        confirmed_at: datetime,
    ) -> tuple[PublishedArtifact, ...]:
        ...

    def activate(
        self,
        batch_id: str,
        *,
        expected_manifest_sha256: str,
        installed_artifact_hashes: Mapping[str, str],
        confirmed_by_role: str,
        confirmed_at: datetime,
    ) -> ActiveCurriculumSnapshot:
        ...

    def snapshot(self) -> ActiveCurriculumSnapshot | None:
        ...

    def active_view(self) -> ActiveCurriculumView | None:
        ...

    def binding(
        self,
        binding_id: str,
    ) -> CurriculumBinding | None:
        ...
```

## Schema and transaction tests

Tests:

- exact expected tables/columns/checks/indexes;
- every connection has foreign keys;
- no Study/telemetry/recommendation table;
- derived path only;
- all status columns enforce shared six values;
- asset resource uniqueness is per batch;
- link tables have complete foreign keys;
- unsupported schema version rejected;
- corrupt database not recreated.
- canonical row bytes independently match exact quoting, doubled quote, Unicode, empty optional, boolean/integer, and ordered-list fixtures;

Transaction tests:

- dry validation writes nothing;
- clean stage leaves active pointer unchanged;
- staged asset bytes survive repository restart and match hash;
- repeated identical batch idempotent;
- same batch ID/new hash rejected;
- same entity/version/new row hash rejected;
- version decrease rejected;
- attestation revocation without version increment rejected;
- versioned revocation plus new active replacement accepted;
- silent omission rejected;
- explicit higher retired version accepted;
- insertion failure rolls back;
- publication from persisted rows/bytes is deterministic;
- compile preview writes nothing and required reviews bind the exact payload hash;
- final publication requires matching previewed artifact-set hash and persists the approval;
- publication failure leaves batch staged;
- activation of staged/unpublished batch rejected;
- repeated activation of the same active batch is an idempotent read/verify;
- repeated application bootstrap performs no curriculum writes;
- graph-enabled bootstrap reports curated-only with no active snapshot;
- verified active snapshot changes only graph mode and never installs recommendation services;
- original first-slice build has no curriculum imports or fields;
- installed artifact hash mismatch rejects activation;
- missing/mismatched publication approval rejects activation;
- revoked/retired installed lesson or corrupt previously used curriculum blocks packaged fallback;
- activation hash mismatch rolls back;
- activation revalidation failure rolls back;
- active pointer changes atomically;
- active-pointer curriculum-state hash independently reproduces; any active row, relation, review, binding, artifact, pointer, or schema mutation blocks startup;
- exactly one active batch;
- previous batch becomes superseded;
- historical batch rows remain immutable.

Binding tests:

- exact lesson hash/interest/nudge/concept order;
- binding ID deterministic from batch/lesson/version/canonical payload hash;
- telemetry can resolve binding after a later batch activates;
- later graph change does not reinterpret old binding.

## Completion criteria

- All domain/report types are defined.
- Complete-snapshot semantics are enforced.
- SQL schema has exact keys and constraints.
- Stage and activate are separate transactions.
- Versions are monotonic and immutable.
- Retirement is explicit.
- Active pointer is atomic.
- Lesson bindings preserve historical meaning.
- Package publication remains human-reviewed.
- Study and telemetry databases are untouched.
