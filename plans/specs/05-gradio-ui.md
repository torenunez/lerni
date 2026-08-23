# Explore Safe Slice — Gradio UI, Curated Visual, and Read-Aloud

## Goal

Build a local Gradio experience that:

- works with deterministic authored content when no tutor, microphone, or browser speech capability is available;
- presents one reviewed visual and short text;
- keeps authoritative lesson state in a server registry bound to one browser/framework session;
- sends typed input through the same safety/tutor pipeline used by transcripts;
- shows explicit retrieval choices;
- optionally reads the final displayed assistant text aloud;
- gives supervising parents status, observation, export, delete, stop, and reset controls;
- never exposes a public share URL or streams unreviewed tokens.

## File map

Create:

```text
src/lerni/explore/
├── presenter.py
├── visuals.py
├── speech_browser.py
├── ui.py
├── launch.py
└── __main__.py

tests/explore/
├── test_presenter.py
├── test_visuals.py
├── test_speech_browser.py
├── test_ui.py
└── test_launch.py
```

Modify:

- `pyproject.toml` to add the qualified Gradio dependency to the `explore` optional profile;
- `pyproject.toml` to add `lerni-explore = "lerni.explore.launch:main"` under project scripts.

The canonical SVG remains only under `src/lerni/explore/lessons/assets/`. `visuals.py` reads it through the lesson catalog.

## Dependency boundary

Add Gradio only to the Explore optional install profile.

Do not add:

- a provider SDK to the core or UI dependency set;
- FastAPI as a direct application layer;
- graph libraries;
- cloud analytics;
- image-upload packages;
- token-streaming helpers.

Use the package manager to add the latest compatible Gradio release during implementation; do not invent a version in advance. After qualification, record the supported project range plus the exact resolved transitive distribution/RECORD identities (or the environment’s hash-pinned lock/constraints artifact) used by clean-build evidence. A version range alone is not reproducible; readiness always hashes the actually installed closure.

Keep Gradio imports behind the launch/composition boundary. Bootstrap configures the private derived framework temp/cache root `audio-temp/framework/` before importing Gradio or constructing the server; ordinary `lerni.explore` domain/config/readiness imports must not import the UI framework. PR-07 then qualifies microphone uploads specifically beneath that root.

## Presenter types

Implement in `presenter.py`.

```python
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import UUID


class InputSource(StrEnum):
    TYPED = "typed"
    TRANSCRIPT = "transcript"


class UiLifecycle(StrEnum):
    ACTIVE = "active"
    STOPPED = "stopped"
    DELETED = "deleted"


class SpeechAction(StrEnum):
    NOOP = "noop"
    SPEAK = "speak"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class ChatEntry:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ParentStatus:
    session_id: UUID
    lesson_id: str
    lesson_content_version: int
    phase: LessonPhase
    capability_messages: tuple[str, ...]
    readiness_report_sha256: str
    fallback_ids: tuple[str, ...]
    telemetry_available: bool


@dataclass(frozen=True, slots=True)
class UiSessionState:
    session_id: UUID
    session_epoch: UUID
    lesson_state: LessonState
    history: tuple[ChatEntry, ...]
    completed_learner_turns: int
    lifecycle: UiLifecycle
    read_aloud_enabled: bool
    microphone_enabled: bool


@dataclass(frozen=True, slots=True)
class BrowserSessionHandle:
    opaque_handle: str
    rendered_revision: int


@dataclass(frozen=True, slots=True)
class SpeechCommand:
    action: SpeechAction
    text: str
    language: str | None
    rate: float
    token: str


@dataclass(frozen=True, slots=True)
class UiResult:
    state: UiSessionState | None
    snapshot: LessonSnapshot | None
    history: tuple[ChatEntry, ...]
    lifecycle: UiLifecycle
    parent_status: ParentStatus
    speech: SpeechCommand
    child_notice: str
    parent_notice: str
```

Validate `ChatEntry.role` as `user` or `assistant`.

`UiSessionState` is authoritative server-only state and contains no service object, database connection, credential, parent token, admission/CSRF nonce, raw audio path, answer key, or adapter instance. The browser receives only a cryptographically random opaque `BrowserSessionHandle` plus a separate ephemeral CSRF nonce. The server registry stores only their digests and binds them to the framework-session identity, current epoch, readiness digest, pending admission grant, authoritative `UiSessionState`, and monotonic rendered revision.

Every callback resolves that binding under the session lock using constant-time digest checks and the qualified framework request identity; it ignores/rejects any browser-supplied session UUID, epoch, lifecycle, lesson state, revision advancement, or capability state. Handles/nonces never enter URLs, persistent browser storage, logs, telemetry, or exports, rotate on Reset/Stop/Delete/wipe/re-admission, and are removed when terminal. No browser component carries an `AdmissionGrant` or parent token.

`UiResult(state=None, snapshot=None, lifecycle=DELETED, ...)` represents successful deletion.

## Session port

```python
class ExploreSessionPort(Protocol):
    def start(self, admission: AdmissionGrant) -> UiResult:
        ...

    def continue_lesson(
        self,
        state: UiSessionState,
    ) -> UiResult:
        ...

    def submit_text(
        self,
        state: UiSessionState,
        text: str,
        source: InputSource,
    ) -> UiResult:
        ...

    def submit_choice(
        self,
        state: UiSessionState,
        choice_id: str,
    ) -> UiResult:
        ...

    def stop(self, state: UiSessionState) -> UiResult:
        ...

    def reset(
        self,
        state: UiSessionState,
        parent_token: str,
    ) -> UiResult:
        ...

    def set_read_aloud(
        self,
        state: UiSessionState,
        enabled: bool,
        parent_token: str,
    ) -> UiResult:
        ...

    # Implemented by PR-07; fallback-only PR-06 returns a fixed unavailable result.
    def set_microphone_enabled(
        self,
        state: UiSessionState,
        enabled: bool,
        parent_token: str,
    ) -> UiResult:
        ...

    # Implemented by PR-07; path_value remains untrusted until the audio boundary.
    def transcribe_recording(
        self,
        state: UiSessionState,
        path_value: str | None,
    ) -> "AudioUiResult":
        ...

    def repeat_last_response(
        self,
        state: UiSessionState,
    ) -> UiResult:
        ...

    def add_parent_observation(
        self,
        state: UiSessionState,
        *,
        engagement: int | None,
        understanding: UnderstandingLevel,
        wanted_more: bool | None,
        followup_recall: UnderstandingLevel,
        notes: str | None,
        parent_token: str,
    ) -> UiResult:
        ...

    def list_session_summaries(
        self,
        *,
        parent_token: str,
    ) -> tuple[SessionSummary, ...]:
        ...

    def abandon_prior_active_sessions(
        self,
        *,
        current_launch_id: UUID,
        confirmed: bool,
        parent_token: str,
    ) -> int:
        ...

    def add_followup_recall(
        self,
        session_id: UUID,
        *,
        followup_recall: UnderstandingLevel,
        notes: str | None,
        parent_token: str,
    ) -> ParentObservation:
        ...

    def export_historical_session(
        self,
        session_id: UUID,
        *,
        parent_token: str,
    ) -> GeneratedExportSummary:
        ...

    def delete_historical_session(
        self,
        session_id: UUID,
        *,
        confirmed: bool,
        parent_token: str,
    ) -> DeletionReport:
        ...

    def export_session(
        self,
        state: UiSessionState,
        parent_token: str,
    ) -> UiResult:
        ...

    def delete_session(
        self,
        state: UiSessionState,
        *,
        confirmed: bool,
        parent_token: str,
    ) -> UiResult:
        ...
```

Create one concrete application service, for example `ExploreSessionService`, that composes:

- approved lesson catalog;
- deterministic lesson engine;
- tutor service;
- telemetry store;
- local data-lifecycle coordinator for every delete/wipe path;
- browser speech-output command builder.

Gradio callbacks depend only on `ExploreSessionPort`. PR-07 extends the port implementation with audio behavior; no Gradio callback receives an STT backend, audio root, session UUID, or epoch directly.

## Presenter behavior

### Admission landing

- successful one-time-code admission renders a parent-only `Start Lesson` / `Manage Local Data` landing state;
- retain the initial `AdmissionGrant` only in the server registry; admission alone creates no `UiResult`, telemetry session, or child interaction;
- token-guarded history/export/delete/wipe controls work from this landing;
- active telemetry rows not owned by the current in-memory registry are shown as prior-launch stale; child Start is disabled until a parent explicitly confirms abandonment through the fixed store method;
- if the held grant expires during management, Start requires a fresh parent-session grant and consumes another launch-budget slot; no silent refresh occurs;
- immediately before any child Start, call the read-only readiness provider and require its digest to equal both the displayed report and original terminal approval; a mismatch disables Start and requires restart/fresh terminal acknowledgement;
- `Start Lesson` requires the current parent token, then passes the still-unconsumed held grant to `ExploreSessionPort.start`; that method is the sole consumer and calls `consume_for_start` exactly once after the comparison.

### Start

- require a live one-time `AdmissionGrant`; page load/admission alone never calls Start or creates telemetry;
- atomically consume it and use its exact `session_epoch` in server registry and `UiSessionState`;
- load approved lesson;
- create deterministic initial state;
- create a new telemetry session with exact lesson ID, content version, package hash, canonical lesson-payload hash, and initial typed events in one store transaction;
- append authored intro as assistant entry;
- supply idempotent `session_started` and `step_viewed` initial events to that transaction;
- return read-aloud `noop` because read-aloud defaults off.

### Continue

- create explicit telemetry `EventType.CONTINUE_SUBMITTED` (distinct from the lesson engine’s `LessonEventType.CONTINUE`);
- transition engine;
- append authored snapshot body;
- record transition event;
- emit speech command only if enabled.

### Typed or transcribed text

- reject when session stopped;
- call `TutorService.respond` with the current session/epoch capability scope and shared registry;
- if `turn_created` is false, show only the fixed UI notice and do not append history, persist turns/events, or increment learner-turn count;
- append learner/display text only when each is non-null and only after final gating;
- record sanitized/withheld telemetry through the store;
- increment learner turn count once;
- do not call engine transition;
- speech command contains exactly the displayed tutor text.
- while a helper call is in flight, clear the raw input component, show only a fixed accessible `Checking that…` status, disable conflicting child mutations but keep Stop available, and never render partial/plugin progress text.

### Choice

- require a selected authored choice ID;
- during `CHECK`/`HINT`, disable typed/transcript Send and do not call tutor; retrieval proceeds only through authored choices/hints so generation cannot reveal or grade the answer;
- call deterministic transition;
- append the authored result/hint;
- record choice and transition outcome;
- tutor is not called;
- completion ends the lesson session as completed.

### Stop

- mark session stopped;
- end telemetry session;
- disable child input;
- emit speech `cancel`.
- rotate `session_epoch` so late callbacks are discarded.

### Reset

- stop the existing active session first;
- create a new session and initial lesson state;
- do not delete the old session automatically;
- emit speech `cancel`, then start with read-aloud off.
- require the in-memory parent token;
- after CSRF/parent verification, obtain and consume a parent-session `AdmissionGrant`; this rotates the epoch and enforces the launch session budget.

### Parent controls

- parent notes use telemetry sanitization;
- observation, export, reset, and delete require the per-launch parent token;
- token-guarded history lists summary metadata only; a selected ended session may receive a later follow-up-recall observation with all unrelated judgment fields set to `not_observed`/null;
- historical export/delete use exact server-listed session UUIDs, still revalidate existence/status, and delegate deletion to the lifecycle coordinator;
- export uses a generated filename under the derived private export directory;
- generated-export listing exposes only ID/kind/time/hash/size; exact-ID deletion requires parent token/confirmation and never accepts a path;
- deletion requires a separate confirmation control;
- deletion returns a representable `DELETED` result with no state/snapshot;
- stop/reset/delete rotate the epoch before releasing the session lock;
- same-page token controls are lightweight local authorization, not account authentication.
- managed local family-data wipe uses `LocalDataLifecycleService`, exact typed confirmation, stops the app, and reports preserved/external residual categories without child text.
- enabling read-aloud requires the parent token after browser support is detected and idempotently records the fixed `read_aloud_enabled` event for residual reporting; child controls may repeat/stop already enabled speech but cannot enable it.

## Curated visual

Implement:

```python
@dataclass(frozen=True, slots=True)
class CuratedVisual:
    visual_id: str
    title: str
    description: str
    svg: str


def load_visual(
    catalog: LessonCatalog,
    asset: AssetRef,
) -> CuratedVisual:
    ...


def render_visual_html(visual: CuratedVisual) -> str:
    ...
```

Validation:

- SVG only for the first milestone;
- UTF-8;
- size limit;
- reject declarations, doctypes, entities, processing instructions, and non-SVG namespaces before parsing with a non-networking XML parser;
- require a fixed element/attribute allowlist plus exactly one root `<svg>`, `<title>`, and `<desc>`;
- reject scripts, style/URL values, event-handler attributes, `foreignObject`, external references, animation, and image/use links;
- rendered HTML includes an accessible surrounding label;
- no child-provided visual ID or file path.

The visual is selected from the current reviewed lesson snapshot.

## Browser speech output

Implement in `speech_browser.py`.

```python
class BrowserSpeechOutput:
    def status(self) -> CapabilityStatus:
        ...

    def speak(
        self,
        text: str,
        *,
        enabled: bool,
        language: str | None,
    ) -> SpeechCommand:
        ...

    def cancel(self) -> SpeechCommand:
        ...
```

Rules:

- disabled returns `noop`;
- empty text returns `noop`;
- text is already final safe display text;
- maximum length equals output policy limit;
- rate clamps to `0.5`–`1.5`;
- token is a random non-secret event ID used to make repeated commands distinct;
- no named voice;
- no HTML in spoken text;
- visible text remains unchanged when unsupported.
- before browser detection status is `unknown_until_browser`; detection reports API presence only and does not prove local routing, retention, or logging.
- support detection never enables speech; a parent-token callback enables it for the current session.

## Browser JavaScript contract

The qualified Gradio API should send a hidden structured `SpeechCommand` to a browser callback.

Normative behavior:

```javascript
(command) => {
  const live = document.getElementById("speech-live");
  const announce = (text) => {
    if (live) live.textContent = text;
  };

  if (!command || command.action === "noop") {
    return [];
  }

  if (!("speechSynthesis" in window) ||
      !("SpeechSynthesisUtterance" in window)) {
    announce("Read-aloud is unavailable. The lesson text remains on screen.");
    return [];
  }

  window.speechSynthesis.cancel();

  if (command.action === "cancel") {
    announce("Read-aloud stopped.");
    return [];
  }

  const utterance = new SpeechSynthesisUtterance(command.text);
  if (command.language) {
    utterance.lang = command.language;
  }
  utterance.rate = Math.max(0.5, Math.min(1.5, command.rate));
  utterance.onstart = () => announce("Reading aloud.");
  utterance.onend = () => announce("Finished reading.");
  utterance.onerror = () => {
    announce("Read-aloud failed. The lesson text remains on screen.");
  };
  window.speechSynthesis.speak(utterance);
  return [];
}
```

Adapt syntax only as required by the qualified Gradio API. Do not weaken the support check, cancellation, text fallback, or status announcement.

Run a separate no-text detection callback first and return only `supported`/`unsupported` to parent status. The speaking callback above is unreachable until parent enablement.

Browser/operating-system synthesis may use implementation-specific services. Documentation must not claim it is necessarily local.

## Gradio component layout

### Child area

- page heading;
- short “A grown-up should stay with you” notice;
- curated SVG in a non-upload HTML component;
- lesson heading/body;
- chat/history component;
- explicit authored radio choices shown only in check/hint phases;
- typed textbox;
- Send button;
- Continue button;
- Check Answer button;
- Stop button;
- Read Again button;
- Stop Reading button;
- child-visible status region.

### Audio area

Added by the audio plan:

- microphone-only recorder;
- transcript preview/edit in the same typed textbox;
- microphone status;
- no auto-send.

### Parent accordion

- capability status;
- browser-speech support/declaration notice and parent-token enable checkbox, off by default;
- lesson ID/version/phase;
- telemetry available/unavailable notice;
- engagement 1–5;
- understanding;
- wanted-more;
- later recall;
- sanitized notes;
- Save Observation;
- token-guarded historical session-summary selector;
- explicit prior-launch active-session abandonment control;
- selected-session follow-up recall save, export, and confirmed delete controls;
- Export Session action with no browser-supplied path;
- generated-export list plus exact-ID confirmed delete action;
- parent-token unlock field;
- launch-code/parent-token fields use password rendering where available, disable autocomplete/password saving where the qualified framework permits, and clear immediately after verification;
- delete confirmation checkbox and Delete Session button;
- exact-phrase Delete All Managed Local Family Data control, visually separated from session deletion;
- Reset Session.

Parent controls require the per-launch token but remain local prototype authorization, not multi-user authentication.

## UI state mapping

The Gradio callback adapter converts:

- authoritative `UiSessionState` to/from the server registry and returns only `BrowserSessionHandle` to browser state;
- `ChatEntry` to the qualified chat message format;
- `LessonSnapshot.choices` to radio choices;
- `CuratedVisual` to HTML;
- `ParentStatus` to parent-facing Markdown/text;
- `SpeechCommand` to hidden structured browser state.

No callback receives the answer key. Child callbacks receive an opaque handle, CSRF nonce, and framework request context; only the resolved server-side state is passed to `ExploreSessionPort`.

Generated text is rendered only through a qualified escaped/plain-text path. Prefer a read-only text component. If a chat component is used, it must support Markdown-disabled or equivalent plain-text rendering plus HTML sanitization. Parent-authored status Markdown must never interpolate raw child or generated text.

## Event wiring

Required flow:

- page load renders supervision/admission only;
- parent admission callback validates the one-time code/Host/Origin, clears the code component, and stores the unconsumed grant in a new server binding while rendering the parent-only landing; the separate token-guarded Start callback passes that still-unconsumed grant to `ExploreSessionPort.start`, which is its sole consumer;
- Send click and textbox Enter call the same typed handler;
- Continue calls `continue_lesson`;
- radio change alone does nothing;
- Check Answer calls `submit_choice`;
- parent-token read-aloud enablement calls `set_read_aloud`;
- Read Again calls `repeat_last_response`;
- Stop Reading emits `cancel`;
- Stop calls `stop`;
- Reset calls `reset`;
- observation save calls `add_parent_observation`;
- export and delete call their explicit methods;
- audio completion only prefills text, as defined in the audio plan.

Use the global order defined by telemetry: already-held runtime lock → shared application mutation gate → server-registry map lock → per-binding/session lock → one store lock. Prevalidate only bounded handle/nonce/request syntax, acquire the mutation gate, resolve the binding under the short registry-map lock, release that map lock, then acquire the binding/session lock and validate CSRF/framework identity/admission/epoch/budget. A tutor/STT callback reserves its operation/call count and captures only the server-resolved session/epoch, releases gate/session lock during helper execution, then reacquires in the same order to verify binding/epoch/operation before any display or persistence. Ordinary continue/choice/second-tutor mutations reject while a conflicting call is in flight.

Stop, Reset, Delete, and managed wipe acquire the mutation gate before session locks while a helper runs: rotate the epoch first, cancel/terminate the registered helper process group, terminalize/clean up, and return without accepting its result. A late helper result reacquires in the same order, observes the stale epoch/operation, is discarded without display/persistence, and is reaped. No external/helper call holds either lock for its full deadline.

Qualify a bounded in-memory framework concurrency configuration with at least two request workers and no queue persistence. Stop/cancel must use a nonqueued or distinct-concurrency path that enters while a barrier-controlled tutor callback is blocked; ordinary mutations still serialize in the application lock. If the selected Gradio API queues Stop behind the helper, generated/STT child use is blocked rather than claiming cancellation.

## Local launch contract

Create:

```python
@dataclass(frozen=True, slots=True)
class LaunchConfig:
    host: str
    port: int
    runtime_dir: Path


def build_app(
    session_factory: Callable[[], ExploreSessionPort],
    *,
    capabilities: CapabilityBundle,
    readiness: LaunchReadinessReport,
    readiness_provider: Callable[[], LaunchReadinessReport],
    approval: ReadinessApproval,
    data_lifecycle: LocalDataLifecycleService,
    parent_guard: ParentControlGuard,
    admission_guard: LocalAdmissionGuard,
    runtime_dir: Path,
) -> object:
    ...


def launch(
    app: object,
    config: LaunchConfig,
    approval: ReadinessApproval,
    *,
    expected_report_sha256: str,
) -> None:
    ...


def main(argv: Sequence[str] | None = None) -> int:
    ...
```

Validation:

- host exactly `127.0.0.1`;
- qualified request context exposes exact `Host` and `Origin` for every mutation; missing/malformed/duplicate/non-loopback/cross-origin values fail before callback state resolution;
- port 1024–65535;
- private writable runtime directory;
- share/public-link option hardcoded false;
- analytics disabled when the qualified Gradio API exposes that option;
- flagging, examples, feedback capture, public API names/schema pages, queue persistence, and debug mode disabled;
- no parent token in URL, browser storage, component value after verification, or logs;
- generated/child text rendered as escaped plain text;
- framework error details hidden from child view;
- no automatic browser-history or monitoring endpoint enabled when configurable.
- launch rejects missing, stale, or mismatched readiness approval before invoking Gradio.

The launcher may print the local URL and parent capability summary. It must not print credentials, raw runtime profile, child turns, or database content.

`main()`:

1. parses `--runtime-profile` plus mutually compatible `--print-readiness` / `--acknowledge-readiness-sha256`;
2. calls `parse_runtime_profile`;
3. calls `build_application`;
4. prints the complete sanitized readiness/fallback report;
5. exits before UI construction for `--print-readiness`;
6. otherwise obtains exact interactive or command-line readiness approval;
7. freshly reopens/revalidates profile/files/store status and recomputes readiness; any digest mismatch aborts before secrets, framework import, or UI construction;
8. issues/prints the launch-scoped parent token and one-time admission code;
9. configures the private framework temp/cache root, then lazily imports/composes Gradio and calls `build_app` with the session factory, capabilities, fresh readiness report, data-lifecycle service, parent guard, and runtime directory;
10. calls `launch` with the approval and expected report digest;
11. rotates/discards issued secrets and returns nonzero with a sanitized operator error if construction/launch fails.

## Framework data-handling qualification

Before child use, submit unique raw canaries through a throwaway local app and inspect:

- stdout/stderr;
- configured runtime directories;
- Gradio cache/temp directories;
- queue state/files;
- flagging/output directories;
- exception output;
- generated app configuration.
- browser and server-process network requests during page load and synthetic callbacks, with browser speech and all external plugins disabled.

Verify:

- analytics disabled;
- no public/share URL;
- no flagging;
- no persistent queue;
- no raw callback body in logs/files;
- no auto-exposed named API for child or parent mutations;
- framework temp root is known;
- no non-loopback asset, analytics, telemetry, update, or callback request is emitted by the app/framework in the qualified fallback-only flow;
- session cleanup occurs.

If the qualified Gradio version cannot suppress or bound raw text persistence, disclose the exact boundary and block the stronger telemetry-only data claim and child pilot until the design is revised.

Write the result atomically as strict private `capability-decisions/framework.json`. Its fixed v1 shape contains only schema version, framework/distribution version and RECORD hash, probe-suite source hash, qualified platform/Python identifiers, fixed configuration booleans, managed temp-root relative ID, per-sink canary occurrence counts, qualification date, and `pass`/`fail`; it never contains canary text, child data, absolute paths, account data, or free-form exceptions. Reject unknown fields, nonzero occurrence counts for a passing result, artifact/probe drift, or a non-passing result. `framework_qualification_sha256` is the exact file hash, and a changed framework/build/probe requires requalification.

## Task 1 — Pure presenter TDD

Tests:

- start works with `ManualTutor`;
- start does not require speech or microphone;
- page load/invalid or valid admission creates no session/telemetry; parent Start consumes the held grant once, while data management does not consume it;
- file/config/store/readiness change while on the parent landing makes Start call count zero and requires restart/re-acknowledgement;
- typed input and transcript source share one submission path;
- empty normalized input creates no history/turn/event and does not increment the cap;
- policy-rejected input never reaches tutor;
- tutor failure displays authored fallback;
- tutor text cannot advance state;
- choice transition never calls tutor;
- read-aloud command contains only displayed assistant text;
- stop disables further submission and cancels speech;
- reset ends old session and creates new state;
- every parent mutation rejects wrong/missing token;
- historical summaries expose no turn/note text; ended-session follow-up recall writes a new sanitized observation and remains usable after restart;
- historical export/delete revalidate the selected UUID and never accept a path;
- deletion returns terminal `DELETED` result;
- late tutor result after stop/reset/delete is discarded and not persisted;
- export/delete/reset cannot race another mutation;
- telemetry failure leaves safety/lesson usable and warns parent;
- delete requires confirmation.

Red:

```bash
"$PYTHON" -m pytest tests/explore/test_presenter.py -q
```

Implement pure application behavior before importing Gradio.

## Task 2 — Visual TDD

Tests:

- packaged visual loads;
- required accessibility elements exist;
- script/external reference/event handler rejected;
- unknown visual ID rejected;
- rendered visual contains no upload control or remote URL.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_visuals.py -q
```

## Task 3 — Read-aloud TDD

Tests:

- disabled is no-op;
- enabled creates speak command;
- empty is no-op;
- rate clamps;
- cancel has no text;
- repeated identical text creates distinct token;
- visible text is unchanged by unavailable browser capability;
- JavaScript smoke fixture handles unsupported, speak, and cancel branches.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_speech_browser.py -q
```

Do not test the browser vendor’s speech quality. Test the application command contract.

## Task 4 — Gradio composition

Tests should assert the application’s own wiring contract, not re-test Gradio internals.

Required tests:

- `build_app` succeeds with qualified Gradio and all manual fallbacks;
- no child image upload component is configured;
- microphone component absent/disabled before audio capability;
- read-aloud defaults off;
- read-aloud cannot be enabled before browser detection or without parent token;
- child input remains when read-aloud unavailable;
- callback map has non-streaming handlers;
- Host/Origin/admission nonce/session and capability-call budgets fail closed;
- browser state contains only an opaque handle/revision; forged handles, stale revisions, replay across framework sessions/epochs, and browser-supplied UUID/state fields fail before the session port;
- launch config rejects non-local host;
- launch config cannot enable share;
- parent status digest/fallback IDs exactly match pre-browser readiness;
- missing or stale readiness approval means Gradio launch is never called;
- parent delete has explicit confirmation input and token;
- generated canary renders as text, not active markup;
- child/assistant canaries do not appear in framework logs/cache during the qualification fixture.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_ui.py tests/explore/test_launch.py -q
```

## Post-pilot extension boundary

Plans 00–07 stop here: no recommendation controls, assignment types, parent-state service, or conditional placeholders are included. Plan 08b later modifies the session port, presenter, bootstrap, and parent accordion in one graph/recommendation PR after its prerequisites pass.

## Accessibility requirements

- keyboard-operable controls;
- explicit text labels;
- no meaning conveyed only by color, image, icon, hover, or audio;
- visible focus;
- primary targets at least 44 CSS pixels where supported;
- responsive single-column layout;
- live regions for lesson, speech, microphone, save/export/delete status;
- read-aloud stop always available while speaking;
- typed input remains the universal freeform fallback in `INTRO`/`TEACH`; retrieval phases intentionally expose authored choices/hints only;
- transcript editable before send;
- SVG title/description and text alternative;
- parent can stop the session immediately.

## Manual smoke before adding microphone

1. Launch with manual tutor, no optional adapters.
2. Confirm only a localhost URL exists.
3. Complete lesson by Continue and explicit choices.
4. Submit one in-scope typed question.
5. Submit one out-of-scope question and confirm redirect.
6. Enable read-aloud, repeat, stop, and disable.
7. Simulate unsupported speech and confirm visible text remains.
8. Save parent observation.
9. Export session and inspect sanitized content.
10. Delete session after confirmation.
11. Reset and confirm a new session.

## Completion criteria

- UI works without a model or microphone.
- A qualified tutor can be injected without UI changes.
- Lesson progress is deterministic.
- Curated visual is local and accessible.
- Read-aloud is optional and off by default.
- No unreviewed token is streamed.
- No public/share URL is possible.
- Parent controls require a per-launch token and are clearly not account authentication.
- Text remains the universal fallback.
- No commit is made.
