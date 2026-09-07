# Curation templates v1

Portable CSV templates for the Explore knowledge graph, per
[`plans/specs/08-graph-recommendations.md`](../../../plans/specs/08-graph-recommendations.md).
Every header here is byte-identical to that spec, so what a parent or educator
drafts imports cleanly once [PR-09](../../../plans/prs/09-curation-csv.md) builds
the validator.

These are drafting aids. **The local importer is the only thing that decides
whether a bundle is valid.** Spreadsheet data validation catches typos; it is not
a safety boundary.

## What is here

| File | Kind | Purpose |
|---|---|---|
| `README.csv` | Helper tab | Conventions and privacy rules, importable as a sheet tab |
| `EDUCATOR_TODO.csv` | Helper tab | Outstanding human decisions — source checks, the four sign-offs, graph tasks |
| `LISTS.csv` | Helper tab | Named ranges for dropdown validation |
| `INTERESTS.csv` … `REVIEWS.csv` | Curriculum | Header-only templates for the seven curriculum tabs |

Helper tabs are never part of a curriculum import. A batch manifest rejects them.

Seeded draft rows live in
[`../../examples/chain-1-v1-draft/`](../../examples/chain-1-v1-draft/) — import
those instead if you want the Chain-1 content already filled in.

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
  behavioral labels. This is cloud storage; the rest of Lerni is local by design.
- **No agent writes a `REVIEWS` row.** Not a verdict, not a date, not a hash.
  `REVIEWS.csv` ships with headers and nothing else, and that is deliberate
  (Standing Rule 3).
- **An edge is not a lesson step.** `parent` / `prerequisite` / `related` state a
  domain relationship. Teaching order is a separate authored sequence. Do not add
  a prerequisite edge to force a traversal (Standing Rule 4).
- **Text may not begin with `=`, `+`, `@`, or `-`.** The importer rejects these
  rather than rewriting them, because silently neutralizing a prefix would alter
  reviewed child-facing content.

## Status

The Chain-1 lesson is `draft` with zero attestations, and the child catalog
refuses to load it. Nothing in these templates has been reviewed. See
[`plans/human-track.md`](../../../plans/human-track.md).
