# Explore Safe Slice — Local Telemetry and Parent Controls

## Goal

Capture enough evidence to improve the supervised family prototype without turning telemetry into an unrestricted child-data store.

Store:

- session lifecycle;
- sanitized accepted learner/tutor turns;
- fixed withholding markers for redirected, blocked, escalated, or rejected content;
- deterministic lesson events;
- policy categories;
- structured parent observations;
- later recall observations.

Do not store:

- child name or account;
- raw blocked input;
- raw rejected tutor output;
- audio bytes, audio paths, or audio metadata;
- secrets or credentials;
- arbitrary event JSON;
- exception messages or stack traces;
- model/provider identifiers;
- full prompts or grounding bundles;
- browser fingerprints, IP addresses, or analytics identifiers.

Use a separate Explore telemetry database supplied by runtime configuration. Do not modify Study’s `lerni.db`.

## File map

Create:

```text
src/lerni/explore/
├── telemetry_models.py
├── telemetry_store.py
├── data_lifecycle.py
└── export.py

tests/explore/
├── test_telemetry_schema.py
├── test_telemetry_store.py
├── test_retention.py
├── test_export.py
├── test_data_lifecycle.py
└── test_safety_telemetry_integration.py
```

## Data model

Implement in `telemetry_models.py`.

```python
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ABANDONED = "abandoned"
    ERROR = "error"


class TurnRole(StrEnum):
    LEARNER = "learner"
    ASSISTANT = "assistant"


class TurnSource(StrEnum):
    TYPED = "typed"
    TRANSCRIPT = "transcript"
    APP = "app"


class EventType(StrEnum):
    SESSION_STARTED = "session_started"
    STEP_VIEWED = "step_viewed"
    CONTINUE_SUBMITTED = "continue_submitted"
    CHOICE_SUBMITTED = "choice_submitted"
    HINT_SHOWN = "hint_shown"
    POLICY_APPLIED = "policy_applied"
    TUTOR_FAILED = "tutor_failed"
    READ_ALOUD_ENABLED = "read_aloud_enabled"
    SESSION_COMPLETED = "session_completed"
    SESSION_STOPPED = "session_stopped"


class UnderstandingLevel(StrEnum):
    NOT_OBSERVED = "not_observed"
    NOT_YET = "not_yet"
    PARTIAL = "partial"
    CLEAR = "clear"


class DeletionRequestKind(StrEnum):
    EXPLICIT = "explicit"
    RETENTION = "retention"


@dataclass(frozen=True, slots=True)
class SessionRecord:
    id: UUID
    launch_id: UUID
    lesson_id: str
    lesson_content_version: int
    lesson_package_sha256: str
    lesson_payload_sha256: str
    curriculum_binding_id: str | None
    assignment_id: str | None
    assignment_operation_id: str | None
    started_at: datetime
    ended_at: datetime | None
    status: SessionStatus


@dataclass(frozen=True, slots=True)
class SessionSummary:
    session_id: UUID
    lesson_id: str
    lesson_content_version: int
    curriculum_binding_id: str | None
    started_at: datetime
    ended_at: datetime | None
    status: SessionStatus
    observation_count: int
    is_current_launch: bool


@dataclass(frozen=True, slots=True)
class TurnRecord:
    id: UUID
    session_id: UUID
    turn_index: int
    role: TurnRole
    source: TurnSource
    content_sanitized: str
    storage_disposition: StorageDisposition
    policy_action: PolicyAction
    policy_reason: PolicyReason
    generation_outcome: GenerationOutcome | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EventRecord:
    id: UUID
    session_id: UUID
    event_type: EventType
    idempotency_key: str
    step_id: str | None
    value_code: str | None
    policy_action: PolicyAction | None
    policy_reason: PolicyReason | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class PendingEventRecord:
    event_type: EventType
    idempotency_key: str
    step_id: str | None
    value_code: str | None
    policy_action: PolicyAction | None
    policy_reason: PolicyReason | None


@dataclass(frozen=True, slots=True)
class ParentObservation:
    id: UUID
    session_id: UUID
    engagement: int | None
    understanding: UnderstandingLevel
    wanted_more: bool | None
    followup_recall: UnderstandingLevel
    notes_sanitized: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class BindingAttachment:
    binding_id: str
    lesson_id: str
    lesson_content_version: int
    lesson_package_sha256: str
    lesson_payload_sha256: str


@dataclass(frozen=True, slots=True)
class SessionReplay:
    session: SessionRecord
    turns: tuple[TurnRecord, ...]
    events: tuple[EventRecord, ...]


@dataclass(frozen=True, slots=True)
class SessionDeletionRequest:
    session_id: UUID
    operation_id: UUID
    kind: DeletionRequestKind
    requested_at: datetime
```

No type includes a raw-text property.

## SQLite schema

Use schema version `1`.

```sql
PRAGMA foreign_keys = ON;
PRAGMA secure_delete = ON;

CREATE TABLE IF NOT EXISTS telemetry_schema_version (
    version INTEGER PRIMARY KEY CHECK (version = 1)
);

CREATE TABLE IF NOT EXISTS telemetry_settings (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    retention_days INTEGER
        CHECK (
            retention_days IS NULL
            OR retention_days BETWEEN 1 AND 3650
        ),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    launch_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    lesson_content_version INTEGER NOT NULL
        CHECK (lesson_content_version >= 1),
    lesson_package_sha256 TEXT NOT NULL CHECK (
        length(lesson_package_sha256) = 64
    ),
    lesson_payload_sha256 TEXT NOT NULL CHECK (
        length(lesson_payload_sha256) = 64
    ),
    curriculum_binding_id TEXT,
    assignment_id TEXT UNIQUE,
    assignment_operation_id TEXT UNIQUE,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL CHECK (
        status IN (
            'active',
            'completed',
            'stopped',
            'abandoned',
            'error'
        )
    ),
    CHECK (
        (status = 'active' AND ended_at IS NULL)
        OR (status != 'active' AND ended_at IS NOT NULL)
    ),
    CHECK (
        (assignment_id IS NULL) = (assignment_operation_id IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS turns (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_index INTEGER NOT NULL CHECK (turn_index >= 0),
    role TEXT NOT NULL CHECK (role IN ('learner', 'assistant')),
    source TEXT NOT NULL CHECK (
        source IN ('typed', 'transcript', 'app')
    ),
    content_sanitized TEXT NOT NULL CHECK (
        length(content_sanitized) BETWEEN 1 AND 1200
    ),
    storage_disposition TEXT NOT NULL CHECK (
        storage_disposition IN ('sanitized_text', 'withhold')
    ),
    policy_action TEXT NOT NULL CHECK (
        policy_action IN (
            'allow',
            'redirect',
            'block',
            'escalate',
            'fallback'
        )
    ),
    policy_reason TEXT NOT NULL CHECK (
        policy_reason IN (
            'ok',
            'empty_input',
            'input_too_long',
            'turn_limit_reached',
            'personal_data',
            'secret_or_credential',
            'serious_distress',
            'harmful_or_age_inappropriate',
            'input_relationship_or_secrecy',
            'instruction_override',
            'out_of_scope',
            'url_or_contact',
            'relationship_or_secrecy',
            'unsafe_markup',
            'unsafe_unicode',
            'output_too_long',
            'too_many_sentences',
            'missing_citation',
            'unknown_fact',
            'unsupported_number',
            'optional_check_block',
            'generated_harm_gate_required',
            'generation_failure',
            'internal_failure'
        )
    ),
    generation_outcome TEXT CHECK (
        generation_outcome IS NULL
        OR generation_outcome IN (
            'not_called',
            'generated',
            'authored_fallback',
            'fixed_policy_response'
        )
    ),
    created_at TEXT NOT NULL,
    UNIQUE(session_id, turn_index, role),
    CHECK (
        (role = 'learner' AND generation_outcome IS NULL)
        OR (role = 'assistant' AND generation_outcome IS NOT NULL)
    ),
    CHECK (
        storage_disposition != 'withhold'
        OR content_sanitized = '[WITHHELD:' || policy_reason || ']'
    ),
    FOREIGN KEY(session_id)
        REFERENCES sessions(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL CHECK (
        length(idempotency_key) BETWEEN 1 AND 128
    ),
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'session_started',
            'step_viewed',
            'continue_submitted',
            'choice_submitted',
            'hint_shown',
            'policy_applied',
            'tutor_failed',
            'read_aloud_enabled',
            'session_completed',
            'session_stopped'
        )
    ),
    step_id TEXT,
    value_code TEXT CHECK (
        value_code IS NULL
        OR length(value_code) BETWEEN 1 AND 64
    ),
    policy_action TEXT CHECK (
        policy_action IS NULL
        OR policy_action IN (
            'allow', 'redirect', 'block', 'escalate', 'fallback'
        )
    ),
    policy_reason TEXT CHECK (
        policy_reason IS NULL
        OR policy_reason IN (
            'ok',
            'empty_input',
            'input_too_long',
            'turn_limit_reached',
            'personal_data',
            'secret_or_credential',
            'serious_distress',
            'harmful_or_age_inappropriate',
            'input_relationship_or_secrecy',
            'instruction_override',
            'out_of_scope',
            'url_or_contact',
            'relationship_or_secrecy',
            'unsafe_markup',
            'unsafe_unicode',
            'output_too_long',
            'too_many_sentences',
            'missing_citation',
            'unknown_fact',
            'unsupported_number',
            'optional_check_block',
            'generated_harm_gate_required',
            'generation_failure',
            'internal_failure'
        )
    ),
    occurred_at TEXT NOT NULL,
    UNIQUE(session_id, idempotency_key),
    CHECK ((policy_action IS NULL) = (policy_reason IS NULL)),
    FOREIGN KEY(session_id)
        REFERENCES sessions(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_deletion_requests (
    session_id TEXT PRIMARY KEY,
    operation_id TEXT NOT NULL UNIQUE,
    request_kind TEXT NOT NULL CHECK (
        request_kind IN ('explicit', 'retention')
    ),
    requested_at TEXT NOT NULL,
    FOREIGN KEY(session_id)
        REFERENCES sessions(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS parent_observations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    engagement INTEGER CHECK (
        engagement IS NULL OR engagement BETWEEN 1 AND 5
    ),
    understanding TEXT NOT NULL CHECK (
        understanding IN (
            'not_observed',
            'not_yet',
            'partial',
            'clear'
        )
    ),
    wanted_more INTEGER CHECK (
        wanted_more IS NULL OR wanted_more IN (0, 1)
    ),
    followup_recall TEXT NOT NULL CHECK (
        followup_recall IN (
            'not_observed',
            'not_yet',
            'partial',
            'clear'
        )
    ),
    notes_sanitized TEXT CHECK (
        notes_sanitized IS NULL
        OR length(notes_sanitized) BETWEEN 1 AND 500
    ),
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id)
        REFERENCES sessions(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_ended_at
    ON sessions(ended_at);

CREATE INDEX IF NOT EXISTS idx_turns_session
    ON turns(session_id, turn_index);

CREATE INDEX IF NOT EXISTS idx_events_session
    ON events(session_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_observations_session
    ON parent_observations(session_id, created_at);
```

Initialize:

- insert version `1` only for a fresh database;
- insert one settings row with 30-day retention;
- reject an unsupported newer schema;
- never silently delete/recreate a corrupt database.

Every Explore SQLite connection (telemetry now; curriculum/parent state later) verifies `foreign_keys=ON`, `secure_delete=ON`, `journal_mode=DELETE`, `synchronous=FULL`, `trusted_schema=OFF`, `temp_store=MEMORY`, and a fixed 5000 ms busy timeout before use; failure blocks that store. Do not load extensions. The single-process/runtime and mutation locks bound contention. Managed wipe still removes legacy/crash `-wal`, `-shm`, and `-journal` sidecars, and neither these pragmas nor file deletion are claimed as forensic media erasure.

Each store owns one `sqlite3.Connection(check_same_thread=False)` only when `sqlite3.threadsafety != 0` and SQLite compile options report nonzero `THREADSAFE`. A private reentrant store lock covers every connection/cursor call and complete result materialization; no cursor/generator escapes the lock. All cross-store writes and coherent multi-store reads first hold the single application mutation gate, then use short store transactions in the normative saga order, and no store method calls back into another store while holding its lock. Unsupported SQLite thread mode blocks that store rather than allowing concurrent Gradio callbacks to share it unsafely.

`secure_delete` is defense in depth. It does not guarantee removal from filesystem snapshots, backups, exported files, caches, or storage media.

## Store interface

Implement in `telemetry_store.py`.

```python
from pathlib import Path


class ExploreTelemetryStore:
    def __init__(self, db_path: Path) -> None:
        ...

    def initialize(self) -> None:
        ...

    def create_session(
        self,
        launch_id: UUID,
        lesson_id: str,
        lesson_content_version: int,
        *,
        lesson_package_sha256: str,
        lesson_payload_sha256: str,
        curriculum_binding_id: str | None = None,
        assignment_id: str | None = None,
        assignment_operation_id: str | None = None,
        initial_events: tuple[PendingEventRecord, ...] = (),
        started_at: datetime | None = None,
    ) -> SessionRecord:
        ...

    def end_session(
        self,
        session_id: UUID,
        status: SessionStatus,
        *,
        ended_at: datetime | None = None,
    ) -> SessionRecord:
        ...

    def record_turn(
        self,
        session_id: UUID,
        *,
        turn_index: int,
        role: TurnRole,
        source: TurnSource,
        persistable: PersistableTurnText,
        generation_outcome: GenerationOutcome | None,
        created_at: datetime | None = None,
    ) -> TurnRecord:
        ...

    def record_turn_pair(
        self,
        session_id: UUID,
        *,
        turn_index: int,
        learner: PersistableTurnText,
        learner_source: TurnSource,
        assistant: PersistableTurnText,
        generation_outcome: GenerationOutcome,
        event: PendingEventRecord | None,
        created_at: datetime | None = None,
    ) -> tuple[TurnRecord, TurnRecord]:
        ...

    def record_event(
        self,
        session_id: UUID,
        event_type: EventType,
        *,
        idempotency_key: str,
        step_id: str | None = None,
        value_code: str | None = None,
        decision: PolicyDecision | None = None,
        occurred_at: datetime | None = None,
    ) -> EventRecord:
        ...

    def get_session_replay(self, session_id: UUID) -> SessionReplay:
        ...

    def list_session_summaries(
        self,
        *,
        current_launch_id: UUID,
    ) -> tuple[SessionSummary, ...]:
        ...

    def add_parent_observation(
        self,
        session_id: UUID,
        *,
        engagement: int | None,
        understanding: UnderstandingLevel,
        wanted_more: bool | None,
        followup_recall: UnderstandingLevel,
        notes: str | None,
        created_at: datetime | None = None,
    ) -> ParentObservation:
        ...

    def set_retention_days(self, days: int | None) -> None:
        ...

    def list_expired_session_ids(
        self,
        *,
        now: datetime | None = None,
    ) -> tuple[UUID, ...]:
        ...

    def mark_prior_launch_sessions_abandoned(
        self,
        *,
        current_launch_id: UUID,
        ended_at: datetime,
    ) -> int:
        ...

    def request_session_deletion(
        self,
        session_id: UUID,
        *,
        operation_id: UUID,
        kind: DeletionRequestKind,
        requested_at: datetime | None = None,
    ) -> SessionDeletionRequest:
        ...

    def list_pending_deletion_requests(
        self,
    ) -> tuple[SessionDeletionRequest, ...]:
        ...

    def delete_session(self, session_id: UUID) -> bool:
        ...

    def attach_curriculum_binding(
        self,
        session_id: UUID,
        binding: BindingAttachment,
    ) -> SessionRecord:
        ...

    def get_session_by_assignment_operation(
        self,
        operation_id: str,
    ) -> SessionRecord | None:
        ...

    def get_session_export(
        self,
        session_id: UUID,
    ) -> dict[str, object]:
        ...
```

Boundary validation:

- database path equals the derived telemetry path from the runtime profile;
- parent directory exists and is private/writable per environment qualification;
- IDs match the shared kebab-case rule where applicable;
- lesson package and payload hashes are lowercase SHA-256;
- assignment ID and operation ID are either both present or both absent;
- a curriculum binding, when present, must match lesson ID, content version, and canonical lesson-payload hash; current package hash remains separately recorded;
- timestamps are timezone-aware UTC;
- naive timestamps are rejected;
- `value_code` matches `^[a-z0-9][a-z0-9_.:-]{0,63}$`;
- free text never enters `value_code`;
- `record_turn` accepts only `PersistableTurnText`, never raw text or a rejected draft;
- learner turns require `generation_outcome=None`;
- assistant turns require an explicit generation outcome;
- `WITHHOLD` content must exactly equal the fixed marker;
- `SANITIZED_TEXT` is sanitized again defensively;
- notes are sanitized and limited to the shared configured `max_parent_note_chars` (which is schema-bounded at 500);
- duplicate turn index/role is rejected, not overwritten.
- session creation and all supplied initial events commit atomically; an initial-event failure leaves no session.
- session service persists each non-empty learner/assistant pair and optional policy/tutor event in one transaction through `record_turn_pair`; no crash-visible half-turn is valid.
- repeated event idempotency key with byte-equivalent typed fields returns the existing row; a mismatch fails.
- `record_turn`, `record_turn_pair`, and interactive `record_event` check `status='active'` and insert in the same transaction; an operation-key replay may return an existing row but never append a missing row to a terminal session.
- `end_session` never transitions a terminal session back to active and is idempotent only for the same terminal identity; post-session parent observations/follow-up recall use their separate explicitly allowed path.
- event keys are app-generated bounded codes such as `session-start:<operation-or-session-id>`, `step:<step-id>:<visit-index>`, and `choice:<check-id>:<attempt-index>`; no child text enters a key.
- replay orders events by `(occurred_at, id)` and turns by `(turn_index, role)` and rejects impossible/non-contiguous assignment state rather than guessing.
- session summaries contain no turn/note text and sort by `(started_at DESC, session_id)`.

`attach_curriculum_binding` is a one-time migration:

- session binding must currently be null;
- binding lesson ID/version and canonical lesson-payload hash must exactly match the recorded session;
- update only `curriculum_binding_id`;
- never infer by title, date, child text, or graph proximity;
- repeated attachment of the same binding is idempotent;
- a different binding fails.

The parent-facing migration service requires the parent token and shows the exact sessions/binding/hash before calling the store.

`lesson_package_sha256` is the approved lesson TOML artifact hash from the package index. `lesson_payload_sha256` is the review-metadata-independent canonical runtime/grounding/asset identity from the same index. A pre-graph migration may tolerate only a package-hash difference caused by PR-02's exact `[review]` status/attestation fields (and resulting index lesson SHA); publication approval metadata is never packaged. Exact payload and asset identity is mandatory.

## Transaction behavior

Use one connection and transaction per public write operation.

Global lock order for every Explore build is: already-held process-lifetime runtime lock → shared application mutation gate → short server-registry map lock → affected server binding/session locks in stable UUID order → one store's private lock/transaction. Release the map lock before taking a session lock. Never acquire an earlier lock while holding a later one, never hold two store locks at once, and release each store transaction before the next cross-store step. Helpers, provider/browser calls, filesystem source parsing, and operator waits hold none of these locks. Wipe first takes the mutation gate and marks callbacks quiescing, then takes session locks in stable order; ordinary Stop/Delete/assignment paths use the same order.

- enable foreign keys on every connection;
- commit on success;
- rollback on exception;
- return an immutable record reconstructed from the inserted row;
- do not leak SQL or path details into child-facing errors.

Deletion:

- delete the session row;
- let foreign-key cascades remove turns/events/observations;
- return `False` for unknown session;
- do not add a tombstone child row that defeats deletion;
- rollback if any delete step fails.

`delete_session` is the low-level telemetry transaction and is never called directly by UI code. From PR-05 onward every UI deletion/retention path uses PR-05's token-guarded `LocalDataLifecycleService`; after PR-11 that same service requires its installed parent-state cascade port so readiness evidence, candidate snapshots, assignments, and telemetry cannot be left dangling.

## Retention

Default: 30 days.

`None` means retain until explicit parent deletion.

Purge:

- only non-active sessions;
- compare `ended_at` to UTC cutoff;
- telemetry store only lists expired IDs and never deletes them in bulk;
- lifecycle coordinator deletes each ID in cross-store order; each store step is transactional and idempotent;
- run before browser launch and on explicit maintenance only while no current child session/nonterminal assignment is live;
- listing/export during a live session is read-only and reports retention deferred; it never starts a multi-session purge behind Stop;
- when idle, listing/export may request maintenance first, but a short busy/gate timeout returns the list/export with a fixed deferred notice rather than waiting;
- do not silently purge an active session;
- active sessions whose `launch_id` differs from the current process may be marked abandoned only through the token-protected explicit parent action.

Retention means “purge on the next startup/maintenance after N days,” not a guaranteed wall-clock deletion deadline. The app has no background scheduler. Retention does not delete prior JSON exports.

Startup records only `not_applicable`, `complete`, or `deferred_nonterminal` plus a count in hashed readiness. An unexpected store/cascade/delete error blocks UI launch; only an active/nonterminal session or assignment may produce the explicit deferral status.

## Local data lifecycle service

Implement the UI-facing coordinator in `data_lifecycle.py`:

```python
@dataclass(frozen=True, slots=True)
class DeletionReport:
    operation_id: UUID
    managed_local_complete: bool
    telemetry_deleted: bool
    curriculum_deleted: bool | None
    parent_state_deleted: bool | None
    exports_deleted: int
    audio_files_deleted: int
    private_curation_files_deleted: int
    unmanaged_external_categories: tuple[str, ...]
    residual_categories: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeletionRecoveryReport:
    resumed_operation_ids: tuple[UUID, ...]
    completed_session_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ParentCascadeReport:
    assignments_deleted: int
    candidates_deleted: int
    decisions_deleted: int
    readiness_evidence_deleted: int
    empty_runs_deleted: int


class GeneratedExportKind(StrEnum):
    SESSION_JSON = "session_json"
    OBSERVATION_BUNDLE = "observation_bundle"
    PARENT_STATE_JSON = "parent_state_json"


@dataclass(frozen=True, slots=True)
class GeneratedExportSummary:
    export_id: UUID
    kind: GeneratedExportKind
    created_at: datetime
    sha256: str
    byte_count: int


class ParentDataCascadePort(Protocol):
    def delete_session_derivatives(
        self,
        session_id: UUID,
        observation_ids: tuple[UUID, ...],
    ) -> ParentCascadeReport:
        ...


class LocalDataLifecycleService:
    def resume_pending_deletions(self) -> DeletionRecoveryReport:
        ...

    def delete_session(
        self,
        session_id: UUID,
        *,
        parent_token: str,
        confirmed: bool,
    ) -> DeletionReport:
        ...

    def purge_expired(self, *, now: datetime) -> tuple[DeletionReport, ...]:
        ...

    def list_generated_exports(
        self,
        *,
        parent_token: str,
    ) -> tuple[GeneratedExportSummary, ...]:
        ...

    def delete_generated_export(
        self,
        export_id: UUID,
        *,
        parent_token: str,
        confirmed: bool,
    ) -> bool:
        ...

    def wipe_all_managed_family_data(
        self,
        *,
        parent_token: str,
        confirmation_phrase: str,
    ) -> DeletionReport:
        ...
```

Before graph integration, the parent cascade port is absent and the service coordinates telemetry, generated exports, audio temp/private-curation cleanup, process/callback locks, token validation, and managed-family-data wipe. From PR-05 onward its fixed path registry already includes all three derived DB filenames and sidecars; absent files are a verified no-op. PR-10/11 initialize/register store closers and cross-store cascades but do not introduce previously unknown wipe paths. Store-level delete methods remain inaccessible to Gradio callbacks.

For every confirmed session deletion or retention deletion, first transactionally insert one `session_deletion_requests` row carrying the operation UUID and exact kind. If a marker already exists for that session, retry must adopt its operation ID/kind rather than changing semantics. Startup order is exact: resume every marked deletion; after PR-11 reconcile remaining assignments; only then run ordinary retention purge. Explicit-delete exports are removed and verified before the telemetry session is deleted; retention-marked deletion preserves exports. Telemetry deletion is the final store step and removes the marker by cascade. Thus every crash leaves either a resumable typed marker/session or a completed deletion, never an unmarked orphan export or assigned telemetry row.

`resume_pending_deletions()` processes markers by `(requested_at, operation_id)`, returns stable UUID-sorted report tuples, and raises on the first incomplete/corrupt operation; a partial recovery report is never treated as launch-ready.

The internal report IDs support deterministic tests/control flow; terminal/readiness-facing maintenance output shows category counts only and does not create a deleted-session tombstone.

For explicit deletion, enumerate only the pinned derived export root without following links. Match ordinary session exports by their strictly parsed envelope session UUID and PR-10 observation bundles by the stable source-session/source-observation UUID arrays in their strict manifest; delete the entire affected aggregate bundle. An app-named malformed/hash-mismatched export blocks telemetry deletion for parent/manual recovery rather than being ignored. Files copied outside the derived root remain an explicitly reported unmanaged residual.

The lifecycle coordinator owns a fixed strict export-parser registry. PR-05 registers session JSON; PR-10 adds observation bundles; PR-11 adds parent-state JSON. Token-guarded listing returns only export ID/kind/time/hash/byte count in stable order. Confirmed deletion accepts only an export UUID resolved by a fresh pinned-root scan—never a browser path—and removes/verifies the whole file or bundle. Unknown/app-named malformed entries block list/delete claims until manual recovery.

For a single-file export, summary SHA-256/byte count cover that exact file; for a bundle they cover the exact manifest and total manifest-plus-declared-file bytes. Export IDs are unique across all kinds.

The exact phrase is `DELETE ALL MANAGED LOCAL FAMILY DATA`. The operation requires exclusive ownership of the process-lifetime runtime lock, quiesces callbacks/helper process groups, closes every initialized store, and removes every fixed managed family-data path including telemetry/curriculum/parent-state DB filenames and `-wal`, `-shm`, and `-journal` sidecars, exports, audio temp, and private curation. PR-05 owns this complete fixed registry even when later stores are absent; PR-10/11 only add closers/cascade behavior when those stores exist. Runtime profile, generic packaged lesson/templates, non-child content quarantine, and capability decision records remain.

Before closing/deleting paths, atomically create and fsync `.managed-wipe-intent.json` with only schema version, operation UUID, UTC request time, and fixed operation kind—never paths or child data. A valid intent makes the next startup reacquire the runtime lock, derive the fixed registered paths from the profile/code, resume deletion before creating/opening a store, remove/fsync the intent only after verified success, and exit. A malformed intent blocks launch for manual recovery; it is never used as a path source. Any failed known-path deletion leaves the intent and blocks child launch.

The report lists preserved and external/unmanaged categories. `managed_local_complete=True` can coexist with nonempty external categories and means only that every registered Lerni-managed local target was durably removed. The UI must say `Managed local deletion complete; listed copies remain outside Lerni control`, never “all data deleted.” It never claims to delete a live Google Sheet, synced/downloaded/manual copy, browser/terminal cache, provider-held data, filesystem snapshot, backup, or storage remanence. The early implementation exercises the same registered-path algorithm with only currently installed stores.

For each session/launch, conservatively derive fixed external category codes from the qualified capability/browser routes that could have received data (`tutor_or_safety_text`, `speech_to_text_audio`, `browser_speech_text`) and include them before deleting local evidence. Include `browser_speech_text` whenever read-aloud was enabled for the session or its declared route is not mechanically verified local. V1 has no provider deletion API/receipt contract. If the parents require verified provider-side erasure rather than the reviewed retention declaration, external child use is ineligible: select a qualified local capability or add and separately review an adapter deletion/receipt contract before that pilot.

## Export contract

Implement in `export.py`.

```python
def session_export_json(
    store: ExploreTelemetryStore,
    session_id: UUID,
    *,
    export_id: UUID,
    exported_at: datetime,
) -> str:
    ...


def write_session_export(
    store: ExploreTelemetryStore,
    session_id: UUID,
    export_root: Path,
) -> GeneratedExportSummary:
    ...
```

Every app-generated export publish is serialized by the one shared application mutation gate. Build bounded path-free preview bytes/source digest outside the gate; then acquire it, reject pending deletion, freshly recompute the canonical source digest/ID set, require equality, atomically no-replace publish, fsync file/directory, and release. PR-10 observation bundles and PR-11 parent-state snapshots use the same rule. Explicit session deletion holds that gate continuously from deletion-marker creation through export scan/unlink and final telemetry deletion, so no export can publish after its scan and become an unmarked orphan.

Envelope:

```json
{
  "schema_version": 1,
  "export_id": "UUID",
  "export_kind": "session_json",
  "exported_at": "UTC timestamp",
  "session": {},
  "turns": [],
  "events": [],
  "parent_observations": []
}
```

Requirements:

- deterministic key order;
- deterministic row order;
- final newline;
- sanitized/withheld content only;
- no database path;
- no settings, credentials, adapter IDs, exceptions, audio, child-name field, or raw source text;
- require `export_root` to equal the derived private export directory;
- generate filename exactly from the fixed kind prefix, session UUID, and export UUID; never from child text or a browser value;
- reject symlinked directories/files and never accept a browser-supplied filename;
- create files with owner-only permissions where supported;
- never overwrite an existing export;
- open/pin the export directory and create a `0600` temporary sibling with `O_CREAT|O_EXCL`;
- flush/fsync the temporary file;
- atomically publish without replacement using exclusive same-directory link/no-replace semantics; if the platform has no qualified no-replace primitive, fail export rather than use check-then-replace;
- unlink the temporary entry, fsync the directory, and verify destination inode/hash;
- remove temporary file on failure;
- leave an existing destination unchanged on failure;
- export does not extend retention;
- warn parent that export is unencrypted and independently retained.

Temporary names use one fixed hidden app prefix plus export UUID. Startup, before listing/readiness, removes only pinned-root regular one-link temp files/directories matching that exact grammar, verifies absence, and reports a count; malformed/symlink/incomplete cleanup blocks export controls and child launch rather than treating partial bytes as an export. PR-10 bundle publication uses the same recovery rule.

## Task 1 — Schema TDD

Tests:

- `test_fresh_database_has_exact_expected_tables`;
- `test_schema_has_no_child_name_audio_raw_prompt_or_blob_columns`;
- `test_database_does_not_create_study_tables`;
- `test_default_retention_is_thirty_days`;
- `test_foreign_keys_are_enabled`;
- `test_unknown_newer_schema_is_rejected`;
- `test_corrupt_schema_is_not_recreated`.

Use real temporary SQLite databases.

Red:

```bash
"$PYTHON" -m pytest tests/explore/test_telemetry_schema.py -q
```

Green:

- implement initialization only;
- inspect schema with SQLite pragmas;
- avoid mocks.

## Task 2 — Session and turn persistence

Tests:

- create active session;
- complete/stop/error require `ended_at`;
- active session rejects `ended_at`;
- naive timestamp rejected;
- allowed turn is sanitized again;
- non-allow turn stores marker only;
- duplicate turn role/index rejected;
- injected failure in turn-pair/event transaction leaves no half-turn;
- event idempotency-key replay returns existing row and rejects mismatched reuse;
- session replay reconstructs exact deterministic event/turn order;
- one assignment/operation can create at most one telemetry session;
- unknown session foreign key fails;
- assistant fallback stores the safe authored fallback with `authored_fallback`, not the raw rejected draft.
- learner role rejects generation outcome;
- assistant role requires generation outcome.
- first-pilot session can have null binding but records exact package and canonical payload hashes;
- binding migration requires exact lesson ID/version/payload hash and null current binding;
- same binding migration is idempotent; different binding fails;
- independent interest/nudge fields do not exist.

Canary test:

```python
raw = "My name is StorageCanary and my email is canary@example.test"
record = store.record_turn(
    session.id,
    turn_index=0,
    role=TurnRole.LEARNER,
    source=TurnSource.TYPED,
    persistable=persistable_input(
        sanitize_text(raw),
        personal_data_decision,
    ),
    generation_outcome=None,
)
assert record.content_sanitized == "[WITHHELD:personal_data]"
assert "StorageCanary" not in database_bytes_or_rows
assert "canary@example.test" not in database_bytes_or_rows
```

Check rows through SQL; do not depend solely on returned objects.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_telemetry_store.py -q
```

## Task 3 — Events and observations

Tests:

- known event inserts;
- unknown event rejected;
- `value_code` rejects spaces/free text;
- policy action/reason must appear together;
- parent note sanitized;
- note over limit rejected without truncation;
- engagement outside 1–5 rejected;
- follow-up recall can be added later as a second observation;
- no observation requires a child identity.

Red/green in the same store test file or a focused observation file.

## Task 4 — Retention and deletion

Tests:

- finite/manual retention accepted;
- values outside 1–3650 rejected;
- store lists expired completed IDs without deleting; lifecycle purges each in order;
- recent completed session kept;
- active session not purged;
- explicit stale-active operation marks abandoned;
- delete cascades all dependent rows;
- confirmed delete writes/adopts one operation marker, removes exports before the session, and crash-point startup recovery completes idempotently;
- unknown delete returns false;
- UI-facing delete cannot bypass lifecycle coordinator;
- managed wipe requires exact token/phrase, quiesces callbacks, removes every registered family-data path/sidecar, and reports preserved/external residue;
- managed wipe removes registered curriculum/private-curation fixtures and preserves only profile/generic-package/setup records;
- managed-wipe intent is strict/non-child, survives every injected crash point, resumes before store creation, and is removed/fsynced last;
- wrong token or partial shutdown deletes nothing;
- injected database failure rolls back.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_retention.py -q
```

## Task 5 — Export

Tests:

- envelope/version exact;
- rows ordered deterministically;
- only sanitized content present;
- settings/path/audio/child-name/credential keys absent;
- final newline;
- export does not mutate session or retention;
- export outside the derived root rejected;
- symlinked export root rejected;
- generated filename cannot overwrite;
- a destination created during the publish race remains unchanged and export fails;
- atomic failure leaves existing destination unchanged;
- unknown session fails without partial file.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_export.py -q
```

## Task 6 — Safety/telemetry integration

Tests:

- blocked personal data reaches neither tutor nor database;
- distress stores category marker, not sensitive content;
- rejected tutor draft reaches neither display nor database;
- database unavailable does not disable safety;
- storage failure does not queue raw content;
- mixed-session export contains none of the unique raw canaries;
- audio path passed accidentally to a turn is sanitized/rejected and never stored.

Use real policy, real SQLite, real export, and a deterministic fake tutor.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_safety_telemetry_integration.py -q
```

## Parent-facing claims

Allowed:

- “Lerni stores sanitized session records in a local Explore database.”
- “Parents can export or delete a session.”
- “Lerni’s schema does not include audio or a child-name field.”
- “Redaction and deletion are best-effort and have documented limits.”

Disallowed:

- anonymous or PII-free;
- encrypted at rest unless implemented separately;
- guaranteed deletion from backups/exports/storage media;
- no third-party retention when a selected tutor/STT adapter is external;
- no audio retention outside verified application boundaries;
- regulatory compliance.

## Completion criteria

- Schema contains only approved columns.
- Study database remains unchanged.
- Raw blocked/rejected content does not persist.
- Parent observations capture completion, hints, engagement, understanding, wanted-more, and later recall without session duration.
- Retention, delete, and export pass real SQLite tests.
- Export is deterministic and sanitized.
- Storage failure does not weaken policy.
- No provider/model or audio backend appears in the telemetry schema.
- No commit is made.
