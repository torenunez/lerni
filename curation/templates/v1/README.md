# Curation templates v1 — legacy partial draft

> **New authoring starts in [`../educator-paths-v1/`](../educator-paths-v1/README.md).**
> These v1 files are kept for reference. They are not where an educator should
> begin, and they are not import-compatible with `educator-paths-v1`.

These seven curriculum tables follow **part of** the older planned delivery
schema in
[`plans/specs/08-graph-recommendations.md`](../../../plans/specs/08-graph-recommendations.md).
Their headers match that spec. That is all a header match means: **no importer
exists**, and this folder is **not a complete import bundle**.

A complete delivery bundle under that spec would also need these tables, which
are absent here: `ASSETS.csv`, `LESSONS.csv`, `LESSON_STEPS.csv`,
`LESSON_CHECKS.csv`, `CHECK_CHOICES.csv`, and `CHECK_HINTS.csv` — plus the asset
bytes, a manifest with integrity handling, compilation, validation, and genuine
approvals. None of that is built ([PR-09](../../../plans/prs/09-curation-csv.md)
and later).

`educator-paths-v1` is a different, separately versioned authoring contract. It
is not directly importable into this delivery schema or into the runtime lesson
TOML. A later adapter needs a deliberate semantic mapping; renaming columns is
not enough.

## What is here

| File | Kind | Purpose |
|---|---|---|
| `README.csv` | Helper tab | Conventions and privacy rules, importable as a sheet tab |
| `EDUCATOR_TODO.csv` | Helper tab | Outstanding human decisions — source checks, the four Chain-1 sign-offs, graph tasks |
| `LISTS.csv` | Helper tab | Named ranges for dropdown validation |
| `INTERESTS.csv` … `REVIEWS.csv` | Curriculum (legacy) | Header-only templates for the seven legacy curriculum tabs |

Seeded draft rows live in
[`../../examples/chain-1-v1-draft/`](../../examples/chain-1-v1-draft/).

## Approving the Chain-1 lesson — not here

The packaged Chain-1 lesson is approved in its **TOML file**, not in this folder.
The installed catalog (`src/lerni/explore/catalog.py`) reads
`review.attestations` from `src/lerni/explore/lessons/chain_1_acceleration.toml`
and requires all four scopes — `science`, `child_content`,
`visual_accessibility`, `parent_approval` — each pinning the same
`reviewed_payload_sha256` of the exact reviewed wording. Follow
[`plans/runbooks/chain-1-source-review.md`](../../../plans/runbooks/chain-1-source-review.md).

- The actual human reviewer records their own verdict and genuine review
  evidence. A technical operator may prepare the candidate payload and point to
  the right fields; no agent or script supplies approval values, dates, or hashes.
- `REVIEWS.csv` belongs to a future curriculum-bundle workflow. Filling it does
  **not** update the installed TOML and does **not** make Chain-1 visible to a child.
- A `reviewed` status in `educator-paths-v1` records curation review only. It does
  not replace these exact-content attestations.

## Learner privacy — the INTERESTS table is legacy

`INTERESTS.csv` has columns for a child's phrase, a parent's observation,
engagement strength, and observation dates. Those are **learner records**, not
shared curriculum, and do not belong in a curriculum sheet. The columns stay so
the old format is not silently broken; do not fill them. Record real
observations in a separate private log kept outside this repository. In
`educator-paths-v1`, a starting topic is just a node, with no learner data.

## Google Sheets recipe

Sheets is optional and needs **no** Google API, OAuth, or service account. Local
CSV is authoritative.

1. `File → Import → Upload`, pick one CSV.
2. Import location: **Insert new sheet(s)**. Separator type: **Comma**.
3. Rename the tab to match the filename exactly, without `.csv`.
4. Repeat per file. Order does not matter.
5. Optional: `Data → Data validation` on a column, range `=LISTS!A2:A7` etc., to
   get dropdowns from `LISTS`.

Exporting back out: `File → Download → Comma-separated values`, one tab at a
time, filename equal to the tab name.

## Rules that bite

- **Never put child identity in the sheet.** No name, account, address, school,
  phone, email, location, raw audio, raw transcript, credentials, or medical or
  behavioral labels.
- **No agent writes a `REVIEWS` row.** Not a verdict, not a date, not a hash.
  `REVIEWS.csv` ships with headers and nothing else, and that is deliberate
  (Standing Rule 3).
- **An edge is not a lesson step.** `parent` / `prerequisite` / `related` state a
  domain relationship. Teaching order is a separate authored sequence. Do not add
  a prerequisite edge to force a traversal (Standing Rule 4).
- **Text may not begin with `=`, `+`, `@`, or `-`.** The planned importer rejects
  these rather than rewriting them, because silently neutralizing a prefix would
  alter reviewed child-facing content.

## Status

The Chain-1 lesson is `draft` with zero attestations, and the child catalog
refuses to load it. Nothing in these templates has been reviewed. See
[`plans/human-track.md`](../../../plans/human-track.md).
