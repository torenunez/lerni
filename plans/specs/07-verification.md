# Explore Safe Slice — Verification and Parent-Supervised Pilot

## Goal

Produce fresh evidence that:

- the implementation matches the plan;
- the new tests proved missing behavior before implementation;
- the Explore slice works with deterministic fallbacks;
- optional tutor and speech adapters satisfy the same contracts;
- the Study CLI remains intact;
- data and audio boundaries behave as designed;
- the first child pilot is parent-supervised and intentionally limited;
- all changes remain uncommitted.

No success claim is permitted without a fresh command or observed pilot result that proves it.

## Verification record

Create an execution log outside child-facing content. Record:

- repository revision and branch at start;
- initial git status;
- command variables from the execution contract;
- Python and dependency versions;
- selected runtime profile with secrets omitted;
- capability qualification outcomes;
- each red test and expected failure;
- each green rerun;
- final commands, exit codes, and failure counts;
- synthetic manual-smoke pass/fail and technical categories only;
- whether the child pilot ran, stopped, or was deferred, without child-specific results;
- known limitations and deferred work;
- final git status and diff summary.

Do not record:

- credentials;
- raw child transcript;
- audio;
- raw blocked/rejected content;
- parent-confidential notes.
- engagement, understanding, wanted-more, delayed-recall, or other child-specific pilot observations outside lifecycle-managed telemetry/parent-state storage.

Child pilot observations are entered only through the parent observation controls under the managed runtime root. Session deletion/retention/family wipe therefore reaches them. A final technical report may state counts/status categories only after sanitization and must not copy the observation text.

## Phase 1 — Baseline before edits

Capture:

```bash
git status --short --branch
git diff --stat
git diff --
"$PYTHON" --version
"$PYTHON" -m pytest -q
```

Record:

- baseline test count;
- baseline failures;
- pre-existing lint/type failures if checked;
- pre-existing user changes.

Do not “fix” unrelated baseline failures without separate authorization. The Explore work may not make them worse.

## Phase 2 — Dependency and packaging qualification

Install the core project and Explore UI profile with the qualified package-manager command. A typical environment may use:

```bash
"$PYTHON" -m pip install -e ".[dev,explore]"
```

This is an example command shape, not a requirement that `pip` or that exact environment is available. Use the qualified equivalent.

Verify imports:

```bash
"$PYTHON" -c "import lerni; import lerni.explore"
```

Build:

```bash
"$PYTHON" -m build
```

If the build frontend is not available, install or select one during environment qualification and record it. Do not skip wheel/source verification while claiming packaged content works.

## Phase 3 — TDD evidence

For every task, retain evidence of:

1. failing test;
2. intended failure reason;
3. minimal implementation;
4. passing focused test;
5. passing containing test file.

A syntax/import error caused by a typo is not an acceptable red test. Fix the test until it fails because the behavior is missing.

A test that passes before implementation does not establish new behavior. Redesign it.

Scaffold importable public symbols first. A missing module or symbol does not count as red evidence for a domain invariant, validation rule, transition, policy, or transaction.

## Claim-to-assertion contract

The execution log maintains one row per normative requirement with: stable requirement ID, plan/file anchor, implementation symbol, exact pytest node ID or manual check ID, fixture/precondition, observable assertion, negative control, result, and evidence path. “Covered by tests,” module import, non-null return, snapshot-only output, or a mock being called is not sufficient unless that is the requirement.

Minimum concrete integration assertions:

- runtime paths: real temporary private root; assert missing root is not created, children are mode-private where supported, and symlink replacement fails before any store opens;
- capability process: real spawned child; assert exact wire bytes/schema/ID, timeout termination and join, descriptor closure, bounded frames, metadata hash drift rejection, and sanitized stderr/result;
- readiness: exact report digest recomputed independently; a maintenance-performing `--print-readiness` and following unchanged launch match; monkeypatch launch/child-Start and assert both call counts remain zero for missing/stale acknowledgement or landing-time drift;
- package/content: install each built artifact into a clean environment and compare resource bytes/hashes to the approved index, not merely successful import;
- policy: parameterize every golden phrase/regex and one adjacent benign counterexample; assert exact action/reason/storage marker and fake tutor call count;
- output grounding: pass an untrusted draft through the complete service and assert rejected canary absent from return value, telemetry rows, exports, captured logs, and app temp/cache paths;
- telemetry schema: inspect `sqlite_master`, `PRAGMA table_info`, foreign keys, and real cascade results; schema-column absence alone does not prove value absence;
- deletion: inject a failure after each cross-store step; reopen real SQLite files and assert either retryable excess telemetry or complete cleanup, never dangling parent evidence; inspect DB/WAL/SHM/export/audio paths;
- UI concurrency: controlled barriers force tutor/stop, reset/delete, and assignment-adoption races; assert epoch/lock behavior and exact final rows, not timing sleeps;
- assignment saga: real separate telemetry/parent SQLite files; crash-point fixtures cover every state transition, replay, resume, adoption acknowledgement, and terminal mapping;
- CSV/import: byte fixtures cover BOM/newline/quoting/formula/hash variants; independently recompute row, manifest, compiled lesson, and package hashes;
- graph/recommendation: construct a minimal real approved graph with decoy ineligible nodes; assert exact ordered candidate IDs/evidence IDs and persisted reconstruction after active-batch change;
- managed wipe: create every registered DB `-wal`/`-shm`/`-journal`, export/audio/private-curation artifact and preservation canaries in profile/generic package/setup records; assert registered family-data paths are absent, only expected canaries remain, tokens are invalid, and incomplete unlink reports failure.

Property claims that the interface cannot prove—external retention, network isolation, complete PII detection, storage-media erasure, browser speech routing, or educational efficacy—must remain labeled declarations, limitations, or manual observations. A passing adapter/plugin self-report may not be promoted to a mechanically verified claim.

## Phase 4 — Automated test order

Run in this order so failures are localized.

### Runtime profile and bootstrap

```bash
"$PYTHON" -m pytest tests/explore/test_runtime_config.py -q
"$PYTHON" -m pytest tests/explore/test_capability_runner.py -q
"$PYTHON" -m pytest tests/explore/test_readiness.py -q
"$PYTHON" -m pytest tests/explore/test_bootstrap.py -q
```

### Lesson core

```bash
"$PYTHON" -m pytest tests/explore/test_domain.py -q
"$PYTHON" -m pytest tests/explore/test_catalog.py -q
"$PYTHON" -m pytest tests/explore/test_chain_1_content.py -q
"$PYTHON" -m pytest tests/explore/test_engine.py -q
"$PYTHON" -m pytest tests/explore/test_distribution.py -q
```

### Safety and tutor boundary

```bash
"$PYTHON" -m pytest tests/explore/test_contracts.py -q
"$PYTHON" -m pytest tests/explore/test_plugin_loader.py -q
"$PYTHON" -m pytest tests/explore/test_qualification.py -q
"$PYTHON" -m pytest tests/explore/test_sanitization.py -q
"$PYTHON" -m pytest tests/explore/test_input_policy.py -q
"$PYTHON" -m pytest tests/explore/test_output_policy.py -q
"$PYTHON" -m pytest tests/explore/test_grounding.py -q
"$PYTHON" -m pytest tests/explore/test_tutor_service.py -q
"$PYTHON" -m pytest tests/explore/test_policy_golden.py -q
```

### Telemetry

```bash
"$PYTHON" -m pytest tests/explore/test_telemetry_schema.py -q
"$PYTHON" -m pytest tests/explore/test_telemetry_store.py -q
"$PYTHON" -m pytest tests/explore/test_retention.py -q
"$PYTHON" -m pytest tests/explore/test_export.py -q
"$PYTHON" -m pytest tests/explore/test_data_lifecycle.py -q
"$PYTHON" -m pytest tests/explore/test_safety_telemetry_integration.py -q
```

### Gradio and read-aloud

```bash
"$PYTHON" -m pytest tests/explore/test_presenter.py -q
"$PYTHON" -m pytest tests/explore/test_visuals.py -q
"$PYTHON" -m pytest tests/explore/test_speech_browser.py -q
"$PYTHON" -m pytest tests/explore/test_ui.py -q
"$PYTHON" -m pytest tests/explore/test_launch.py -q
```

### Push-to-talk

```bash
"$PYTHON" -m pytest tests/explore/test_plugin_loader.py -q
"$PYTHON" -m pytest tests/explore/test_qualification.py -q
"$PYTHON" -m pytest tests/explore/test_recordings.py -q
"$PYTHON" -m pytest tests/explore/test_audio_presenter.py -q
```

### Curation and graph integration, when implemented

This is a second verification pass after the first-slice pilot gate, not a prerequisite for that pilot.

```bash
"$PYTHON" -m pytest tests/explore/test_curation_csv.py -q
"$PYTHON" -m pytest tests/explore/test_curation_validation.py -q
"$PYTHON" -m pytest tests/explore/test_curriculum_store.py -q
"$PYTHON" -m pytest tests/explore/test_curriculum_graph.py -q
"$PYTHON" -m pytest tests/explore/test_content_compile.py -q
"$PYTHON" -m pytest tests/explore/test_recommendations.py -q
"$PYTHON" -m pytest tests/explore/test_observation_export.py -q
"$PYTHON" -m pytest tests/explore/test_parent_state_schema.py -q
"$PYTHON" -m pytest tests/explore/test_observation_aggregation.py -q
"$PYTHON" -m pytest tests/explore/test_assignments.py -q
"$PYTHON" -m pytest tests/explore/test_data_lifecycle.py -q
```

After plan 08b, repeat the manual UI fixture and assert that recommendation controls appear only with a fully initialized service, Start/Resume adoption is acknowledged before interaction, every assigned terminal state is reconciled, session deletion removes derived parent evidence/candidates/assignments before telemetry, and managed wipe removes parent-state/curriculum sidecars plus private curation.

### Explore suite and full regression

```bash
"$PYTHON" -m pytest tests/explore -q
"$PYTHON" -m pytest -q
```

The full suite must include and preserve existing SM-2 tests.

## Phase 5 — Static quality

Using qualified tools:

```bash
"$PYTHON" -m ruff check src/lerni/explore tests/explore
"$PYTHON" -m mypy --strict src/lerni/explore
```

Then run full-project checks:

```bash
"$PYTHON" -m ruff check src tests
"$PYTHON" -m mypy src/lerni
```

Distinguish:

- failures introduced by Explore;
- pre-existing failures;
- environment/tool-version incompatibilities.

Fix introduced failures. Do not claim the full project is clean when only the Explore subset passes.

If a project-declared static tool is unavailable, install the declared development profile or record technical verification as incomplete. Do not silently convert a required check into a skip.

## Phase 6 — Distribution verification

For wheel and source distribution separately:

1. Create a clean temporary Python environment.
2. Install the artifact.
3. Import `lerni.explore`.
4. Load the approved Chain-1 TOML through `importlib.resources`.
5. Read the SVG.
6. Build the Gradio app with manual fallbacks.
7. Confirm no source-checkout path is required.

Expected:

- lesson and visual are present;
- Study command entry point remains present;
- Explore entry point is present;
- optional tutor/STT plugins are not imported during core import.

## Phase 7 — Security and privacy boundary checks

Use unique canaries.

### Input canaries

- explicit name;
- email;
- phone;
- address/school;
- credential-like string;
- URL;
- serious-distress phrase;
- out-of-scope request;
- request to keep a secret;
- prompt-injection-style request to ignore lesson rules.

Verify:

- non-allowed input does not reach tutor;
- raw value does not appear in SQLite;
- raw value does not appear in JSON export;
- fixed safe response is shown;
- policy category is recorded.

### Output canaries

Configure fake tutor drafts with:

- unsupported number;
- unknown fact citation;
- URL/contact detail;
- every bounded secrecy/relationship/dependency/coercion/personal-data-solicitation/meeting fixture;
- too many sentences;
- overlong output;
- exception detail;
- script/HTML content.

Verify:

- raw draft does not reach display;
- raw draft does not persist;
- authored fallback appears;
- child sees no stack trace or adapter name.

### Audio canaries

- valid short WAV;
- too short;
- too long;
- invalid container;
- file outside root;
- symlink;
- STT exception;
- empty transcript;
- cleanup failure.

Verify:

- no unsafe delete;
- no audio/path in telemetry/export;
- cleanup attempted;
- cleanup failure withholds transcript and disables microphone;
- typed path remains.

## Phase 8 — Study regression smoke

Run:

```bash
"$PYTHON" -m lerni --help
study --help
study list
study today
```

Use a temporary or explicitly safe Study data directory if commands would touch personal data.

Verify:

- command names and help still work;
- core install does not require Explore extras;
- no Study schema migration occurred;
- existing Study data is not read by Explore tests;
- Explore entry point does not replace the `study` entry point.

## Phase 9 — Manual deterministic UI smoke

Launch with:

- manual tutor;
- speech-to-text unavailable;
- read-aloud off;
- temporary Explore telemetry database.

Verify:

1. Missing/stale readiness acknowledgement opens no browser/server; exact acknowledgement shows the same digest/fallback IDs in parent UI.
2. Localhost-only URL.
3. No public/share URL.
4. Supervision notice visible.
5. Curated SVG visible with accessible text.
6. Continue moves intro to teach.
7. Continue moves teach to check.
8. Wrong answer shows first hint.
9. Another wrong answer shows next hint/reveal according to engine.
10. Correct answer completes.
11. Typed question uses fallback safely.
12. Parent observation saves.
13. JSON export contains sanitized data.
14. Delete removes the telemetry session cascade and matching generated exports.
15. Reset starts a new session and stops the prior telemetry session.
16. Read-aloud unsupported/disabled does not remove text.
17. Wrong/missing parent token blocks observation, export, reset, delete, and wipe.
18. Generated HTML/Markdown canary appears only as escaped text.
19. Late tutor callback after Stop, Reset, or Delete is discarded.
20. Framework cache/log/temp inspection contains no raw input canary.
21. Managed-wipe dry fixture removes every currently registered family-data path, preserves profile/generic package/setup records, invalidates parent/admission tokens, and exits.

If framework data-handling qualification cannot bound raw text persistence, stop the child pilot and report the exact boundary.

## Phase 10 — Qualified generated-tutor smoke

Do not use child input yet.

With the selected tutor and mandatory additional-safety plugins:

1. Review both adapter qualification/decision reports.
2. Confirm parents understand local/external routing and retention status.
3. Send a fixed synthetic in-scope request.
4. Confirm complete structured draft.
5. Confirm citations refer only to current facts.
6. Confirm output gate accepts a valid draft.
7. Force an unsupported number and confirm fallback.
8. Force timeout/failure and confirm fallback.
9. Confirm lesson phase does not change.
10. Run the reviewed benign/harmful input/output safety probes and require every expected result.
11. Confirm a harm-gate failure blocks/circuit-breaks generation.
12. Confirm status/errors expose no secret.

The `generated_tutor` eligibility level is ready only after both real capabilities pass. Otherwise use authored fallback and do not label the session an LLM interaction.

## Phase 11 — Read-aloud smoke

1. Read-aloud starts off.
2. Enable it.
3. Continue lesson; hear only final displayed text.
4. Repeat.
5. Stop speech.
6. Reset while speech is active; speech stops.
7. Simulate unsupported browser capability; text remains.
8. Confirm no named voice assumption.

Do not claim browser speech stays local unless independently verified for the actual browser/OS.

## Phase 12 — Push-to-talk smoke

Follow the audio plan’s manual sequence.

Before child use:

- parents review routing/retention notice;
- microphone permission is explicit;
- managed audio directory is empty;
- typed input works.

After success and forced failure:

- managed directory is empty;
- no audio/path is in database/export;
- transcript requires review and Send.

## Phase 13 — Parent-supervised child pilot

### Preconditions

- both parents consent;
- one parent remains present and can stop immediately;
- lesson status is approved with actual required science, child-content, visual-accessibility, and parent attestations;
- the exact selected eligibility level is recorded: `authored_typed`, `generated_tutor`, or `generated_tutor_voice_input`, with browser read-aloud status recorded separately;
- real tutor plus mandatory safety reports are reviewed for `generated_tutor`; real STT/media reports are additionally reviewed for `generated_tutor_voice_input`;
- pre-browser readiness digest and every fallback trace are reviewed and acknowledged for this launch;
- local telemetry retention is configured;
- export/delete controls were smoke-tested;
- no public/share URL exists;
- the per-launch parent token is available to the supervising parent and absent from URL, logs, profile, and browser storage;
- no unrelated personal data is visible on the device;
- child can use typed/choice fallback if audio fails.

### Parent briefing

Explain:

- this is a prototype, not a friend or companion;
- do not enter names, address, school, contact details, or secrets;
- stop if anything feels wrong;
- the parent may interrupt or end the activity;
- speech/text may be processed by the selected adapter according to the reviewed runtime notice;
- voice reaches STT before transcript redaction and may contain identifying speech;
- local sanitized records can be reviewed and deleted.

### Pilot flow

1. Parent starts session.
2. Child sees the acceleration visual.
3. Child explores the authored hook.
4. If desired and qualified, child uses push-to-talk.
5. Parent/child reviews transcript before Send.
6. Child completes explicit retrieval check.
7. Parent stops when curiosity drops; do not extend for a target duration.
8. Parent records structured observation.
9. Parent reviews local session record.
10. Parent deletes or retains under configured policy.

### Immediate observation

Record:

- completed: yes/no;
- hints used;
- engagement 1–5;
- understanding: not observed/not yet/partial/clear;
- wanted more: yes/no/unknown;
- sanitized note;
- guardrail or capability failures.

Do not use session duration as success or ranking input.

### Delayed recall

At a parent-selected later date, outside the app if preferred, ask a simple question:

> Two cars both go from 0 to 60. One takes less time. Which has greater average acceleration, and why?

Record:

- not observed;
- not yet;
- partial;
- clear.

If retaining this result in Lerni, use the token-guarded historical session selector to append a follow-up observation; never place the answer text itself in telemetry. A parent may instead keep no app record.

Do not infer permanent learning from one answer.

## Phase 14 — Requirements audit

Re-read each subplan and map every requirement to:

- implementation file;
- test or manual check;
- current result;
- deferred status if explicitly out of scope.

Unmapped requirements are gaps, even if tests pass.

## Phase 15 — Git and no-commit audit

Run:

```bash
git status --short --branch
git diff --stat
git diff --
git log -1 --oneline
```

Compare with baseline.

Verify:

- pre-existing `.claude/` and documentation changes remain;
- no unrelated file changed;
- no credential, environment file, runtime database, audio, export, or content-sheet private copy is tracked;
- no commit was created;
- no push occurred.

## Final reporting format

Report:

- implemented milestones;
- exact verification commands and results;
- test count and failures;
- capability qualification status;
- child pilot not run / run with observations;
- known residual risks;
- deferred graph/curation work;
- working-tree summary;
- explicit “no commit created.”

Do not say “safe,” “complete,” “production-ready,” or “validated learning” without qualification.

## Completion criteria

The first slice is technically complete only when:

- all requirements are mapped;
- Explore and full regression tests pass or pre-existing failures are precisely reported;
- introduced lint/type errors are zero;
- installed distribution loads content;
- deterministic/manual UI works;
- authored fallback always passes; any claimed LLM eligibility has real tutor and mandatory safety contracts passing;
- read-aloud fallback works;
- a real selected STT contract, framework upload boundary, and cleanup smoke pass before voice-input use;
- privacy canaries stay out of forbidden boundaries;
- parent export/delete work;
- readiness gate and managed local family-data wipe work with documented residue limits;
- Study remains intact;
- final diff is reviewed;
- no commit exists.

The child pilot is a separate evidence event. Technical completion does not imply educational efficacy or broad-release readiness.
