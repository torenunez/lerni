# PR-01 — Explore-First Product Documentation

## Goal

Align repository-facing product documentation around one repo with two modes: Study maintenance-only and Explore active. This PR changes Markdown only and preserves all pre-existing uncommitted documentation/hook work.

## Depends on

- Approved master decisions.
- No code PR.

## Normative plan

- [Documentation alignment](./explore_safe_slice_01_documentation.md)
- [Master plan](./explore_safe_slice_62964d1d.plan.md)

## Files

Modify:

- `docs/mission.md`
- `docs/PRD.md`
- `docs/roadmap.md`
- `docs/todo.md`
- `docs/spec.md`
- `README.md`
- `CLAUDE.md`
- `docs/progress.md`

Do not modify Python, package metadata, tests, runtime state, or `.claude/` hooks/settings.

## Manual prerequisites

- [ ] Review the initial Git diff and identify user-owned edits in every target file.
- [ ] Confirm “Explore active / Study maintenance-only” remains the desired product decision.
- [ ] Confirm graph/recommendation remains post-first-pilot, not first-slice acceptance.

No service account or credential is needed.

## Implementation tasks

- [ ] Capture baseline status/diff for all target files.
- [ ] Rewrite mission language without erasing Study history.
- [ ] Define deterministic first slice, push-to-talk, curation graph, and recommendation as separate milestones.
- [ ] State that no required model/provider/service exists.
- [ ] Define local/account-free fallback behavior.
- [ ] Add child safety, parent supervision, retention/export/delete, and managed family-data wipe limitations.
- [ ] Add the portable CSV/Google Sheets curation boundary.
- [ ] Keep graph edges, nudges, and lesson steps semantically separate.
- [ ] Update CLI examples without implying the Study entry point is removed.
- [ ] Add progress entry that distinguishes plans from implemented behavior.
- [ ] Re-read the merged diff to ensure pre-existing AI-skill, iOS, hook, and Study content remains.

## Verification

Run Markdown/content checks from the normative plan, including searches for:

- claims that Study is deleted or fully hardened;
- a required provider/model/API key;
- graph-edge-as-tutor-turn wording;
- public deployment/share URL;
- automatic Google Sheets synchronization;
- graph/recommendation in first-slice completion;
- claims of COPPA compliance, production safety, or validated learning.

Then inspect:

```bash
git diff -- README.md CLAUDE.md docs/mission.md docs/PRD.md docs/roadmap.md docs/todo.md docs/spec.md docs/progress.md
git status --short
```

Expected: documentation-only changes; existing unrelated edits remain; no commit.

## Acceptance

- All eight documents use the same product mode and milestone language.
- First-slice and post-pilot graph/recommendation gates are distinct.
- Optional services and credentials are described as capability setup, not requirements.
- Manual parent supervision and data limitations are explicit.
- No pre-existing user work is overwritten.

## Out of scope

- Code/package changes.
- Provider selection.
- Content approval.
- Child pilot.
- Commit, push, or PR creation.
