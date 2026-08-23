# Explore Safe Slice — Portable Spreadsheet Curation and Early Graph Priming

## Goal

Give parents and educators a practical spreadsheet schema, usable in Google Sheets or another CSV-capable editor, for:

- recording a child’s interests without storing a child name or raw transcript;
- defining educational concepts and source-backed facts;
- authoring parent/educator nudges from an interest toward a concept;
- defining domain relationships separately from lesson order;
- reviewing and approving content before child visibility;
- exporting a portable CSV bundle;
- validating and importing approved content into an early local curriculum graph;
- using local pilot observations to improve future parent-approved recommendations.

The normative artifacts are versioned CSV templates, a local README/LISTS specification, and a manifest. Google Sheets is one optional editing recipe. This plan does not require a Google account, Google Sheets API, named model, graph library, network connection, or cloud database. A future sheet-source adapter may automate retrieval without changing the importer.

## Core design decisions

### Separate the things that the original pivot conflated

The workbook treats these as different records:

- **Interest**: something the child repeatedly asks about or enjoys.
- **Concept**: a stable piece of knowledge.
- **Fact**: reviewed content that may be shown or supplied to a tutor.
- **Nudge**: a parent-authored educational move connecting an interest or concept to a target concept.
- **Domain edge**: a semantic relationship such as parent, prerequisite, or related.
- **Lesson**: a reviewed learning experience.
- **Lesson step**: explicit pedagogical order.
- **Observation**: parent-entered evidence from a pilot session.

An edge never implies a tutor turn. A nudge never becomes child-visible merely because it exists. A lesson sequence never rewrites graph semantics.

### Approval is data, not an assumption

Every child-facing interest, concept, source, fact, nudge, edge, asset, and lesson has an approval status and review attestations.

Only `approved` rows with all required active attestations may enter the active graph or compiled lesson bundle.

Rows with `draft`, `proposed`, `rejected`, `paused`, or `retired` status remain unavailable to the child.

### The sheet is a curation surface, not a child-data store

Do not place these in Google Sheets:

- child name;
- account identifier;
- exact address, school, phone, email, or location;
- raw audio;
- raw transcript;
- full model prompt or response;
- credentials;
- medical, behavioral, or diagnostic labels;
- secrets or family-confidential details.

The optional, non-importable observations tab contains aggregate parent judgments and sanitized notes only. Export from local telemetry for separate parent review is manual and parent-triggered.

## Workbook tabs

Create CSV templates or spreadsheet tabs with these exact names:

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

`README` and `LISTS` exist for human guidance/editing validation but are not curriculum inputs. A production batch directory and manifest reject them, `OBSERVATIONS`, and every other unlisted directory entry; copy only the exact imported CSVs, asset, and manifest into the pinned batch directory.

## Shared cell rules

- IDs use lowercase kebab case matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- Dates use ISO `YYYY-MM-DD`.
- Date-times use UTC RFC 3339, ending in `Z`.
- Booleans use lowercase `true` or `false`.
- Ordered integer fields start at `0`.
- ID-list fields use `|` between kebab-case IDs, preserve authored order, reject duplicates, and do not sort implicitly.
- Token-list fields (`scope_terms`, `allowed_short_replies`) use `|`; each item must match the policy token grammar, be casefolded, preserve first-authored order for hashing, and reject duplicates.
- Label-list fields (`aliases`) use `|`; each trimmed item is 1–120 characters, may contain spaces, preserves authored order, and rejects duplicate casefolded values.
- Numeric-list fields (`allowed_numbers`) use `|`; each item must match and normalize through the exact number grammar in the policy appendix, preserve authored order after normalization, and reject normalized duplicates. A leading minus is permitted only when the complete item is a valid number, so it is not treated as a spreadsheet-formula prefix.
- No list item may contain `|`. Non-list free text must not contain `|`.
- Empty optional cells are blank, not `N/A`, `none`, or `-`.
- Human-readable text is Unicode plain text. After NFKC/control handling and leading-space trim, reject a first `=`, `+`, `@`, or `-`; leading `-` is allowed only for a complete valid typed-number field or a numeric-list item validated before joining. This literal formula defense complements, but cannot replace, the formula-free workbook attestation.
- Curriculum import never “neutralizes then accepts” a dangerous prefix, because that would change reviewed child-facing content and defeat literal-prefix tests. Prefix neutralization is reserved solely for app-generated spreadsheet-facing `notes_sanitized` observation exports under the separate manifest/count contract below.
- Every row has a stable ID or a documented composite key. Row numbers are never identifiers.
- A content version is a positive integer.
- Approval is established by content status plus required active attestations in `REVIEWS`; inline reviewer fields are not used.

## Tab 1 — `README`

Include:

- workbook purpose;
- privacy rules;
- ID/date/multi-value conventions;
- status workflow;
- definitions of interest, concept, nudge, edge, lesson, and observation;
- export instructions;
- statement that only the local importer determines whether a bundle is valid;
- statement that Google Sheets validation is convenience, not a safety boundary.

Status workflow:

```text
draft -> proposed -> approved
draft/proposed -> rejected
approved -> paused
approved/paused -> retired
```

Only an educator/parent review may move child-facing content to `approved`.

## Tab 2 — `LISTS`

Provide named ranges for data validation:

```text
content_status: draft, proposed, approved, rejected, paused, retired
interest_status: candidate, active, paused, retired
concept_kind: anchor, bridge, mechanism, fundamental, application
concept_track: interest, learning
nudge_kind: question, comparison, prediction, demonstration, analogy, retrieval, activity
relationship_type: parent, prerequisite, related
step_kind: intro, teach
understanding_level: not_observed, not_yet, partial, clear
entered_by_role: parent, educator
locale: en-US, es-US
review_scope: science, child_content, visual_accessibility, parent_approval
review_status: active, revoked
entity_type: interest, concept, source, fact, nudge, edge, asset, lesson
```

The importer owns the authoritative enums. A workbook list that diverges from code is an import error.

## Tab 3 — `INTERESTS`

CSV header:

```csv
interest_id,lifecycle_status,approval_status,label,category,anchor_concept_ids,child_phrase_sanitized,parent_observation_sanitized,engagement_strength,first_observed_on,last_observed_on,locale,entered_by_role,notes_sanitized,content_version
```

Field rules:

- `interest_id`: stable ID, for example `fast-cars`.
- `lifecycle_status`: `candidate`, `active`, `paused`, or `retired`.
- `approval_status`: standard content status; active graph requires `approved`.
- `label`: parent-facing concise label.
- `category`: broad non-sensitive grouping such as `vehicles`.
- `anchor_concept_ids`: one or more explicit approved interest-track anchor concepts.
- `child_phrase_sanitized`: optional short paraphrase or sanitized quote; never a raw transcript.
- `parent_observation_sanitized`: why the parent believes this interest is durable.
- `engagement_strength`: integer `1`–`5`; parent judgment, not automated engagement optimization.
- `first_observed_on`, `last_observed_on`: dates.
- `locale`: current content locale.
- `entered_by_role`: `parent` or `educator`.
- `notes_sanitized`: optional, maximum 500 characters.

Seed row:

```csv
fast-cars,active,draft,Fast cars,vehicles,zero-to-sixty-time,"Which car gets to 60 fastest?","Repeatedly compares acceleration figures on car cards.",5,2026-08-01,2026-08-22,en-US,parent,"Use hypothetical cars unless a current claim has a reviewed source.",1
```

The actual dates must be replaced with truthful observation dates.

## Tab 4 — `CONCEPTS`

CSV header:

```csv
concept_id,status,label,kind,track,aliases,description_child,description_parent,locale,content_version
```

Field rules:

- `kind`: `anchor`, `bridge`, `mechanism`, `fundamental`, or `application`.
- `track`: `interest` or `learning`.
- `aliases`: pipe-separated labels, not identifiers.
- `description_child`: short concrete wording.
- `description_parent`: precise adult definition and boundaries.
- review fields are mandatory when approved.

Seed rows:

```csv
zero-to-sixty-time,draft,0–60 elapsed time,anchor,interest,0-to-60|launch time,"How many seconds it takes to change from 0 to 60 miles per hour.","An elapsed-time measurement over a fixed velocity change; it is not itself acceleration.",en-US,1
average-acceleration,draft,Average acceleration,fundamental,learning,change in velocity,"How quickly velocity changes over a stretch of time.","Change in velocity divided by elapsed time; a 0–60 time supports average acceleration over that interval, not instantaneous acceleration.",en-US,1
```

The seed starts as draft. Required review attestations must be added before either row becomes approved.

## Tab 5 — `SOURCES`

CSV header:

```csv
source_id,status,title,publisher,url,retrieved_on,license_or_use_notes,content_version
```

Rules:

- URLs must be HTTPS.
- `status` must be `approved` before a fact can be approved.
- `retrieved_on` records when the source was checked.
- `license_or_use_notes` records whether text, data, or media may be reused.
- Sources do not prove a generated sentence is entailed; they establish curation provenance.

Seed rows:

```csv
nasa-acceleration,draft,"Displacement, Velocity, Acceleration","NASA Glenn Research Center",https://www.grc.nasa.gov/WWW/K-12/airplane/disvelac.html,2026-08-22,"Use as scientific reference; paraphrase for child text.",1
```

The retrieval date reflects the research used to draft this plan. Recheck source availability before approval and use the actual review date.

## Tab 6 — `FACTS`

CSV header:

```csv
fact_id,status,concept_id,canonical_text,child_text,source_ids,allowed_numbers,scope_note,content_version
```

Rules:

- `concept_id` must reference an approved concept for an approved fact.
- `source_ids` are pipe-separated.
- `allowed_numbers` are exact normalized forms that child-facing output may use, pipe-separated.
- `scope_note` states what the fact does not establish.
- Canonical and child text must not contain unsupported mutable rankings.

Seed rows:

```csv
zero-to-sixty-is-time,draft,zero-to-sixty-time,"A 0-to-60 result reports the elapsed time for velocity to change from 0 miles per hour to 60 miles per hour.","A 0–60 result tells how many seconds the speed change took.",nasa-acceleration,0|60,"Does not identify the fastest current production car.",1
acceleration-definition,draft,average-acceleration,"Average acceleration is change in velocity divided by elapsed time.","Acceleration tells how quickly velocity changes.",nasa-acceleration,,"Does not describe acceleration at every instant.",1
shorter-time-greater-average,draft,average-acceleration,"For two straight-line runs with the same initial and final velocities, the shorter elapsed time has the greater average acceleration.","If both cars make the same speed change, the one that does it in less time has greater average acceleration.",nasa-acceleration,0|4|8|60,"Requires the same start and end velocities; 4 and 8 are hypothetical lesson times.",1
average-not-instant,draft,average-acceleration,"A 0-to-60 elapsed time can support average acceleration over the interval but does not reveal acceleration at every instant.","A car can accelerate differently during the run, so 0–60 supports an average.",nasa-acceleration,0|60,"Does not claim constant or instantaneous acceleration.",1
```

## Tab 7 — `NUDGES`

CSV header:

```csv
nudge_id,status,from_interest_id,from_concept_id,target_concept_id,nudge_kind,parent_goal,child_prompt,expected_signal,hint_1,hint_2,reveal_text,priority,prerequisite_concept_ids,source_ids,locale,content_version
```

Rules:

- Exactly one of `from_interest_id` and `from_concept_id` must be populated.
- `target_concept_id` must exist.
- `priority` is integer `1`–`5`, set by a parent/educator.
- `expected_signal` describes observable understanding, not time-on-app.
- Hints progress from smaller to larger.
- Approved nudges require approved target concepts and sources.
- A nudge is a candidate teaching move; it is not automatically shown to the child.

Seed row:

```csv
compare-same-speed-change,draft,fast-cars,,average-acceleration,comparison,"Connect 0–60 interest to average acceleration without claiming the time is acceleration.","Car A goes from 0 to 60 in 4 seconds. Car B takes 8 seconds. Which car has greater average acceleration?","Child identifies Car A and explains that the same speed change took less time.","Both cars make the same speed change: 0 to 60 miles per hour.","The same change in less time means greater average acceleration.","It is Car A. Both cars go from 0 to 60, but Car A does it in less time.",5,zero-to-sixty-time,nasa-acceleration,en-US,1
```

## Tab 8 — `EDGES`

CSV header:

```csv
edge_id,status,from_concept_id,to_concept_id,relationship_type,rationale,source_ids,content_version
```

Relationship semantics:

- `parent`: `from_concept_id` is the narrower/child concept; `to_concept_id` is broader.
- `prerequisite`: `from_concept_id` is the concept being learned; `to_concept_id` is knowledge required first.
- `related`: symmetric association; author/import requires `from_concept_id < to_concept_id` by ASCII stable-ID order, stores that exact canonical pair once, rejects a noncanonical/reverse/duplicate pair, and builds both adjacency directions at read time.

Seed row:

```csv
average-acceleration-related-zero-to-sixty,draft,average-acceleration,zero-to-sixty-time,related,"A fixed velocity change and its elapsed time can be used to discuss average acceleration.",nasa-acceleration,1
```

Do not encode the teaching order with a `prerequisite` edge merely to make traversal convenient.

## Tab 9 — `ASSETS`

CSV header:

```csv
asset_id,status,resource_name,media_type,sha256,title,description,alt_text,source_id,license_or_use_notes,content_version
```

Rules:

- `resource_name` is package-relative under `assets/`; no absolute path or `..`.
- First slice accepts `image/svg+xml` only.
- `sha256` is lowercase 64-character hexadecimal calculated from exact bytes.
- title, description, and alt text are required.
- `source_id` is blank for an original project-authored diagram or references a reviewed source.
- status approval requires active `visual_accessibility` and `parent_approval` attestations.
- the bundle includes the exact asset file and its manifest hash.

The seed asset row is created by a local helper after the SVG exists so no placeholder hash can be mistaken for a real one. Its stable ID is `chain-1-acceleration-visual`.

## Tab 10 — `LESSONS`

CSV header:

```csv
lesson_id,status,title,interest_id,locale,audience,goal,grounding_scope,fallback_text,redirect_text,max_turns,content_version
```

Seed row:

```csv
chain-1-acceleration,draft,"What does 0–60 tell us?",fast-cars,en-US,ages-7-9,"Distinguish elapsed 0–60 time from average acceleration.","Straight-line 0-to-60 elapsed time, velocity change, and average acceleration. Excludes current car rankings, brand performance, crashes, and buying advice.","That question goes beyond this lesson. Let's save it for a grown-up to check, and come back to 0–60 time and acceleration.","Let's stay with 0–60 time and average acceleration. A grown-up can help save that other question for later.",8,1
```

`max_turns` is a reviewed safety/session bound, not an engagement target. Effective runtime maximum is the minimum of this value and the operator profile’s maximum.

## Tab 11 — `LESSON_STEPS`

CSV header:

```csv
lesson_id,lesson_content_version,status,step_index,step_id,step_kind,concept_id,nudge_id,asset_id,heading,body,fact_ids,scope_terms,required
```

Rules:

- `(lesson_id, lesson_content_version, step_index)` is unique.
- Step indexes are contiguous from `0`.
- `step_id` is unique within a lesson version.
- `step_kind` is only `intro` or `teach`; checks and hints have separate tabs.
- `concept_id` is required.
- `nudge_id` is optional.
- `asset_id` must reference an approved asset.
- `fact_ids` and `scope_terms` are required pipe-separated reviewed values.
- `required` must be exact `true` in schema v1; `false` is rejected because the deterministic engine has no optional-step semantic.
- The lesson sequence comes exclusively from `step_index`.
- Approved steps require approved lesson, concept, nudge when present, asset, and facts.

Seed rows:

```csv
chain-1-acceleration,1,draft,0,hook-0-to-60,intro,zero-to-sixty-time,,chain-1-acceleration-visual,"What does 0–60 measure?","A car card might say 0–60 in 4 seconds. The 4 seconds are elapsed time: how long the speed change took.",zero-to-sixty-is-time,0|60|car|seconds|time,true
chain-1-acceleration,1,draft,1,teach-acceleration,teach,average-acceleration,,chain-1-acceleration-visual,"Acceleration is a rate of change","Acceleration means how quickly velocity changes. If two cars make the same 0–60 change, the car with the shorter time has greater average acceleration.",acceleration-definition|shorter-time-greater-average|average-not-instant,0|60|acceleration|average|car|seconds|time|velocity,true
```

## Tab 12 — `LESSON_CHECKS`

CSV header:

```csv
lesson_id,lesson_content_version,status,check_id,nudge_id,prompt,success_text,reveal_text,fact_ids,scope_terms,allowed_short_replies
```

Exactly one check is allowed in the first lesson version.

Seed row:

```csv
chain-1-acceleration,1,draft,compare-average-acceleration,compare-same-speed-change,"Car A goes from 0 to 60 in 4 seconds. Car B takes 8 seconds. Which car has greater average acceleration?","Yes. Car A makes the same speed change in less time, so its average acceleration is greater.","It is Car A. Both cars go from 0 to 60, but Car A does it in less time.",zero-to-sixty-is-time|acceleration-definition|shorter-time-greater-average,0|60|acceleration|average|car|seconds|time|velocity,how|no|why|yes
```

The check’s prompt, hints, and reveal text must match the referenced nudge or the compiler reports a conflict; the lesson rows remain the authoritative authored runtime sequence.

## Tab 13 — `CHECK_CHOICES`

CSV header:

```csv
lesson_id,lesson_content_version,check_id,choice_index,choice_id,label,is_correct
```

Rules:

- composite key `(lesson_id, lesson_content_version, check_id, choice_index)`;
- indexes contiguous from `0`;
- choice IDs unique within the check;
- at least two choices;
- exactly one `is_correct=true`.

Seed rows:

```csv
chain-1-acceleration,1,compare-average-acceleration,0,car-a,Car A — 4 seconds,true
chain-1-acceleration,1,compare-average-acceleration,1,car-b,Car B — 8 seconds,false
chain-1-acceleration,1,compare-average-acceleration,2,same,They have the same average acceleration,false
```

## Tab 14 — `CHECK_HINTS`

CSV header:

```csv
lesson_id,lesson_content_version,check_id,hint_index,hint_text
```

Indexes are contiguous from `0`. First slice requires exactly two progressive hints.

Seed rows:

```csv
chain-1-acceleration,1,compare-average-acceleration,0,"Both cars make the same speed change: 0 to 60 miles per hour."
chain-1-acceleration,1,compare-average-acceleration,1,"The same change in less time means greater average acceleration."
```

## Tab 15 — `REVIEWS`

CSV header:

```csv
attestation_id,attestation_version,entity_type,entity_id,entity_version,review_scope,reviewer_role,reviewed_on,evidence_ref,reviewed_payload_sha256,review_status
```

Rules:

- no seed review is fabricated;
- `reviewer_role` is actual role, not a person’s name;
- `reviewed_on` is actual review date;
- `evidence_ref` is optional repository-relative evidence ID/path, never an external private path;
- `reviewed_payload_sha256` is required for lesson reviews and equals the exact read-only canonical child-facing compile-preview payload hash; for asset reviews it equals the asset SHA-256; it is blank for other entities;
- each attestation version is immutable;
- revocation carries the same `attestation_id`, increments `attestation_version`, and changes status to revoked in a newer full snapshot;
- replacement approval uses a new attestation ID at version 1;
- one active attestation per entity/version/scope;
- an entity’s version change invalidates prior-version attestations.

Required scopes:

- interest: `parent_approval`;
- source: `science`;
- concept/fact/edge: `science` and `child_content`;
- nudge: `science`, `child_content`, and `parent_approval`;
- asset: `visual_accessibility` and `parent_approval`;
- lesson version: `science`, `child_content`, `visual_accessibility`, and `parent_approval`.

Lesson approval covers its steps, check, choices, hints, grounding, and SVG only when all required lesson attestations carry the exact same compile-preview payload SHA-256. The preview hash excludes the TOML review-attestation section to avoid a self-reference, but includes every child-visible/runtime grounding byte. A separate publication approval binds the final TOML/SVG/index artifact set after attestations are compiled.

`reviewed_payload_sha256` is emitted into each strict PR-02 `ReviewAttestation` TOML object and must equal the package index’s recomputed lesson-payload identity. The review section, including this field, is excluded from payload hashing to avoid self-reference; publication/activation also verify it from curriculum persistence.

For a lesson, this field always means `ReviewPayload.payload_sha256` / package-index `lesson_payload_sha256`. It must never contain the CSV bundle’s raw `manifest_sha256`, final TOML package hash, or publication artifact-set hash.

## Read-only review compile preview

PR-09 implements the pure compiler before any approval or database staging. Given a zero-error draft bundle, it emits:

```python
@dataclass(frozen=True, slots=True)
class ReviewPayload:
    lesson_id: str
    lesson_content_version: int
    payload_bytes: bytes
    assets: tuple[tuple[str, bytes], ...]
    payload_sha256: str
```

`payload_bytes` is the exact PR-02 canonical lesson-payload JSON: every runtime lesson field except review metadata plus sorted referenced asset identities/hashes. `payload_sha256` hashes those exact bytes and must equal the installed package index’s `lesson_payload_sha256` for version 1. Preview writes only beneath pinned derived `curation-private/previews/` with private atomic no-replace semantics, never SQLite, an arbitrary path, or package resources; managed wipe covers it.

Reviewers inspect the rendered child-visible text/visual plus exact grounding/source projection and attest this payload hash. After review rows are added, the compiler builds final TOML with attestations; PR-10 separately presents and records the final artifact-set hash before publication.

## Tab 16 — `OBSERVATIONS`

This tab is optional and parent-controlled.

CSV header:

```csv
observation_id,session_ref,observed_at,interest_id,lesson_id,lesson_content_version,nudge_id,curriculum_binding_id,completed,hints_used,engagement_1_5,understanding,wanted_more,followup_recall,notes_sanitized
```

Rules:

- `session_ref` is a random session identifier, not a child identity.
- No transcript or audio.
- `engagement_1_5` is a parent observation.
- `understanding`: `not_observed`, `not_yet`, `partial`, or `clear`.
- `followup_recall`: blank until checked later, then `not_observed`, `not_yet`, `partial`, or `clear`.
- `notes_sanitized`: maximum 500 characters.
- Session duration is intentionally absent.

This tab may be populated manually from a local aggregate export. Automatic cloud synchronization is deferred.

## Normative local templates

Version one canonical blank/header-only template and a separate non-importable draft example:

```text
curation/templates/v1/
├── README.md
├── LISTS.csv
├── INTERESTS.csv
├── CONCEPTS.csv
├── SOURCES.csv
├── FACTS.csv
├── NUDGES.csv
├── EDGES.csv
├── ASSETS.csv
├── LESSONS.csv
├── LESSON_STEPS.csv
├── LESSON_CHECKS.csv
├── CHECK_CHOICES.csv
├── CHECK_HINTS.csv
├── REVIEWS.csv
└── OBSERVATIONS.csv

curation/examples/chain-1-v1-draft/
├── README.md
├── CSV files containing the documented draft seed rows
├── empty REVIEWS.csv
└── empty OBSERVATIONS.csv
```

The blank template has headers only. The example has no `manifest.json`, uses only draft statuses, and cannot activate. Any CSV-capable editor may be used. The local importer is authoritative.

## Optional Google Sheets editing recipe

If the parents choose Google Sheets:

1. Import/create tabs in the exact order above.
2. Freeze header rows.
3. Protect `README` and `LISTS`.
4. Apply named-range validation from `LISTS`.
5. Add conditional formatting for:
   - approved rows missing review fields;
   - duplicate IDs;
   - malformed IDs or dates;
   - blank required cells;
   - non-approved dependencies.
6. Keep content cells formula-free.
7. Restrict sharing to the consenting parents/educators.
8. Disable public link access.
9. Review Google account activity, retention, and export location before entering sanitized observations.

Google Sheets, accounts, protection, validation, and network access are conveniences, not implementation requirements or security boundaries.

CSV export may contain an evaluated formula value rather than the source formula. The importer can reject only literal formula prefixes. Activation also requires an operator attestation that the workbook was formula-free.

## Portable export bundle

Phase 1 uses a local CSV directory. When Google Sheets is used, parents export each tab manually; no Google API is required.

Export each imported tab as UTF-8 CSV with exact filenames:

```text
INTERESTS.csv
CONCEPTS.csv
SOURCES.csv
FACTS.csv
NUDGES.csv
EDGES.csv
ASSETS.csv
LESSONS.csv
LESSON_STEPS.csv
LESSON_CHECKS.csv
CHECK_CHOICES.csv
CHECK_HINTS.csv
REVIEWS.csv
assets/chain_1_acceleration.svg
```

CSV byte grammar is portable but strict: UTF-8 without BOM/NUL; one consistent record terminator per file (`LF` or `CRLF`); required final terminator; no bare `CR`, mixed terminators, blank trailing records, or embedded CR/LF cells; RFC-style doubled quotes with `delimiter=","`, `quotechar='"'`, `doublequote=True`, `escapechar=None`, and strict parsing. Hash the exact exported file bytes in the manifest, while canonical row hashes use the fixed all-quoted LF representation in the persistence plan. Per-file/row/cell limits are enforced before constructing the full object graph.

Version-1 hard limits are exact bytes: manifest `65_536`; each CSV `2_000_000`; each asset `1_000_000`; total declared files `32_000_000`; 10,000 data rows per CSV; `8_192` UTF-8 bytes per cell before tighter field-specific character limits. Read/hash bounded streams and reject a declared/actual overage before full decoding or row construction.

The operator supplies one local batch directory, never individual browser paths. Open/pin it and each exact manifest entry with no-follow semantics where supported; require regular one-link files, reject symlink/path traversal/absolute/case-collision/duplicate entries, hash and parse the same descriptor bytes, and re-stat before stage. If the host cannot qualify equivalent anti-swap behavior, validation may report issues but publication/activation is blocked.

`OBSERVATIONS.csv` is never part of a curriculum import bundle. Its header-only template is an editing/reference convenience; real observations use the separate local observation-export bundle below and are never imported into curriculum persistence.

Place files in an operator-selected batch directory with:

```text
manifest.json
```

Manifest contract:

```json
{
  "schema_version": 1,
  "batch_id": "stable-kebab-id",
  "exported_at": "UTC RFC 3339 timestamp",
  "exported_by_role": "parent or educator",
  "formula_free_attested": true,
  "files": {
    "INTERESTS.csv": "sha256",
    "CONCEPTS.csv": "sha256",
    "SOURCES.csv": "sha256",
    "FACTS.csv": "sha256",
    "NUDGES.csv": "sha256",
    "EDGES.csv": "sha256",
    "ASSETS.csv": "sha256",
    "LESSONS.csv": "sha256",
    "LESSON_STEPS.csv": "sha256",
    "LESSON_CHECKS.csv": "sha256",
    "CHECK_CHOICES.csv": "sha256",
    "CHECK_HINTS.csv": "sha256",
    "REVIEWS.csv": "sha256",
    "assets/chain_1_acceleration.svg": "sha256"
  }
}
```

The importer verifies hashes before parsing.

`manifest_sha256` is SHA-256 of the exact raw `manifest.json` bytes as read, before JSON parsing. Parse with duplicate-key rejection and exact field/type/enum/hash/path rules, re-encode the decoded object with PR-02 `canonical_json_bytes()`, and require raw bytes to equal that canonical encoding plus exactly one final LF; the generator always writes that form. `manifest.json` does not contain its own hash.

`OBSERVATIONS.csv` and `observation_notes_neutralized` are rejected as unknown curriculum-manifest entries. The curriculum file map is exact; no optional file is accepted.

## Import architecture

Create:

- `curation/templates/v1/README.md`
- `curation/templates/v1/LISTS.csv`
- blank header-only CSV templates for tabs 3–16
- `curation/examples/chain-1-v1-draft/` with documented draft seed rows, empty reviews/observations, and no manifest
- `src/lerni/explore/curation_models.py`
- `src/lerni/explore/curation_csv.py`
- `src/lerni/explore/curation_validation.py`
- `src/lerni/explore/curriculum_store.py`
- `src/lerni/explore/curriculum_graph.py`
- `src/lerni/explore/content_compile.py`
- `src/lerni/explore/recommendations.py`
- corresponding tests under `tests/explore/`

Protocols:

```python
class CurationBundleSource(Protocol):
    def read_manifest(self) -> bytes: ...
    def read_file(self, relative_path: str) -> bytes: ...
```

The first source implementation reads a local directory. A future Google Sheets adapter may implement the same source protocol.

The exact immutable import types, SQL schema, version rules, activation pointer, and transactions are normative in [Curriculum persistence](./08a-curriculum-persistence.md).

## Validation pipeline

Validate in this order:

1. Manifest schema and required files.
2. File hashes.
3. UTF-8 and CSV headers.
4. Cell normalization, literal formula-prefix rejection, and formula-free operator attestation.
5. Field types, enum values, IDs, dates, and lengths.
6. Privacy scan for forbidden columns and obvious personal data.
7. Duplicate primary keys.
8. Required active review attestations by entity/version/scope.
9. Cross-tab references.
10. Approval dependencies.
11. Edge constraints.
12. Asset file hashes and safe SVG checks.
13. Lesson-step/check/choice/hint contiguity and reference checks.
14. Fact/source/current-context grounding.
15. Active graph construction.
16. Compiled lesson generation.

Errors include:

- filename;
- CSV row number;
- stable row ID when parsable;
- field;
- machine-readable code;
- human-readable message.

Messages use fixed field/code-oriented wording and never echo raw cell values. No row is applied when any validation error exists.

Warnings may be emitted for:

- long child text;
- missing optional aliases;
- an active interest with no approved nudge;
- an approved concept with no facts;
- an approved nudge not used by a lesson;
- a related edge duplicated in reverse order;
- a lesson with no curated visual.

Warnings require parent review but do not automatically block unless promoted by policy.

## Curriculum database

Use the separate content database derived from the runtime root. It is distinct from telemetry and Study.

Tables:

- `content_schema_version`
- `import_batches`
- `interests`
- `curriculum_concepts`
- `curriculum_sources`
- `curriculum_facts`
- `curriculum_nudges`
- `curriculum_edges`
- `curriculum_assets`
- `curriculum_lessons`
- `curriculum_lesson_steps`
- `curriculum_lesson_checks`
- `curriculum_check_choices`
- `curriculum_check_hints`
- `curriculum_review_attestations`
- `curriculum_bindings`
- `active_content_snapshot`

Requirements:

- all tables carry source batch and content version;
- activation is transactional;
- active snapshot changes only after a clean staged import;
- previous active snapshot remains intact on failure;
- imported rows are immutable within a batch;
- retirement is an explicit newer row, not destructive deletion;
- telemetry tables are absent;
- Study tables are absent;
- raw CSV cells outside validated fields are not retained.

This table list is explanatory only; the complete DDL in the curriculum-persistence subplan is authoritative.

## Dry-run and activation

The import command or callable must support:

```text
validate bundle
-> show deterministic report
-> stage immutable rows/assets
-> compile and publish reviewed artifacts
-> verify installed package hashes
-> explicit activate
```

Dry-run is the default.

Activation requires:

- zero validation errors;
- explicit batch ID;
- manifest hash confirmation;
- parent/educator confirmation;
- successful compilation of every active lesson;
- published lesson/asset/index bytes stored and installed hashes verified;
- successful graph invariant checks.

Never auto-activate a newly downloaded or modified sheet.

## Compiling the first packaged lesson

For the first slice:

1. Generate the v1 seed rows from the installed PR-02 lesson artifact and assert every child-facing/source/review field round-trips; hand-maintained drift is an error.
2. Read the active `chain-1-acceleration` lesson, steps, check, ordered choices, and ordered hints.
3. Resolve referenced concepts, nudge, facts, sources, asset bytes/hash, scope terms, allowed replies, maximum turns, and review attestations.
4. Produce the strict lesson TOML, package index, and asset contract from the lesson-core plan.
5. Produce a deterministic content manifest with input batch/hash and output hash.
6. Require the compiled v1 `lesson_payload_sha256` to equal the installed pilot package index’s `lesson_payload_sha256`. The only permitted metadata-only TOML difference is the exact `[review]` status and `[[review.attestations]]` fields defined by PR-02; the only resulting package-index difference is that lesson entry’s final TOML `sha256`. Index `lesson_payload_sha256`, all asset entries/bytes/hashes, and every non-review TOML field must remain identical. Publication approval metadata lives only in curriculum persistence/private publication manifest and never changes lesson/index schema. Any other difference requires content version 2 and makes the v1 pilot session intentionally unbindable.
7. Require human review before changing status to child-loadable.

The runtime never reads a live spreadsheet directly.

The packaged TOML remains the child-facing immutable snapshot for the first milestone. The content database and sheet establish its curation provenance and future graph mapping.

## Priming the early graph

The first active graph contains:

- interest: `fast-cars`;
- anchor concept: `zero-to-sixty-time`;
- learning concept: `average-acceleration`;
- reviewed related edge between those concepts;
- reviewed nudge: `compare-same-speed-change`;
- explicit lesson: `chain-1-acceleration`;
- lesson steps that reference both concepts and the nudge;
- reviewed acceleration source and grounded facts;
- immutable `CurriculumBinding` linking exact lesson ID/version/canonical payload plus the precomputed final attestation-bearing package hash (which publication/activation must reproduce exactly) to its interest, nudge, and ordered concept IDs.

Build adjacency with ordinary Python mappings for this graph size.

Graph invariants:

- every edge endpoint exists and is approved;
- no self-edge;
- related edges are already author/import-validated canonical ordered pairs and produce symmetric adjacency;
- prerequisite subgraph is acyclic;
- parent edges have documented direction;
- graph cycles through related edges are allowed;
- every active interest has at least one approved nudge or a warning;
- every active approved interest has at least one approved `track=interest`, `kind=anchor` concept in `anchor_concept_ids`;
- every active lesson starts from its declared interest;
- every active lesson target is reachable through its explicit lesson references;
- every schema-v1 approved lesson references exactly one distinct non-empty `nudge_id` across its steps/check; that ID is the binding’s `nudge_id`;
- no graph path is interpreted as lesson order;
- no candidate/proposed content enters the active snapshot.

Telemetry stores only the `curriculum_binding_id`; interest/nudge/concept mappings are resolved from the immutable content snapshot. The binding survives later graph edits and prevents historical sessions from being reinterpreted.

The first pre-graph pilot records lesson ID, content version, exact package hash, and canonical lesson-payload hash with a null binding. After activation, a parent-token-protected migration may attach the new binding only when ID/version and payload hash exactly match. A package difference limited to PR-02's exact review block/resulting index lesson SHA is disclosed but does not reinterpret child/runtime payload. Sessions whose payload or assets differ remain unbound and are excluded from graph feedback; no fuzzy inference is allowed.

PR-10 implements `binding_migration.py`:

```python
@dataclass(frozen=True, slots=True)
class BindingMigrationPreview:
    session_id: UUID
    recorded_lesson_id: str
    recorded_content_version: int
    recorded_package_sha256: str
    recorded_lesson_payload_sha256: str
    proposed_binding_id: str
    proposed_package_sha256: str
    proposed_lesson_payload_sha256: str
    package_sha256_matches: bool
    exact_match: bool


class BindingMigrationService:
    def preview(self, *, parent_token: str) -> tuple[BindingMigrationPreview, ...]:
        ...

    def attach(
        self,
        session_id: UUID,
        binding_id: str,
        *,
        expected_lesson_payload_sha256: str,
        confirmed: bool,
        parent_token: str,
    ) -> SessionRecord:
        ...
```

Preview is deterministic/read-only and shows IDs/hashes only. `exact_match` means lesson ID, content version, and canonical payload identity; package equality is reported separately. Attach recomputes active binding/payload identity, requires exact match and explicit confirmation, and delegates the one-time telemetry update. It never binds by title/date/text/graph proximity.

## Post-graph parent-guided recommendation contract

This section is design input for plan 08b. It is not implemented or accepted as part of the curation/graph milestone.

Initial recommendations are deterministic candidates shown to a parent, never directly to the child.

The exact readiness model, eligibility filters, warning behavior, scope object, persistence, observation aggregation, ordering tuple, defer/reject behavior, and lesson-assignment state are defined only in [Recommendation and feedback contract](./08b-recommendation-feedback.md). This graph plan intentionally duplicates none of those rules.

Candidate explanation includes:

- source interest;
- target concept;
- nudge kind;
- parent-authored goal;
- prerequisite status;
- facts and sources;
- prior observation summary;
- why the candidate is eligible;
- what remains unverified.

Do not order by:

- session duration;
- message count;
- emotional manipulation;
- return streaks;
- opaque model score;
- raw transcript sentiment;
- advertising or monetization value.

The parent must choose `approve for next lesson`, `defer`, or `reject`.

An approved recommendation creates a new explicit lesson assignment; it does not mutate the domain graph.

## Future generated suggestions

A future suggestion capability may propose:

- a candidate bridge concept;
- a candidate nudge;
- a candidate related/prerequisite edge;
- a candidate fact or question.

Every suggestion:

- enters with `proposed` status;
- identifies inputs and rationale;
- contains no child-visible content by default;
- requires source review;
- requires parent/educator approval;
- is never auto-activated;
- is never allowed to rewrite an approved lesson in place.

This contract is provider- and model-neutral.

## Feedback integration

Local telemetry maps sessions to:

- `interest_id`;
- `lesson_id`;
- `lesson_content_version`;
- `nudge_id`;
- `curriculum_binding_id`, which resolves immutable concept IDs from the content snapshot;
- completion;
- hints used;
- policy outcome categories;
- parent observations;
- later recall observation.

The local aggregate exporter may produce `OBSERVATIONS.csv`.

PR-10 owns `src/lerni/explore/observation_export.py`:

```python
@dataclass(frozen=True, slots=True)
class ObservationExportPreview:
    export_id: UUID
    created_at: datetime
    source_session_ids: tuple[UUID, ...]
    source_observation_ids: tuple[UUID, ...]
    csv_bytes: bytes
    csv_sha256: str
    manifest_bytes: bytes
    manifest_sha256: str


def preview_observations(
    scope: ObservationExportScope,
    parent_token: str,
) -> ObservationExportPreview:
    ...


def write_observations(
    preview: ObservationExportPreview,
    *,
    confirmed: bool,
    parent_token: str,
) -> GeneratedExportSummary:
    ...
```

The separate export manifest is canonical JSON with schema version, random export ID, exact `observation_bundle` kind, UTC creation time, active batch/manifest identity, stable-sorted exact source session/observation UUID arrays plus matching counts, `spreadsheet_neutralized=true`, nonnegative `neutralized_note_count`, and exactly `{"OBSERVATIONS.csv": <sha256>}`. These opaque local IDs let lifecycle deletion identify and remove an affected aggregate export without retaining child text. Under the shared mutation lock, write re-queries/recomputes the complete preview using the preview’s fixed export ID/creation time and requires the same IDs/hashes before publishing; a concurrent delete/change rejects and discards the stale preview. Preview bytes equal written bytes. Publish beneath the derived export root with atomic no-replace semantics, fsync file/directory, and no browser path.

For spreadsheet-facing `notes_sanitized` only, after ordinary sanitization/trim, a first non-space `=`, `+`, `-`, or `@` is neutralized by prefixing one literal ASCII apostrophe and incrementing the manifest count. If that would exceed the 500-character field limit, emit fixed `[WITHHELD:spreadsheet_formula_prefix]` instead of truncating. No other cell is rewritten; an unsafe non-note field blocks export.

PR-10 registers the strict `observation_bundle` parser with the PR-05 lifecycle export registry so generic token-guarded list/delete works by export UUID.

For bound sessions, `interest_id` and `nudge_id` in that export are derived from `CurriculumBinding`; they are never independently trusted telemetry fields. Unbound sessions are excluded from the graph observation export and remain available in the ordinary local session export.

Before a parent imports it into any spreadsheet:

- omit turns and transcripts;
- omit audio and file paths;
- omit child identifiers;
- omit runtime adapter names and credentials;
- sanitize notes again;
- show a preview;
- require explicit confirmation.
- neutralize leading spreadsheet formula characters in exported notes and disclose the change in the export manifest.

Feedback may inform parent review and deterministic candidate ordering. It must not automatically approve content or optimize for time spent.

## Test-first tasks

### Workbook parsing

Tests:

- valid minimal bundle parses;
- headers must match exactly;
- literal formula prefixes in content cells are rejected;
- missing formula-free operator attestation blocks activation;
- malformed IDs/dates/enums are rejected;
- multi-value IDs parse in stable order;
- unknown columns are rejected;
- forbidden child-name/audio/transcript columns are rejected.

### Referential integrity

Tests:

- approved fact requires approved concept and sources;
- approved nudge requires one source anchor, target concept, and all required reviews;
- edge endpoints must exist;
- asset hash/path/media/accessibility reviews validate;
- lesson steps must reference approved lesson/concept/nudge/asset/facts;
- step indexes are contiguous;
- check, choice, and hint indexes are contiguous;
- check has exactly one correct choice;
- lesson current-context fact/scope bindings compile exactly;
- noncanonical or reverse-duplicate related edges are rejected; one canonical row produces both adjacency directions.

### Approval

Tests:

- draft content never enters active snapshot;
- approved row without every required active scope attestation fails;
- attestation for another entity version does not count;
- revoked attestation does not count;
- retire/pause/reject then reactivate requires a higher content version and fresh exact-version attestations for every required scope; prior active rows remain history only;
- active interest without parent approval does not enter graph;
- rejected/paused/retired content is unavailable;
- a newer retired version removes content from the next active snapshot without deleting history.

### Graph

Tests:

- seed bundle produces exactly the intended two concepts and one related edge;
- prerequisite cycles fail activation;
- related cycles do not fail;
- lesson order remains independent from edges;
- active interest with no nudge emits warning;
- candidate content never appears in adjacency.
- immutable curriculum binding maps exact lesson version/hash to interest/nudge/concepts.
- zero or multiple distinct v1 lesson nudges fail compilation/binding.

### Import transactions

Tests:

- dry-run writes nothing;
- invalid batch leaves active snapshot unchanged;
- clean stage does not activate;
- publication persists exact lesson/asset/index bytes and still does not activate;
- unpublished batch cannot activate;
- installed hash mismatch cannot activate;
- explicit activation changes snapshot atomically;
- repeated import of the same batch is idempotent;
- changed file hash under the same batch ID is rejected;
- database failure rolls back.

### Compilation

Tests:

- Chain-1 compilation is deterministic;
- compiled TOML contains approved referenced facts only;
- compiled check/choices/hints match their ordered source rows;
- compiled asset and package-index hashes match;
- current-step fact/scope bindings match;
- output contains no sheet-only private notes;
- output hash changes when child-facing content changes;
- output does not change when a parent-only observation changes;
- unapproved source blocks compilation.

### Recommendations — plan 08b only

Tests:

- ineligible prerequisites remove a candidate;
- parent priority wins among equally ready candidates;
- stable ID breaks ties;
- duration and message count are absent from scoring input;
- recommendation returns an explanation;
- no recommendation is child-visible without parent approval;
- rejected candidate does not reappear until its content version changes.

### Observation export

Tests:

- aggregate export contains no transcript/audio/child-name columns;
- sanitized notes only;
- leading formula characters are neutralized in spreadsheet-facing notes;
- export manifest records neutralization;
- preview matches exported bytes;
- export requires explicit confirmation;
- local telemetry remains unchanged after export.

## Verification

Run the focused suites in red/green order, then:

```bash
"$PYTHON" -m pytest tests/explore/test_curation_csv.py -q
"$PYTHON" -m pytest tests/explore/test_curation_validation.py -q
"$PYTHON" -m pytest tests/explore/test_curriculum_store.py -q
"$PYTHON" -m pytest tests/explore/test_curriculum_graph.py -q
"$PYTHON" -m pytest tests/explore/test_content_compile.py -q
"$PYTHON" -m pytest tests/explore/test_observation_export.py -q
```

Then rerun the graph-specific automated suites, full regression, distribution check, privacy canaries, and final no-commit audit from the verification plan. The first child pilot is not automatically repeated merely because graph plumbing changed; a new pilot requires parent review of the new active snapshot.

## Milestone acceptance

The early graph/curation milestone is complete when:

- parents can fill the portable workbook in Google Sheets or another CSV-capable editor without implementation-specific knowledge;
- a manually exported bundle validates without network access;
- validation reports row-level errors;
- dry-run is non-mutating;
- approved Chain-1 rows stage, publish, verify installed hashes, and activate transactionally;
- the active graph contains the intended interest, concepts, edge, and nudge;
- the packaged lesson can be deterministically compiled from approved content;
- no lesson order is inferred from graph edges;
- aggregate observations can be reviewed locally and optionally exported without transcripts or audio;
- no model, provider, coding agent, or Google API is required by the schema or importer.
