# Explore Safe Slice — Recommendation and Feedback Contract

## Goal

Define a deterministic, parent-controlled recommendation layer that:

- reads one immutable active curriculum snapshot;
- uses parent-approved interest scope and readiness;
- summarizes sanitized local observations;
- returns explainable candidates;
- persists parent defer/reject/approve decisions;
- creates explicit lesson assignments only after approval;
- never changes graph edges, content approval, mastery, or child-visible state automatically.

This milestone begins only after the first-slice pilot and curriculum importer are verified.

Recommendation generation reads one immutable `ActiveCurriculumView` from the curriculum repository; it does not issue ad hoc SQL against content tables.

## File map

Create:

```text
src/lerni/explore/
├── parent_state.py
├── observation_aggregation.py
├── recommendations.py
└── assignment_reconcile.py

tests/explore/
├── test_parent_state_schema.py
├── test_observation_aggregation.py
├── test_recommendations.py
└── test_assignments.py
```

Modify `src/lerni/explore/data_lifecycle.py` and `tests/explore/test_data_lifecycle.py` from the telemetry milestone to install the parent-state cascade port.

Also modify:

```text
src/lerni/explore/bootstrap.py
src/lerni/explore/ui.py
src/lerni/explore/presenter.py
tests/explore/test_bootstrap.py
tests/explore/test_ui.py
tests/explore/test_presenter.py
```

This is a post-pilot milestone. Only now add `parent_state_store`, `recommendation_service`, and `assignment_reconciler` to `ApplicationBundle`; install the parent cascade port; run reconciliation; create the assignment-aware session factory; add recommendation/assignment controls; and upgrade readiness schema `2` to exact `3` with fields `recommendation_mode` and `parent_state_schema_sha256`; strict encoding/decoding rejects another version’s shape. The original plans 00–07 do not import these modules or render disabled placeholder controls.

`recommendation_mode` is exactly `parent_controlled_v1`. The schema hash covers the migration bytes and verified normalized `sqlite_master` objects. Internal deletion/reconciliation reports use fixed schemas and stable-sorted IDs, but terminal maintenance output exposes counts/categories only; neither becomes a readiness input or persisted tombstone. Readiness is created only after successful clean reconciliation, and corruption blocks launch. This keeps `--print-readiness` followed by an unchanged acknowledged launch reproducible.

```python
@dataclass(frozen=True, slots=True)
class RecommendationLaunchReadinessReport(GraphLaunchReadinessReport):
    recommendation_mode: str
    parent_state_schema_sha256: str
```

This concrete type requires `readiness_schema_version == 3`; v2 rejects these fields and v3 requires both.

The PR-03 process-lifetime runtime lock is already held before any store opens. After this extension, graph-enabled bootstrap order is: handle any path-based managed-wipe intent; verify packaged/active curriculum identity; initialize telemetry and parent state; install the cascade port into the lifecycle coordinator; construct services; resume every telemetry-marked session deletion; reconcile remaining assignments; run lifecycle-coordinated retention purge; then build readiness. No reconciliation or retention purge may run earlier. With an active curriculum or any existing parent-state data, lock/store/schema/cascade/recovery/reconciliation failure blocks child launch and every new telemetry delete/purge; it never degrades around dangling assignments/evidence. The pre-browser operator may still invoke the path-based managed family-data wipe while holding the exclusive runtime lock. Curated-only mode is allowed only for a genuinely new empty curriculum/parent-state setup with no prior assignment state.

## Storage boundary

Use a separate derived parent-state database:

```text
runtime-root/explore-parent-state.sqlite3
```

It is separate from:

- immutable curated content;
- Study;
- session telemetry.

It stores parent operational decisions, not transcripts/audio/model output.

It verifies the shared Explore SQLite connection contract: foreign keys and secure delete on, DELETE journaling, FULL synchronous writes, trusted schema off, memory temp storage, fixed busy timeout, and no extension loading.

Independent parent-authored state (scopes, readiness attestations, and suppressions) has explicit/manual retention. Session-derived evidence, candidates, decisions, and terminal assignments follow lifecycle-coordinated deletion of their source telemetry so no dangling references remain. There is no separate hidden parent-state timer. Deleting parent state does not delete telemetry or immutable curriculum; those have separate controls.

## Exact types

```python
class ReadinessLevel(StrEnum):
    UNKNOWN = "unknown"
    INTRODUCED = "introduced"
    READY = "ready"


class RecommendationDecisionKind(StrEnum):
    APPROVE = "approve"
    DEFER = "defer"
    REJECT = "reject"


class AssignmentStatus(StrEnum):
    PENDING = "pending"
    STARTING = "starting"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class RecommendationScope:
    scope_id: str
    active_batch_id: str
    interest_ids: frozenset[str]
    allowed_nudge_kinds: frozenset[str]
    repeat_window_days: int
    created_by_role: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RecommendationScopeDraft:
    interest_ids: frozenset[str]
    allowed_nudge_kinds: frozenset[str]
    repeat_window_days: int
    created_by_role: str


@dataclass(frozen=True, slots=True)
class ConceptReadiness:
    concept_id: str
    active_batch_id: str
    level: ReadinessLevel
    attested_by_role: str
    attested_at: datetime
    evidence_observation_ids: tuple[str, ...]
    note_sanitized: str | None


@dataclass(frozen=True, slots=True)
class ConceptReadinessDraft:
    concept_id: str
    level: ReadinessLevel
    attested_by_role: str
    evidence_observation_ids: tuple[str, ...]
    note_sanitized: str | None


@dataclass(frozen=True, slots=True)
class ObservationSummary:
    binding_id: str
    completed_sessions: int
    total_hints: int
    latest_engagement: int | None
    latest_understanding: UnderstandingLevel
    latest_wanted_more: bool | None
    latest_followup_recall: UnderstandingLevel
    latest_observed_at: datetime | None
    evidence_session_ids: tuple[str, ...]
    evidence_observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecommendationRun:
    run_id: str
    active_batch_id: str
    scope_id: str
    requested_by_role: str
    requested_at: datetime
    evidence_cutoff_at: datetime


@dataclass(frozen=True, slots=True)
class RecommendationCandidate:
    candidate_id: str
    run_id: str
    active_batch_id: str
    scope_id: str
    interest_id: str
    interest_content_version: int
    interest_row_sha256: str
    nudge_id: str
    nudge_content_version: int
    nudge_row_sha256: str
    target_concept_id: str
    target_concept_version: int
    target_concept_row_sha256: str
    lesson_id: str
    lesson_content_version: int
    binding_id: str
    lesson_package_sha256: str
    lesson_payload_sha256: str
    parent_priority: int
    repeat_penalty: int
    interest_strength: int
    prerequisite_ids: tuple[str, ...]
    fact_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    observation_summary: ObservationSummary
    content_identity_sha256: str
    explanation_lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecommendationDecision:
    decision_id: str
    candidate_id: str
    kind: RecommendationDecisionKind
    decided_by_role: str
    decided_at: datetime
    defer_until: date | None
    note_sanitized: str | None


@dataclass(frozen=True, slots=True)
class LessonAssignment:
    assignment_id: str
    candidate_id: str
    binding_id: str
    lesson_id: str
    lesson_content_version: int
    status: AssignmentStatus
    start_operation_id: str | None
    telemetry_session_id: UUID | None
    terminal_reason_code: str | None
    approved_by_role: str
    approved_at: datetime
    start_requested_at: datetime | None
    started_at: datetime | None
    completed_or_cancelled_at: datetime | None


@dataclass(frozen=True, slots=True)
class RecommendationDecisionResult:
    decision: RecommendationDecision
    assignment: LessonAssignment | None


@dataclass(frozen=True, slots=True)
class AssignmentLaunchContext:
    assignment_id: str
    start_operation_id: str
    telemetry_session_id: UUID
    curriculum_binding_id: str
    lesson_id: str
    lesson_content_version: int
    lesson_package_sha256: str
    lesson_payload_sha256: str


@dataclass(frozen=True, slots=True)
class AssignmentStartResult:
    assignment: LessonAssignment
    launch_context: AssignmentLaunchContext


@dataclass(frozen=True, slots=True)
class AssignmentReadinessReport:
    assignment_id: str
    active_batch_id: str
    active_manifest_sha256: str
    active_artifact_set_sha256: str
    lesson_id: str
    lesson_content_version: int
    lesson_package_sha256: str
    lesson_payload_sha256: str
    fallback_text_sha256: str
    launch_readiness_report_sha256: str
    recommendation_mode: str
    report_sha256: str
```

Build this report from a freshly recomputed base `LaunchReadinessReport` plus the current assignment/candidate/active-binding identities. `launch_readiness_report_sha256` is that exact base report digest. `report_sha256` hashes strict canonical JSON for every field above with `report_sha256` omitted. Start/Resume recomputes both layers and rejects a stale assignment or base readiness digest.

No type includes child name, transcript, audio, duration, message count, emotion score, model score, or free-form generated rationale.

## Parent scope

A candidate may be generated only for:

- an active curriculum batch matching `scope.active_batch_id`;
- an interest explicitly selected in `interest_ids`;
- a nudge kind explicitly selected in `allowed_nudge_kinds`.

`repeat_window_days` is integer 1–90. Default for a newly created scope is 14, but the parent must save the scope before recommendation runs.

Scope changes create a new immutable `scope_id`; they do not mutate historical runs.

## Readiness

Readiness is a parent/educator attestation.

- `unknown`: no readiness claim.
- `introduced`: child encountered it; not sufficient for a prerequisite.
- `ready`: parent/educator approves its use as a prerequisite.

Only `ready` satisfies a prerequisite.

Observations can be shown as evidence but never automatically change readiness.

A readiness attestation is batch-specific. A concept version change returns readiness to `unknown` until re-attested.

## Observation aggregation

Read from sanitized telemetry only.

Each explicit Refresh captures one timezone-aware UTC `requested_at` from the server clock under the shared mutation gate and sets `evidence_cutoff_at` to that exact instant. Every curriculum/readiness/assignment/telemetry query and the persisted run/candidates use that immutable cutoff; never derive it from `max(completed_at)` or another evidence row. Include only records committed and effective at or before the cutoff (`started_at`/`ended_at`, observation `created_at`, readiness `attested_at`, decision/assignment timestamps as applicable). Future-dated rows are excluded with a fixed parent warning.

The bounded source reads, candidate computation, and parent-state insert run against the same gate/precondition hashes so a concurrent delete, readiness edit, assignment change, or active-batch change cannot create a mixed-time run. If this cannot meet the qualified callback budget, compute a path-free candidate preview outside the gate and reacquire it to requery every source ID/hash/cutoff predicate before the atomic insert; stale preview means no write.

For each immutable `curriculum_binding_id`:

1. Exclude null/unbound sessions. A pre-graph pilot counts only after exact lesson ID/version/canonical payload/asset binding migration; only PR-02 review-block/resulting index-SHA package differences may be disclosed/tolerated as defined in telemetry/curation plans.
2. Include non-deleted bound sessions with status `completed`, `stopped`, or `abandoned`.
3. `completed_sessions`: count status `completed`.
4. `total_hints`: count `hint_shown` events.
5. Parent observations order by `(created_at, id)`.
6. Latest non-null engagement wins.
7. Latest non-`not_observed` understanding wins.
8. Latest non-null wanted-more wins.
9. Latest non-`not_observed` follow-up recall wins.
10. If no value exists, use null/`not_observed`.
11. Never average conflicting parent judgments.
12. Persist every contributing session ID ordered by `(started_at, id)`.
13. Persist every contributing observation ID ordered by `(created_at, id)`.

If telemetry is unavailable, return an empty summary and state that no observation evidence was available.

## Eligibility

A candidate is eligible only when all are true:

1. Active snapshot exists and matches scope.
2. Interest lifecycle is `active`, approval status is `approved`, and required review is active.
3. Nudge is approved with required reviews.
4. Nudge source interest equals selected interest, or its source concept is reachable from one of that interest row’s explicit approved `anchor_concept_ids` within at most two hops in the eligibility-only undirected view: each approved `related` edge and each approved directed `parent` edge may be traversed either way. This does not change stored parent direction or imply lesson order.
5. Target concept and every referenced fact/source are approved.
6. Nudge kind is allowed by scope.
7. Every prerequisite has parent-attested `ready`.
8. An approved curriculum binding exists for a lesson using this nudge and active batch.
9. The lesson and asset reviews remain active.
10. No pending/starting/started assignment already uses that binding.
11. No unexpired defer suppression exists for this scope/content identity.
12. No global reject suppression exists for the same content identity.

Candidate evidence order:

1. Traverse selected binding’s lesson steps by `step_index`.
2. Append each step `fact_ids` in authored order, keeping first occurrence.
3. Append check `fact_ids` in authored order, keeping first occurrence.
4. For each resulting fact, traverse its `source_ids` in authored order and keep first occurrence.

The resulting tuples are `candidate.fact_ids` and `candidate.source_ids`. Every direct nudge source ID must be a subset of the fact-derived source tuple; otherwise the candidate is ineligible. Nudge-only sources are never appended.

Content identity:

Use the exact ordered fields `interest_id`, decimal `interest_content_version`, `interest_row_sha256`, `nudge_id`, decimal `nudge_content_version`, `nudge_row_sha256`, `target_concept_id`, decimal `target_concept_version`, `target_concept_row_sha256`, `lesson_id`, decimal `lesson_content_version`, and `lesson_payload_sha256`. Encode `b"recommendation-content-v1\n"` followed by each field as eight lowercase hexadecimal UTF-8 byte-length digits, LF, then exact bytes. SHA-256 of that byte stream is `content_identity_sha256`; no delimiter concatenation or locale formatting is allowed.

Batch ID and binding ID are deliberately excluded from suppression identity. A rejected candidate remains suppressed across unrelated batch activations until at least one relevant version/hash changes. A new recommendation run alone does not resurrect it.

Reject suppression is global within this local parent-state database for that content identity. Defer suppression applies only to the same `scope_id` through `defer_until`.

## Candidate ID and run ID

`scope_id`, `run_id`, `decision_id`, `assignment_id`, and `start_operation_id` are server-generated UUIDv4 values rendered as lowercase canonical hyphenated strings. A scope save and explicit Refresh generate scope/run IDs respectively; every decision generates one decision ID; Approve generates the decision and assignment IDs in the same parent-state transaction; `pending→starting` generates the operation ID. Randomness is intentional for event identity, unlike deterministic candidate/content/binding hashes. A collision retries before mutation and never overwrites an existing row.

`candidate_id` is:

```text
sha256(
    length_prefixed_utf8("recommendation-candidate-v1")
    + length_prefixed_utf8(run_id)
    + length_prefixed_utf8(content_identity_sha256)
    + length_prefixed_utf8(scope_id)
)
```

Use the same eight-hex-digits/LF length prefix.

`content_identity_sha256` excludes `run_id`, `scope_id`, batch ID, and binding ID; defer/reject suppression uses that stable content identity across later runs.

## Ordering

For every eligible candidate:

```python
requested_date = requested_at.astimezone(timezone.utc).date()
matching_assignments = [
    assignment
    for assignment in non_cancelled_assignments
    if candidate.target_concept_id
       in curriculum_binding(assignment.binding_id).concept_ids
]
latest_assignment_at = max(
    (
        assignment.started_at
        if assignment.started_at is not None
        else assignment.approved_at
        for assignment in matching_assignments
    ),
    default=None,
)
repeat_penalty = (
    1
    if latest_assignment_at is not None
    and latest_assignment_at.astimezone(timezone.utc).date()
        >= requested_date - timedelta(days=repeat_window_days)
    else 0
)
```

Cancelled assignments do not count. Completed, started, and pending assignments count; pending uses approval time.

Sort ascending by:

```python
(
    -parent_priority,
    repeat_penalty,
    -interest_strength,
    nudge_id,
    lesson_id,
)
```

Prerequisite readiness is a filter, not a score.

Do not use:

- session duration;
- turn/message count;
- streak;
- inferred emotion;
- transcript sentiment;
- generated/model score;
- return frequency;
- monetization.

## Candidate explanation

Build only from reviewed structured fields:

1. `Interest: {label} (parent strength {1-5}).`
2. `Bridge: {nudge_kind} toward {target concept label}.`
3. `Parent goal: {parent_goal}.`
4. `Prerequisites ready: {stable ordered labels}` or `No prerequisites.`
5. `Reviewed facts: {fact IDs}.`
6. `Sources: {source titles}.`
7. `Prior evidence: {deterministic observation summary}.`
8. `Repeat status: new/not within window` or `repeated within {N}-day window.`

If any field is unavailable, state `not observed` rather than infer.

## Parent decisions

### Approve

- requires current per-launch parent token;
- candidate must still be eligible under same active batch/scope;
- atomically inserts decision and one pending lesson assignment;
- assignment references immutable binding;
- does not alter graph/content/readiness.

### Defer

- requires `defer_until` after decision date and within 365 days;
- candidate suppressed through that date;
- transaction writes an independent `(scope_id, content_identity_sha256)` suppression that survives deletion of evidence-bearing candidate/decision rows;
- no assignment.

### Reject

- `defer_until` must be null;
- candidate content identity suppressed until changed;
- transaction writes an independent global content-identity suppression with null scope/expiry;
- no assignment.

Every decision note is optional, sanitized, and 500 characters maximum.

## Assignment lifecycle

Allowed transitions:

```text
pending -> starting
pending -> cancelled
starting -> started
starting -> pending
starting -> cancelled
started -> completed
started -> cancelled
```

No transition out of completed/cancelled.

Starting uses an idempotent saga because separate SQLite databases cannot provide one atomic transaction:

1. Revalidate current active/published content, installed hashes, assignment readiness acknowledgement, and parent token.
2. In parent-state transaction, move `pending -> starting` and assign a random `start_operation_id`.
3. Create telemetry session idempotently with assignment ID, operation ID, binding, lesson ID/version, and package/payload hashes.
4. In parent-state transaction, record telemetry session ID but remain `starting`.
5. Return `AssignmentStartResult` whose launch context tells the session service to adopt that exact session under a live admission grant.
6. Adoption replays any existing telemetry events and inserts the initial session/lesson events with deterministic operation-derived idempotency keys; repeated adoption cannot duplicate turns/events or reset progress.
7. After the session service validates/reconstructs the context and before enabling interaction, call `acknowledge_assignment_adopted` to move `starting -> started`.
8. On normal telemetry creation failure before any session exists, return assignment to pending and clear operation ID, telemetry ID, `start_requested_at`, and every started/terminal field.

Mandatory reconciliation at startup and before assignment listing:

- for every `starting` row, query telemetry by operation ID;
- if exactly one session exists and is `active`, retain `starting`, store its ID, and expose a Resume Assigned Lesson action that reconstructs the same launch context;
- if that exactly one session is terminal, never expose Resume: apply the same completed/stopped/error/abandoned fixed terminal mapping used for `started`;
- if none exists, immediately return to pending and clear operation ID, telemetry ID, and all start timestamps; reconciliation holds the shared mutation lock and exclusive process lock, so no other creator can still commit that operation;
- more than one session is a corruption error and blocks assignment launch.
- for every `started` row with active telemetry, expose Resume and reconstruct engine state/history by deterministic replay;
- a `started` row whose telemetry is terminal is repaired through the fixed terminal mapping.

Reconciliation never marks an assignment started without an explicit adoption acknowledgement.

`acknowledge_assignment_adopted` is idempotent only for the same assignment/operation/session triple and freshly requires that telemetry session to remain `active`: `starting -> started`, or already `started` returns the same row. A terminal/missing session applies reconciliation/fails rather than becoming started. Any different identity fails. A crash after acknowledgement and before browser rendering therefore leaves a resumable `started` assignment, not a stranded one.

Completion:

1. Lesson engine completion marks telemetry session completed.
2. Parent-state transaction moves matching started assignment to completed.
3. Reconciliation scans started assignments whose telemetry session is completed and repairs the parent-state transition idempotently.

Other terminal mappings:

- telemetry `stopped` → assignment cancelled, `parent_or_child_stopped`;
- telemetry `error` → cancelled, `session_error`;
- telemetry `abandoned` → cancelled, `session_abandoned`;
- missing telemetry row after an explicitly authorized telemetry deletion → cancelled, `telemetry_missing`;
- reset first performs the same stopped/cancelled mapping.

The recommendation service implements `AssignmentLifecyclePort`. Pending cancellation with no telemetry is one parent-state transaction. Cancelling `starting`/`started` first idempotently terminalizes any exact operation/session telemetry as `stopped`, then commits assignment cancellation; a crash between stores leaves a nonterminal assignment plus terminal telemetry that reconciliation repairs, never a cancelled assignment with live telemetry. Cancellation normally does not delete telemetry. For an explicit telemetry delete, terminalization/assignment cancellation succeeds first; if it fails, telemetry deletion is blocked. Reconciliation applies the same mappings after a crash.

Start revalidation requires:

- telemetry store is enabled, schema-verified, and writable; recommendation browsing may work without it but assignment Start/Resume cannot;
- candidate/binding batch is still the current active batch;
- batch remains published;
- all required reviews are active;
- lesson/nudge/interest/assets are still approved and not paused/retired;
- installed lesson TOML, asset, and package-index hashes equal published artifacts;
- parent token is current.

`prepare_assignment_readiness` is read-only and derives a fresh report from the target lesson plus the current build/dependency/profile/policy/framework/capability-decision hashes, active batch/manifest/final artifact-set approval, telemetry retention, recommendation mode, qualifications, and exact authored fallback hash. The parent UI displays it and requires `START <first-12-hash>` or equivalent exact full-hash confirmation. `start_assignment`/`resume_assignment` recompute and compare immediately before any saga mutation; a stale report performs no write. Restart, code/config/service-record/content change, or assignment target change therefore requires new acknowledgement.

If any content/review/hash condition fails, cancel with fixed reason `stale_content_requires_reapproval`: a pending/no-session assignment cancels atomically in parent state; a starting/started assignment first terminalizes its exact telemetry session and then uses the crash-reconciled cancellation order above. A new current recommendation and parent approval are required; an old binding alone is never enough to launch.

## Session and UI extension

Add:

```python
class AssignmentLifecyclePort(Protocol):
    def complete_from_session(
        self,
        assignment_id: str,
        telemetry_session_id: UUID,
        *,
        completed_at: datetime,
    ) -> None:
        ...

    def cancel_from_session(
        self,
        assignment_id: str,
        telemetry_session_id: UUID,
        *,
        reason_code: str,
        cancelled_at: datetime,
    ) -> None:
        ...
```

Keep base `ExploreSessionPort.start(admission)` for unassigned sessions and add one orchestration-only `start_assigned(admission, assignment_id, expected_assignment_readiness_sha256, *, resume, parent_token)`. Under the shared mutation lock it rechecks base/assignment readiness and token, consumes the one-time admission grant before any parent-state/telemetry mutation, invokes the internal start/resume saga, loads/validates the resulting context, replays existing typed events/turns, idempotently initializes only missing operation-keyed events, and acknowledges adoption before returning an interactive result. Assignment ID, operation, binding, lesson ID/version plus package/payload hashes must all match and no second session is created. The UI cannot call the saga or telemetry creator directly; a failure after grant consumption does not refund the launch-budget slot.

Compose `AssignmentLifecyclePort` into the session service:

- lesson completion marks telemetry complete, then assignment complete;
- Stop maps to `parent_or_child_stopped`;
- Reset terminalizes the assigned prior session before creating an unassigned session;
- session error/abandonment use their fixed terminal codes;
- delete requires assignment cancellation before telemetry deletion.

Extend `build_app` with a narrow `recommendation_parent_port` plus the already injected session port, never the full saga-capable service. Render no placeholder controls when absent. When present, the parent accordion adds saved scope selection, Refresh Candidates, exact deterministic candidate explanation, Approve/Defer/Reject, pending/starting/started assignment selection, assignment-specific readiness report/confirmation, Start/Resume Assigned Lesson through `session_port.start_assigned`, and parent-state export creation; generic export list/delete remains owned by the lifecycle controls.

In graph/recommendation mode, extend PR-06's existing parent launch/data-management landing with default-versus-assignment choices. It still creates no telemetry session. The initial server-only `AdmissionGrant` remains unconsumed until the parent starts the default lesson or a selected assignment; the child area stays disabled.

The landing is a separate pre-session presentation state, not a fabricated `UiResult`/`ParentStatus` with a session ID. The server registry retains the grant by qualified framework session; the browser carries only the existing opaque admission handle/CSRF nonce and stable assignment IDs returned by token-guarded listing.

Prior-launch active telemetry blocks a new default/other assignment. An exactly reconciled `started` assignment may use Resume to adopt that same telemetry session; otherwise the parent must explicitly cancel/abandon through assignment lifecycle before the telemetry store marks it abandoned. Graph mode never calls the base bulk-abandon store method around parent state.

Every recommendation callback verifies the parent token and active admission. Start/Resume calls only `start_assigned`, which first requires a fresh base readiness digest equal to the original terminal approval, then recomputes and verifies the separately acknowledged assignment readiness. It requires no active child session; switching from one requires separate parent confirmation and terminalization. The first selected session passes the held initial grant; a later session reserves a new parent-session grant. `start_assigned` consumes that grant before beginning/resuming the saga, adopts/replays the exact context, acknowledges adoption idempotently, and only then enables child interaction. It uses the same non-refundable launch-session budget and lock/epoch discipline as Reset.

## SQLite schema

```sql
PRAGMA foreign_keys = ON;
PRAGMA secure_delete = ON;

CREATE TABLE parent_state_schema_version (
    version INTEGER PRIMARY KEY CHECK (version = 1)
);

CREATE TABLE parent_state_settings (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    retention_mode TEXT NOT NULL CHECK (retention_mode = 'manual'),
    updated_at TEXT NOT NULL
);

CREATE TABLE recommendation_scopes (
    scope_id TEXT PRIMARY KEY,
    active_batch_id TEXT NOT NULL,
    repeat_window_days INTEGER NOT NULL CHECK (
        repeat_window_days BETWEEN 1 AND 90
    ),
    created_by_role TEXT NOT NULL CHECK (
        created_by_role IN ('parent', 'educator')
    ),
    created_at TEXT NOT NULL
);

CREATE TABLE scope_interests (
    scope_id TEXT NOT NULL,
    interest_id TEXT NOT NULL,
    PRIMARY KEY(scope_id, interest_id),
    FOREIGN KEY(scope_id)
        REFERENCES recommendation_scopes(scope_id)
        ON DELETE CASCADE
);

CREATE TABLE scope_nudge_kinds (
    scope_id TEXT NOT NULL,
    nudge_kind TEXT NOT NULL CHECK (
        nudge_kind IN (
            'question', 'comparison', 'prediction',
            'demonstration', 'analogy', 'retrieval', 'activity'
        )
    ),
    PRIMARY KEY(scope_id, nudge_kind),
    FOREIGN KEY(scope_id)
        REFERENCES recommendation_scopes(scope_id)
        ON DELETE CASCADE
);

CREATE TABLE concept_readiness (
    active_batch_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    level TEXT NOT NULL CHECK (
        level IN ('unknown', 'introduced', 'ready')
    ),
    attested_by_role TEXT NOT NULL CHECK (
        attested_by_role IN ('parent', 'educator')
    ),
    attested_at TEXT NOT NULL,
    note_sanitized TEXT CHECK (
        note_sanitized IS NULL
        OR length(note_sanitized) BETWEEN 1 AND 500
    ),
    PRIMARY KEY(active_batch_id, concept_id)
);

CREATE TABLE readiness_evidence (
    active_batch_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    evidence_index INTEGER NOT NULL CHECK (evidence_index >= 0),
    observation_id TEXT NOT NULL,
    PRIMARY KEY(active_batch_id, concept_id, evidence_index),
    UNIQUE(active_batch_id, concept_id, observation_id),
    FOREIGN KEY(active_batch_id, concept_id)
        REFERENCES concept_readiness(active_batch_id, concept_id)
        ON DELETE CASCADE
);

CREATE TABLE recommendation_runs (
    run_id TEXT PRIMARY KEY,
    active_batch_id TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    requested_by_role TEXT NOT NULL CHECK (
        requested_by_role IN ('parent', 'educator')
    ),
    requested_at TEXT NOT NULL,
    evidence_cutoff_at TEXT NOT NULL CHECK (
        evidence_cutoff_at = requested_at
    ),
    FOREIGN KEY(scope_id)
        REFERENCES recommendation_scopes(scope_id)
        ON DELETE CASCADE
);

CREATE TABLE recommendation_candidates (
    candidate_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    content_identity_sha256 TEXT NOT NULL CHECK (
        length(content_identity_sha256) = 64
    ),
    active_batch_id TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    interest_id TEXT NOT NULL,
    interest_content_version INTEGER NOT NULL,
    interest_row_sha256 TEXT NOT NULL CHECK (
        length(interest_row_sha256) = 64
    ),
    nudge_id TEXT NOT NULL,
    nudge_content_version INTEGER NOT NULL,
    nudge_row_sha256 TEXT NOT NULL CHECK (
        length(nudge_row_sha256) = 64
    ),
    target_concept_id TEXT NOT NULL,
    target_concept_version INTEGER NOT NULL,
    target_concept_row_sha256 TEXT NOT NULL CHECK (
        length(target_concept_row_sha256) = 64
    ),
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    binding_id TEXT NOT NULL,
    lesson_package_sha256 TEXT NOT NULL CHECK (
        length(lesson_package_sha256) = 64
    ),
    lesson_payload_sha256 TEXT NOT NULL CHECK (
        length(lesson_payload_sha256) = 64
    ),
    parent_priority INTEGER NOT NULL CHECK (
        parent_priority BETWEEN 1 AND 5
    ),
    repeat_penalty INTEGER NOT NULL CHECK (repeat_penalty IN (0, 1)),
    interest_strength INTEGER NOT NULL CHECK (
        interest_strength BETWEEN 1 AND 5
    ),
    completed_sessions INTEGER NOT NULL CHECK (completed_sessions >= 0),
    total_hints INTEGER NOT NULL CHECK (total_hints >= 0),
    latest_engagement INTEGER CHECK (
        latest_engagement IS NULL OR latest_engagement BETWEEN 1 AND 5
    ),
    latest_understanding TEXT NOT NULL CHECK (
        latest_understanding IN (
            'not_observed', 'not_yet', 'partial', 'clear'
        )
    ),
    latest_wanted_more INTEGER CHECK (
        latest_wanted_more IS NULL OR latest_wanted_more IN (0, 1)
    ),
    latest_followup_recall TEXT NOT NULL CHECK (
        latest_followup_recall IN (
            'not_observed', 'not_yet', 'partial', 'clear'
        )
    ),
    latest_observed_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, content_identity_sha256, scope_id),
    FOREIGN KEY(run_id)
        REFERENCES recommendation_runs(run_id)
        ON DELETE CASCADE,
    FOREIGN KEY(scope_id)
        REFERENCES recommendation_scopes(scope_id)
        ON DELETE CASCADE
);

CREATE TABLE candidate_prerequisites (
    candidate_id TEXT NOT NULL,
    prerequisite_index INTEGER NOT NULL CHECK (prerequisite_index >= 0),
    concept_id TEXT NOT NULL,
    PRIMARY KEY(candidate_id, prerequisite_index),
    UNIQUE(candidate_id, concept_id),
    FOREIGN KEY(candidate_id)
        REFERENCES recommendation_candidates(candidate_id)
        ON DELETE CASCADE
);

CREATE TABLE candidate_explanation_lines (
    candidate_id TEXT NOT NULL,
    line_index INTEGER NOT NULL CHECK (line_index >= 0),
    text TEXT NOT NULL CHECK (length(text) BETWEEN 1 AND 1000),
    PRIMARY KEY(candidate_id, line_index),
    FOREIGN KEY(candidate_id)
        REFERENCES recommendation_candidates(candidate_id)
        ON DELETE CASCADE
);

CREATE TABLE candidate_facts (
    candidate_id TEXT NOT NULL,
    fact_index INTEGER NOT NULL CHECK (fact_index >= 0),
    fact_id TEXT NOT NULL,
    PRIMARY KEY(candidate_id, fact_index),
    UNIQUE(candidate_id, fact_id),
    FOREIGN KEY(candidate_id)
        REFERENCES recommendation_candidates(candidate_id)
        ON DELETE CASCADE
);

CREATE TABLE candidate_sources (
    candidate_id TEXT NOT NULL,
    source_index INTEGER NOT NULL CHECK (source_index >= 0),
    source_id TEXT NOT NULL,
    PRIMARY KEY(candidate_id, source_index),
    UNIQUE(candidate_id, source_id),
    FOREIGN KEY(candidate_id)
        REFERENCES recommendation_candidates(candidate_id)
        ON DELETE CASCADE
);

CREATE TABLE candidate_session_evidence (
    candidate_id TEXT NOT NULL,
    session_index INTEGER NOT NULL CHECK (session_index >= 0),
    telemetry_session_id TEXT NOT NULL,
    PRIMARY KEY(candidate_id, session_index),
    UNIQUE(candidate_id, telemetry_session_id),
    FOREIGN KEY(candidate_id)
        REFERENCES recommendation_candidates(candidate_id)
        ON DELETE CASCADE
);

CREATE TABLE candidate_observation_evidence (
    candidate_id TEXT NOT NULL,
    observation_index INTEGER NOT NULL CHECK (observation_index >= 0),
    observation_id TEXT NOT NULL,
    PRIMARY KEY(candidate_id, observation_index),
    UNIQUE(candidate_id, observation_id),
    FOREIGN KEY(candidate_id)
        REFERENCES recommendation_candidates(candidate_id)
        ON DELETE CASCADE
);

CREATE TABLE recommendation_decisions (
    decision_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (
        kind IN ('approve', 'defer', 'reject')
    ),
    decided_by_role TEXT NOT NULL CHECK (
        decided_by_role IN ('parent', 'educator')
    ),
    decided_at TEXT NOT NULL,
    defer_until TEXT,
    note_sanitized TEXT CHECK (
        note_sanitized IS NULL
        OR length(note_sanitized) BETWEEN 1 AND 500
    ),
    CHECK (
        (kind = 'defer' AND defer_until IS NOT NULL)
        OR (kind != 'defer' AND defer_until IS NULL)
    ),
    FOREIGN KEY(candidate_id)
        REFERENCES recommendation_candidates(candidate_id)
        ON DELETE CASCADE
);

CREATE TABLE recommendation_suppressions (
    suppression_id TEXT PRIMARY KEY,
    scope_id TEXT,
    content_identity_sha256 TEXT NOT NULL CHECK (
        length(content_identity_sha256) = 64
    ),
    kind TEXT NOT NULL CHECK (kind IN ('defer', 'reject')),
    defer_until TEXT,
    created_at TEXT NOT NULL,
    CHECK (
        (kind = 'defer' AND defer_until IS NOT NULL AND scope_id IS NOT NULL)
        OR
        (kind = 'reject' AND defer_until IS NULL AND scope_id IS NULL)
    ),
    FOREIGN KEY(scope_id)
        REFERENCES recommendation_scopes(scope_id)
        ON DELETE CASCADE
);

CREATE UNIQUE INDEX one_reject_suppression_per_identity
    ON recommendation_suppressions(content_identity_sha256)
    WHERE kind = 'reject';

CREATE UNIQUE INDEX one_defer_suppression_per_scope_identity
    ON recommendation_suppressions(scope_id, content_identity_sha256)
    WHERE kind = 'defer';

CREATE TABLE lesson_assignments (
    assignment_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL UNIQUE,
    binding_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'pending', 'starting', 'started', 'completed', 'cancelled'
        )
    ),
    start_operation_id TEXT UNIQUE,
    telemetry_session_id TEXT UNIQUE,
    approved_by_role TEXT NOT NULL CHECK (
        approved_by_role IN ('parent', 'educator')
    ),
    approved_at TEXT NOT NULL,
    start_requested_at TEXT,
    started_at TEXT,
    completed_or_cancelled_at TEXT,
    terminal_reason_code TEXT CHECK (
        terminal_reason_code IS NULL
        OR terminal_reason_code IN (
            'completed',
            'parent_cancelled',
            'parent_or_child_stopped',
            'session_error',
            'session_abandoned',
            'telemetry_missing',
            'stale_content_requires_reapproval'
        )
    ),
    CHECK (
        (status = 'pending'
            AND start_operation_id IS NULL
            AND telemetry_session_id IS NULL
            AND start_requested_at IS NULL
            AND started_at IS NULL
            AND completed_or_cancelled_at IS NULL)
        OR (status = 'starting'
            AND start_operation_id IS NOT NULL
            AND start_requested_at IS NOT NULL
            AND started_at IS NULL
            AND completed_or_cancelled_at IS NULL)
        OR (status = 'started'
            AND start_operation_id IS NOT NULL
            AND telemetry_session_id IS NOT NULL
            AND start_requested_at IS NOT NULL
            AND started_at IS NOT NULL
            AND completed_or_cancelled_at IS NULL)
        OR (status IN ('completed', 'cancelled')
            AND completed_or_cancelled_at IS NOT NULL)
    ),
    CHECK (
        (status IN ('pending', 'starting', 'started')
            AND terminal_reason_code IS NULL)
        OR (status = 'completed'
            AND terminal_reason_code = 'completed'
            AND start_operation_id IS NOT NULL
            AND telemetry_session_id IS NOT NULL
            AND started_at IS NOT NULL)
        OR (status = 'cancelled'
            AND terminal_reason_code IN (
                'parent_cancelled',
                'parent_or_child_stopped',
                'session_error',
                'session_abandoned',
                'telemetry_missing',
                'stale_content_requires_reapproval'
            ))
    ),
    FOREIGN KEY(candidate_id)
        REFERENCES recommendation_candidates(candidate_id)
        ON DELETE CASCADE
);
```

`retention_mode='manual'` governs independent parent-authored rows; foreign/source-derived rows still participate in the explicit cross-store cascade above.

Each individual database write is locally transactional. Cross-database consistency is not atomic: it uses current-state revalidation, immutable IDs/hashes, idempotent operation IDs, and mandatory reconciliation. SQLite cannot foreign-key across these files.

## Recommendation API

```python
class ParentStateStore:
    def initialize(self) -> None:
        ...

    def close(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    recovered_starting: tuple[str, ...]
    returned_to_pending: tuple[str, ...]
    repaired_completed: tuple[str, ...]
    corrupt_assignment_ids: tuple[str, ...]


class AssignmentReconciler:
    def reconcile(self, *, now: datetime) -> ReconciliationReport:
        ...
```

Every report tuple is stable assignment-ID sorted. Any non-empty `corrupt_assignment_ids` blocks readiness/report creation; successful repair categories/counts are shown only in the transient sanitized maintenance summary.

Reconciliation is an internal recovery operation over fixed IDs/categories; it never accepts or emits child text.

```python
class RecommendationService:
    # Constructor receives a server-owned UTC clock; production APIs never
    # accept browser-supplied cutoff time.
    def list_scopes(
        self,
        *,
        parent_token: str,
    ) -> tuple[RecommendationScope, ...]:
        ...

    def list_assignments(
        self,
        *,
        statuses: frozenset[AssignmentStatus],
        parent_token: str,
    ) -> tuple[LessonAssignment, ...]:
        ...

    def save_scope(
        self,
        draft: RecommendationScopeDraft,
        *,
        parent_token: str,
    ) -> RecommendationScope:
        ...

    def attest_readiness(
        self,
        draft: ConceptReadinessDraft,
        *,
        parent_token: str,
    ) -> ConceptReadiness:
        ...

    def candidates(
        self,
        *,
        scope_id: str,
        parent_token: str,
        requested_by_role: str,
    ) -> tuple[RecommendationCandidate, ...]:
        ...

    def decide(
        self,
        candidate_id: str,
        *,
        kind: RecommendationDecisionKind,
        parent_token: str,
        decided_by_role: str,
        defer_until: date | None = None,
        note: str | None = None,
    ) -> RecommendationDecisionResult:
        ...

    def prepare_assignment_readiness(
        self,
        assignment_id: str,
        *,
        parent_token: str,
    ) -> AssignmentReadinessReport:
        ...

    def start_assignment(
        self,
        assignment_id: str,
        *,
        parent_token: str,
        expected_readiness_sha256: str,
    ) -> AssignmentStartResult:
        ...

    def resume_assignment(
        self,
        assignment_id: str,
        *,
        parent_token: str,
        expected_readiness_sha256: str,
    ) -> AssignmentStartResult:
        ...

    def acknowledge_assignment_adopted(
        self,
        assignment_id: str,
        telemetry_session_id: UUID,
        *,
        parent_token: str,
        adopted_at: datetime,
    ) -> LessonAssignment:
        ...

    def cancel_assignment(
        self,
        assignment_id: str,
        *,
        parent_token: str,
        cancelled_at: datetime,
    ) -> LessonAssignment:
        ...

    def export_parent_state(
        self,
        *,
        parent_token: str,
        exported_at: datetime,
    ) -> GeneratedExportSummary:
        ...

    def delete_scope(
        self,
        scope_id: str,
        *,
        parent_token: str,
        confirmed: bool,
    ) -> bool:
        ...

    def delete_readiness(
        self,
        active_batch_id: str,
        concept_id: str,
        *,
        parent_token: str,
        confirmed: bool,
    ) -> bool:
        ...

    def delete_all_parent_state(
        self,
        *,
        parent_token: str,
        confirmed: bool,
    ) -> int:
        ...
```

All parent-facing mutation methods capture IDs and timestamps (`scope_id`, `created_at`, active batch, `attested_at`, `decision_id`, `decided_at`, assignment approval/start times) from server-owned state/clock under the mutation gate. Drafts carry only parent selections/role/sanitized note/evidence IDs. `candidates()` captures `requested_at`/`evidence_cutoff_at` exactly once after token validation and gate acquisition. Tests use a fake clock; no UI/component value can choose a cutoff, repeat-window date, persisted ID, batch, or event timestamp.

Every user-triggered method that writes, exports, or deletes verifies the per-launch token before reading sensitive parent-state detail. Internal startup reconciliation is the only non-token mutation and may perform only the fixed saga repairs above. `candidates()` is read-only with respect to curriculum/telemetry but records its run/candidate snapshot in parent state. `decide()` rechecks active batch and eligibility before writing.

Expose only list/scope/readiness/candidate/decision/export/delete operations through `RecommendationParentPort`. `start_assignment`, `resume_assignment`, and adoption acknowledgement remain internal methods reachable only by the session-service `start_assigned` orchestration after admission consumption.

All parent-state mutations/reconciliation run under the one shared application mutation gate and global lock order defined in plan 04, then use `BEGIN IMMEDIATE` on the parent-state connection; there is no separate parent-state mutation lock. The localhost prototype supports one application process; a second process opening the same parent-state database is an unsupported configuration and must fail the runtime lock-file check.

Parent-state export:

- writes generated filename under the derived private export root;
- includes a random export ID and exact `parent_state_json` kind in its strict envelope/filename;
- includes stable-sorted exact source session/observation UUID arrays and counts for every exported evidence reference, outside the payload, so lifecycle can remove an affected app-generated snapshot without parsing notes;
- deterministic JSON schema/version/order;
- sanitized notes only;
- no token, child name, transcript, audio, duration, adapter, or credential;
- atomic no-overwrite write;
- does not alter retention.
- register the `parent_state_json` strict parser with the PR-05 lifecycle coordinator, whose generic token-guarded ID/kind/time/hash/size list and fresh-scan exact-ID deletion controls apply.

Deletion:

- requires token plus explicit confirmation;
- acquires the same shared application mutation gate used by decision, start, cancel, completion, reconciliation, and cross-store lifecycle; no second lock exists;
- rejects scope/all deletion when any affected assignment is `starting` or `started`;
- requires reconciliation of `starting`, then explicit stop/cancel of any active started session before deletion;
- transactionally cascades dependent parent-state rows;
- never deletes curriculum or telemetry;
- returns exact deleted count/category without child text;
- exported files are independently retained and must be deleted separately.

## Cross-store deletion and managed local family-data wipe

Extend PR-05's existing `LocalDataLifecycleService` in `data_lifecycle.py` by installing `ParentDataCascadePort`; PR-11 does not recreate or re-own the service. UI session deletion and retention continue calling this coordinator, not `ExploreTelemetryStore.delete_session` directly, once parent state exists.

Add a parent-state adapter implementing `ParentDataCascadePort.delete_session_derivatives(...)` with the exact ordered cleanup below. Managed wipe does not call a logical “delete all” port: PR-11 registers only the parent-state closer/cascade with the coordinator; PR-05 already owns the fixed DB/sidecar path registry, where absent files are verified no-ops.

For one session, under the application-wide mutation gate:

1. Verify parent token/confirmation for an interactive delete; retention uses its fixed internal policy.
   - preview impacted assignments;
   - preview every app-generated parent-state snapshot whose strict envelope names the session/observation IDs;
   - explicit deletion requires parent confirmation to cancel pending assignments and requires active starting/started sessions to be stopped first;
   - retention skips/reports any session whose direct or evidence-linked candidate has a pending/starting/started assignment.
2. Read the session, its observation IDs, assignment ID, and app-owned export filenames.
3. Transactionally create/adopt the typed telemetry `session_deletion_requests` marker, operation ID, and explicit/retention kind.
4. Reconcile and terminalize any directly linked assignment, then delete that assignment row so no parent-state telemetry-session reference survives.
5. Find exactly impacted candidates through `candidate_session_evidence` or `candidate_observation_evidence`; terminalize/delete their assignment rows first.
6. In one parent-state transaction, remove matching `readiness_evidence`, impacted candidates and their candidate-bound decisions/evidence/lines, then delete only the impacted run IDs for which `NOT EXISTS (SELECT 1 FROM recommendation_candidates ...)`.
7. Preserve independent defer/reject suppressions; deleting an evidence-bearing candidate cannot resurrect rejected/deferred content.
8. For explicit parent deletion, remove/verify matching session JSON, PR-10 observation bundles, and parent-state snapshots under the derived export root without following symlinks. Retention leaves every export unchanged and reports that fact.
9. Delete the telemetry session and its cascades in a final separate transaction, which also removes the request marker.
10. Return a structured per-store result. The operation is idempotent by session ID and adopted operation ID.

Parent-state cleanup happens before telemetry deletion. A crash can leave excess marked telemetry, but cannot leave parent-state evidence pointing at deleted telemetry. Bootstrap resumes the marker before assignment reconciliation, and retry completes later steps. Any parent-state or export cleanup failure blocks telemetry deletion.

Provide a separate parent control, `Delete all managed local family data`, requiring the token plus exact phrase `DELETE ALL MANAGED LOCAL FAMILY DATA`. It:

1. proves ownership of the process-lifetime exclusive runtime lock, stops accepting callbacks, and acquires mutation/session locks;
2. atomically creates/fsyncs the strict non-child managed-wipe intent;
3. terminates/reaps helper process groups and removes managed audio temp files;
4. closes telemetry, curriculum, and parent-state connections;
5. deletes registered telemetry, curriculum, and parent-state DB files plus `-wal`, `-shm`, and `-journal` sidecars;
6. deletes app-generated exports, all managed audio-temp children, and the managed `curation-private/` family bundle without following symlinks;
7. leaves only the runtime profile, generic packaged lesson/templates, non-child content quarantine, capability decision records, and runtime lock;
8. verifies known paths absent, removes/fsyncs the intent last, rotates/invalidates parent and admission tokens, marks the UI stopped, and exits; empty stores are recreated only on a later acknowledged launch.

The control reports categories it could not delete and never claims success if a known file remains. It states that a live Google Sheet, downloaded/synced/manual copy, provider-held copy, browser/terminal cache, filesystem snapshot, backup, and storage remanence are outside managed deletion and require the manual runbook.

No child text is ever printed to the terminal. Readiness data and the parent token may remain in terminal scrollback; a portable app cannot reliably erase that scrollback. The token becomes invalid at exit, and the parent notice instructs the parent to clear/close the terminal and child browser profile after managed wipe. The app does not emit ANSI “clear” sequences and claim deletion.

## Tests

### Scope/readiness

- scope requires at least one interest and nudge kind;
- scope batch must be active;
- repeat window bounds;
- readiness batch/version reset behavior;
- observation evidence optional and sanitized;
- observation never auto-promotes readiness.

### Aggregation

- deleted sessions absent;
- exact completed-session and hint counts;
- latest non-null/non-not-observed value wins;
- ties use stable observation ID;
- no averaging;
- telemetry unavailable returns explicit empty summary.
- run cutoff equals the one captured UTC request instant; later/future-dated session, observation, readiness, decision, and assignment rows are excluded and cannot change a persisted run;
- a concurrent source delete/readiness edit/assignment mutation yields either one coherent run or a no-write stale/busy result, never mixed evidence.

### Eligibility

- unapproved dependency filters candidate;
- missing review filters candidate;
- not-ready prerequisite filters candidate;
- no binding filters candidate;
- active assignment filters candidate;
- starting assignment filters candidate;
- defer filters through date;
- reject filters unchanged content identity;
- unrelated new batch with identical relevant row/artifact hashes remains rejected;
- content/candidate identity golden bytes resist delimiter/Unicode/version ambiguity and independently reproduce;
- changed version permits a new candidate;
- eligibility reachability treats approved related and parent edges as bidirectional, stops at two hops, and never changes stored direction or implies lesson order.

### Ordering

- exact tuple ordering;
- repeat date uses matching target-concept assignment and UTC request date;
- parent priority first;
- recent-repeat penalty second;
- interest strength third;
- stable IDs tie-break;
- persisted candidate reconstructs every scalar and ordered prerequisite/fact/source tuple after a later batch activates;
- duration/messages/streak/emotion/model fields cannot be passed to scorer.

### Decisions/assignments

- wrong parent token fails;
- saved scopes and pending/starting/started assignments reconstruct in stable order after repository restart;
- approve revalidates and atomically creates one assignment;
- approve returns the exact decision-plus-assignment result; defer/reject return null assignment;
- defer date rules;
- reject rules;
- duplicate decision fails;
- allowed assignment transitions only;
- telemetry failure returns assignment to pending;
- crash after telemetry create leaves a resumable `starting` assignment;
- only explicit session-adoption acknowledgement moves `starting -> started`;
- repeated adoption/start event initialization is idempotent by operation key;
- crash after acknowledgement leaves a resumable `started` assignment with exact replayed progress/history;
- stale starting row with no telemetry returns to pending;
- duplicate telemetry operation ID is impossible/corruption blocks;
- completed telemetry repairs started assignment;
- stopped/error/abandoned telemetry maps to fixed cancellation reason;
- assignment cancellation failure blocks telemetry deletion;
- reset cannot leave an assigned session started;
- recommendation controls are absent without a fully initialized service;
- graph-mode admission stops at the parent launch chooser with no telemetry; default/assignment first start consumes exactly the held grant;
- every recommendation/assignment callback rejects a wrong token;
- Start/Resume passes the exact launch context, acknowledges only after adoption, and leaves interaction disabled on failure;
- late batch activation invalidates undecided old candidate;
- decision does not mutate graph/readiness/content.

### Privacy

- schema contains no child-name/transcript/audio/duration/model columns;
- notes sanitized;
- explanation derived only from reviewed fields/aggregate categories;
- parent token absent from rows/logs/errors.
- second application process/runtime lock is rejected;
- every mutation/export/delete rejects wrong token;
- deterministic export contains only allowed fields;
- lifecycle listing exposes parent-state exports only as ID/kind/time/hash/size and exact-ID confirmed deletion cannot escape the derived root;
- scope/readiness/all deletion cascades only parent-state rows;
- candidate session/observation evidence reconstructs exact contributing IDs;
- session delete removes parent evidence/candidates before telemetry and is idempotent after each injected crash point;
- session delete removes every linked assignment row, deletes only truly empty impacted runs, preserves unrelated candidates/runs, and leaves no telemetry reference;
- explicit session delete also removes every strict app-generated parent-state snapshot naming its session/observation evidence; retention preserves it.
- defer/reject suppression survives deletion of its evidence-bearing candidate/decision;
- retention uses the same cross-store order but preserves exports;
- retention skips/reports evidence sessions linked to nonterminal assignments;
- managed wipe removes telemetry/curriculum/parent-state DB sidecars including journals, exports, audio temp, and private curation while preserving only generic package/profile/setup records;
- failed known-file deletion reports incomplete and never claims a complete managed wipe;
- deletion cannot race or remove a starting/started assignment;
- deletion leaves curriculum/telemetry unchanged;
- manual retention has no hidden purge;

## Completion criteria

- Recommendation inputs and persistence are explicit.
- Readiness is parent-attested.
- Aggregation is deterministic.
- Eligibility and ordering are exact.
- Defer/reject behavior is version-aware.
- Approval creates an assignment, never a graph mutation.
- Child never sees an unapproved candidate.
- Recommendation controls appear only after complete post-pilot bootstrap.
- Assignment adoption and every terminal state reconcile across databases.
- Cross-store session deletion and managed local family-data wipe satisfy the lifecycle contract.
- No engagement-maximizing metric is used.
- Content, telemetry, and parent-state databases remain separated.
