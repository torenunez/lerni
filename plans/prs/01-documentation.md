# PR-01 — Explore Bootstrap: Product Docs, Plan Bundle, and Agent Tooling

## Goal

Land the Explore-first documentation alignment, vendor the implementation
bundle under `plans/`, and wire Claude Code / Cursor / git commit gates so
later PRs have a single source of truth and a shared quality gate.

This GitHub PR is broader than a markdown-only docs pass: it is the
**bootstrap** that makes PR-02+ executable. Product docs remain the
normative product story; `plans/` is the normative implementation contract.

## Depends on

- Approved master decisions.
- No Explore application code.

## Normative plan

- [Documentation alignment](../specs/01-documentation.md)
- [Master plan](../cursor_master_plan.plan.md)

## Files

Modify / add:

- Product docs: `docs/mission.md`, `docs/PRD.md`, `docs/roadmap.md`,
  `docs/todo.md`, `docs/spec.md`, `docs/progress.md`, `README.md`, `CLAUDE.md`
- Explore implementation bundle: `plans/` (`prs/`, `specs/`, `runbooks/`,
  `cursor_master_plan.plan.md`, `README.md`)
- Claude Code hooks: `.claude/settings.json`, `.claude/hooks/*`
- Shared git hook: `.githooks/pre-commit`
- Thin Cursor rule: `.cursor/rules/lerni.mdc`
- `.gitignore` (ignore `.claude/settings.local.json`)

Do not modify Python package code, Study models/CLI, or package metadata.

## Manual prerequisites

- [ ] Confirm “Explore active / Study maintenance-only” remains the desired product decision.
- [ ] Confirm graph/recommendation remains post-first-pilot, not first-slice acceptance.
- [ ] Ensure a project `.venv` with `ruff` and `pytest` (gate fails closed without them).
- [ ] Ensure `jq` is on PATH for Claude Code PreToolUse commits.

No service account or credential is needed.

## Implementation tasks

- [ ] Align the eight product documents around the two-mode model.
- [ ] Vendor and organize the Explore plan bundle under `plans/`.
- [ ] Restore portable `.claude/` hooks; shared quality gate fails closed and shows tool output.
- [ ] Add dual-agent tooling (thin Cursor rule, optional `.githooks/pre-commit`).
- [ ] Document machine-local paths that are not in git (`.venv/`, `~/.lerni/`, etc.).

## Verification

Run Markdown/content checks from the normative plan, including searches for:

- claims that Study is deleted or fully hardened;
- a required provider/model/API key;
- graph-edge-as-tutor-turn wording;
- public deployment/share URL;
- automatic Google Sheets synchronization;
- graph/recommendation in first-slice completion;
- claims of COPPA compliance, production safety, or validated learning.

Then:

```bash
.claude/hooks/quality-gate.sh
git status --short
```

Expected: documentation + plans + agent tooling only; no Explore application modules; Study tests still pass.

## Acceptance

- All eight product documents use the same mode and milestone language.
- `plans/` is present, linked from README/CLAUDE, and is the implementation contract.
- First-slice and post-pilot graph/recommendation gates are distinct.
- Optional services and credentials are capability setup, not requirements.
- Quality gate fails closed when ruff/pytest (or jq on the Claude path) are missing, and surfaces tool output.

## Out of scope

- Explore application code under `src/lerni/explore/`.
- Provider selection or capability adapters.
- Content approval / child pilot.
- Study feature work.
