# Explore Safe Slice — Push-to-Talk Audio Input

## Goal

Add microphone input as soon as the typed/visual/read-aloud core is stable, without coupling the application to a named speech model, provider, SDK, accelerator, or operating system.

The microphone path must:

- remain optional;
- preserve typed input;
- record only after an explicit user action;
- accept a short bounded clip;
- pass the clip to a qualified speech-to-text capability;
- show the transcript for parent/child review and correction;
- never auto-submit the transcript;
- route submitted transcript text through the same input policy as typed text;
- attempt immediate recording deletion in success and failure paths;
- never place audio or its path in telemetry or exports.

## File map

Create:

```text
src/lerni/explore/
├── recordings.py
├── audio_presenter.py
└── speech_to_text_process.py

tests/explore/
├── test_recordings.py
├── test_audio_presenter.py
└── fixtures/
```

Modify:

- `src/lerni/explore/contracts.py` to add speech-to-text contracts.
- `src/lerni/explore/plugin_loader.py` to add speech-to-text factory validation.
- `src/lerni/explore/qualification.py` to add speech-to-text qualification.
- `src/lerni/explore/ui.py` to add the qualified microphone component.
- `src/lerni/explore/launch.py` to configure the managed temporary-audio root before microphone use.
- `tests/explore/test_plugin_loader.py` and `tests/explore/test_qualification.py` with speech-to-text cases.

Do not add a specific speech-recognition dependency to the normative plan. The selected environment may install a plugin package separately.

## Speech-to-text contract

Add to `contracts.py`:

```python
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    language: str


class SpeechToTextError(RuntimeError):
    pass


class SpeechToTextBackend(Protocol):
    def status(self) -> CapabilityStatus:
        ...

    def transcribe(
        self,
        recording: Path,
        *,
        call_scope: CapabilityCallScope | None = None,
        call_registry: CapabilityCallRegistry | None = None,
    ) -> Transcript:
        ...


class SpeechToTextPlugin(Protocol):
    def status(self) -> PluginStatusPayload:
        ...

    def transcribe(self, recording: Path) -> Transcript:
        ...
```

Rules:

- `recording` is an absolute path to an application-created quarantine copy within the managed audio root;
- parent-process backend has a finite timeout and accepts null scope/registry only for synthetic qualification; child transcription requires both;
- adapter returns complete text, not a stream;
- adapter returns a canonical BCP-47 language in its qualified `supported_languages`;
- adapter does not delete or move the file;
- the application interface does not pass lesson state, telemetry, tutor, runtime profile, or credentials;
- logging/retention/routing are explicit plugin/operator declarations and cannot be proven solely by the interface;
- adapter maps implementation errors to `SpeechToTextError` without sensitive detail;
- adapter status declares local/external routing in its human-readable operator metadata, but that routing is not persisted in child telemetry.

Speech audio reaches the selected STT capability before transcript sanitization can inspect it. Therefore an external route may receive names, voices, locations, or other identifying speech; supervision and a reviewed route/retention decision are mandatory, and the app must never imply that transcript redaction protected the submitted audio.

## Unavailable fallback

```python
class UnavailableSpeechToText:
    def status(self) -> CapabilityStatus:
        return CapabilityStatus(
            availability=CapabilityAvailability.UNAVAILABLE,
            adapter_id="unavailable",
            reason="No speech-to-text capability was qualified.",
            fallback="Type your response instead.",
            metadata=UNAVAILABLE_CAPABILITY_METADATA,
        )

    def transcribe(
        self,
        recording: Path,
        *,
        call_scope: CapabilityCallScope | None = None,
        call_registry: CapabilityCallRegistry | None = None,
    ) -> Transcript:
        raise CapabilityUnavailableError(
            "Speech-to-text is unavailable."
        )
```

The microphone is disabled when this capability is selected.

## Plugin loading

Extend the standard-library loader created by the tutor plan. It runs only inside the helper process.

```python
def load_factory(import_reference: str) -> Callable[..., object]:
    ...


def load_speech_to_text(
    import_reference: str,
    *,
    settings: Mapping[str, str],
) -> SpeechToTextPlugin:
    ...
```

Import-reference grammar:

```text
python.module.path:factory_name
```

Validation:

- one colon;
- valid dotted module and identifier;
- no relative import;
- factory callable;
- returned object has callable `status` and `transcribe`;
- status call succeeds without transcribing;
- settings contain no values whose keys match secret/key/token/password patterns;
- import/factory errors map to a sanitized qualification failure.

PR-07 implements `ProcessSpeechToTextBackend` in `speech_to_text_process.py` by composing PR-03's generic `ProcessCapabilityClient`; earlier PRs never import this later-owned contract. The application parent validates only the import-reference syntax and constructs that typed adapter; status, qualification probes, and transcription all use the versioned bounded wire protocol. The loader is not a sandbox. Plugins are fully trusted code; only operator-approved plugins may be configured. Raw plugin objects never cross into the parent process.

Use the same pattern for tutor plugins, but keep tutor and STT settings separate.

## Environment qualification

Extend `qualification.py`.

```python
def qualify_speech_to_text(
    backend: SpeechToTextBackend,
    *,
    probe_recording: Path | None = None,
) -> CapabilityQualification:
    ...
```

Checks:

- status contract;
- finite operator-configured timeout;
- structured declaration of local/external audio routing;
- explicit retention and logging declarations;
- no secret exposed in status;
- helper-process deadline terminates a hung probe;
- controlled probe returns bounded text;
- operational metadata includes the active lesson locale and probe transcript returns that canonical language;
- missing/empty/malformed output becomes typed failure;
- application remains usable after failure.

Do not run a real microphone probe automatically. It requires an explicit operator action.

Before the first child audio session, the parent reviews the qualification notice and confirms the selected routing/retention tradeoff.

Microphone authorization is a server-side per-session-epoch boolean, default false and cleared on Reset/Stop/Delete/wipe. A token-guarded parent action may set it true only after displaying the exact qualified route/retention notice. The browser control/permission request remains disabled until then, and every upload/transcription callback rechecks the flag under the session lock before accepting bytes. A direct disabled/stale upload is never transcribed and may unlink only its verified managed framework entry; cleanup failure disables audio and alerts the parent.

PR-07 implements this through `ExploreSessionPort.set_microphone_enabled(state, enabled, parent_token)` and the authoritative `UiSessionState.microphone_enabled` field. The Gradio adapter first resolves the opaque binding/CSRF/framework session, then calls the port; it never mutates a browser boolean into authority.

## Managed recording root

The parsed runtime profile derives the absolute private directory:

```text
runtime.root/audio-temp/
```

Requirements:

- owner-only access where the platform supports permissions;
- no symlink;
- not inside repository;
- not inside telemetry/export directories;
- created before Gradio microphone component is enabled;
- contains separate pinned `framework/` and `quarantine/` children;
- is configured through the qualified Gradio version’s supported temp-root setting (environment or API, set before framework import/server construction) so microphone uploads land only in `framework/`.

If the qualified Gradio version cannot ensure microphone files land inside the managed root, disable microphone input for this milestone. Do not delete arbitrary framework paths.

Qualification must also prove that every microphone upload route exposes and enforces exact localhost Host/Origin before accepting bytes, is microphone-only in the UI, and is bounded to `maximum_bytes` before any server-side media decode/conversion. Direct pre-admission, missing/mismatched Host/Origin, malformed, and limit-plus-one HTTP fixtures must not invoke a converter/callback or leave a file. If Gradio hides request metadata or preprocesses attacker-supplied media before those controls, microphone input is blocked and the implementation must switch to a separately reviewed capture boundary rather than weakening this requirement.

## Recording lifecycle

Implement in `recordings.py`.

```python
@dataclass(frozen=True, slots=True)
class AudioLimits:
    minimum_seconds: float = 0.25
    maximum_seconds: float = 30.0
    maximum_bytes: int = 10_000_000
    minimum_sample_rate: int = 8_000
    maximum_sample_rate: int = 48_000
    maximum_channels: int = 2


@dataclass(frozen=True, slots=True)
class CleanupReport:
    removed: tuple[Path, ...]
    failed: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class QuarantinedRecording:
    path: Path
    inode: int
    session_id: UUID
    session_epoch: UUID


@contextmanager
def quarantine_recording(
    framework_path: Path,
    *,
    root: Path,
    session_id: UUID,
    session_epoch: UUID,
    limits: AudioLimits = AudioLimits(),
) -> Iterator[QuarantinedRecording]:
    ...


def validate_wav(
    recording: QuarantinedRecording,
    capability: CapabilityMetadata,
    limits: AudioLimits = AudioLimits(),
) -> None:
    ...


def purge_recordings(root: Path) -> CleanupReport:
    ...
```

`quarantine_recording`:

1. Open/pin the managed root directory and untrusted framework file with no-follow semantics where available.
2. `fstat` the opened source; require regular file, owner-only mode, one link, and size within limit. Confirm its directory entry is beneath the managed framework root.
3. Create a random application-owned quarantine file with `O_CREAT|O_EXCL`, `0600`, and one link under a pinned `audio-temp/quarantine` directory.
4. Copy at most `maximum_bytes + 1` from the already-open source descriptor; never reopen the source pathname.
5. Flush/fsync, reopen/read through the quarantine descriptor, and validate WAV from that same pinned inode.
6. Close/remove the framework source through its pinned directory descriptor.
7. Make the quarantine copy read-only where supported, record inode/device/link count, and yield only its path plus session ID/epoch.
8. Immediately before and after STT, re-stat and require the same regular one-link inode/device/size.
9. In `finally`, unlink both known entries through pinned directory descriptors and verify absence.
10. If any cleanup/inode check fails, raise a sanitized cleanup error, discard transcript, and disable microphone.

Never unlink a path outside the managed root.

This closes normal framework path-swap/hardlink races. It is not protection against malicious code running as the same OS user or a trusted plugin that deliberately tampers with files.

`validate_wav` uses the standard-library `wave` module over the pinned quarantine file object:

- file size within limit;
- valid WAV container;
- frames greater than zero;
- duration within bounds;
- sample rate within bounds;
- channels within bounds;
- sample width in `capability.supported_sample_width_bytes`;
- sample rate and channels within both application limits and capability metadata.

No metadata is persisted.

Startup, while holding the exclusive runtime lock:

- securely empty `framework/` and `quarantine/` without following links, because no prior process may still own a recording;
- reject unexpected directory types/hardlinks and surface failures to the parent;
- verify both children are empty before enabling microphone;
- disable microphone if cleanup integrity or the framework temp-root setting cannot be established.

Reset, Stop, session end, retention/session deletion, and managed family-data wipe also remove every known recording for the affected scope. No age threshold is used for crash leftovers.

The callback clears the microphone component as soon as the managed server copy is acquired. Lerni cannot prove erasure of a browser/OS capture buffer, cache, permission history, or external STT copy; the parent runbook requires closing the dedicated browser profile/session and handles provider deletion/expiry separately. Session deletion and managed family-data wipe report external STT audio as an unmanaged residual and claim only verified local cleanup; v1 has no provider-deletion receipt.

## Audio presenter

Implement in `audio_presenter.py`.

```python
@dataclass(frozen=True, slots=True)
class AudioUiResult:
    state: UiSessionState
    transcript_text: str | None
    microphone_notice: str
    microphone_enabled: bool
    auto_submit: bool = False


def process_recording(
    state: UiSessionState,
    path_value: str | None,
    *,
    stt: SpeechToTextBackend,
    audio_root: Path,
    policy_limits: PolicyLimits,
    active_epoch: Callable[[UUID], UUID | None],
    lesson_locale: str,
    call_registry: CapabilityCallRegistry,
    limits: AudioLimits = AudioLimits(),
) -> AudioUiResult:
    ...
```

`process_recording` is an internal application helper, never a Gradio callback. It receives authoritative server-only `UiSessionState` and derives scope from `state.session_id/state.session_epoch`. The PR-07 `ExploreSessionPort.transcribe_recording(state, path_value)` implementation supplies every backend/root/limit/locale/registry dependency from server configuration, invokes this helper, and commits the server-only `AudioUiResult.state` to the registry. `AudioUiResult` is never serialized to a browser; browser outputs contain only the existing opaque handle/revision plus transcript preview/notices, never a session UUID or epoch.

Flow:

1. `None`: return “No recording received”; typed input remains.
2. Check capability status.
3. Require `state.microphone_enabled` and an active freeform phase, then enter `quarantine_recording` bound to the server state's session ID/epoch.
4. Validate the pinned quarantine WAV.
5. Construct the typed STT request only from the validated pinned recording descriptor/hash plus server-owned `lesson_locale`, then call STT once with `CapabilityCallScope(state.session_id, state.session_epoch)` and the shared registry; the process backend performs race-safe registration. Ignore browser filename, MIME, locale, claimed duration/rate/channels, and all other client metadata.
6. Fully materialize transcript.
7. Reject empty, text longer than `policy_limits.max_input_chars`, missing/malformed language, language outside qualified metadata, or language unequal to `lesson_locale`.
8. Exit context and delete source/quarantine entries.
9. Recheck `active_epoch(state.session_id) == state.session_epoch`; stale/terminal callbacks return no transcript and clear any browser/server preview.
10. Only after verified cleanup/current epoch, return transcript text.
11. Set `auto_submit=False`.

If validation, transcription, or cleanup fails:

- no transcript is returned;
- typed input remains enabled;
- child sees short fallback;
- parent sees sanitized category;
- raw exception and path are not shown or stored.

The transcript is placed in the existing editable text field. Sending it invokes:

```python
ExploreSessionPort.submit_text(
    state,
    edited_transcript,
    InputSource.TRANSCRIPT,
)
```

No special policy bypass exists for speech.

Stop, Reset, Delete, managed family-data wipe, and process shutdown cancel every registered audio helper for the old epoch and clear transcript values in browser/server state. Send and explicit Discard also clear the preview after copying the edited value into the normal typed submission call.

## Gradio microphone contract

Use the qualified API to provide:

- microphone recording only;
- WAV output;
- non-streaming recording;
- no upload-from-files option;
- no editing that creates unmanaged copies;
- parent-token enable/disable action with server-side per-epoch enforcement; capability availability alone never enables capture;
- Stop Recording event bound only to the Gradio adapter that resolves the opaque binding and calls `ExploreSessionPort.transcribe_recording`;
- microphone control disabled when STT unavailable;
- microphone and transcript Send disabled during deterministic `CHECK`/`HINT` phases;
- transcript output bound to the existing textbox;
- parent-visible microphone status.

Recording completion never triggers Send.

PR-07 also modifies `CapabilityBundle`, bootstrap, and readiness to add `speech_to_text: SpeechToTextBackend`, qualification status, process codec, and the stable typed-input fallback trace. PR-06 contains no STT field/import.

The child/parent must be able to:

1. review transcript;
2. correct it;
3. discard it;
4. submit it;
5. switch to typing.

## Task 1 — Plugin loader TDD

Extend the installed temporary fixture-plugin package from PR-03; isolated workers do not import the repository `tests` package.

Tests:

- valid factory loads;
- relative/malformed reference rejected;
- missing factory rejected;
- non-callable factory rejected;
- wrong object contract rejected;
- secret-like setting key rejected;
- plugin exception maps to sanitized error;
- unavailable plugin leaves typed fallback.

Red:

```bash
"$PYTHON" -m pytest tests/explore/test_plugin_loader.py -q
```

Green:

- implement only import/contract logic;
- no third-party import.

## Task 2 — Qualification TDD

Tests:

- unavailable backend fails with fallback;
- status cannot expose secret canary;
- unknown routing/retention/logging fails qualification and leaves microphone disabled;
- controlled probe success qualifies;
- timeout/empty/malformed probe fails;
- missing/unsupported/mismatched language metadata fails;
- qualification does not persist transcript;
- no probe runs unless explicitly requested.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_qualification.py -q
```

## Task 3 — Recording lifecycle TDD

Generate minimal WAV files in tests with `wave`; do not check in a voice recording.

Tests:

- valid generated WAV passes;
- too short/long/large fails;
- invalid container fails;
- excessive channels/rate fails;
- file exists while fake STT executes;
- file absent after success;
- file absent after STT exception;
- file absent after empty transcript;
- file absent after validation failure;
- outside-root path rejected and not deleted;
- symlink rejected;
- source hardlink rejected;
- source-path swap after open cannot alter copied bytes;
- quarantine inode/link replacement before/after STT is rejected;
- cleanup failure discards transcript;
- startup crash recovery empties only the managed framework/quarantine roots and verifies them before microphone enable.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_recordings.py -q
```

## Task 4 — Audio presenter TDD

Tests:

- `None` recording returns typed fallback;
- unavailable capability disables microphone;
- valid transcript prefills text;
- only exact active lesson locale prefills text;
- transcript does not auto-send;
- transcript over input limit rejected;
- non-default runtime input limit is honored;
- STT receives validated managed path once;
- transcript is not written to telemetry;
- path absent from result/notice;
- cleanup failure returns no transcript;
- subsequent typed input still works.
- late callback after Stop/Reset/Delete returns no transcript and clears preview;
- helper registration is cancelled for terminal epoch;

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_audio_presenter.py -q
```

## Task 5 — UI integration

Tests:

- microphone hidden/disabled when unavailable;
- microphone source is recording-only;
- audio event prefills textbox;
- no callback links audio directly to tutor;
- transcript Send uses `InputSource.TRANSCRIPT`;
- Stop/Reset do not leave managed recording files;
- Send/Discard/Stop/Reset/Delete clear transcript state;
- UI construction does not import a concrete STT plugin.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_ui.py tests/explore/test_audio_presenter.py -q
```

## Manual audio smoke

With parents present and a qualified plugin:

1. Confirm runtime notice states local/external routing and retention status.
2. Deny microphone permission; verify typed path.
3. Grant permission.
4. Record a short non-sensitive phrase.
5. Stop recording.
6. Verify transcript appears but is not sent.
7. Correct one word.
8. Send.
9. Confirm normal safety policy applies.
10. Confirm managed audio directory is empty.
11. Force transcription failure and recheck cleanup.
12. Force cleanup failure; verify transcript is withheld and microphone disables.
13. Confirm telemetry/export contains transcript only after normal sanitized submission and contains no audio/path field.

## Claims and limitations

Allowed:

- Lerni does not intentionally persist audio in its own schema.
- Lerni attempts immediate deletion from its managed recording directory.
- Typed input remains available whenever the lesson permits freeform input; `CHECK`/`HINT` remain authored-choice-only.
- The selected STT adapter’s data route is disclosed to parents.

Do not claim:

- all operating-system/browser/framework temporary copies are erased;
- external adapters retain nothing unless independently verified;
- audio never leaves device unless the selected adapter and browser path prove it;
- speech recognition is accurate;
- a transcript is safe merely because it came from speech;
- cleanup is forensic deletion.

## Completion criteria

- No named STT model/provider is required.
- Plugin selection occurs through qualification.
- Microphone remains optional.
- Recording is bounded and under managed root.
- Deletion is attempted and verified before transcript return.
- Cleanup failure fails closed.
- Transcript is editable and never auto-sent.
- Typed and transcript text share one policy pipeline.
- Telemetry/export schema contains no audio/path.
- Manual audio smoke passes with the selected runtime plugin.
- No commit is made.
