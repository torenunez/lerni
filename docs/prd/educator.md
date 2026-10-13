# PRD: Educator tools

An educator manages the household's student accounts and guides **supervised students**. They don't write lessons: they choose a few **goals** (what they'd like the student to explore), watch the student's **interest map** grow as the student talks with Lerni, and tell the admin what to change. At first they sit beside the student in every session; later they step back. An **independent student** is their own educator: they set their own goals, and no educator screen shows their map. What the student experiences is in the [student app PRD](student.md). The admin's terminal work is in the [admin tool PRD](admin.md). Design: [interest map spec](../../plans/specs/04-interest-map.md).

## Outcome

The educator steers a supervised student's learning through what the student already loves, without code, files, or the terminal: closely at first, then by glancing at the map as the system earns trust.

## Users

- **Educator:** adds and manages student accounts; for supervised students, chooses goals, watches their maps, sits beside them in sessions, and gives the admin feedback. The educator can also learn for themselves with their own map.

## How educator involvement changes

| Stage | Student app versions | The educator… |
|---|---|---|
| 1. Beside them | 1–3 | chooses goals, is beside the student in every session, and gives feedback |
| 2. Accept suggestions | 4 | accepts or declines goals the agent suggests from the map |
| 3. Occasional monitoring | 5 | glances at the map, removes what shouldn't be steered toward, and answers rare consent requests |

Each stage needs evidence from the one before.

## Settings

| Setting | Default | Effect | From version |
|---|---|---|---|
| Voice | Off | When on, the student can hold the talk button | 2 |
| Remembering preferences | On | When off, the companion keeps no preferences beyond the map | 4 |
| Without me present | Off | When on, the supervised student may talk with Lerni without an educator beside them | 6 |

Settings never change on their own, and each takes effect at once. The starting exclusion list (violence, weapons, sexual content, self-harm, drugs) is built into the supervised rules.

## Constraints

- The educator uses only the app: everything they need is in the app (MentalMaps and Students). No git, no files, no code, no IDs.
- No educator screen shows an independent student's map. That is privacy by default, not a protection: the educator is trusted with account recovery, and a password reset lets them sign in as that student (who notices, because their password stops working).
- An adult (the educator or admin) is near a supervised student whenever they use Lerni, and can press Stop or take the iPad at any moment. That's a household rule, not something the app enforces.
- Before first use, the educator agrees to which outside services receive the student's data, and can withdraw that at any time.
- No student identity or private observations go into the repository.

## Version 1: set goals, watch, and give feedback

The educator signs in with their own account, which has educator access (the admin creates the first one), adds the student accounts, and opens **MentalMaps**.

### Story: Manage student accounts

As an educator, I want to add and manage the students who use the app, so that each one signs in as themselves.

- WHEN an educator signs in THE SYSTEM SHALL show their own Ask and My MentalMap, plus MentalMaps and Students; educator access is a flag on an independent account, never on a supervised one, and `educator` and `admin` are never usernames.
- WHEN the educator adds a student THE SYSTEM SHALL save a username (lowercase letters, digits, and hyphens, starting with a letter, never reused), a display name, the kind (supervised or independent), and a starting password (at least 8 characters for an independent student, 4 for a supervised one), storing only the password's hash.
- WHEN the educator resets a password or archives a student THE SYSTEM SHALL sign that account out on every device at once; an archived student can't sign in, and their username stays taken.
- WHEN the educator views the students THE SYSTEM SHALL show an independent student's name and kind only, never their map.

### Story: Set goals

As an educator, I want to add what I'd like the student to explore, so that Lerni bridges toward it from what they love.

- WHEN the educator tells the educator agent on MentalMaps what they'd like for a supervised student (in words, or with notes attached as .txt, .md, or .docx) THE SYSTEM SHALL propose changes, each labeled (a goal with notes for Lerni, an interest, new notes for a goal, or removing an entry), and change that student's map only with the ones the educator ticks.
- WHEN the educator taps an item in the MentalMap's picture THE SYSTEM SHALL light up its links and open it in the list.
- WHEN the educator adds, renames, or removes a goal or an interest in the MentalMap's list THE SYSTEM SHALL change the map at once. A removed entry waits in Removed, where Put back restores it with its history; Lerni never adds it back on its own, stops steering toward a removed goal, and never brings up a removed interest (if the student does, Lerni acknowledges it briefly and turns to something they love).

### Story: See the map

As an educator, I want to see a supervised student's map, so that I know what they love and whether my goals are landing.

- WHEN the educator opens MentalMaps and picks a supervised student THE SYSTEM SHALL draw their map: interests in green and goals in coral, each sized by its strength (a group counts its kinds), goals outlined until they come up, linked items drawn together, and bridges as dashed lines.
- WHEN the educator taps an item in the list THE SYSTEM SHALL show its strength (strong, growing, faint, or not yet, from the days it came up in the last 30), the facts behind it, and its bridges and related items, each a tap away.
- WHEN an interest is a kind of another (a Great White is a kind of shark) THE SYSTEM SHALL list it under that group and count the group's strength from the days any of its kinds came up, each day once; the tagger may group names already on the map, and the educator can put an item under a group, take it out (it stays out), or tick a group the MentalMaps chat proposes.

### Story: Give feedback

As an educator, I want to tell the admin what to change in plain words, so that the app improves without me learning anything technical.

- WHEN the educator mentions something about the app in the MentalMaps chat THE SYSTEM SHALL propose it as a feedback item, and save it for the admin only when the educator ticks it.
- WHEN feedback is saved THE SYSTEM SHALL never act on it: no change to the map, the goals, or the app. The admin reads it in the terminal and makes changes by hand.

### What to watch for in the first sessions

- The student uses the iPad with you beside them. Offer it in one sentence; they may say no or stop at any time.
- Plan on 5–10 minutes. Finishing is not the goal.
- Afterward, keep brief private notes, or tell the MentalMaps chat (it goes to the admin): what caught their interest, what confused them, what to change. Keep what happened separate from what you think it means.

| Watch for | It shapes |
|---|---|
| Whether the student would rather talk, type, or point | How soon voice matters |
| Whether the bridges feel natural or forced | How often and how the agent bridges |
| When attention drops | Reply length and pacing |
| Whether the replies suit them | The supervised persona |
| What you had to do: re-read, rephrase, encourage | What the app must do itself |
| Whether they can explain, not just repeat | Whether the map's "explained" matches what you saw |
| Whether the map matches what you saw | How the map is updated |

These notes are for the admin and educator, not the app; the in-app text stays short (CLAUDE.md rule 9).

## Version 3: play and points

- WHEN the educator opens Games THE SYSTEM SHALL let them race too, to rehearse; their points are their own.
- WHEN the educator picks a supervised student on MentalMaps THE SYSTEM SHALL show that student's points and cars.
- Race questions come from the student's goals and interests, so the goals on MentalMaps are what the race practices. Whether Lerni's questions now get real answers instead of emojis is noted privately.

## Version 4: remembering

### Story: See and delete what's remembered

As an educator, I want to see and delete what the app remembers about a supervised student, so that I control what is kept.

- WHEN the educator removes an entry THE SYSTEM SHALL keep it in Removed with its history, so Put back is a true undo; WHEN they press Delete for good THE SYSTEM SHALL delete that history from Lerni's storage, keeping only its name and kind so it isn't re-added; copies an outside service keeps follow that service's rules.

## Settings (Versions 2, 4, and 6)

### Story: Change a setting

As an educator, I want to turn voice, remembering, and conversation without me on or off, so that the student gains independence only when I decide.

- WHEN the educator changes a setting THE SYSTEM SHALL apply it at once and keep it until the educator changes it again.

## Version 5: accept suggested goals

- WHEN the agent suggests a goal from the map THE SYSTEM SHALL show it on MentalMaps for the educator to accept or decline.

## Version 6: occasional monitoring

### Story: Consent to a sensitive subject

As an educator, I want to be asked before the app discusses a sensitive subject, so that I decide without watching every conversation.

- WHEN the student raises a sensitive subject THE SYSTEM SHALL ask the educator for consent.

## Out of scope

Running the admin tool. Editing app code or files directly.

## Decisions

- 2026-09-25: Educators author paths alongside development instead of after a pilot, because authoring, development, and early observations should inform each other.
- 2026-10-07: Educator involvement steps down in stages: seed, then draft and approve, then occasional monitoring once drafting is reliable.
- 2026-10-07: Every educator task lives in this PRD; the student PRD covers only the student, and admin terminal work stays in the admin tool PRD.
- 2026-10-07: The educator keeps an allowlist and an exclusion list, set before first use and added to over time. (Replaced 2026-10-09 by the interest map.)
- 2026-10-07: The educator is present for every Version 1 session, then usually but not always. First-hand observation plus the concept map replace reading transcripts; the educator never gates every interaction, and consent is asked only for sensitive subjects.
- 2026-10-08: Exploration mode, voice, and remembering are educator settings. They never change on their own; voice is authorized once, not per session. (Replaced 2026-10-09 by the interest map.)
- 2026-10-08: Drafting and conversation use the admin's Claude account, so keys and billing stay with whoever runs the system.
- 2026-10-08: The educator reviews drafts in the educator view. (Replaced 2026-10-09 by the interest map.)
- 2026-10-08: The starting exclusion list covers violence, weapons, sexual content, self-harm, and drugs.
- 2026-10-08: The educator writes plans in plain language; the six authoring tables were too technical for an educator. (Superseded the same day: planning moved into the educator view.)
- 2026-10-08: The educator plans only in the educator view, from the start (Version 1, step 3), primed with example plans to edit. CSV authoring, the plan sheet, and the six authoring tables are retired. The admin packages a saved card at first, then it's automated; the educator records approvals in the app (step 6, now step 9). (Replaced 2026-10-09 by the interest map.)
- 2026-10-08: The educator can import a rough plan in any shape; Claude proposes a structured plan, and the educator saves or discards it. Each import asks the educator to confirm the notes go to Claude (Anthropic) and contain no names or personal details. (Replaced 2026-10-09 by the interest map.)
- 2026-10-08: The educator view runs on the educator's own device (a phone or laptop), separate from the student's iPad, and controls the same session.
- 2026-10-08: Only the educator logs in, with one passcode the admin sets; the student screen has no login. The educator can preview a draft on their own device before approving it. (Sign-in replaced 2026-10-09.)
- 2026-10-09: The educator manages every student account (supervised and independent) in a Students tab. No educator screen shows an independent student's plans or sessions; that's privacy by default, since the educator is trusted with account recovery.
- 2026-10-09: The app has one sign-in; the educator signs in as `educator` with the passcode, and the separate educator view at `/educator/` goes away. (Replaces "only the educator logs in; the student screen has no login".)
- 2026-10-09: No plan assignment yet: a supervised student sees every activity the educator approved. Assignment comes when an educator has more than one supervised student. (Replaced 2026-10-09 by the interest map.)
- 2026-10-09: In Version 1 the educator approves library cards in the app; the supervised student's first activity is the cars example's car card. Packaged activity files aren't played or approved in the app. (Replaced 2026-10-09 by the interest map.)
- 2026-10-09: Educator is a permission on a person's independent account, not a shared `educator` sign-in, so the educator signs in once for both learning and planning. The educator passcode is gone; the admin creates the first educator account from the terminal. (Replaces the earlier 2026-10-09 decision about signing in as `educator`.)
- 2026-10-09: The educator no longer writes plans, cards, or approvals. They choose goals (a name and optional notes, or uploaded notes Claude turns into proposed interests and goals), watch each supervised student's interest map, and give free-text feedback that the agent summarizes for the admin and never acts on. Only educators see a supervised student's map. (Replaces planning, approvals, Sessions, and the allowlist from the earlier decisions.)
- 2026-10-11: On Maps, one chat with an educator agent replaces Add a goal, Rename or remove, Upload notes, and Feedback; it proposes, and only ticked items change a map or reach the admin (v2.14, [spec 06](../../plans/specs/06-educator-chat.md)). My map keeps its panels for now.
- 2026-10-11: The map is a **MentalMap** on screen (code and data keep `map`). Each MentalMap is an editable list: removing an interest steers Lerni away from it, Put back undoes a removal, and tapping an item shows its strength and bridges (v2.17, [spec 07](../../plans/specs/07-mentalmap-list.md)).
- 2026-10-12: Interests can be grouped ("kind of"): a group's strength counts each day any of its kinds came up, so a specific shark never outgrows sharks. The tagger's groups count at once and a person can undo one; new group names come only from a person. Goals aren't grouped yet, and nothing rolls up into a mastery score.
- 2026-10-12: Play and points are Version 3: a race in Games and answers in the conversation earn a student points to spend on cars; the educator can race to rehearse and sees a supervised student's points. Later versions move up one.

## Open questions

- [NEEDS CLARIFICATION] (Version 5) What evidence shows the agent's suggested goals are good enough to move from accepting each one to occasional monitoring?
