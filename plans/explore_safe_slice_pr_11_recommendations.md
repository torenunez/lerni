# PR-11 — Parent Recommendations, Assignments, and Feedback

## Goal

Add deterministic, explainable, parent-controlled recommendation candidates and crash-recoverable lesson assignments backed by a separate parent-state database. Recommendations never mutate content/graph/readiness or reach the child without explicit parent approval.

## Depends on

- PR-10 verified active curriculum and immutable bindings.
- PR-05 lifecycle extension port.
- PR-06 session/UI lock/epoch behavior.
- Real post-pilot sanitized observations when available; empty evidence remains valid.

## Normative plan

- [Recommendation and feedback contract](./explore_safe_slice_08b_recommendation_feedback.md)
- [Verification plan](./explore_safe_slice_07_verification.md)
- [Post-pilot data priming](./explore_safe_slice_data_priming.md)

## Files

Create:

- `src/lerni/explore/parent_state.py`
- `src/lerni/explore/observation_aggregation.py`
- `src/lerni/explore/recommendations.py`
- `src/lerni/explore/assignment_reconcile.py`
- parent-state/aggregation/recommendation/assignment tests

Modify:

- `bootstrap.py` and readiness;
- `data_lifecycle.py`;
- `presenter.py`;
- `ui.py`;
- bootstrap/UI/presenter/lifecycle tests.

## Manual prerequisites

- [ ] Active curriculum/package hashes verify.
- [ ] Parent selects interest scope and allowed nudge kinds.
- [ ] Parent/educator attests concept readiness only from actual observation.
- [ ] Parent reviews each deterministic explanation before approval.
- [ ] No transcript/audio is imported as evidence.

No external service account or credential is needed.

## Implementation tasks

- [ ] Create parent-state DDL and require the already-held PR-03 process-lifetime application lock before opening it.
- [ ] Add exact parent scope, readiness/evidence, run/candidate/decision/assignment schemas.
- [ ] Aggregate sanitized telemetry by immutable binding with exact contributing session/observation IDs.
- [ ] Implement eligibility, content identity, ordering tuple, explanation, defer, and reject behavior.
- [ ] Add token-guarded stable scope/assignment listing and decision-plus-assignment results for restart-safe UI.
- [ ] Persist complete candidate snapshots so later active-batch changes cannot reinterpret them.
- [ ] Revalidate active content/reviews/hashes before approval and start.
- [ ] Implement pending/starting/started/completed/cancelled transitions and operation-ID saga.
- [ ] Add assignment-specific readiness preview/acknowledgement and idempotent telemetry replay for starting/started Resume.
- [ ] Keep `starting` resumable until explicit session-adoption acknowledgement.
- [ ] Reconcile every crash point and fixed terminal mapping.
- [ ] Upgrade readiness schema `2`→`3` with exact recommendation mode/schema; reject cross-version shapes and emit transient sanitized recovery/reconciliation summaries while hashing only the resulting clean state.
- [ ] Implement/install the parent-state session-derivative cascade before telemetry deletion and add its store closer to PR-05's already-complete fixed wipe-path registry.
- [ ] Verify parent-state DB/WAL/SHM/journal and derived candidate evidence are removed through that existing registry/cascade.
- [ ] Add strict parent-state snapshot export creation with exact source session/observation IDs; register list/delete parsing and explicit-session cascade removal.
- [ ] Add recommendation controls only when the complete service initializes.
- [ ] Extend the PR-06 parent landing with default/assignment choices while preserving deferred initial-grant consumption and zero telemetry on admission.
- [ ] Start/Resume adopts exact telemetry context, acknowledges, then enables interaction.

## Required concrete tests

- Readiness remains manual; observations never auto-promote.
- Aggregation order/count/latest rules and contributing IDs are exact.
- Decoy graph nodes/prerequisites/defer/reject/active assignments filter correctly.
- Exact stable candidate ordering and full persisted reconstruction after later activation.
- Scorer input has no duration/message/streak/emotion/model fields.
- Wrong token, duplicate decision, stale content, and invalid transitions fail.
- Parent callbacks cannot supply persisted IDs, active batch, cutoff, or timestamps; a fake server clock deterministically owns them.
- Real separate SQLite crash injection covers every saga point, replay, resume, adoption, completion, cancellation, and corruption case.
- Reconciliation resumes `starting` only with active telemetry; terminal telemetry maps immediately, adoption rechecks active status, and telemetry rejects every new turn/event after terminalization.
- UI controls are absent without complete service and all callbacks require token.
- Graph-mode admission creates no telemetry until the parent selects default/assignment; first selection consumes the held grant and later starts consume new budget slots.
- Interaction remains disabled if adoption acknowledgement fails.
- Session deletion removes parent evidence/candidates/assignments before telemetry; retries after each injected crash are idempotent.
- Startup resumes telemetry-marked deletions before assignment reconciliation, so no missing-assignment row is misclassified as corruption.
- Managed wipe removes telemetry/curriculum/parent-state sidecars plus private curation while preserving only generic profile/package/setup/quarantine records.
- Golden readiness transition proves the exact v2→v3 field set/digest; v2 rejects recommendation fields and v3 rejects missing, extra, or future-version fields.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_parent_state_schema.py -q
"$PYTHON" -m pytest tests/explore/test_observation_aggregation.py -q
"$PYTHON" -m pytest tests/explore/test_recommendations.py -q
"$PYTHON" -m pytest tests/explore/test_assignments.py -q
"$PYTHON" -m pytest tests/explore/test_data_lifecycle.py -q
"$PYTHON" -m pytest tests/explore/test_bootstrap.py tests/explore/test_presenter.py tests/explore/test_ui.py -q
"$PYTHON" -m pytest tests/explore -q
"$PYTHON" -m pytest -q
```

## Acceptance

- Parent sees transparent candidates only within saved scope when truthful readiness makes one eligible; a real zero-candidate result is valid.
- Explicit approve creates one assignment; defer/reject are deterministic and version-aware.
- No unapproved candidate reaches child UI.
- Assignment adoption/terminal lifecycle is recoverable across crashes.
- Cross-store deletion/managed wipe leaves no dangling child-derived parent evidence.
- Content, telemetry, and parent-state databases remain separate.
- No engagement-maximizing metric or automatic graph/readiness mutation exists.

Synthetic reviewed fixtures prove approve/assignment paths even if family readiness remains `unknown`; manual acceptance never fabricates readiness to force a candidate.

## Out of scope

- Generated graph/content suggestions.
- Automatic mastery/readiness.
- Child-facing recommendation feed.
- Multi-user/authenticated remote access.
- Commit, push, or PR creation.
