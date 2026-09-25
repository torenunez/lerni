# PR-09 — Curation Templates and Strict CSV Validation

## Status and split (2026-09-25)

This work package is now two separate deliveries:

1. **Early authoring (delivered at roadmap M1, not part of this PR's acceptance).**
   The [`educator-paths-v1`](../specs/08c-educator-path-authoring.md) contract,
   blank templates, draft examples, and the offline **drafting** checker
   `scripts/validate_curation_templates.py`. That checker explains incomplete
   drafts; it is not this PR's strict parser, it does not produce
   `ValidatedCurationRows`, and it does not complete any task below.
2. **Strict import and compilation (this file, roadmap M5).** Everything below.
   Nothing here is implemented.

The `curation/templates/v1/` and `curation/examples/chain-1-v1-draft/` files listed
under *Files* already exist as a **legacy partial draft**: seven of the sixteen
tabs, no asset/lesson/check tables, no manifest, no importer.

**New prerequisite task — before any strict-parser work:** specify how the six
`educator-paths-v1` tables map into a reviewed delivery representation (lessons,
facts, sources, assets, and a separate path/step identity mapping), and reconcile
the older v1 schema's learner-bearing INTERESTS table and fixed concept roles.
Renaming columns is not a mapping. Update spec 08 before implementation.

## Goal

Provide portable spreadsheet templates and a deterministic offline curriculum parser/validator for interests, concepts, sources, facts, nudges, edges, assets, lessons, checks, and reviews. Keep the observation header as a non-importable reference for the separate PR-10 export contract; observations never enter a curriculum import manifest. This PR does not write a curriculum database or activate content.

## Depends on

- PR-08 technical/pilot gate and parent decision to proceed (for the strict importer only; educator authoring does not wait).
- The `educator-paths-v1` delivery mapping task above.
- PR-02 lesson schema.
- PR-04 policy normalization/number rules.

## Normative plans

- [Spreadsheet curation and graph priming](../specs/08-graph-recommendations.md)
- [`ValidatedCurationRows` boundary only](../specs/08a-curriculum-persistence.md); PR-10 owns `StageableCurationBundle` and persistence
- [Data priming runbook](../runbooks/data-priming.md)
- [Manual Google Sheets setup](../runbooks/manual-setup.md)

## Files

Create:

- `curation/templates/v1/README.md`
- `curation/templates/v1/LISTS.csv`
- blank header-only CSV templates for tabs 3–16
- `curation/examples/chain-1-v1-draft/` with seed rows, empty reviews/observations, and no manifest
- `src/lerni/explore/curation_models.py`
- `src/lerni/explore/curation_csv.py`
- `src/lerni/explore/curation_validation.py`
- `src/lerni/explore/curation_data/curation-schema-v1.json`
- `src/lerni/explore/curation_data/svg-policy-v1.json`
- `src/lerni/explore/content_compile.py` with read-only review-preview mode
- parser/validation fixtures and tests

Blank templates contain headers only. The separate example contains only draft sample content and no fabricated `REVIEWS` rows, child identity, real observations, credentials, or importable approval manifest.

## Manual prerequisites

- [ ] Choose local CSV editor or private Google Sheets.
- [ ] If Google Sheets is used, complete account/sharing/privacy steps; no Google API setup.
- [ ] Real learner observations stay in a separate private log, never in the curriculum bundle (the legacy INTERESTS observation columns are not filled).
- [ ] Science/content/accessibility reviewers are available for later approval.

## Implementation tasks

- [ ] Specify and review the `educator-paths-v1` → delivery mapping (prerequisite; see top).
- [ ] Lock exact headers, enums, ID/list/date/timestamp/number grammar, limits, and privacy exclusions.
- [ ] Install/hash the exact curation-schema and SVG-policy resources used with the shared policy-cases resource in `validated_rows_sha256`.
- [ ] Add versioned README/LISTS and draft Chain-1 template rows.
- [ ] Implement bounded manifest reader with exact JSON byte grammar and hashes.
- [ ] Implement strict UTF-8 CSV reader with exact header/order, quoting/newline rules, and duplicate rejection.
- [ ] Reject literal spreadsheet-formula prefixes after bounded NFKC/control/leading-space normalization and before ordinary field coercion, with only the exact typed-number exception.
- [ ] Parse immutable typed rows and canonical row hashes.
- [ ] Return path-free `ValidatedCurationRows` with its exact digest; do not construct PR-10's final `CompiledStagingPlan`.
- [ ] Validate reviews, references, approvals, graph edges, assets, lesson order/checks, grounding scope, and forbidden fields.
- [ ] Produce deterministically ordered row-level issues with stable codes.
- [ ] Keep validation read-only; no SQLite/store import.
- [ ] Reject observations in a curriculum manifest and label the observation template as non-importable; PR-10 owns the separate neutralized export manifest.
- [ ] Compile the exact review-section-free canonical lesson/asset payload without package/database writes.
- [ ] Add local manifest-generation helper for exact exported bytes and formula-free attestation.
- [ ] Document that live Google Sheets/API access is not part of runtime.

## Required concrete tests

- Exact valid minimal draft bundle parses.
- BOM, malformed UTF-8, bare/mixed/missing-final newline, malformed quote/header/order, unknown/missing column, duplicate key, bad list order, and formula prefix fail; consistent LF and CRLF fixtures canonicalize to equal row hashes.
- Manifest rejects unknown key, duplicate JSON key, trailing bytes, path traversal, missing/extra manifested or directory file, and hash mismatch.
- Pinned-root no-follow fixtures reject symlink, hardlink, absolute/case-colliding path, and descriptor/path-swap changes before staging can be allowed.
- Manifest/CSV/asset/total-byte, row-count, and pre-normalization cell-byte limits fail before unbounded reads/object construction.
- Forbidden child-name/audio/transcript/credential columns fail.
- Approved entity missing dependency/review fails; draft rows remain non-active.
- Edge direction/cycle, asset/SVG/hash, lesson/check/choice/hint contiguity, and exact fact/scope references are asserted.
- Issue order and canonical hashes are stable across runs; issue text never echoes a raw-cell canary.
- Independent golden `validated_rows_sha256` uses the fixed resource/file/table/asset mapping and primary-key order; any resource or row mutation changes it.
- Compile-from-CSV review payload using the example’s exact ASSETS file bytes/hashes is byte-identical to the approved PR-02 `PackageLessonCatalog` v1 payload golden; do not compare against draft TOML with an empty `visual_sha256`.
- Validator performs no database/network write.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_curation_csv.py -q
"$PYTHON" -m pytest tests/explore/test_curation_validation.py -q
```

## Manual data task

Use the data-priming runbook to create a private family draft. Do not add the filled private workbook/CSV bundle to Git. Actual attestations and final hashes are required before PR-10 activation tests, but not fabricated to make this PR pass.

## Acceptance

- Any CSV-capable editor can produce the exact offline bundle.
- Google Sheets remains optional and API-free.
- Invalid/unsafe bundle produces deterministic errors and writes nothing.
- Tracked templates are privacy-safe and draft-only.
- No recommendation code or active graph exists.

## Out of scope

- Curriculum SQLite.
- Final attestation-bearing compilation, publication, and activation.
- Recommendation UI.
- Automatic Sheets synchronization.
- Commit, push, or PR creation.
