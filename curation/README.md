# Curation — start here

This folder holds curriculum-authoring material for Lerni Explore. There are
three different things here, and only the first is where new work starts.

| If you want to… | Use | State |
|---|---|---|
| **Outline learning paths and prepare an activity (educators start here)** | [`templates/educator-paths-v1/`](./templates/educator-paths-v1/README.md) and the [six draft example paths](./examples/educator-paths-v1-draft/README.md) | Current authoring format. Checked offline by [`scripts/validate_curation_templates.py`](../scripts/validate_curation_templates.py). |
| Look at the older delivery-format drafts | [`templates/v1/`](./templates/v1/README.md) and [`examples/chain-1-v1-draft/`](./examples/chain-1-v1-draft/) | **Legacy partial draft.** Kept for reference; not a complete import bundle and not import-compatible with `educator-paths-v1`. |
| Put authored content into the app | — | **Not built.** A future import/publication workflow (roadmap M5) will map reviewed activities into packaged lessons. Until then the handoff is manual. |

The exact field meanings for the current format are in
[`plans/specs/08c-educator-path-authoring.md`](../plans/specs/08c-educator-path-authoring.md).
The machine-readable column list is
[`schemas/educator-paths-v1.json`](./schemas/educator-paths-v1.json).

## What these files are not

- **Not approval.** A clean checker result, or a row marked `reviewed`, does not
  approve anything for a child. The installed lesson's approval lives in its TOML
  `review.attestations` — see
  [`plans/runbooks/chain-1-source-review.md`](../plans/runbooks/chain-1-source-review.md).
- **Not a learner record.** Nothing about a particular student — name, what they
  liked, how a session went, dates — goes in these tables. Keep real observations
  in a separate private log, never in this repository.
- **Not the app.** The app, parent controls, and any importer are later work. See
  [`docs/roadmap.md`](../docs/roadmap.md).

Repository templates support authoring; filled curriculum copies and learner
observations remain separately managed.
