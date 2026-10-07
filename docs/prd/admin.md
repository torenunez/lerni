# PRD: Admin tool

The admin's terminal tool (`study` in the code). The admin is the engineer or developer who builds and runs Lerni. Educators and parents never use it; they work in the [supervised student app](student.md).

## Outcome

The admin can do anything Lerni does from the terminal: learn topics, try out what a student would see, and tune the mechanics before the student app relies on them.

## Users

- **Admin (engineer or developer):** has full access. Learns technical topics with it, tries activities and mechanics as the student would, finds what breaks, and tunes it. Also runs and maintains the system behind the student app.

## Constraints

- Terminal only. Data stays on this computer in `~/.lerni/`.
- No credentials in files; tests use fakes and make no network calls.
- Existing commands and data keep working.
- Full access is for trying things out. Anything a child sees still goes through the student app's approval and supervision; the admin tool never puts unapproved content in front of a child.

## Release 1: test the mechanics (exists)

Today's CLI is effectively an admin testing tool. It exercises two mechanics:

- **Explaining (Feynman technique):** write raw notes, a simple explanation, gaps, then a refined explanation.
- **Spaced review (SM-2):** explain from memory, grade yourself 0–5, and get the next review date.

Commands and behavior: [admin tool reference](../reference/study.md). Open maintenance work: [todo](../todo.md#admin-tool-maintenance).

## Later

- Try out a student activity in the terminal exactly as the student app would run it, including draft activities.
- Run the curation checker and other admin tasks from the same tool.
- Package a reviewed activity for the student app, recording the approvals real people gave.
- Tune the mechanics the student app shares, once the shared core is designed.

## Out of scope

Use by educators, parents, or students.

## Decisions

- 2026-10-07: The CLI is the admin tool; educators and parents never need it.
- 2026-10-07: Today's CLI is an admin testing tool for the learning mechanics.
- 2026-10-07: The admin has full access: learn topics, try anything the student would see, and run or tune the system.
- 2026-10-07: The student app relies on mechanics the admin tunes here, so the two share a core.

## Open questions

- [NEEDS CLARIFICATION] Which parts of the core (concept map, scheduler, explanation checks) does the student app reuse, given that the admin tool's database was not built for children's data?
