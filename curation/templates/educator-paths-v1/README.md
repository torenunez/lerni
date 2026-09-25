# Educator path templates — `educator-paths-v1`

Blank, header-only CSV files for outlining learning paths. Open them in any
spreadsheet program (LibreOffice, Numbers, Excel, or Google Sheets — none is
required), fill in rows, and save back to CSV.

Field meanings: [`08c-educator-path-authoring.md`](../../../plans/specs/08c-educator-path-authoring.md).
A filled-in example: [`../../examples/educator-paths-v1-draft/`](../../examples/educator-paths-v1-draft/README.md).

## Where each kind of information goes

| File | One row is… | Put here | Never put here |
|---|---|---|---|
| `NODES.csv` | a reusable idea (e.g. *fractions*) | label, adult definition, aliases, scope | anything about a particular student |
| `RELATIONSHIPS.csv` | a subject fact linking two ideas | the claim type and why it holds | teaching order |
| `CONNECTIONS.csv` | a teaching move from one idea to another | why the move could help, what to check first | an observed result |
| `PATHS.csv` | one route from a starting topic | title, entry idea, overall goal | a child's name or profile |
| `PATH_STEPS.csv` | one activity in a route, in order | sequence, target idea, connection, goal, and — for the next activity only — its full wording | what actually happened in a session |
| `SOURCES.csv` | one reference | citation, optional link, what it supports | a verdict that the source is correct |

`LISTS.csv` holds the allowed values for `status`, `relationship_type`, and
`reviewer_role`. It is a helper, not curriculum.

## Worked example: add a path and prepare its first activity

1. **PATHS** — add a row: `p-trains`, a title, an entry node, a learning goal,
   `status` = `draft`.
2. **NODES** — search existing labels, aliases, and definitions first. Reuse an
   existing node when it means the same thing (e.g. `n-distance`). Otherwise add
   one, e.g. `n-trains`, with a definition and a scope note.
3. **CONNECTIONS** — for each move (entry → first target, then target → next
   target), reuse a connection whose reason still fits, or add one with its own
   `learning_reason`.
4. **PATH_STEPS** — sketch three to five rows: `p-trains-s01` with `sequence` 1,
   `p-trains-s02` with 2, and so on. Each needs a target node, a connection, and a
   `step_goal`. Leave the activity fields blank for later steps.
5. Fill **only the first step's** `opening_prompt`, `activity`,
   `understanding_check`, `expected_observation`, `materials` (write `none` if
   nothing is needed), and `content_revision` = `1`.
6. Add **RELATIONSHIPS** only for real subject claims. A teaching move does not
   need a matching subject relationship.
7. Run the checker and fix any errors:

   ```bash
   python scripts/validate_curation_templates.py --bundle path/to/your/folder
   ```

8. Ask the educator and parent to review that first activity's exact wording and
   materials. Only after a real review does anyone change `status` to `reviewed`
   and enter their role and the real date. If the wording changes later, set
   `needs_revision`, clear the review fields, and bump `content_revision`.

The checker lists unfinished activity fields as drafting notes, not errors. You
do not have to finish every step before trying one well-prepared activity.

## Spreadsheet round trip

- **Import:** open each CSV as its own sheet/tab named after the file, comma
  separated, UTF-8. In Google Sheets: *File → Import → Upload → Insert new
  sheet(s)*.
- **Export:** save each tab back to CSV under its original filename, **only the
  columns in the header** — delete any helper or formula columns you added. In
  Google Sheets: *File → Download → Comma-separated values*, one tab at a time.
- **Types:** keep `sequence` and `content_revision` as plain whole numbers and
  `review_date` as `YYYY-MM-DD`. Watch for spreadsheets turning `1` into `1.0` or
  a date into another format.
- **Leading `=`, `+`, `-`, `@`:** type these as literal text (prefix with an
  apostrophe in most spreadsheets). The checker warns about them.
- CSV does not keep dropdowns, frozen rows, colors, or formula warnings. If you
  want those, use a private workbook as your editor and export the six tables.

## Keep out of these files

Child name or initials, school, address, contact details, photos, audio,
transcripts, what a particular student said or liked, session dates, scores, and
medical, behavioral, or diagnostic information. A generic starting topic
("music") is curriculum; "my kid loves music" is a private observation — write it
in a separate private log, never in this repository.
