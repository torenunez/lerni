# PRD: Admin tool

The admin's terminal tool, the `lerni` command. The admin is the engineer or developer who builds and runs Lerni. Educators never use it; they work in the [supervised student app](student.md).

## Outcome

The admin can do anything Lerni does from the terminal: learn topics, try out what a student would see, and tune the mechanics before the student app relies on them.

## Users

- **Admin (engineer or developer):** has full access. Learns technical topics with it, tries activities and mechanics as the student would, finds what breaks, and tunes it. Also runs and maintains the system behind the student app.

## Constraints

- Terminal only. Data stays on this computer in `~/.lerni/`.
- No credentials in files; tests use fakes and make no network calls.
- Existing commands and data keep working.
- The admin runs the student app: a Gradio web app on a home server (an always-on Mac), opened in Safari on an iPad on the home Wi-Fi. It uses the existing lesson format, catalog, and engine (the code calls an activity a lesson).
- Student data may leave the device, but only to services the educator agreed to. No sharing, analytics, or advertising. In Release 1, session state stays in memory and logs contain no learner content.
- These are prototype guardrails, not production moderation. One family; no public use.
- Full access is for trying things out. Anything a student sees still goes through the student app's approval and supervision; the admin tool never puts unapproved content in front of a student.

## Release 1: test the mechanics (exists)

Today's CLI is effectively an admin testing tool. It exercises two mechanics:

- **Explaining (Feynman technique):** write raw notes, a simple explanation, gaps, then a refined explanation.
- **Spaced review (SM-2):** explain from memory, grade yourself 0–5, and get the next review date.

Commands and behavior: [admin tool reference](../reference/admin.md). Open maintenance work: [todo](../todo.md#admin-tool-maintenance).

## Later

- Try out a student activity in the terminal exactly as the student app would run it, including draft activities.
- Run the curation checker and other admin tasks from the same tool.
- Package a reviewed activity for the student app, recording the approvals real people gave.
- Tune the mechanics the student app shares, once the shared core is designed.
- Host the student app outside the home (such as Hugging Face Spaces), if the student needs it away from home.
- Connect cloud services and the admin's Claude account for drafting and conversation, behind a replaceable adapter.

## Out of scope

Use by educators or students.

## Decisions

- 2026-10-07: The CLI is the admin tool; educators never need it.
- 2026-10-07: Today's CLI is an admin testing tool for the learning mechanics.
- 2026-10-07: The admin has full access: learn topics, try anything the student would see, and run or tune the system.
- 2026-10-07: The student app relies on mechanics the admin tunes here, so the two share a core.
- 2026-10-07: The student app is a Gradio web app used on an iPad rather than as a native app.
- 2026-10-08: The student app runs on a home server first: plain HTTP on the home Wi-Fi for Releases 1–2, then HTTPS on the same server for the microphone in Release 3. Hosting outside the home (such as Hugging Face Spaces) waits until it's needed.
- 2026-10-07: For now, student data may leave the device, under educator supervision.

## Open questions

- [NEEDS CLARIFICATION] (Release 3) How to add HTTPS on the home server for the microphone: a private network with its own certificates, or a locally trusted certificate. The admin decides while building.
- [NEEDS CLARIFICATION] (Release 2) Which parts of the core (concept map, scheduler, explanation checks) does the student app reuse, given that the admin tool's database was not built for students' data?
