# PRD: Admin tool

The admin's terminal tool, the `lerni` command. The admin is the engineer or developer who builds and runs Lerni. Educators never use it; they work in the [student app](student.md).

## Outcome

The admin can do anything Lerni does from the terminal: learn topics, try out what a student would see, and tune the mechanics before the student app relies on them.

## Users

- **Admin (engineer or developer):** has full access. Learns technical topics with it, tries activities and mechanics as the student would, finds what breaks, and tunes it. Also runs and maintains the system behind the student app, and uses that app as an independent student, with their own account, to try it as a learner.

## Constraints

- Terminal only. Data stays on this computer in `~/.lerni/`.
- No credentials in files; tests use fakes and make no network calls.
- Existing commands and data keep working.
- The admin runs the student app: a Gradio web app on a home server (an always-on Mac), opened in Safari on an iPad on the home Wi-Fi. It uses the existing lesson format, catalog, and engine (the code calls an activity a lesson).
- Student data may leave the device, but only to services agreed to: by the educator for supervised students, by an independent student for themselves. No sharing, analytics, or advertising. In Release 1, session state stays in memory and logs contain no learner content.
- These are prototype guardrails, not production moderation. One household; no public use.
- Full access is for trying things out. Anything a student sees still goes through the student app's approval and supervision; the admin tool never puts unapproved content in front of a student. In the app, the admin is an independent student like any other: their own plans, their own approvals or Explore freely. They create the first educator account (and can recover any account) with `lerni student` on the home server, and dogfood on their own device, never the supervised student's iPad.

## Release 1: test the mechanics (exists)

Today's CLI is effectively an admin testing tool. It exercises two mechanics:

- **Explaining (Feynman technique):** write raw notes, a simple explanation, gaps, then a refined explanation.
- **Spaced review (SM-2):** explain from memory, grade yourself 0–5, and get the next review date.

Commands and behavior: [admin tool reference](../reference/admin.md). Open maintenance work: [todo](../todo.md#admin-tool-maintenance).

## Later

- Try out a student activity in the terminal exactly as the student app would run it, including draft activities.
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
- 2026-10-08: For the prototype, the student app calls Claude through the Claude Code CLI on the home server and the Claude account it's logged into (no API key). Before anyone outside the household uses the app, or it's hosted outside the home, switch to an API-key adapter; Anthropic doesn't allow offering claude.ai login in products for others. Default model: Sonnet 5.5 (`LERNI_CLAUDE_MODEL` overrides it).
- 2026-10-08: The command `study` was renamed `lerni`; `study` stays as a deprecated alias so existing scripts keep working.
- 2026-10-07: For now, student data may leave the device, under educator supervision.
- 2026-10-08: The student app runs on a home server first: plain HTTP on the home Wi-Fi for Releases 1–2, then HTTPS on the same server for the microphone in Release 3. Hosting outside the home (such as Hugging Face Spaces) waits until it's needed.
- 2026-10-09: The admin tries the student app as an independent student with their own account, importing their own interests; that dogfooding comes before a supervised student's first session.
- 2026-10-09: Claude's import gets an on-demand eval set (real calls, run by hand when its instructions, schema, or model change), never in `pytest` or the commit gate. An agent with tools waits for the Release 3 plan.
- 2026-10-09: The educator's and independent students' imports keep running through the admin's Claude account (the Claude Code CLI, no API key) for the prototype, a choice the admin made knowing that Anthropic's consumer terms don't allow making an account available to anyone else, and that Claude Code's sign-in is meant for the account holder's own use. The consent box names the admin's account, the adapter turns off Claude Code's transcript saving, and the API-key adapter replaces it before anyone outside the household uses the app.

- 2026-10-09: The admin adds the first educator account and recovers accounts with `lerni student` (add, reset-password, educator, list) on the home server; passwords are typed at a hidden prompt. The educator passcode is gone.
- 2026-10-09: Ask Lerni's conversations also run through the admin's Claude account (the same known exception to Anthropic's consumer terms), for independent students only, with no tools and no saved transcripts.
## Open questions

- [NEEDS CLARIFICATION] (Release 3) How to add HTTPS on the home server for the microphone: a private network with its own certificates, or a locally trusted certificate. The admin decides while building.
- [NEEDS CLARIFICATION] (Release 2) Which parts of the core (concept map, scheduler, explanation checks) does the student app reuse, given that the admin tool's database was not built for students' data?
