# PR-10 — Curriculum Persistence, Graph, and Publication

## Goal

Stage validated immutable curation batches in a separate SQLite database, compile reviewed lesson artifacts deterministically, publish exact bytes, verify installed hashes, explicitly activate one snapshot, and expose the early approved graph/binding without recommendations.

## Depends on

- PR-09 parser/validator and a real reviewed Chain-1 bundle.
- PR-02 package lesson contract.
- PR-05 telemetry binding attachment contract.
- PR-08 pilot gate.

## Normative plans

- [Curriculum persistence](./explore_safe_slice_08a_curriculum_persistence.md)
- [Graph/import/compilation](./explore_safe_slice_08_graph_recommendations.md)
- [Data priming](./explore_safe_slice_data_priming.md)

## Files

Create:

- `src/lerni/explore/curriculum_store.py`
- `src/lerni/explore/curriculum_graph.py`
- `src/lerni/explore/curriculum_data/content-schema-v1.json`
- `src/lerni/explore/observation_export.py`
- `src/lerni/explore/binding_migration.py`
- curation operator command/callable for validate, stage, publish, verify, activate
- store/graph/compiler/observation-export tests

Modify:

- `content_compile.py` to add final attestation-bearing publication output while reusing preview logic;
- `bootstrap.py` and readiness for post-pilot graph mode only;
- packaged Chain-1 TOML/SVG/index only through reviewed publication;
- telemetry binding migration service.

Do not add parent-state/recommendation services or UI controls.

## Manual prerequisites

- [ ] Private bundle has exact actual dates, source review, asset hash, and 25 minimum required active attestations.
- [ ] Both parents review the generated lesson/asset/index diff and hashes.
- [ ] Operator confirms the manifest hash and formula-free attestation.
- [ ] Build tooling for wheel and sdist is available.

No cloud/service account or credential is needed.

## Implementation tasks

- [ ] Create exact curriculum DDL, schema version, keys/checks/foreign keys/indexes.
- [ ] Install/hash `content-schema-v1.json` with fixed table order, DDL-order columns, primary keys, and asset-BLOB replacement rules used by curriculum-state hashing.
- [ ] Implement full-snapshot version/hash monotonicity and no silent omission.
- [ ] Persist source asset bytes and immutable bindings.
- [ ] Require every lesson/asset attestation to match PR-09 review payload/asset hashes.
- [ ] Implement staging transaction with zero-error precondition, compile checks, rollback, and idempotent same-batch replay.
- [ ] Snapshot/copy/parse/privacy-scan/review/compile outside the shared mutation gate; stage/publish/activate revalidate immutable digests and run only bounded transactions.
- [ ] Purely compile PR-09 `ValidatedCurationRows` into exact final `StageableCurationBundle`; `stage()` independently recompiles and rejects mismatch before opening a transaction.
- [ ] Implement deterministic graph adjacency and invariants without a graph dependency.
- [ ] Compile lesson TOML/SVG/package index from approved rows only.
- [ ] Recompute a read-only final publication preview, require expected artifact-set hash, and persist exact publication approval plus bytes transactionally.
- [ ] Write only an atomic no-replace private publication bundle; manually review/apply exact bytes through the development workflow, then verify clean installed wheel/sdist.
- [ ] Implement explicit activation pointer transaction with persisted/recomputed canonical curriculum-state hash; startup remains read-only.
- [ ] Upgrade readiness schema `1`→`2` with graph/active-state/artifact identities, nullable content-quarantine hash, and stable curated-only fallback; reject cross-version shapes.
- [ ] Keep revocation quarantine sticky; add exact-hash/token clearing only after a different/newer active publication and installed package fully verify.
- [ ] Install the curriculum store closer/cascade into PR-05's already-complete fixed wipe-path registry; do not add a new path class.
- [ ] Add parent-token-protected exact-hash binding attachment for pre-graph sessions.
- [ ] Preview/write optional aggregate observations with exact separate manifest, neutralization flag, parent token, atomic no-replace publish, and lifecycle export-parser registration.

## Required concrete tests

- Real SQLite DDL/foreign-key inspection and all transaction rollback points.
- Same batch/hash/count replay is idempotent; changed bytes under same ID fail.
- Lower/same-changed entity and attestation versions fail.
- Publication/activation are separate; staged/unpublished or installed-hash mismatch cannot activate.
- Staged binding package/payload hashes come from the precomputed final artifact plan; publication and activation reject any byte/hash divergence.
- Golden artifact-set/plan/stageable-bundle digests reproduce independently; a tampered caller plan writes nothing and does not consume its batch ID.
- Repeated activation of the same exact active batch is read/verify idempotent.
- Any covered post-activation schema/pointer/row/relation/review/binding/approval/artifact mutation blocks child startup.
- Golden readiness transition proves exact v1→v2 field set/digest; v1 rejects graph fields and v2 rejects missing/extra/recommendation fields.
- Quarantine survives restart/wipe/ordinary activation; wrong token/hash, same quarantined identity, unverified replacement, and unlink failure cannot clear it.
- Barrier-controlled slow validation/compilation does not delay child Stop; busy gate returns a no-write retry, and source mutation during snapshot copy is rejected.
- Application bootstrap performs no curriculum write.
- Graph contains exactly one interest, two concepts, one related edge, one nudge, and one immutable binding; no draft/proposed content.
- Prerequisite cycles fail; related cycles do not; lesson order is never inferred.
- Compiled bytes/hashes are deterministic and contain no sheet-only private fields.
- Original first-slice build had no graph imports; graph extension adds no recommendation controls.
- Telemetry binding attachment accepts only exact lesson/version/canonical payload hash and reports package-hash metadata differences.
- Observation export manifest carries exact stable source IDs/counts so deleting any source session removes the affected local aggregate bundle before telemetry.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_curriculum_store.py -q
"$PYTHON" -m pytest tests/explore/test_curriculum_graph.py -q
"$PYTHON" -m pytest tests/explore/test_content_compile.py -q
"$PYTHON" -m pytest tests/explore/test_observation_export.py -q
"$PYTHON" -m pytest tests/explore/test_bootstrap.py -q
"$PYTHON" -m build
```

## Acceptance

- Offline bundle validates and stages without changing active content.
- Human-confirmed exact artifacts publish and match installed distributions.
- Explicit activation yields the expected approved graph/binding.
- Startup is read-only and hash-verifies active content.
- Child app still uses independently approved packaged lesson.
- No recommendation/assignment behavior is accepted in this PR.

## Out of scope

- Candidate scoring/ordering.
- Readiness attestations and parent-state DB.
- Recommendation/assignment UI.
- Automatic activation or Sheets sync.
- Commit, push, or PR creation.
