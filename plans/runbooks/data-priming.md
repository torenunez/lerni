# Explore Safe Slice — CSV and Google Sheets Data Priming

## Goal

Produce the smallest truthful, reviewed content bundle that can:

1. compile the approved Chain-1 acceleration lesson;
2. activate the early curriculum graph;
3. bind later telemetry without reinterpreting history;
4. support parent-approved recommendation experiments after the first pilot.

The spreadsheet is a curation surface, not a child profile or live runtime database.

## Authoritative schema

Use the exact columns, enums, normalization, CSV grammar, review scopes, and seed text in [Portable spreadsheet curation and early graph](../specs/08-graph-recommendations.md). Persistence and activation use [Curriculum persistence](../specs/08a-curriculum-persistence.md).

Create these tabs in this order:

1. `README`
2. `LISTS`
3. `INTERESTS`
4. `CONCEPTS`
5. `SOURCES`
6. `FACTS`
7. `NUDGES`
8. `EDGES`
9. `ASSETS`
10. `LESSONS`
11. `LESSON_STEPS`
12. `LESSON_CHECKS`
13. `CHECK_CHOICES`
14. `CHECK_HINTS`
15. `REVIEWS`
16. `OBSERVATIONS`

Only tabs 3–15 plus the asset enter the curriculum bundle. `OBSERVATIONS` is a non-importable reference/export tab: do not include it in the curriculum manifest, and never fabricate it.

## Privacy rules before entering data

Never enter:

- child name, initials, account ID, birthday, school, address, contact details, or exact location;
- raw transcript, audio, chat, prompt, or generated response;
- medical, behavioral, diagnostic, or protected-class labels;
- credentials, account recovery details, private family notes, or secrets;
- current car rankings or claims that have not been reviewed against a stable source.

`child_phrase_sanitized` is an optional short paraphrase, not a raw quote archive. `parent_observation_sanitized` explains the interest without identifying the child.

## Minimum seed inventory

### Interest

Create exactly one initial interest:

- `interest_id`: `fast-cars`
- lifecycle: `active`
- initial approval: `draft`, later `approved`
- category: `vehicles`
- anchor: `zero-to-sixty-time`
- locale: `en-US`
- engagement strength: truthful parent judgment from 1–5
- first/last observed dates: truthful dates, not plan placeholders
- entered role: `parent` or `educator`

Replace the sample child phrase and parent observation with truthful sanitized wording, or leave optional child wording blank.

### Concepts

Create:

- `zero-to-sixty-time`: interest-track anchor; elapsed time for a fixed velocity change, not acceleration itself;
- `average-acceleration`: learning-track fundamental; change in velocity divided by elapsed time.

Do not add prerequisite edges merely to force lesson order.

### Source

Create `nasa-acceleration` from the source row in the schema plan.

Before approval:

- open the HTTPS source manually;
- confirm it still supports the canonical definitions;
- record the actual retrieval date;
- record license/use notes;
- avoid copying source prose beyond permitted use;
- set status approved only after science review.

If the source is unavailable or no longer supports the facts, replace it with another stable reviewed source and update every dependent row/hash before approval.

### Facts

Create these four reviewed facts:

1. `zero-to-sixty-is-time`
2. `acceleration-definition`
3. `shorter-time-greater-average`
4. `average-not-instant`

Preserve each scope limitation:

- 0–60 is elapsed time, not acceleration;
- comparison assumes the same start/end velocity;
- 4 and 8 seconds are hypothetical lesson values;
- average acceleration does not establish instantaneous/constant acceleration;
- no fact establishes a current fastest-car ranking.

Allowed numbers must use the exact normalized list grammar.

### Nudge

Create `compare-same-speed-change`:

- source anchor: `fast-cars`;
- target: `average-acceleration`;
- kind: `comparison`;
- prerequisite: `zero-to-sixty-time`;
- priority: parent-authored 1–5;
- prompt: compare hypothetical 4-second and 8-second 0–60 runs;
- expected signal: identifies Car A and explains same speed change in less time;
- two progressive hints;
- reviewed reveal text;
- source: `nasa-acceleration`.

This is a candidate teaching move, not automatic child-visible content.

### Edge

Create one canonical approved `related` edge:

```text
from_concept_id=average-acceleration
to_concept_id=zero-to-sixty-time
```

This ASCII stable-ID ordering is required for symmetric related edges; the graph exposes both adjacency directions. Its rationale must explain the fixed velocity change plus elapsed-time relationship. It does not encode sequence, mastery, or a tutor turn.

### Asset

Use the project-authored Chain-1 SVG:

- ID `chain-1-acceleration-visual`;
- package-relative path under `assets/`;
- media type `image/svg+xml`;
- exact SHA-256 generated from final bytes;
- title, description, and alt text;
- blank source ID only if it is wholly project-authored;
- actual license/use note;
- visual-accessibility and parent-approval reviews.

Any byte change requires a new hash and renewed affected review.

### Lesson

Create `chain-1-acceleration`, version 1:

- interest `fast-cars`;
- audience `ages-7-9`;
- locale `en-US`;
- reviewed goal and grounding scope;
- reviewed fallback text;
- `max_turns=8`.

Add two ordered lesson steps:

1. `hook-0-to-60`
2. `teach-acceleration`

Add one check:

- `compare-average-acceleration`;
- exact reviewed prompt/success/reveal text;
- three choices with exactly one correct answer;
- two contiguous progressive hints;
- fact IDs and scope terms from the schema plan.

Lesson order comes only from `step_index`.

## Required review attestations

No review row may be fabricated. Use actual role and date; do not store a reviewer name.

The minimum approved seed requires 25 active attestations:

- interest: 1 `parent_approval`;
- source: 1 `science`;
- two concepts: 2 each (`science`, `child_content`);
- four facts: 2 each (`science`, `child_content`);
- nudge: 3 (`science`, `child_content`, `parent_approval`);
- edge: 2 (`science`, `child_content`);
- asset: 2 (`visual_accessibility`, `parent_approval`);
- lesson version: 4 (`science`, `child_content`, `visual_accessibility`, `parent_approval`).

Use a stable unique attestation ID, version 1, exact entity ID/version, active status, actual `reviewed_on`, and optional repository-relative evidence reference. Every lesson review records the same exact read-only child-facing payload hash; asset reviews record the exact SVG hash.

Both-parent pilot consent belongs in the private operator setup record. The content schema’s single active `parent_approval` scope is an approval control, not a complete consent ledger.

## Draft-to-approved workflow

1. Copy tracked blank templates to a private working location.
2. Enter all seed rows with draft status.
3. Replace placeholder dates and parent judgments with truthful values.
4. Generate the final SVG hash locally.
5. Export every imported tab as UTF-8 CSV.
6. Run parser/validator while all rows are draft; fix schema, reference, privacy, and content errors.
7. Run the read-only compile preview and record its canonical child-facing payload hash.
8. Perform science, child-content, accessibility, and parent reviews against that exact preview.
9. Add actual `REVIEWS` rows with the required payload/asset hashes.
10. Change only reviewed entities to approved; keep the interest lifecycle active.
11. Re-export all tabs; do not patch individual CSVs after review.
12. Confirm the workbook contains no formulas; only then attest `formula_free_attested=true`.
13. Generate `manifest.json` and all file SHA-256 values from exact exported bytes.
14. Run dry-run import and inspect every warning/error.
15. Stage the immutable batch and recompile the same payload hash.
16. Compile final attestation-bearing lesson TOML, SVG, and package index deterministically.
17. Review generated final bytes/diff and artifact-set hash; record explicit publication approval.
18. Write the exact private publication bundle; a developer reviews and applies those bytes through the normal source/build workflow (the app never edits its checkout/install).
19. Verify installed wheel/source artifacts against published hashes.
20. Explicitly activate the batch.
21. Reopen the active snapshot and assert the exact expected graph/binding.

Never auto-activate after export, import, publication, or application startup.

## Google Sheets export checklist

- [ ] Private sharing only.
- [ ] Exact tab names and headers.
- [ ] No hidden extra imported columns.
- [ ] No formulas, smart chips, external links, Apps Script, or add-ons.
- [ ] Pipe-separated lists retain authored order.
- [ ] Empty optional fields are blank.
- [ ] Dates and UTC timestamps use exact formats.
- [ ] CSV files are exported individually with exact uppercase filenames.
- [ ] Asset is copied as exact bytes, not re-saved by the spreadsheet.
- [ ] CSVs are inspected locally before manifest generation.
- [ ] `README`/`LISTS` are not placed in the imported file map.
- [ ] `OBSERVATIONS.csv` is absent from the curriculum bundle/manifest; any later real sanitized export uses its separate export manifest.
- [ ] The production batch directory contains only `manifest.json`, exact manifested CSV/assets, and implied asset directories—no editing tabs, hidden files, or stale exports.

## Expected active graph after priming

The active snapshot contains:

- one active interest: `fast-cars`;
- two approved concepts;
- one canonical related edge;
- one approved comparison nudge;
- four approved facts backed by one approved source;
- one approved SVG asset;
- one approved lesson version with two steps and one retrieval check;
- one immutable curriculum binding for exact lesson/version/canonical payload plus current published package hash.

It must not contain draft/proposed rows, a lesson-order edge, current rankings, fabricated observations, or recommendations.

## Post-pilot recommendation priming

Do this only after plan 08b is implemented and the first pilot data exists:

1. Attach the active curriculum binding to a pre-graph session only when lesson ID, content version, and canonical lesson-payload/asset identity match exactly; disclose a package-hash difference only when it is limited to PR-02’s exact review block and resulting index lesson SHA.
2. Create a parent scope selecting `fast-cars` and allowed nudge kind `comparison`.
3. Review sanitized aggregate observations; do not import transcript/audio.
4. Attest `zero-to-sixty-time` readiness only if a parent/educator actually observed it. Otherwise leave readiness `unknown`.
5. Refresh candidates.
6. Parent explicitly approves, defers, or rejects; no candidate is child-visible automatically.

No spreadsheet row or observation automatically changes readiness, content approval, graph edges, or assignment state.

## Acceptance

Priming is complete only when:

- the exact bundle validates offline with zero errors;
- every approved row has required active reviews;
- generated hashes match installed artifacts;
- activation is explicit and transactional;
- active adjacency and binding equal the expected inventory;
- the packaged lesson compiles deterministically;
- no prohibited child data or credential exists in sheet/CSV/manifest;
- a second import of identical bytes is idempotent;
- changed bytes under the same batch ID are rejected.
