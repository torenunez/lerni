# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by release; the admin's build work is the running list of [upcoming PRs](#upcoming-prs). When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each release: [roadmap](roadmap.md).

## Educator

### Now: Release 1 MVP

- [ ] Open the educator view, read the Guide tab, and make a learning plan: import your rough notes with Claude, or start from the cars or sharks example, then fill in one activity card.
- [ ] Review the car card's science with the admin (who has the review sheet). It's the fourth activity in the cars example, and the supervised student's first activity; your own cards come next.

### Later: Release 1 MVP

- [ ] Once step 8 lands: approve the car card's four checks in the app: science, wording, pictures and accessibility, and OK to use.
- [ ] Once step 5 lands: sign in with your own educator account (the admin creates it), add the student accounts in the Students tab, and say what's confusing. Save only the supervised student's own password on their iPad.
- [ ] Rehearse the MVP on the iPad and your own device, including Stop and Reset, then authorize student use.
- [ ] Watch the student try it, keep notes private, and revise one thing.

## Admin

### Upcoming PRs

The running list of what ships next, in order. Design: [specs/03-student-accounts.md](../plans/specs/03-student-accounts.md); step details: [Release 1 plan](../plans/release-1-mvp.md#to-build).

How PRs are split:

- **One unit per PR:** one build step (with the docs it changes), or one docs-only change, never two units in one PR.
- **In order:** each branch starts from `main` after the PR before it merges.
- **Each PR carries its own docs:** code manifest, in-app guide, todo, and progress for what it ships.
- **Merged only by the admin,** after the "done when" is checked on the real devices.
- **When a PR merges:** delete its row and add a dated entry to [progress](progress.md). Work found along the way gets a new row or a task below, not a bigger PR.

| # | PR | Branch | Ships | Done when | Status |
|---|---|---|---|---|---|
| 1 | Step 5: accounts and one sign-in | `feat/student-accounts` | Student accounts; our own sign-in page, re-checked on every request; one app with tabs by role; the Students tab; wrong-password delays; Signed in as and Sign out; the in-app guide | On the admin's own device, Safari saves the password and a reload and Safari restart keep them signed in; an archive or reset signs out a second device at once; the educator sees the educator tabs | Open: PR #8 |
| 2 | Step 6: plan my own | `feat/plan-my-own` | Guide, Learning plans, and Explore freely for independent students; plan schema v2, set only by the server; self-approval; no Claude Code transcripts; the first real Claude import; the import evals | The admin turns on Explore freely, imports their own interests, gets full cards, and the evals pass | Not started |
| 3 | Step 7: play a card | `feat/card-activities` | Card activities (complete, and may play for this viewer); one session per student; Learn and the activity screens | The admin does their own activity end to end on their own device | Not started |
| 4 | Step 8: the supervised path | `feat/supervised-sessions` | The educator's Start, Stop, Reset, and recap; the four checks on library cards in the app | The educator runs a supervised student's session on the iPad from their own device | Not started |

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

- [ ] Independent student (the admin first): once step 7 lands, do your own activity end to end on your own device; note what's confusing.
- [ ] Supervised student: try the MVP with the educator beside them. They can say no or stop at any time.
