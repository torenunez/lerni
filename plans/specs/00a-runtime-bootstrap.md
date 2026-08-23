# Explore Safe Slice — Runtime Profile, Capability Metadata, and Bootstrap

## Goal

Define one portable application assembly path that:

- parses a strict operator-owned runtime profile;
- contains no credential values;
- resolves all mutable paths under one private runtime root;
- selects optional capabilities by import reference;
- records what is operator-declared versus mechanically verified;
- enforces a hard application deadline with a helper process;
- builds a complete dependency bundle or a deterministic fallback bundle;
- never changes lesson, safety, telemetry, or UI code for a different adapter.

The runtime profile is configuration, not a source of lesson content or child data.

## File map

Create:

```text
src/lerni/explore/
├── runtime_config.py
├── capability_runner.py
├── capability_supervisor.py
├── capability_worker.py
├── readiness.py
└── bootstrap.py

tests/explore/
├── test_runtime_config.py
├── test_capability_runner.py
├── test_readiness.py
└── test_bootstrap.py
```

This plan uses contracts defined in the lesson, tutor/safety, telemetry, UI, and audio plans. Implement the parser types early, then complete bootstrap wiring as each capability exists.

Modify `src/lerni/explore/contracts.py` for shared capability metadata. `runtime_config.py` imports from `contracts.py`; `contracts.py` never imports runtime configuration, avoiding a cycle.

## Runtime profile

The default location is supplied explicitly by the operator. No home-directory or repository-relative profile is silently discovered.

Strict TOML schema version `1`:

```toml
schema_version = 1

[server]
host = "127.0.0.1"
port = 7860

[runtime]
root = "/absolute/private/runtime/directory"

[safety]
max_input_chars = 500
max_output_chars = 1200
max_parent_note_chars = 500
max_turns = 8
max_generated_sentences = 3
max_sessions_per_launch = 3
max_capability_calls_per_session = 32
admission_grant_ttl_seconds = 900

[telemetry]
enabled = true
retention_days = 30
# Use the exact string "manual" instead of an integer for no automatic purge.

[content]
lesson_id = "chain-1-acceleration"

[capabilities.tutor]
enabled = false
import_reference = ""
timeout_seconds = 20.0
data_route = "unknown"
retention = "unknown"
logging = "unknown"

[capabilities.tutor.settings]

[capabilities.tutor.credential_refs]

[capabilities.speech_to_text]
enabled = false
import_reference = ""
timeout_seconds = 30.0
data_route = "unknown"
retention = "unknown"
logging = "unknown"

[capabilities.speech_to_text.settings]

[capabilities.speech_to_text.credential_refs]

[capabilities.additional_safety]
enabled = false
import_reference = ""
timeout_seconds = 10.0
data_route = "unknown"
retention = "unknown"
logging = "unknown"

[capabilities.additional_safety.settings]

[capabilities.additional_safety.credential_refs]

[capabilities.browser_speech]
enabled = false
data_route = "unknown"
retention = "unknown"
logging = "unknown"
```

The example is fallback-only. Enabling a plugin requires a non-empty import reference and complete metadata.

Capability ownership is build-version strict. Before PR-07's STT contracts/codec/backend are installed, a profile with `capabilities.speech_to_text.enabled=true` is an unsupported-wired-capability bootstrap error; it is never parsed into readiness and silently ignored. The disabled STT entry and latent `typed-input-v1` fallback remain valid in readiness v1. The same rule applies to any capability kind whose owning PR is absent.

## Immutable configuration types

Place `CapabilityAvailability`, `DataRoute`, `RetentionDeclaration`, `LoggingDeclaration`, `PolicyLimits`, `CapabilityMetadata`, `CapabilityStatus`, `CapabilityCallScope`, the `CapabilityCallRegistry` protocol, `AdmissionGrant`, and `AdmissionResult` in `contracts.py`. Implement the concrete `InMemoryCapabilityCallRegistry` in `capability_runner.py` and the remaining configuration dataclasses in `runtime_config.py`; `contracts.py` never imports the runner.

```python
class CapabilityAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class DataRoute(StrEnum):
    LOCAL = "local"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class RetentionDeclaration(StrEnum):
    NONE_DECLARED = "none_declared"
    DECLARED = "declared"
    UNKNOWN = "unknown"


class LoggingDeclaration(StrEnum):
    DISABLED_DECLARED = "disabled_declared"
    ENABLED = "enabled"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PolicyLimits:
    max_input_chars: int = 500
    max_output_chars: int = 1200
    max_parent_note_chars: int = 500
    max_turns: int = 8
    max_generated_sentences: int = 3
    max_sessions_per_launch: int = 3
    max_capability_calls_per_session: int = 32
    admission_grant_ttl_seconds: int = 900


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str
    port: int


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    root: Path
    telemetry_db: Path
    curriculum_db: Path
    parent_state_db: Path
    audio_temp: Path
    exports: Path
    private_curation: Path
    capability_decisions: Path
    content_quarantine: Path
    wipe_intent: Path
    process_lock: Path


@dataclass(frozen=True, slots=True)
class TelemetryConfig:
    enabled: bool
    retention_days: int | None


@dataclass(frozen=True, slots=True)
class PluginConfig:
    enabled: bool
    import_reference: str
    timeout_seconds: float
    data_route: DataRoute
    retention: RetentionDeclaration
    logging: LoggingDeclaration
    settings: Mapping[str, str]
    credential_refs: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class BrowserSpeechConfig:
    enabled: bool
    data_route: DataRoute
    retention: RetentionDeclaration
    logging: LoggingDeclaration


@dataclass(frozen=True, slots=True)
class ContentConfig:
    lesson_id: str


@dataclass(frozen=True, slots=True)
class RuntimeProfile:
    schema_version: int
    server: ServerConfig
    paths: RuntimePaths
    safety: PolicyLimits
    telemetry: TelemetryConfig
    content: ContentConfig
    tutor: PluginConfig
    speech_to_text: PluginConfig
    additional_safety: PluginConfig
    browser_speech: BrowserSpeechConfig
```

Use immutable read-only mappings for plugin settings and credential references. A credential reference is not a value; version 1 accepts only `env:VARIABLE_NAME`.

## Parsing

```python
class RuntimeConfigError(ValueError):
    pass


def parse_runtime_profile(
    text: str,
    *,
    origin: str = "<runtime-profile>",
) -> RuntimeProfile:
    ...


def load_runtime_profile(path: Path) -> RuntimeProfile:
    ...
```

The launcher accepts one explicit absolute profile path. `load_runtime_profile` rejects symlink path components, non-regular or multi-link files, group/other permission bits where POSIX modes are available, files over `65_536` bytes, NUL/malformed UTF-8, and descriptor/path inode replacement; it reads/parses the same no-follow pinned descriptor and reports only a sanitized field/origin category. Fresh readiness recomputation reopens/revalidates the same path and normalized effective profile rather than trusting the earlier object.

Reject:

- malformed TOML;
- unknown keys at every level;
- schema version other than `1`;
- host other than `127.0.0.1`;
- port outside 1024–65535;
- relative, missing, symlinked, or non-directory runtime root;
- runtime root inside repository checkout;
- runtime root or any already-existing derived child with any group/other permission bit (`mode & 0o077 != 0`) when POSIX modes are available;
- enabled plugin without import reference;
- disabled plugin with non-empty settings, credential references, or import reference;
- timeout outside 0.5–120 seconds;
- enabled plugin with unknown route, retention, or logging declaration;
- setting value not a string;
- key/value longer than configured bounds;
- setting key matching `secret`, `password`, `credential`, `token`, `api_key`, `private_key`, or equivalent normalized form;
- value that looks like a bearer token or private-key block;
- credential logical name outside `^[a-z][a-z0-9_]{0,63}$`;
- credential reference outside `^env:[A-Z_][A-Z0-9_]{0,127}$`;
- duplicate source environment variable within one capability;
- policy bounds outside: input `1..500`, output `1..1200`, parent note `1..500`, turns `1..20`, generated sentences `1..5`, sessions/launch `1..10`, capability calls/session `1..100`, admission-grant TTL `60..3600` seconds;
- invalid lesson ID;
- telemetry retention other than integer `1..3650` or exact string `manual`;
- browser-speech declaration outside the same route/retention/logging enums; `unknown` is permitted only because browser routing is not mechanically known before launch.

Do not log the input profile or values. Errors identify only origin and field path.

The parser maps integer retention to that integer and exact `manual` to `None`. Bootstrap applies this value to `telemetry_settings` before any purge/list/export and reports it as “purge on next startup/maintenance after N days” or “manual deletion”; it never describes this as a wall-clock deletion guarantee.

## Credential references and manual provisioning

The runtime profile may name, but never contain, an optional capability credential:

```toml
[capabilities.tutor.credential_refs]
api_key = "env:LERNI_TUTOR_API_KEY"
```

At qualification probes and each non-status invocation, the parent resolves the named source variable. Missing/empty values make that capability unavailable with a sanitized reason. Standalone `status` receives no credential values and must be local, idempotent, and non-billable; qualification observes/reviews that behavior, otherwise the adapter is unavailable. Parent code never intentionally places resolved values in dataclasses with default `repr`, requests, status, readiness, telemetry, exports, exception text, or disk files. Because trusted plugin code could return a secret, the parent rejects any response frame containing an exact resolved secret byte sequence, disables the capability, and tells the operator to rotate it. This detects exact reflection only and is not a containment guarantee.

The helper is started with a minimal explicit environment and receives each secret only as `LERNI_CAPABILITY_CREDENTIAL_<LOGICAL_NAME_UPPER>`. The configured source variable name and unrelated inherited environment variables are not passed. The plugin contract reads only those standardized child variables. This is accidental-secret minimization, not a sandbox: trusted plugin code can still read accessible files or call operating-system APIs.

External capability setup is optional. The operator owns account creation, billing/usage limits, key creation/rotation/revocation, acceptance of service terms, and confirmation of routing/retention/logging. A local/manual fallback requires no service account or credential.

For each enabled plugin, require strict canonical `capability-decisions/<kind>.json`:

```json
{
  "schema_version": 1,
  "capability": "tutor",
  "adapter_id": "stable-adapter-id",
  "adapter_artifact_sha256": "lowercase-sha256",
  "data_route": "external",
  "data_sent": [
    "sanitized_learner_text",
    "reviewed_current_lesson_context",
    "lesson_state_without_answer_key"
  ],
  "retention": "operator-reviewed-declaration",
  "logging": "operator-reviewed-declaration",
  "training_use": "operator-reviewed-declaration",
  "child_use_terms_reviewed": true,
  "status_local_idempotent_nonbillable_reviewed": true,
  "terms_reviewed_on": "YYYY-MM-DD",
  "account_owner_role": "parent",
  "quota_and_billing_limit_reviewed": true,
  "credential_logical_names": ["api_key"],
  "provider_deletion_or_expiry_process": "bounded non-secret text",
  "unresolved_items": [],
  "qualification_sha256": "lowercase-sha256"
}
```

Reject unknown/missing fields, personal/account identifiers, credential values, text over fixed bounds, a mismatched capability/adapter/artifact/qualification, `unresolved_items` for child use, or false required reviews. `data_sent` is not free text: it must exactly equal the parent-owned wire-codec category allowlist for that capability (`tutor`: sanitized learner text, reviewed current lesson context, state without answer key; `additional_safety`: sanitized learner text and candidate generated text; `speech_to_text`: managed local audio descriptor, bounded child voice audio, locale, and media metadata). Local adapters use truthful local declarations rather than pretending a service account exists.

`qualification_sha256` is the exact SHA-256 of strict sibling `<kind>.qualification.json`, not a self-hash. That fixed v1 generated record contains capability kind, adapter/artifact/effective-metadata hashes, platform/Python identifiers, qualification probe-suite source hash, fixed check IDs/results/counts, qualification date, and overall `pass`/`fail`; it contains no credential, probe payload/output, account identifier, absolute path, or free-form exception. Startup revalidates the pointer plus current artifact/profile/status metadata and runs status through the helper; it does not silently repeat a live/billable probe. Changed code, profile semantics, probe suite, platform, or failed/nonmatching status requires explicit requalification and a new decision.

## Derived paths

Only `runtime.root` is configurable.

Derive:

```text
root/explore-telemetry.sqlite3
root/explore-curriculum.sqlite3
root/explore-parent-state.sqlite3
root/audio-temp/
root/exports/
root/curation-private/
root/capability-decisions/
root/content-quarantine.json
root/.managed-wipe-intent.json
root/.lerni-explore.lock
```

This prevents browser-supplied paths and inconsistent stores.

The operator creates only `runtime.root` ahead of time with private permissions. Derived directories and database files may be absent. During bootstrap, after profile parsing and before stores open:

- root must already exist;
- create each missing derived directory with owner-only permissions where supported;
- do not create, chmod, or replace the root itself;
- re-open/re-stat root and every derived child after creation and before use;
- reject symlinks at every path segment;
- reject unexpected POSIX ACL entries when the platform exposes an ACL inspection API; otherwise record that ACL verification is unavailable;
- acquire a nonblocking exclusive advisory lock on `.lerni-explore.lock` before creating/opening any store and hold it through shutdown/managed wipe;
- securely create a SQLite file as `0600` with no-follow/exclusive semantics only when its store is initialized by the current build, or verify an existing file before that store opens; first-slice never creates curriculum/parent-state files, disabled telemetry creates no telemetry file;
- reject a second process using the same runtime root;
- telemetry/curriculum files may be created only at derived paths;
- exports use generated filenames under `exports/`;
- audio files may exist only under `audio-temp/`;
- filled local family curation may exist only under `curation-private/` when the app is expected to include it in managed wipe; a live Google Sheet or manually copied file remains outside that guarantee.

## Capability metadata

Extend `CapabilityStatus`:

```python
@dataclass(frozen=True, slots=True)
class PluginOperationalMetadata:
    max_input_chars: int | None
    max_output_chars: int | None
    supported_media_types: tuple[str, ...]
    supported_languages: tuple[str, ...]
    supported_sample_width_bytes: tuple[int, ...]
    minimum_sample_rate: int | None
    maximum_sample_rate: int | None
    maximum_channels: int | None
    declarations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PluginStatusPayload:
    availability: CapabilityAvailability
    adapter_id: str
    reason: str
    fallback: str
    operational: PluginOperationalMetadata


@dataclass(frozen=True, slots=True)
class CapabilityMetadata:
    data_route: DataRoute
    retention: RetentionDeclaration
    logging: LoggingDeclaration
    configured_timeout_seconds: float
    operational: PluginOperationalMetadata


@dataclass(frozen=True, slots=True)
class CapabilityStatus:
    availability: CapabilityAvailability
    adapter_id: str
    reason: str
    fallback: str
    metadata: CapabilityMetadata


@dataclass(frozen=True, slots=True)
class CapabilityQualification:
    capability: str
    passed: bool
    adapter_id: str
    plugin_fingerprint_sha256: str | None
    effective_metadata_sha256: str | None
    decision_record_sha256: str | None
    checks: tuple[str, ...]
    failures: tuple[str, ...]
    parent_notice: str
```

Raw plugin `status()` returns `PluginStatusPayload`; it does not echo parent configuration. The process wrapper merges parent-owned route, retention, logging, and timeout with the validated operational payload to construct application `CapabilityStatus`.

Distinguish:

- **mechanically verified**: status call, bounded probe completion, output shape, app deadline, cleanup;
- **operator/plugin declared**: route, retention, logging, external-service behavior.

The parent notice labels declarations as declarations.

For speech-to-text, qualification requires:

- `audio/wav` in supported media types;
- non-empty sample-width bytes selected from `1, 2, 3, 4`;
- sample-rate minimum/maximum with `8000 <= minimum <= maximum <= 192000`;
- maximum channels of `1` or `2`.
- non-empty canonical BCP-47 `supported_languages` containing the active lesson locale (`en-US` in the first slice).

Non-audio capabilities use empty media/language/sample-width tuples and null rate/channel fields unless their contract explicitly uses a language. Recording validation intersects application limits with this qualified metadata; an empty intersection disables microphone input.

## Trust and process boundary

Configured Python plugins are fully trusted code. Import references are not a sandbox.

The interface and helper process:

- avoid accidentally passing telemetry stores, Study state, or UI objects;
- isolate plugin crashes;
- enforce an application deadline;
- permit termination of a hung call.

They do not prevent a plugin from:

- reading accessible files/environment variables;
- opening network connections;
- importing application modules;
- writing outside the runtime root;
- retaining or transmitting received data.

Only operator-reviewed plugins may run. If stronger isolation is required, it is a separate security architecture and pilot blocker.

## Capability runner

Implement in `capability_runner.py`.

```python
class CapabilityKind(StrEnum):
    TUTOR = "tutor"
    SPEECH_TO_TEXT = "speech_to_text"
    ADDITIONAL_SAFETY = "additional_safety"


class CapabilityOperation(StrEnum):
    STATUS = "status"
    GENERATE = "generate"
    TRANSCRIBE = "transcribe"
    ASSESS = "assess"


class CapabilityResultKind(StrEnum):
    PLUGIN_STATUS = "plugin_status"
    TUTOR_DRAFT = "tutor_draft"
    TRANSCRIPT = "transcript"
    SAFETY_RESULT = "safety_result"
    ERROR = "error"


class CapabilityErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    LOAD_FAILED = "load_failed"
    STATUS_FAILED = "status_failed"
    UNAVAILABLE = "unavailable"
    CALL_FAILED = "call_failed"
    INVALID_RESULT = "invalid_result"
    INTERNAL_FAILURE = "internal_failure"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    SECRET_REFLECTION = "secret_reflection"


@dataclass(frozen=True, slots=True)
class CapabilityInvocation:
    protocol_version: int
    invocation_id: UUID
    kind: CapabilityKind
    operation: CapabilityOperation
    import_reference: str
    settings: Mapping[str, str]
    payload: object | None
    timeout_seconds: float
    qualified_plugin_fingerprint_sha256: str | None


@dataclass(frozen=True, slots=True)
class CapabilityResponse:
    protocol_version: int
    invocation_id: UUID
    result_kind: CapabilityResultKind
    payload: object | None
    error_code: CapabilityErrorCode | None


class CapabilityDeadlineExceeded(RuntimeError):
    pass


class CapabilityInvocationFailed(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CapabilityCallScope:
    session_id: UUID
    session_epoch: UUID


class CapabilityCallRegistry(Protocol):
    def cancel_scope(self, scope: CapabilityCallScope) -> int:
        ...

    def cancel_all(self) -> int:
        ...


class InMemoryCapabilityCallRegistry(CapabilityCallRegistry):
    ...


def invoke_in_helper_process(
    invocation: CapabilityInvocation,
    *,
    credential_refs: Mapping[str, str],
    call_scope: CapabilityCallScope | None = None,
    call_registry: CapabilityCallRegistry | None = None,
) -> object:
    ...
```

The scope dataclass and registry protocol in this excerpt are the `contracts.py` definitions; the runner imports them and supplies the concrete registry. Tutor/safety/audio contracts depend only on `contracts.py`, preventing a contracts↔runner import cycle.

Protocol version `1` uses one UTF-8 JSON request frame and one UTF-8 JSON response frame over helper subprocess stdin/stdout; do not send Python objects through pickle. A frame is exactly eight lowercase ASCII hexadecimal length digits, one LF, then that many bytes, with EOF after the frame. Maximum request and response frames are 256 KiB, with a 32 KiB maximum for status. Codecs are explicit allowlists for `PluginStatusPayload`, `TutorRequest`/`TutorDraft`, managed-audio descriptor/transcript, and `AdditionalSafetyResult`; they reject unknown/missing fields, unknown enums, non-finite numbers, duplicate JSON keys, depth over 16, wrong capability/operation pairs, bad length prefixes, and trailing bytes/frames. UUIDs and timestamps use canonical strings. No arbitrary class name or import reference may appear inside payload.

Canonical JSON uses `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, `allow_nan=False`, UTF-8, arrays for tuples, and enum string values. Status fingerprint SHA-256 covers canonical `{"adapter_id": ..., "operational": ...}` only; dynamic availability/reason/fallback are validated separately. Application effective-metadata SHA-256 covers the fingerprint plus parent-owned route/retention/logging/timeout.

Exact response invariants:

- success uses the one result kind required by the operation, non-null payload, and null error;
- failure uses `ERROR`, null payload, and one fixed error code;
- `status` request payload/fingerprint are null and result is `PLUGIN_STATUS`;
- every non-status request carries the qualified plugin fingerprint and the worker rejects drift before invoking the operation;
- tutor `generate` → `TUTOR_DRAFT`, STT `transcribe` → `TRANSCRIPT`, additional safety `assess` → `SAFETY_RESULT`.

Allowed operation pairs:

- tutor: `status`, `generate`;
- speech-to-text: `status`, `transcribe`;
- additional safety: `status`, `assess`.

PR-03 implements framing plus plugin-status/error envelopes. PR-04 adds tutor/additional-safety payload codecs; PR-07 adds STT payload codecs. No earlier PR imports a later-owned contract.

Use a fresh credential-free control handshake per invocation. The parent launches `python -I -m lerni.explore.capability_supervisor`; only that minimal supervisor, after registration, may launch `python -I -m lerni.explore.capability_worker` in the target process group:

1. Parent validates/encodes one protocol frame and reserves the invocation ID atomically in the registry before resolving credentials or creating a process; a pre-cancelled scope creates nothing. Qualification uses an internal one-call registry.
2. Parent resolves only required credentials, creates a dedicated lifetime/control channel, and launches the minimal supervisor with the minimal environment, stdin/stdout pipes, and no shell; the supervisor blocks before worker/plugin creation.
   - `STATUS` resolves/passes no credentials; non-status operations resolve only their declared references;
   - runtime child-session calls require both scope and registry; qualification creates neither at the API boundary but the runner still uses its private reservation;
   - atomically attach supervisor ownership to the reservation before sending the fixed start control; a concurrently cancelled reservation terminates the blocked supervisor without worker creation;
   - after start, the supervisor creates the worker in a new target process group and reports that group into the same registry; cancellation at any handshake barrier terminates both;
   - supervisor/worker lifetime pipes are arranged so unexpected parent or supervisor death causes an out-of-group watcher to kill the target worker group; worker/plugin descendants never inherit a lifetime-channel write end;
   - on every normal path, the supervisor terminates any residual worker descendants, reaps the worker, verifies target-group absence, then returns the bounded response and exits.
3. Worker duplicates its response descriptor, redirects plugin stdout/stderr to the null device before import, and never treats plugin output as protocol data.
4. Worker decodes the bounded frame, validates version/kind/operation/payload, then imports the configured factory and constructs the plugin.
5. Worker calls the contractually local/idempotent/non-billable `status()` first. For non-status operations, status must be available and its adapter ID plus canonical metadata hash must match the qualified baseline carried in the invocation header; any adapter whose status requires provider contact is not eligible for this protocol.
6. Worker calls exactly the selected protocol method.
7. Worker writes only the allowlisted contract response or one fixed error code: `invalid_request`, `load_failed`, `status_failed`, `unavailable`, `call_failed`, `invalid_result`, or `internal_failure`.
8. Parent writes/closes stdin and reads a bounded response while waiting until the monotonic deadline derived from the configured application timeout.
9. On timeout, scope cancellation, wipe, or unexpected parent death, terminate the complete process group, kill it after a bounded grace period, wait/reap where still parent-owned, and verify a test descendant is gone. If process-tree/lifetime containment cannot be qualified, credential-bearing/generated/audio plugins are unavailable for child use.
10. Parent scans raw response bytes and every decoded string scalar for exact resolved credential values before contract construction; a match becomes `SECRET_REFLECTION`, disables the capability, and requires rotation.
11. Parent unregisters only the same invocation, closes pipes/process handles, and drops resolved credential values in all paths.
12. Parent validates frame size, protocol version, invocation ID, result kind, exact schema, and semantic output limits before constructing a contract object.

Do not serialize:

- exceptions;
- traceback;
- environment;
- telemetry;
- runtime profile;
- parent token;
- raw blocked input;
- rejected tutor draft after gate processing.

For speech-to-text, only the validated managed audio path and adapter-public settings cross the boundary. Cleanup remains the application parent’s responsibility.

PR-03 provides only the contract-neutral process client:

```python
class ProcessCapabilityClient:
    def status(self, kind: CapabilityKind) -> CapabilityStatus:
        ...

    def invoke(self, invocation: CapabilityInvocation) -> object:
        ...
```

Owning PRs then provide typed adapters without any earlier→later import:

```python
# PR-04, in tutor_process.py
class ProcessTutorBackend(TutorBackend):
    ...

class ProcessAdditionalSafetyBackend(AdditionalSafetyBackend):
    ...

# PR-07, in speech_to_text_process.py
class ProcessSpeechToTextBackend(SpeechToTextBackend):
    ...
```

The generic client owns framing/supervision only. Each typed adapter stores/uses only validated import reference, public settings, credential-reference names, qualified status, canonical qualified-metadata hash, and timeout—never resolved values. `status()` returns that immutable qualified status. Each operational protocol method creates one `CapabilityInvocation`; the child rechecks live status against the qualified baseline before the call. Application services never load or call a configured plugin object directly.

Qualification itself invokes `status` and any explicit probe through this protocol. It validates the full metadata round-trip:

- profile values are authoritative for route, retention, logging, and configured timeout;
- plugin status declares only bounded operational input/output/media/language fields; the parent merges and hashes effective metadata;
- adapter ID is a normalized non-empty identifier no longer than 128 characters;
- reason, fallback, and declaration strings are bounded and control-character-free;
- audio ranges satisfy the rules above;
- tuple order and duplicates are canonicalized/rejected before hashing;
- process-group descendant termination and a forced parent-process-death fixture both pass with controlled descendants;
- any mismatch disables the capability rather than silently replacing metadata.

## Capability bundle

Define in `bootstrap.py`.

```python
@dataclass(frozen=True, slots=True)
class CapabilityBundle:
    tutor: TutorBackend
    browser_speech: BrowserSpeechOutput
    additional_safety: AdditionalSafetyBackend | None
    qualifications: tuple[CapabilityQualification, ...]


@dataclass(frozen=True, slots=True)
class ApplicationBundle:
    launch_id: UUID
    profile: RuntimeProfile
    capabilities: CapabilityBundle
    lesson_catalog: LessonCatalog
    telemetry_store: ExploreTelemetryStore | None
    data_lifecycle: LocalDataLifecycleService
    session_factory: Callable[[], ExploreSessionPort]
    readiness: LaunchReadinessReport
    readiness_provider: Callable[[], LaunchReadinessReport]
    launch_config: LaunchConfig
    parent_guard: ParentControlGuard
    admission_guard: LocalAdmissionGuard
    capability_call_registry: CapabilityCallRegistry
    runtime_lock: ProcessLifetimeLock
```

This is the first-slice bundle implemented by plans 00–07. It has no curriculum, recommendation, assignment, or parent-state imports. Plans 08a and 08b explicitly modify this bundle and bootstrap only after the first-slice pilot gate; the base bootstrap does not discover those schemas conditionally.

`readiness_provider` is read-only and recomputes the full current report from already qualified application state and rehashed files/config/decisions/store status. It never reuses the prior digest as an input and never performs capability probes or external calls. Launch-scoped operational circuit-breaker state is shown separately in dynamic parent status and assignment-specific readiness; it does not rewrite the base digest because every possible authored fallback is acknowledged up front.

## Pre-browser readiness and fallback trace

Define in `readiness.py`:

```python
@dataclass(frozen=True, slots=True)
class FallbackTrace:
    capability: str
    fallback_id: str
    source_kind: str
    source_ref: str
    source_sha256: str
    child_behavior: str


@dataclass(frozen=True, slots=True)
class LaunchReadinessReport:
    readiness_schema_version: int
    application_build_sha256: str
    dependency_set_sha256: str
    runtime_profile_sha256: str
    policy_profile_sha256: str
    framework_qualification_sha256: str
    capability_decision_sha256s: tuple[str, ...]
    lesson_id: str
    lesson_content_version: int
    lesson_package_sha256: str
    lesson_payload_sha256: str
    telemetry_mode: str
    telemetry_retention: str
    retention_purge_status: str
    retention_deferred_count: int
    browser_speech_status: str
    generated_tutor_status: str
    qualifications: tuple[CapabilityQualification, ...]
    fallbacks: tuple[FallbackTrace, ...]
    report_sha256: str


@dataclass(frozen=True, slots=True)
class ReadinessApproval:
    report_sha256: str
    approved_at: datetime
```

Readiness schema ownership is centralized here:

- exact v1 is the `LaunchReadinessReport` field set above and remains the complete first-slice shape through PR-08;
- exact v2 is v1 plus only `graph_mode`, `active_batch_id`, `active_manifest_sha256`, `active_artifact_set_sha256`, `curriculum_state_sha256`, and `content_quarantine_sha256`, under plan 08a's nullability rules;
- exact v3 is v2 plus only `recommendation_mode` and `parent_state_schema_sha256`, under plan 08b.

All versions include the discriminator and final digest; the digest omits only itself. Strict version-dispatched encoders/decoders reject every missing, extra, duplicate, wrong-type, or wrong-version field. PR-07 represents STT in v1's existing fixed capability-kind qualification/decision/fallback collections and does not mutate the v1 field set. Transient recovery/reconciliation IDs or outcome summaries never enter any version.

Fallback traces are a complete stable inventory resolved after qualification and before app construction, including latent paths even when the corresponding capability currently qualifies:

- manual tutor → lesson-authored `fallback_text`, identified by lesson/version/package hash and exact text SHA-256;
- unavailable browser speech → built-in `visible-text-v1` contract text/hash;
- unavailable generated-content harm gate → built-in authored-tutor/deterministic-policy-only notice/hash;
- unavailable speech-to-text → built-in `typed-input-v1` freeform fallback notice/hash;
- unavailable telemetry → built-in no-recording notice/hash;

`generated_tutor_status` is exactly `enabled` or `disabled_authored_fallback`. It is `enabled` only when both the tutor and mandatory additional-safety capabilities have enabled decisions and pass startup qualification. Absence/degradation of either is an acknowledgement-ready authored baseline, but never a partially qualified generated mode: no tutor or additional-safety generation call is exposed, and parent/pilot status explicitly labels generated tutoring unavailable.

The report explicitly says that tutor/harm-gate operational failure selects the exact authored fallback and disables generated tutoring for the remainder of the launch. `FallbackTrace` contains no mutable active/latent flag. Dynamic parent status identifies the path currently in effect without changing the already acknowledged fallback contract.

Before browser execution, enabled browser speech is reported as `unknown_until_browser`, never `available`. Visible text is the acknowledged fallback. After the page reports API support, a parent-token action may enable read-aloud for that session only; route/retention/logging remain operator/browser declarations, not mechanically verified facts.

Fresh readiness recomputation keeps this pre-browser declaration (`unknown_until_browser` or disabled); transient API support/permission is shown only in dynamic parent status and does not rewrite the acknowledged report.

Every source reference is an app-owned stable identifier, never an adapter exception. Capability framing and readiness reuse PR-02's strict `canonical_json_bytes()` encoder; `report_sha256` hashes the report with that field omitted.

`retention_purge_status` is exactly `not_applicable`, `complete`, or `deferred_nonterminal`; the count contains no IDs. An unexpected purge/storage/cascade error blocks launch and produces no acknowledgement-ready report. A deliberate active/nonterminal deferral is hashed and parent-visible.

Startup may print a separate sanitized deletion-recovery summary before readiness. Transient recovered IDs/counts are not report inputs or persisted tombstones: only the resulting `complete`/deferred state enters readiness, so a `--print-readiness` maintenance run and the following unchanged launch can reproduce the same digest.

Hash inputs:

- application build: sorted package-relative regular-file paths and SHA-256 values under the resolved `lerni/explore` package roots plus project version; reject symlinks/special files and exclude only fixed generated cache suffixes/directories, never operator-selected globs;
- dependency set: the normalized transitive closure declared by the Explore extra plus configured plugin distributions, including Gradio, with sorted names/versions, metadata/RECORD hash, and verification of every recorded file hash; an enabled plugin outside the application build must be installed from a complete non-editable recorded distribution, while editable/unrecorded third-party distributions fail child qualification;
- runtime profile: every normalized non-secret effective field, including host/port, runtime-root string, safety limits, retention, capability declarations/settings/credential-reference names, and browser-speech declarations;
- policy profile: policy schema/version, golden-fixture hash, phrase/regex/stop-word/number-rule hash, and effective `PolicyLimits`;
- framework qualification: exact strict private `capability-decisions/framework.json` hash, revalidated against the installed Gradio RECORD, current platform/Python, and probe-suite source hash;
- capability decisions: fixed capability-kind-ordered exact SHA-256 values for each enabled plugin’s strict private `capability-decisions/<kind>.json`, each pointing to its strict qualification sibling and covering artifact/package hash, route, retention, logging/training declaration, terms review date, quota/billing decision, credential reference name, and qualification result—never the credential value. `framework.json` is hashed only in the separate framework field; unknown files or decision/qualification files for a disabled capability must be archived outside this derived directory or bootstrap rejects the ambiguous setup.

An enabled plugin requires a matching decision record and installed artifact/dependency identity. Bootstrap rehashes files/config/records immediately before launch. `--acknowledge-readiness-sha256` is compared with the freshly recomputed report, so edits after `--print-readiness` invalidate it. External account settings cannot be mechanically re-read by this local hash and remain an operator declaration.

The runner prints the sanitized report to the launching terminal only after all qualification and package checks. Before opening a browser or accepting a child event, a parent must either:

- interactively type `LAUNCH <first-12-report-hash-characters>` in a TTY; or
- supply `--acknowledge-readiness-sha256 <full-hash>` obtained from a prior `--print-readiness` invocation.

The acknowledgement is one-launch, in-memory state. A changed build/dependency, profile/policy, lesson package, framework result, capability decision/qualification, telemetry mode/retention or post-maintenance purge status, browser declaration, or fallback changes the digest and requires a new acknowledgement. The parent accordion shows the same digest and fallback list after launch. No raw plugin error, input, secret, or parent token enters the report.

Immediately after acknowledgement and before issuing launch secrets, importing Gradio, or constructing a browser app, call the read-only readiness provider and require exact digest equality. This is separate from the same fresh check before every child Start.

## Parent control guard

```python
@dataclass(frozen=True, slots=True)
class AdmissionGrant:
    grant_id: UUID
    session_epoch: UUID
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    grant: AdmissionGrant
    csrf_nonce: str


class ParentControlGuard:
    def issue_token(self) -> str:
        ...

    def verify(self, candidate: str) -> bool:
        ...

    def rotate(self) -> str:
        ...


class LocalAdmissionGuard:
    def issue_one_time_code(self) -> str:
        ...

    def admit(
        self,
        candidate: str,
        *,
        framework_session_id: str,
        host: str,
        origin: str | None,
    ) -> AdmissionResult:
        """Return a server-side start grant plus an ephemeral browser nonce."""
        ...

    def consume_for_start(self, grant: AdmissionGrant) -> bool:
        ...

    def authorize_mutation(
        self,
        *,
        framework_session_id: str,
        candidate_nonce: str,
        session_epoch: UUID,
        host: str,
        origin: str | None,
    ) -> AdmissionGrant:
        ...

    def issue_parent_session_grant(
        self,
        *,
        framework_session_id: str,
        current_session_epoch: UUID | None,
    ) -> AdmissionGrant:
        """Rotate any current epoch and consume one launch session-budget slot."""
        ...
```

Requirements:

- parent token has at least 256 random bits; one-time admission code and CSRF nonce each have at least 128 random bits; values are generated per launch/session with `secrets`, not predictable UUID/time sources;
- parent token/admission code are issued and shown only in the launching terminal after exact readiness acknowledgement and immediately before UI launch; `--print-readiness` issues neither;
- held in memory;
- never placed in runtime profile, URL, telemetry, browser storage, export, logs, or exception;
- compared with constant-time comparison;
- rotate on explicit parent action;
- protected callbacks require the current token;
- protected browser callbacks always require the qualified exact Host/same-origin Origin checks below; unavailable metadata makes child UI ineligible;
- failed checks emit category only.

Child-session admission requirements:

- page load renders only the supervision/admission screen and creates no telemetry session;
- parent enters a separate one-time launch code shown in the terminal; the component is cleared immediately;
- five failed admission-code attempts invalidate that code and require a fresh terminal-issued code; failures are fixed-category/rate-limited without echoing candidates;
- every mutating browser request must expose an exact loopback `Host`/port and exact same-origin `Origin`; missing, duplicate, malformed, or mismatched values fail before nonce/binding lookup;
- admission creates one active browser session and an unguessable in-memory CSRF nonce bound to its epoch;
- admission holds its one-time `AdmissionGrant` server-side behind a parent launch/data-management landing; it does not itself create telemetry or enable child interaction;
- only `csrf_nonce` enters an ephemeral hidden browser component; the server registry retains its digest/session/epoch binding, while `AdmissionGrant` passes directly between server-side callback/controller layers and is never serialized to the browser;
- `ExploreSessionPort.start()` atomically consumes the exact grant once; later callbacks call `authorize_mutation()` before invoking the session service;
- nonce is required on every child and parent mutation, never appears in URL/log/export, and is invalidated on stop/wipe/shutdown;
- first slice permits one active child session, at most `max_sessions_per_launch`, and at most `max_capability_calls_per_session`;
- the capability-call budget counts each runtime helper invocation separately (input harm, tutor, output harm, or STT), including timeout/error attempts; startup qualification and browser-local speech do not consume a child-session budget;
- after separate parent-token and mutation authorization, any parent-started additional/reset session uses `issue_parent_session_grant()`; it invalidates any old epoch, consumes the same session budget, and returns a one-time server-only grant;
- grant issuance reserves that launch-budget slot even if later setup fails; reservations are not refunded or reusable, preventing retry races from bypassing the cap;
- an unconsumed grant expires after `admission_grant_ttl_seconds`; expiry leaves its slot consumed, and a still-authorized parent may request a new parent-session grant if budget remains;
- budget exhaustion ends generation/audio for the session and uses deterministic local fallback.

This is lightweight local admission/authorization, not user authentication or protection against malicious code running as the same operating-system user.

Tier-B framework qualification must prove the callback/request API exposes trustworthy raw `Host` and `Origin` values for every mutating route. If it cannot, Gradio child UI is ineligible and bootstrap must use headless authored-core verification or a separately reviewed HTTP boundary; the implementation may not silently downgrade to nonce-only checks.

## Bootstrap

```python
def build_application(
    profile: RuntimeProfile,
) -> ApplicationBundle:
    ...
```

Order:

1. Validate the existing private root and acquire the process-lifetime exclusive lock.
2. If the strict managed-wipe intent exists, resume the registered path-based wipe, verify known paths absent, remove/fsync the intent last, and exit without recreating stores or launching.
3. Generate one random in-memory `launch_id`; it is operational correlation, not a readiness input.
4. Securely create/verify derived directories and validate any already-existing fixed database paths without creating unopened stores.
5. Load raw packaged lesson index and approved lesson catalog.
6. Initialize/create only telemetry if enabled; otherwise use no-op telemetry and leave its DB absent.
7. Build the local data-lifecycle service bound to the runtime lock.
8. Resume typed pending session-deletion requests, then apply configured retention through that lifecycle coordinator and complete startup purge before browser launch.
9. Load and qualify additional safety or select `None`.
10. Load and qualify tutor; select `ManualTutor` unless both tutor and the mandatory generated-content harm gate qualify.
11. Configure browser speech as disabled or `unknown_until_browser`.
12. Create safety policy and grounding gate from the same immutable `PolicyLimits`.
13. Create the normal session service factory with launch ID plus admission/session/capability-call budgets.
14. Resolve and hash the complete readiness/fallback report.
15. Build unissued parent/admission guards and local launch config.

PR-07 later inserts STT qualification after step 10 and populates v1's existing fixed capability qualification/decision/fallback collections; it does not add readiness fields, and PR-06 does not own an STT type.

`build_application` does not launch Gradio or issue browser-control secrets. The runner obtains readiness acknowledgement, issues/prints the parent token and one-time admission code, calls `build_app`, and only then invokes the local launch method; any construction/launch failure rotates/discards both before exit.

Failure behavior:

- invalid profile: do not start;
- lesson missing/not approved: do not start child UI;
- telemetry unavailable: may start in visibly non-recording mode after parent acknowledgement;
- tutor unavailable: start with manual fallback;
- browser speech unavailable: start with visible text;
- unsafe runtime path: do not start;
- runtime lock unavailable: do not start;
- unknown plugin declarations: plugin unavailable until corrected.

## Qualification tiers

### Tier A — required headless core

- Python and package import;
- lesson parsing/approval;
- deterministic engine;
- safety/grounding;
- in-memory/manual tutor fallback;
- temporary SQLite support when telemetry enabled.

Failure blocks all implementation verification.

### Tier B — optional local UI

- browser and Gradio app construction;
- localhost bind;
- no public/share URL;
- framework data-handling controls.

Failure blocks UI and child pilot, not headless core.

### Tier C — optional read-aloud

- browser speech API support/behavior.

Failure disables read-aloud only.

### Tier D — optional microphone/STT

- managed recording root;
- microphone permission;
- WAV capture;
- qualified STT adapter;
- cleanup.

Failure disables microphone only.

### Tier E — optional generated tutor

- qualified tutor plugin;
- separately qualified mandatory additional-safety plugin;
- exact installed 56-case input/output harm/benign probe resource and passing results;
- routing/retention notice;
- structured output probe;
- grounding and output gate.

Failure of either plugin, any required probe, or any generated-output gate uses manual fallback and blocks only the generated-tutor portion of the pilot.

## Runtime profile TDD

Tests:

- minimal fallback profile parses;
- unknown key rejected at each level;
- public host rejected;
- relative/repository/symlink runtime root rejected;
- insecure permissions rejected where testable;
- mode `0755` root and non-private ACL are rejected; SQLite files are `0600`, regular, one-link, and inode-stable;
- existing private root with absent children parses and bootstrap creates private children;
- missing root is rejected and never auto-created;
- second process using the runtime root is rejected before any store opens;
- derived paths exact;
- secret-like setting rejected;
- credential reference grammar accepted while literal secret values are rejected;
- missing referenced environment variable disables only that capability;
- enabled plugin requires complete declarations;
- disabled plugin rejects settings;
- timeout/retention/policy bounds enforced;
- error never contains canary setting value.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_runtime_config.py -q
```

## Runner TDD

Use test plugins only. Build a tiny fixture-plugin wheel under `tests/explore/fixtures/capability_plugin_package/`, install it with the local project into a temporary isolated environment, and point the runner at that environment’s absolute Python. Do not rely on the repository `tests` package or `PYTHONPATH`; isolated `-I` workers cannot import them.

Tests:

- valid typed result returns;
- wrong result type rejected;
- oversized result rejected;
- plugin exception becomes sanitized failure;
- crash becomes sanitized failure;
- hung plugin terminated at deadline;
- plugin-spawned descendant process is terminated/reaped with the group;
- malformed, duplicate-key, wrong-ID, wrong-kind, oversized, and trailing frames rejected;
- complete status metadata survives exact wire round-trip;
- live metadata drift from qualified baseline disables the call;
- helper receives only standardized referenced credential variables and no unrelated canary environment value;
- credential canary is absent from frames, results, status, readiness, captured output, and errors;
- exact credential reflection disables capability and returns only fixed error code;
- channels/process cleaned after every branch;
- only allowed payload fields cross boundary;
- raw exception/traceback not returned;
- blocked input is never sent to runner.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_capability_runner.py -q
```

## Bootstrap TDD

Tests:

- fallback-only profile builds;
- missing approved lesson blocks child UI;
- unavailable tutor selects manual fallback;
- unavailable browser speech keeps text;
- telemetry failure produces explicit no-recording state;
- first-slice bootstrap imports no graph/recommendation modules;
- data lifecycle is telemetry-only before the graph milestone;
- parent token required for export/delete/reset/observation controls;
- page load before one-time admission creates no telemetry session;
- Host/Origin/nonce/session/capability-call budgets fail closed;
- no secret/profile value appears in status;
- session factory creates isolated states.

Readiness tests additionally prove:

- every unavailable/degraded path has one stable fallback trace;
- manual fallback hash equals the approved lesson-authored text;
- report hashing is deterministic and excludes no displayed decision field;
- changed source/build/dependency/policy/profile/decision record/qualification/content/retention/browser mode invalidates prior acknowledgement;
- browser launch and child callbacks are unreachable before exact acknowledgement;
- report and parent UI contain the same digest/fallback IDs;
- report contains no canary secret, raw adapter error, parent token, or child text.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_bootstrap.py -q
```

## Completion criteria

- Exact runtime profile parser exists.
- All mutable paths are derived under one private root.
- Runtime profile/IPC requests accept no credential value; exact reflected responses are rejected with stated limitations.
- Plugin trust limitations are explicit.
- Helper process enforces application deadline.
- Optional capabilities fail independently.
- `CapabilityBundle` and application assembly are defined.
- Parent controls require a per-launch token.
- Fallback-only application builds without tutor/browser speech; PR-07 proves the same with STT absent.
- No model, provider, credential system, operating system, accelerator, or coding agent is assumed.
