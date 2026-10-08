# Progress

Last checked: 2026-10-08. Older entries are in [history.md](history.md).

## Where things stand

The plan and the tools for writing activities are ready. The student app itself is not built yet, and no student has used anything. The next step is the MVP: the educator prepares and approves one activity, and the admin builds the smallest app the student can try it in.

## For the educator

**Ready to use:**

- Blank templates for planning learning paths: [curation guide](../curation/README.md).
- Six example paths to copy from, built around cars, sharks, and soccer. They are drafts: nobody has reviewed them or tried them with a student.

**Not done yet:**

- No activity has been reviewed or approved.
- No student has tried anything yet.

**Your next step:** choose an interest, sketch three to five activities, and prepare and approve the first one. The admin builds the [MVP](roadmap.md#m2--mvp) around it, and you watch the student try it.

## For the admin

**Built and working:**

- The core of the student app: the format an activity is stored in, the code that loads approved activities, and the step-by-step engine. Automated tests cover it.
- The admin tool, the `lerni` command (renamed from `study`).
- The checker for the educator's spreadsheet files. It finds no errors in the examples, but warns that the shark, soccer, and force records have no sources yet.

**Not built yet:**

- The student app's screens (Release 1). The one stored activity, about car acceleration, is still a draft with no approvals, so a student could not see it yet.

**Your next step:** update the technical requirements for Release 1, the MVP, then build it around the educator's first approved activity.

**Open housekeeping:** the documentation rework is on [pull request #4](https://github.com/torenunez/lerni/pull/4), not yet merged; `main` is at `b523254` and this branch at `8d870c8`. Maintenance items are in the [to-do list](todo.md#admin-tool-maintenance).

## Milestones

| Milestone | What it means | Status |
|---|---|---|
| M1 — Authoring | Templates, examples, and the checker exist, and the educator has tried them | Tools exist; the educator has not tried them yet |
| M2 — MVP | Release 1: the first student app, one approved activity answered by tapping, tried by the student | Not built |
| M3–M6 — Releases 2–5 | Remembering, voice, new ideas, free conversation | Planned in the [student](prd/student.md) and [educator](prd/educator.md) PRDs |

## Evidence

Automated tests on 2026-10-08: 196 passed, 2 expected failures. Passing tests show the code behaves as specified. They do not mean anything is ready for a student. That also needs approved content, a working app, and a trial run with the educator.

Keep this file dated. Code built, content approved, app ready, and a student session are separate achievements; record each only when it actually happens.
