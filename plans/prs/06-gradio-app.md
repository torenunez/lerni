# PR-06 — Local Gradio App, Bootstrap, and Read-Aloud

## Goal

Assemble the first child-facing application: deterministic lesson, safety/tutor fallback, telemetry/lifecycle, curated visual, typed interaction, retrieval choices, optional browser read-aloud, parent controls, and a mandatory pre-browser readiness acknowledgement.

## Depends on

- PR-02 lesson core.
- PR-03 runtime/readiness boundary.
- PR-04 safety/tutor service.
- PR-05 telemetry/lifecycle.

## Normative plans

- [Gradio UI and read-aloud](../specs/05-gradio-ui.md)
- [Runtime bootstrap](../specs/00a-runtime-bootstrap.md)
- [Verification plan](../specs/07-verification.md)

## Files

Create:

- `src/lerni/explore/bootstrap.py`
- `src/lerni/explore/presenter.py`
- `src/lerni/explore/visuals.py`
- `src/lerni/explore/speech_browser.py`
- `src/lerni/explore/framework_qualification.py`
- `src/lerni/explore/ui.py`
- `src/lerni/explore/launch.py`
- `src/lerni/explore/__main__.py`
- presenter/visual/speech/UI/launch/bootstrap tests

Modify `pyproject.toml` for the qualified Explore UI extra, `lerni-explore` entry point, and two-mode package description/keywords/classifiers while preserving the `study` entry point and core dependency boundary.

## Manual prerequisites

- [ ] Qualify a compatible current Gradio version/API.
- [ ] Use a test browser profile for cache/log/temp canaries.
- [ ] Confirm browser speech behavior; do not assume local routing.
- [ ] Complete fallback-only readiness review before first launch.

No hosted Gradio account, tutor account, STT account, or public URL is needed.

## Implementation tasks

- [ ] Add pure presenter/state/result/speech types.
- [ ] Compose lesson, tutor, telemetry, lifecycle, and browser speech into one session service.
- [ ] Implement deterministic start/continue/choice/text/stop/reset/observation/export/delete behavior.
- [ ] Add per-session mutation lock and epoch checks for late callbacks.
- [ ] Load/escape the indexed SVG through the catalog; no upload or remote asset.
- [ ] Implement browser speech detection/command/cancel with read-aloud off, route still declared/unknown, parent-token enablement, and text always retained.
- [ ] Keep Gradio lazily imported; under the runtime lock, securely empty/configure/verify `audio-temp/framework/` as its private temp/cache root before import/server construction.
- [ ] Generate/validate the strict private framework qualification record with artifact/probe/platform hashes and count-only canary results.
- [ ] Expose an operator-only qualification command backed by installed probe code/resources, never a test-directory dependency.
- [ ] Build localhost-only Gradio components and non-streaming callback map.
- [ ] Gate every mutation behind mandatory exact loopback Host/same-origin Origin, one-time parent admission, per-session nonce/epoch, and launch/capability-call budgets; unavailable request metadata blocks child UI qualification.
- [ ] Keep authoritative `UiSessionState` server-side; expose only a random opaque binding handle/revision and bind every callback to handle, CSRF, framework session, and epoch before resolving state.
- [ ] Inject the PR-03 admission guard into app composition; never recreate admission state inside callbacks.
- [ ] Disable share, analytics, flagging, examples, feedback, public API/schema pages, queue persistence, and debug where supported.
- [ ] Render generated/child text through qualified escaped/plain-text components.
- [ ] Add parent-token controls plus exact-phrase managed family-data wipe.
- [ ] Add summary-only historical session selection with later-recall save and exact-ID export/delete.
- [ ] Assemble the first-slice `ApplicationBundle` with no graph/recommendation imports.
- [ ] Resolve fallback trace, print readiness, require exact digest acknowledgement, then construct/launch UI.
- [ ] Recompute readiness read-only before each child Start; landing-time state/file drift invalidates approval and requires restart.
- [ ] Ensure stale/missing acknowledgement never calls Gradio launch.

## Required concrete tests

- Pure callbacks have exact state/history/telemetry/speech results.
- Admission reaches a parent-only start/data-management landing with zero telemetry; only parent-token Start consumes the held grant.
- Forged/stale/replayed browser handles, revisions, framework-session bindings, UUIDs, and state fields fail before any session-port/capability/store call.
- In-flight generation shows only fixed accessible busy text, clears raw input, keeps Stop usable, and never streams plugin progress.
- CHECK/HINT phases expose authored choice/hint controls only; typed/transcript tutor calls are unreachable and cannot reveal or grade the answer.
- Barrier-controlled stop/reset/delete races cancel/reap scoped helpers and discard every stale late tutor result.
- Barrier lock-order test races Delete and managed wipe and proves runtime→mutation→registry→session→single-store order cannot deadlock.
- Qualified live Gradio barrier fixture proves Stop enters while a helper callback is blocked rather than waiting behind the same queue.
- Visual bytes/hash/alt text match approved package resource.
- SVG validation rejects declarations/entities, non-SVG namespaces, non-allowlisted elements/attributes, and event/style/URL/image/use content.
- Unsupported speech leaves visible text and emits no failing action.
- Launch rejects non-loopback/share and stale readiness approval.
- Parent token never enters URL, browser storage, logs, or component value after verification.
- Historical summaries contain no turn/note text and support restart-safe follow-up recall without accepting a path.
- Prior-launch active sessions block new Start until token-confirmed abandonment; current-launch active sessions cannot be bulk-abandoned.
- Generated markup canary renders inert.
- Framework canary inspection finds no raw input in configured logs/cache/temp; otherwise child pilot is blocked.
- Browser/server network canary shows no non-loopback framework asset/analytics/telemetry/update/callback request with browser speech and external plugins off.
- Unsupported temp-root configuration or an uncleanable prior framework temp entry blocks child launch.
- Fallback-only complete app starts after acknowledgement.
- A pre-PR-07 profile that enables speech-to-text fails bootstrap as unsupported rather than changing readiness or being ignored.
- Base bootstrap/UI has no curriculum/recommendation module imports or controls.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_bootstrap.py -q
"$PYTHON" -m pytest tests/explore/test_presenter.py -q
"$PYTHON" -m pytest tests/explore/test_visuals.py -q
"$PYTHON" -m pytest tests/explore/test_speech_browser.py -q
"$PYTHON" -m pytest tests/explore/test_ui.py -q
"$PYTHON" -m pytest tests/explore/test_launch.py -q
```

## Acceptance

- Exact readiness acknowledgement occurs before browser/server launch.
- Local fallback-only lesson completes through choices.
- Typed questions use safe authored fallback.
- Parent can observe/export/delete/reset/wipe synthetic data.
- No public/share path or child upload exists.
- Study entry point remains present and core install need not include Gradio.
- Installed `lerni-explore` and `"$PYTHON" -m lerni.explore.launch` reach the same strict launcher.

## Out of scope

- Microphone/STT.
- Curriculum graph/recommendations/placeholders.
- Public deployment.
- Child pilot before PR-08 gate.
- Commit, push, or PR creation.
