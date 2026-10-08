# PRD: Educator tools

An educator is initially heavily involved in developing and supervising the learning plan, and later steps back to occasionally monitor activities to ensure they are appropriate and safe. The educator does not gate every interaction: they see and hear most sessions first-hand, and review the map of concepts the student explored instead of reading transcripts. What the student experiences is in the [student app PRD](student.md). The admin's terminal work is in the [admin tool PRD](admin.md).

## Outcome

The educator shapes a student's learning plan without code or the terminal: closely at first, then through occasional monitoring as the system earns trust.

The **learning plan** is the interests, goals, and ordered activities the educator prepares and approves for a student.

## Users

- **Educator:** builds the learning plan, approves what the student sees, keeps the exclusion list, and supervises from the educator view. Later reviews drafts, then only monitors.

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

- No terminal, no code, and no IDs: educators work in a plain plan sheet, an activity card, and the educator view.
- The educator is present for every Release 1 session; from Release 2, for most but not all. They can stop any session at any moment.
- Before first use, the educator agrees to which outside services receive the student's data, and can withdraw that at any time.
- No student identity or private observations go into shared curriculum.

## Release 1: seed, approve, and supervise

Before the app, the educator fills in a plan sheet (one plain row per activity) and an activity card for the first activity ([curation guide](../../curation/README.md)); the admin turns them into the authoring tables and the app's format.

### Story: Approve an activity

As an educator, I want to approve an activity's exact wording and pictures, so that nothing reaches the student unchecked.

- WHEN an activity has not been approved THE SYSTEM SHALL not offer it.
- WHEN its wording or pictures change THE SYSTEM SHALL require approval again.
- WHEN the educator previews a draft THE SYSTEM SHALL run it only in the educator view, marked as a draft, and never on the student's screen.

Approval covers four checks: the science is right, the wording suits the student, the pictures work, and it's OK to use. Approve only after the admin's technical checks pass and you have tried the activity yourself. Marking a row `reviewed` in the authoring tables is a drafting note, not approval.

### Story: Run a session

As an educator, I want to start, stop, and reset activities, so that I stay in control.

- WHEN someone opens the educator view THE SYSTEM SHALL ask for the educator's passcode.
- WHEN the educator opens the educator view on their own device THE SYSTEM SHALL list approved activities, and drafts separately for preview only.
- WHEN the educator presses Start THE SYSTEM SHALL show the activity's first step on the student's iPad.
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
- 2026-10-08: The educator writes plans in plain language (a plan sheet and activity cards); the admin converts them into the six authoring tables. The tables were too technical for an educator.
- 2026-10-08: The educator view runs on the educator's own device (a phone or laptop), separate from the student's iPad, and controls the same session.
- 2026-10-08: Only the educator logs in, with one passcode the admin sets; the student screen has no login. The educator can preview a draft on their own device before approving it.

## Open questions

- [NEEDS CLARIFICATION] (Release 4) What evidence shows drafting is reliable enough to move from approving each activity to occasional monitoring?
