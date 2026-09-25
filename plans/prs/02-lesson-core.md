# PR-02 — Reviewed Lesson Core and Chain-1 Content

## Goal

Add a standard-library, deterministic lesson domain and one packaged, source-backed Chain-1 acceleration lesson. Tutor output cannot select content, inspect answers, or advance state.

## Depends on

- PR-01 documentation decisions.

## Normative plan

- [Lesson domain and content](../specs/02-lesson-core.md)
- [Policy algorithms](../specs/03a-policy-algorithms.md) for token/number compatibility
- [Data priming](../runbooks/data-priming.md) for later schema parity

## Files

Create:

- `src/lerni/explore/__init__.py`
- `src/lerni/explore/canonical.py`
- `src/lerni/explore/domain.py`
- `src/lerni/explore/catalog.py`
- `src/lerni/explore/engine.py`
- `src/lerni/explore/lessons/__init__.py`
- `src/lerni/explore/lessons/lesson_index.toml`
- `src/lerni/explore/lessons/chain_1_acceleration.toml`
- `src/lerni/explore/lessons/assets/chain_1_acceleration.svg`
- lesson/domain/catalog/engine/distribution tests under `tests/explore/`

Modify `pyproject.toml` for package resources. Modify `MANIFEST.in` only if source-distribution evidence requires it.

Do not modify Study models, database, SM-2, or commands.

## Manual prerequisites

- [ ] Recheck every source and record the actual retrieval date.
- [ ] Parent/educator reviews the corrected distinction: 0–60 is elapsed time; acceleration is velocity change over time.
- [ ] Perform real science, child-content, visual-accessibility, and parent-approval reviews.
- [ ] Generate exact final SVG, canonical lesson-payload, and TOML/package SHA-256 values.

No tutor/STT account or credential is needed.

## Implementation tasks

Code tasks are done (2026-09-06, see `docs/progress.md`). The attestation task and
all manual prerequisites above remain open: they need genuine human review.

- [x] Scaffold importable public symbols.
- [x] Write behavior-specific failing tests for frozen types and constructor invariants.
- [x] Implement immutable lesson/source/fact/step/check/review types and the shared strict canonical-JSON encoder used by lesson payload identity and later readiness records.
- [x] Write failing strict-TOML and package-index tests.
- [x] Implement `importlib.resources` loading, exact schema rejection, hash verification, and child catalog filtering.
- [x] Write failing event/state transition tests.
- [x] Implement intro, teach, check, progressive hint, correct completion, and revealed completion transitions.
- [x] Ensure snapshots omit answer keys and internal review/source detail.
- [x] Add corrected Chain-1 draft content and accessible project-authored SVG.
- [x] Keep production content draft until human review is complete.
- [ ] Add actual attestations carrying the exact reviewed payload hash and switch to approved only after the gate.
- [x] Verify wheel and source distribution carry exact indexed bytes.

## Required concrete tests

- Invalid enum/ID/version/index/hash/review scope fails closed.
- Index/TOML/SVG limit-plus-one fixtures fail before unbounded decode/render.
- Draft content never enters child catalog.
- Approved content without each required attestation fails.
- Every approved attestation must carry the same independently recomputed canonical lesson-payload hash.
- Duplicate/mismatched attestations fail.
- Asset/TOML byte change fails index verification.
- Canonical lesson-payload hash changes for runtime/grounding/asset changes but not review-only metadata.
- Wrong choices advance hints deterministically; no random branch exists.
- Tutor-like text has no engine event.
- Public snapshot contains only the current reviewed context and no answer key.
- Wheel and sdist resource bytes equal source hashes in clean installs.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_domain.py -q
"$PYTHON" -m pytest tests/explore/test_catalog.py -q
"$PYTHON" -m pytest tests/explore/test_chain_1_content.py -q
"$PYTHON" -m pytest tests/explore/test_engine.py -q
"$PYTHON" -m pytest tests/explore/test_distribution.py -q
```

## Acceptance

- One actually reviewed lesson loads from installed resources.
- Exact content/index/asset hashes match.
- Deterministic state tests cover every allowed/rejected transition.
- Scientific text avoids instantaneous acceleration and mutable ranking claims.
- Study remains untouched.

## Out of scope

- Gradio.
- Tutor/safety generation.
- Telemetry.
- Audio.
- Curriculum database or recommendations.
- Fabricated review records.
- Commit, push, or PR creation.
