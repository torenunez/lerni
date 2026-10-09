# PRD: Educator tools

An educator manages the household's student accounts and guides **supervised students**. With a supervised student, the educator is initially heavily involved in developing and supervising the learning plan, and later steps back to occasionally monitor activities to ensure they are appropriate and safe. The educator does not gate every interaction: they see and hear most sessions first-hand, and review the map of concepts the student explored instead of reading transcripts. An **independent student** is their own educator: they use the planning and approval tasks below for their own plans, and the educator never sees those plans. What the student experiences is in the [student app PRD](student.md). The admin's terminal work is in the [admin tool PRD](admin.md).

## Outcome

The educator shapes a supervised student's learning plan without code or the terminal: closely at first, then through occasional monitoring as the system earns trust.

The **learning plan** is the interests, goals, and ordered activities the educator prepares and approves for a student.

## Users

- **Educator:** adds and manages student accounts; for supervised students, builds the learning plan, approves what they see, keeps the exclusion list, and supervises from the educator's tabs. Later reviews drafts, then only monitors. The educator can also have an independent student account to learn for themselves.

## How educator involvement changes

| Stage | Student app releases | The educator… |
|---|---|---|
| 1. Seed | 1–3 | writes one or two activities by hand, approves them, and is there for sessions |
| 2. Draft and approve | 4 | approves each activity the system drafts |
| 3. Occasional monitoring | 5 | reviews the concept map, blocks paths, and answers rare consent requests |

Each stage needs evidence from the one before.

## Lists and settings

- **Allowlist:** the concepts and questions the app may explore. Approving an activity adds to it.
- **Exclusion list:** concepts never explored in any mode, and never seeded, drafted, or suggested. It starts with violence, weapons, sexual content, self-harm, and drugs; the educator adds to it any time.

| Setting | Default | Effect | From release |
|---|---|---|---|
| Exploration mode | Allowlist | Exclusion-list mode lets the student explore anything not excluded | 5 |
| Voice | Off | When on, the app listens whenever the student holds the talk button, in every session | 3 |
| Remembering | On | When off, nothing new about the student's progress is saved | 2 |

Settings never change on their own, and each takes effect at once.

## Constraints

- The educator uses only the app: everything they need, including instructions and examples, is in the educator's tabs. No git, no files, no code, no IDs.
- The educator never sees an independent student's plans or sessions; they manage only the account.
- The educator is present for every supervised Release 1 session; from Release 2, for most but not all. They can stop any session at any moment.
- Before first use, the educator agrees to which outside services receive the student's data, and can withdraw that at any time.
- No student identity or private observations go into shared curriculum.

## Release 1: seed, approve, and supervise

The educator signs in with the educator passcode, adds the student accounts, makes a learning plan, and fills in activity cards, starting from the example plans and the in-app guide. The educator's tabs (together, the **educator view**) are Guide, Students, Sessions, and Learning plans. A supervised student sees every activity the educator approved. Design: [student accounts spec](../../plans/specs/03-student-accounts.md).

### Story: Manage student accounts

As an educator, I want to add and manage the students who use the app, so that each one signs in as themselves.

- WHEN the educator adds a student THE SYSTEM SHALL save a username, a display name, the kind (supervised or independent), and a starting password, storing only the password's hash.
- WHEN the educator resets a password or archives a student THE SYSTEM SHALL apply it at once; an archived student can't sign in.
- WHEN the educator views the students THE SYSTEM SHALL show an independent student's name and kind only, never their plans or sessions.

### Story: Approve an activity

As an educator, I want to approve an activity's exact wording and pictures, so that nothing reaches the student unchecked.

- WHEN an activity has not been approved THE SYSTEM SHALL not offer it.
- WHEN its wording or pictures change THE SYSTEM SHALL require approval again.
- WHEN the educator previews a draft THE SYSTEM SHALL run it only in the educator view, marked as a draft, and never on the student's screen.

Approval covers four checks: the science is right (`science`), the wording suits the student (`student_content`), the pictures work and are described in words (`visual_accessibility`), and it's OK to use (`educator_approval`). The names in brackets are how the activity file records them. The approvals are recorded in the app (step 8), tied to the activity's exact content. Approve only after you have tried the activity yourself. Saving an activity card is not approval.

### Story: Run a session

As an educator, I want to start, stop, and reset activities, so that I stay in control.

- WHEN someone signs in as the educator THE SYSTEM SHALL require the educator's passcode.
- WHEN the educator opens Sessions on their own device THE SYSTEM SHALL list approved activities, and drafts separately for preview only.
- WHEN the educator presses Start for a supervised student THE SYSTEM SHALL show the activity's first step on that student's screen.
- WHEN the educator presses Stop THE SYSTEM SHALL end the interaction at once.
- WHEN the educator presses Reset THE SYSTEM SHALL clear progress and return the student's screen to waiting.

### Story: See a recap

As an educator, I want a short summary when an activity ends, so that I can note what worked.

- WHEN the activity ends or is stopped THE SYSTEM SHALL show which choices were picked, which hints were used, and how long it took, then discard it. Notes stay private, outside the app.

## Release 2: remembering

### Story: Write reminders and recall questions

As an educator, I want to write a short reminder and a recall question for each idea, so that the app builds on what the student explored.

- WHEN an earlier idea comes up THE SYSTEM SHALL use only the reminder and recall question the educator wrote and approved.

### Story: See and delete the record

As an educator, I want to see and delete what the app remembers, so that I control what is kept.

- WHEN the educator opens the progress view THE SYSTEM SHALL show activities finished, ideas reached, and recall results.
- WHEN the educator deletes the record THE SYSTEM SHALL remove it from Lerni's storage; copies an outside service keeps follow that service's rules.

## Settings (Releases 2, 3, and 5)

### Story: Change a setting

As an educator, I want to turn voice, remembering, and the exploration mode on or off, so that the student gains independence only when I decide.

- WHEN the educator changes a setting THE SYSTEM SHALL apply it at once and keep it until the educator changes it again.

## Release 4: review drafts

### Story: Review a draft

As an educator, I want to see each activity the system drafts, so that I decide what reaches the student.

- WHEN the system drafts an activity THE SYSTEM SHALL show it in the educator view to approve, send back, or reject.

## Release 5: occasional monitoring

### Story: Review the concept map

As an educator, I want to see which concepts the student explored and how they connect, so that I can check their learning without reading transcripts.

- WHEN the educator opens the concept map THE SYSTEM SHALL show the concepts explored and the paths between them.
- WHEN the educator blocks a path THE SYSTEM SHALL stop suggesting or discussing it.
- WHEN the educator prunes a concept THE SYSTEM SHALL remove it from the student's map.

### Story: Consent to a sensitive subject

As an educator, I want to be asked before the app discusses a sensitive subject, so that I decide without watching every conversation.

- WHEN the student raises a sensitive subject THE SYSTEM SHALL ask the educator for consent.
- WHEN the educator declines THE SYSTEM SHALL offer to add the subject to the exclusion list.

## Out of scope

Running the admin tool. Editing app code or lesson files directly.

## Decisions

- 2026-09-25: Educators author paths alongside development instead of after a pilot, because authoring, development, and early observations should inform each other.
- 2026-10-07: Educator involvement steps down in stages: seed, then draft and approve, then occasional monitoring once drafting is reliable.
- 2026-10-07: Every educator task lives in this PRD; the student PRD covers only the student, and admin terminal work stays in the admin tool PRD.
- 2026-10-07: The educator keeps an allowlist and an exclusion list, set before first use and added to over time.
- 2026-10-07: The educator is present for every Release 1 session, then usually but not always. First-hand observation plus the concept map replace reading transcripts; the educator never gates every interaction, and consent is asked only for sensitive subjects.
- 2026-10-08: Exploration mode, voice, and remembering are educator settings. They never change on their own; voice is authorized once, not per session.
- 2026-10-08: Drafting and conversation use the admin's Claude account, so keys and billing stay with whoever runs the system.
- 2026-10-08: The educator reviews drafts in the educator view.
- 2026-10-08: The starting exclusion list covers violence, weapons, sexual content, self-harm, and drugs.
- 2026-10-08: The educator writes plans in plain language; the six authoring tables were too technical for an educator. (Superseded the same day: planning moved into the educator view.)
- 2026-10-08: The educator plans only in the educator view, from the start (Release 1, step 3), primed with example plans to edit. CSV authoring, the plan sheet, and the six authoring tables are retired. The admin packages a saved card at first, then it's automated; the educator records approvals in the app (step 6).
- 2026-10-08: The educator can import a rough plan in any shape; Claude proposes a structured plan, and the educator saves or discards it. Each import asks the educator to confirm the notes go to Claude (Anthropic) and contain no names or personal details.
- 2026-10-08: The educator view runs on the educator's own device (a phone or laptop), separate from the student's iPad, and controls the same session.
- 2026-10-08: Only the educator logs in, with one passcode the admin sets; the student screen has no login. The educator can preview a draft on their own device before approving it. (Sign-in replaced 2026-10-09.)

- 2026-10-09: The educator manages every student account (supervised and independent) in a Students tab, but never sees an independent student's plans or sessions.
- 2026-10-09: The app has one sign-in; the educator signs in as `educator` with the passcode, and the separate educator view at `/educator/` goes away. (Replaces "only the educator logs in; the student screen has no login".)
- 2026-10-09: No plan assignment yet: a supervised student sees every activity the educator approved. Assignment comes when an educator has more than one supervised student.

## Open questions

- [NEEDS CLARIFICATION] (Release 4) What evidence shows drafting is reliable enough to move from approving each activity to occasional monitoring?
