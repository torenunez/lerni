# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by release; the admin's build work is the running list of [upcoming PRs](#upcoming-prs-release-1-mvp). When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each release: [roadmap](roadmap.md).

## Educator

### Now: Release 1 MVP

- [ ] Open the educator view, read the Guide tab, and make a learning plan: import your rough notes with Claude, or start from the cars or sharks example, then fill in one activity card.
- [ ] Review the car activity's science with the admin (who has the review sheet). It's the activity for the MVP, because it already exists as a draft; your own activity card comes next.

### Later: Release 1 MVP

- [ ] Approve the activity's four checks: science, wording, pictures and accessibility, and OK to use.
- [ ] Once step 5 lands: sign in from your own device, add the student accounts in the Students tab, and say what's confusing.
- [ ] Rehearse the MVP on the iPad and your own device, including Stop and Reset, then authorize student use.
- [ ] Watch the student try it, keep notes private, and revise one thing.

## Admin

### Upcoming PRs: Release 1 MVP

The running list of what ships next, in order. Design: [specs/03-student-accounts.md](../plans/specs/03-student-accounts.md); step details: [Release 1 plan](../plans/release-1-mvp.md#to-build).

How PRs are split:

- **One unit per PR:** one build step (with the docs it changes), or one docs-only change, never two units in one PR.
- **In order:** each branch starts from `main` after the PR before it merges.
- **Each PR carries its own docs:** code manifest, in-app guide, todo, and progress for what it ships.
- **Merged only by the admin,** after the "done when" is checked on the real devices.
- **When a PR merges:** delete its row and add a dated entry to [progress](progress.md). Work found along the way gets a new row or a task below, not a bigger PR.

| # | PR | Branch | Ships | Done when | Status |
|---|---|---|---|---|---|
| 1 | Docs: two kinds of student | `docs/student-kinds` | The approved design and the docs reframed for it | The admin reviews and merges it | [Open: #7](https://github.com/torenunez/lerni/pull/7) |
| 2 | Step 5: accounts and one sign-in | `feat/student-accounts` | Student accounts; one app at `/` with Gradio's login and tabs by role; the Students tab; lockout; Log out; the in-app guide for the Students tab and the two kinds of student | The admin signs in on the iPad, Safari saves the password, and a reload keeps them signed in; the educator sees the educator tabs | Next |
| 3 | Step 6: plan my own | `feat/plan-my-own` | Guide, Learning plans, and My account for independent students; plan schema v2; Explore freely; self-approval; the first real Claude import; the import evals | The admin turns on Explore freely, imports their own interests, gets full cards, and the evals pass | Not started |
| 4 | Step 7: play a card | `feat/card-activities` | Card activities; one session per student; Learn and the activity screens | The admin does their own activity end to end on the iPad | Not started |
| 5 | Step 8: the supervised path | `feat/supervised-sessions` | The educator's Start, Stop, Reset, and recap; the four approvals in the app, including the car activity's; packaged activities in Learn | The educator runs a supervised student's session on the iPad from their own device | Not started |

After these, Release 1 needs content and sessions, not code: the educator approves an activity, rehearses, and a supervised student tries it (Educator and Student tasks above and below).

### Later: Release 2 Remembering

- [ ] Write `plans/release-2-remembering.md`, starting with mapping each activity revision to the concepts it teaches.

### Later: Release 3 Voice

- [ ] Plan the conversation agent with tools (reading the plan, checking the allowlist, giving hints), and grow its evals from the import evals.
- [ ] Before anyone outside the household uses the app: replace the Claude Code adapter with an API-key adapter (`env:ANTHROPIC_API_KEY`).

- [ ] Before choosing speech or model services, check each one's data retention for a student's audio and text, and get the educator's agreement.

### Admin tool maintenance

- [ ] Add database, CLI, and full-workflow tests.
- [ ] Clear ruff lint debt in `src/` (99 findings on 2026-08-23, mostly style).
- [ ] Run mypy and fix type errors.
- [ ] Add `lerni --version`.
- [ ] Check empty-database, invalid-ID, and concurrent-access behavior.

## Student

### Later: Release 1 MVP

- [ ] Independent student (the admin first): once step 7 lands, import your own interests and do an activity end to end; note what's confusing.
- [ ] Supervised student: try the MVP with the educator beside them. They can say no or stop at any time.
