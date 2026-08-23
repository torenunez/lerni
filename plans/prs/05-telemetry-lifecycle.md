# PR-05 — Local Telemetry and Data Lifecycle

## Goal

Persist only sanitized session evidence in a separate Explore SQLite database and provide parent-token-guarded observation, export, session deletion, retention, and registered managed-family-data wipe.

## Depends on

- PR-03 private runtime paths and parent guard.
- PR-04 `PersistableTurnText`, policy decisions, and generation outcomes.

## Normative plan

- [Local telemetry and parent controls](../specs/04-telemetry.md)
- [Manual setup and wipe limitations](../runbooks/manual-setup.md)

## Files

Create:

- `src/lerni/explore/telemetry_models.py`
- `src/lerni/explore/telemetry_store.py`
- `src/lerni/explore/data_lifecycle.py`
- `src/lerni/explore/export.py`
- telemetry/schema/retention/export/lifecycle/integration tests

Do not modify Study’s database or schema.

## Manual prerequisites

- [ ] Choose telemetry enabled/disabled.
- [ ] Choose 1–3650 day “purge on next startup/maintenance” retention or explicit manual retention; no wall-clock scheduler is promised.
- [ ] Confirm telemetry/export/audio derived paths are private and non-synced.
- [ ] Review the managed family-data wipe scope and storage-remanence limitations.

No external account or credential is needed.

## Implementation tasks

- [ ] Add immutable records with no raw-text/audio/provider/child-name fields.
- [ ] Create schema version, settings, sessions, turns, events, observations, and typed session-deletion requests with exact checks/foreign keys.
- [ ] Verify the full shared Explore SQLite pragma contract on every connection; disable extensions and WAL/disk temp state.
- [ ] Require nonzero SQLite thread support and serialize every shared connection/cursor/result lifetime behind its store lock.
- [ ] Accept only typed sanitized/withheld persistence values.
- [ ] Add idempotent assignment-operation columns now without implementing assignments.
- [ ] Implement one transaction per public store write.
- [ ] Implement deterministic JSON export under the derived export root with no browser path.
- [ ] Publish every generated export under the shared mutation gate only after fresh source-digest/ID revalidation; deletion holds the same gate through export scan and final session removal.
- [ ] Add strict token-guarded export ID/kind/time/hash/size listing and fresh-scan exact-ID confirmed deletion.
- [ ] Implement non-active-session retention and stale-session abandonment.
- [ ] Populate hashed readiness with exact purge status/deferred count; unexpected purge/storage errors block launch.
- [ ] Print a sanitized transient deletion-recovery summary, but hash only the resulting complete/deferred maintenance state so two-step readiness acknowledgement is reproducible.
- [ ] Implement token-guarded lifecycle facade; UI cannot call low-level deletion.
- [ ] Delete generated matching exports on explicit session deletion.
- [ ] Implement exact-phrase managed wipe with the complete fixed telemetry/curriculum/parent-state DB/sidecar path registry from day one: prove exclusive runtime lock, quiesce, close initialized stores, remove present paths plus exports/audio/private-curation, invalidate tokens, stop.
- [ ] Preserve runtime profile, generic packaged content/templates, setup records, and non-child quarantine; curriculum/parent-state DB paths remain in PR-05's day-one registry and are removed when present, while PR-10/11 add only store closers/cascades.
- [ ] Report residual categories and never claim secure media erasure.

## Required concrete tests

- Inspect `sqlite_master`, columns, checks, indexes, and foreign keys.
- Database policy action/reason literals exactly equal the shared contract enums.
- Telemetry accepts the fixed `continue_submitted` event and maps optional-safety codes only through `policy_applied`/`tutor_failed` plus bounded `value_code`; no dynamic event type is possible.
- Forbidden columns/values and raw canaries are absent from rows and exports.
- Allowed/withheld turns persist exact disposition/outcome.
- Session summaries are stable and contain no turn/note text; later recall is a separate observation.
- Launch IDs distinguish current from prior active sessions; abandonment is explicit and cannot affect a current-launch active row.
- Real cascade removes turns/events/observations.
- Retention skips active sessions and leaves exports.
- Listing/export during a live session never launches purge; a barrier-controlled assigned Stop is not delayed by retention maintenance.
- Readiness reports only `not_applicable`, `complete`, or counted `deferred_nonterminal`; unexpected purge failure prevents launch.
- Explicit session deletion removes matching exports.
- Barrier race proves export either publishes before deletion and is removed, or loses revalidation after deletion and publishes nothing; no orphan file remains.
- Export list/delete cannot accept or reveal a filesystem path; malformed/app-named entries block claims.
- Crash-injected deletion always leaves a resumable telemetry marker until exports/store deletion complete; startup resumes it before launch.
- Failure after each lifecycle step is retryable and never reports false success.
- Managed wipe removes DB `-wal`/`-shm`/`-journal`, export/audio/private-curation fixtures, preserves profile/generic package/setup canaries, invalidates tokens, and exits.
- Crash-injected managed wipe leaves a strict non-child intent; next startup resumes before store creation, removes the marker last, and exits.
- Wrong token/confirmation and concurrent callback delete nothing.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_telemetry_schema.py -q
"$PYTHON" -m pytest tests/explore/test_telemetry_store.py -q
"$PYTHON" -m pytest tests/explore/test_retention.py -q
"$PYTHON" -m pytest tests/explore/test_export.py -q
"$PYTHON" -m pytest tests/explore/test_data_lifecycle.py -q
"$PYTHON" -m pytest tests/explore/test_safety_telemetry_integration.py -q
```

## Acceptance

- Study DB is untouched.
- No raw rejected input/draft or audio metadata reaches storage.
- Parent can export/delete synthetic sessions and exercise managed wipe.
- Disabled/unavailable telemetry does not disable lesson/safety.
- Filesystem/snapshot/browser/external-copy limits are explicit.

## Out of scope

- Parent recommendation database.
- Cross-store graph evidence cascade; PR-11 extends the lifecycle port.
- Cloud analytics or sync.
- Commit, push, or PR creation.
