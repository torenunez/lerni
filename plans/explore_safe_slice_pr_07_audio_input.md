# PR-07 — Push-to-Talk Speech Input

## Goal

Add parent-enabled microphone capture, strict managed WAV validation, replaceable speech-to-text through the capability subprocess, editable transcript preview, and cleanup on every branch. Typed input remains the universal fallback whenever the lesson permits freeform input.

## Depends on

- PR-03 process/credential boundary.
- PR-04 policy/tutor pipeline.
- PR-05 lifecycle/audio-temp management.
- PR-06 Gradio presenter/UI.

## Normative plans

- [Push-to-talk audio](./explore_safe_slice_06_audio_input.md)
- [Manual account/credential setup](./explore_safe_slice_manual_setup.md)

## Files

Create:

- `src/lerni/explore/recordings.py`
- `src/lerni/explore/audio_presenter.py`
- `src/lerni/explore/speech_to_text_process.py`
- `tests/explore/test_recordings.py`
- `tests/explore/test_audio_presenter.py`

Extend:

- `contracts.py`
- `plugin_loader.py`
- `qualification.py`
- `capability_worker.py` codecs/operations
- `bootstrap.py` and `readiness.py`
- `presenter.py`
- `ui.py`
- related tests

No named STT SDK/model is added to core dependencies.

## Manual prerequisites

- [ ] Decide typed-only, local STT, or external STT.
- [ ] For external STT, review child-voice terms, route, retention, logging/training, account, quota, key, and revocation.
- [ ] Parents explicitly acknowledge that raw voice reaches STT before transcript redaction and may contain identifying speech.
- [ ] For local STT, preinstall/verify package and speech artifacts/licenses and observe network behavior.
- [ ] Parents review qualification notice and both consent to the selected audio route.
- [ ] Browser microphone permission is available for the local origin.

Audio remains disabled if any prerequisite is unresolved.

## Environment-specific capability realization

The generic STT path can complete with fakes and typed fallback, but that does not deliver voice input. Before PR-08 can report `generated_tutor_voice_input`, the implementation environment must install a reviewed compatible STT plugin distribution or implement one in a separate provider-specific adapter change/package. Keep its SDK/model/artifact dependencies outside core, build a non-editable recorded artifact, qualify real route/media metadata with synthetic WAV only, and keep any explicit live probe child-data-free.

## Implementation tasks

- [ ] Add exact `Transcript` and `SpeechToTextBackend` contracts.
- [ ] Add child-process-only STT loader and process wrapper operation.
- [ ] Qualify complete media/sample metadata and optional synthetic probe.
- [ ] Configure the qualified Gradio temp root before framework import/server construction; require uploads under pinned `audio-temp/framework/`.
- [ ] Under the exclusive runtime lock, empty and verify managed framework/quarantine roots at startup; disable microphone on any integrity/cleanup failure.
- [ ] Open the framework source once with no-follow semantics, reject non-regular/multi-link input, and copy bounded bytes into an application-created `0600` quarantine file.
- [ ] Pin/recheck quarantine inode/link/size and unlink through pinned directory descriptors.
- [ ] Parse the pinned quarantine WAV with standard library and enforce container, PCM, channels, sample width/rate, frame consistency, and duration/size limits.
- [ ] Intersect application limits with qualified adapter metadata.
- [ ] Invoke STT only after validation and before deadline.
- [ ] Normalize transcript, enforce max input chars, and withhold on malformed/overlong output.
- [ ] Require qualified BCP-47 language matching the active lesson locale.
- [ ] Put transcript into editable preview; never auto-send.
- [ ] Default microphone authorization off; require a token-guarded per-epoch parent enable action after the exact route/retention notice and recheck it in every callback.
- [ ] Route edited Send through the exact typed policy/tutor pipeline.
- [ ] Delete recording in `finally`; cleanup failure withholds transcript, disables microphone, and alerts parent.
- [ ] Bind audio/helper to session epoch; terminal actions cancel it and stale callbacks cannot refill preview.
- [ ] Store no audio path/bytes/metadata.
- [ ] Populate readiness v1's existing speech-to-text qualification/decision collection entry plus exact `typed-input-v1` fallback trace; add no new readiness field.

## Required concrete tests

- Valid boundary WAVs pass; short/long/truncated/compressed/wrong channel/rate/width fail.
- Outside path, symlink, hardlink, file swap, and non-regular entry fail without unsafe deletion.
- Direct pre-admission/malformed/limit-plus-one upload-route fixtures are rejected before converter/callback execution and leave no file; otherwise microphone mode is ineligible.
- Timeout/crash/exception/empty/malformed/overlong transcript uses typed fallback.
- Cleanup occurs after success and every failure; forced cleanup failure withholds.
- Simulated prior-process crash leftovers are removed before microphone enable; unsupported/ignored framework temp-root configuration leaves typed-only mode.
- Transcript is not sent until explicit Send and then uses the same policy path.
- Audio/path canaries are absent from telemetry/export/logs/readiness.
- UI does not import a concrete STT adapter.
- Available STT alone never enables capture; wrong token, disabled epoch, reset, or stale direct upload cannot invoke STT.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_plugin_loader.py -q
"$PYTHON" -m pytest tests/explore/test_qualification.py -q
"$PYTHON" -m pytest tests/explore/test_recordings.py -q
"$PYTHON" -m pytest tests/explore/test_audio_presenter.py -q
```

## Acceptance

- Typed mode remains usable with STT unavailable.
- Qualified push-to-talk produces only an editable transcript.
- Managed audio directory is empty after success and forced failure.
- No audio data/path enters persistent stores.
- Parents review actual route/retention before child audio.

## Out of scope

- Continuous listening.
- Auto-send.
- Voice cloning or synthesis service.
- Named STT provider/model requirement.
- Commit, push, or PR creation.
