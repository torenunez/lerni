# PR-08 — First-Slice Integration and Pilot Gate

## Goal

Close first-slice integration gaps, prove distribution/privacy/regression behavior with concrete assertions, and publish an operator runbook for a separate parent-supervised pilot. The child pilot itself is not test data and is not part of the PR.

## Depends on

- PRs 01–07.

## Normative plans

- [Verification and pilot](./explore_safe_slice_07_verification.md)
- [Manual setup](./explore_safe_slice_manual_setup.md)
- [Execution contract](./explore_safe_slice_00_execution_contract.md)

## Files

Create or complete:

- cross-component privacy-boundary integration tests;
- built wheel/sdist clean-environment tests;
- launch/readiness/framework qualification fixtures;
- deterministic crash/race/failure-injection fixtures;
- a generic parent-supervised pilot runbook with no child data;
- an execution-record template that excludes secrets/transcripts/audio and child-specific pilot observations.

Modify only code needed to fix failures demonstrated by these tests; do not add features.

## Manual prerequisites

- [ ] Actual lesson attestations and hashes are complete.
- [ ] Selected optional capability setup is complete or disabled.
- [ ] Synthetic export/delete/managed-wipe exercises pass.
- [ ] Browser framework data-handling canaries pass.
- [ ] Parent reviews the exact readiness report and limitations.

These are technical/synthetic qualification prerequisites. Both-parent consent is obtained only in the separate post-PR pilot gate below.

No external account is required for fallback-only pilot mode.

The runbook exposes three cumulative, explicitly named eligibility levels:

1. `authored_typed`: approved lesson, typed input, authored fallback, curated visual, and authored choices;
2. `generated_tutor`: level 1 plus one real selected tutor plugin and the mandatory additional-safety plugin, each installed, synthetically qualified, decision-approved, and readiness-acknowledged;
3. `generated_tutor_voice_input`: level 2 plus one real selected STT plugin and qualified managed browser/WAV path.

Browser read-aloud is reported as a separate `qualified`/`unavailable` capability because visible text always remains. Passing a lower level does not satisfy or imply the requested LLM/voice milestone. The fastest child rehearsal may use level 1 while provider/model choices remain open; any session described as “LLM interaction” requires level 2, and the complete requested audio-input/output experience requires level 3 plus qualified browser read-aloud.

## Implementation tasks

- [ ] Capture baseline full-suite/static/build results.
- [ ] Add claim-to-assertion requirement mapping with exact pytest/manual IDs.
- [ ] Add end-to-end canary tests from input/output/audio through every forbidden sink.
- [ ] Add real SQLite/filesystem deletion/wipe failure-injection tests.
- [ ] Add real subprocess timeout/cleanup tests.
- [ ] Add lock/epoch concurrency barriers without timing sleeps.
- [ ] Build wheel and sdist; install each in clean environments and compare resource hashes.
- [ ] Exercise fallback-only app construction and readiness-gated local launch.
- [ ] Emit an exact eligible-level report; prove generated/voice levels remain unavailable until real selected capability artifacts and decisions qualify.
- [ ] Verify Study help/list/today against a temporary safe data root.
- [ ] Run Explore and full regression/static checks.
- [ ] Document unresolved external/browser declarations without promoting them to verified claims.
- [ ] Write pilot preconditions, briefing, stop conditions, immediate observation, delayed recall, and deletion choices.

## Required evidence

- Exact commands, exit codes, test counts, failures, environment versions, and Git diff/status.
- No raw canary in SQLite rows/bytes where applicable, WAL/SHM, JSON exports, configured framework cache/temp/logs, readiness, or captured errors.
- No public URL/share flag.
- Missing/stale readiness acknowledgement means launch call count zero.
- Managed wipe removes every registered family-data path while preserving only profile/generic package/setup records.
- Existing Study schema/data is not read or migrated by Explore.
- No live child text/audio in automated tests.

Run the complete command order in the verification plan, ending with:

```bash
"$PYTHON" -m pytest tests/explore -q
"$PYTHON" -m pytest -q
"$PYTHON" -m build
git status --short --branch
git diff --stat
```

Use project-declared static tools; an unavailable required tool leaves verification incomplete.

## Acceptance

- Every first-slice requirement maps to concrete evidence.
- Explore and full regression pass or pre-existing failures are precisely separated.
- Introduced lint/type failures are zero.
- Installed artifacts load exact approved content.
- Fallback-only manual UI smoke passes.
- Optional tutor/audio is either qualified or visibly disabled, and the app/runbook names only the highest eligibility level actually satisfied.
- Technical completion is not described as educational validation or production safety.
- Working tree remains uncommitted until explicit authorization.

## Post-PR manual gate

Only after technical acceptance:

1. Reconfirm both parents’ consent and enabled data routes.
2. Select and record the highest actually eligible pilot level; do not label authored fallback as an LLM session.
3. Run one bounded, continuously supervised session.
4. Record structured sanitized observations only.
5. Review/delete/retain local data.
6. Perform delayed recall only at a parent-chosen later time.
7. Decide whether the graph/curation sequence may begin.

## Out of scope

- Graph/curation/recommendations.
- Automatic interpretation of pilot results.
- Public/family-external access.
- Actual child records in Git.
- Commit, push, or PR creation during the current planning/implementation session.
