# The interest map: one conversation, interests and goals

Approved in conversation on 2026-10-09 (sections "What each person sees" through "Educator feedback"). "Upload" and "Build order" are proposals for the admin's review. It replaces the activity cards, learning plans, approvals, Explore freely, and the plan import from [spec 03](03-student-accounts.md); that spec's accounts, sign-in, and Ask Lerni sections still hold. Requirements: [student PRD](../../docs/prd/student.md), [educator PRD](../../docs/prd/educator.md).

## Why

Activity cards and learning plans asked the educator to write lessons, and the student to tap through them. What the family wants is simpler: the student talks with Lerni about what they love, and Lerni gently bridges toward what the educator wants them to explore. The **interest map** is a picture of that: what the student loves, what the educator is nudging toward, and the bridges between them.

Two standard names, used everywhere (docs, code, and screens), for both kinds of student:

- **Interests** are what the student loves. They grow out of the conversation (or are uploaded to seed the map). Their size shows the time spent on them.
- **Goals** are what an educator wants the student to reach (or, for an independent student, things they want to practice). Interests are green on the map; goals are coral.
- **Bridges** are where the agent led from an interest to a goal.

The conversation is the whole activity. There are no cards, plans, or approvals.

## What each person sees

- **Supervised student:** the conversation, full screen: the chat, the question box, and one Send button that becomes Stop. No tabs and no topic picker; the agent decides where to steer. The educator is beside them in every Release 1 session. Hold-to-talk replaces typing in Release 3.
- **Independent student:** Ask (no topic picker; they say what they want), **My map** (their own map; they add their own goals, things to practice, and can Upload too), and My account.
- **Educator:** their own Ask and My map, plus **Maps**: pick a supervised student to see their map, with:
  - the picture: green circles for interests, sized by time; coral circles for goals, outlined until one comes up, lightly filled once it has, and solid once the student has explained it back; dashed coral lines for bridges; anything not revisited lately fades;
  - a short list of goals below it, with **Add** (a name and optional notes), **Rename**, and **Remove** (Remove and Rename work on interests too);
  - **Upload**: paste notes or upload a file, and Claude proposes interests and goals to tick and add;
  - **Feedback**: free text for the admin (below);
  - and the Students tab, unchanged.
- **Removed:** Learn, Learning plans, Sessions, the Topic picker, and the long Guide (one line on Maps replaces it).

Only educators see a supervised student's map; the student never does. An independent student's map is visible only to them: no educator screen shows it (privacy by default, as in spec 03).

## Data

**One map per student**, `<data>/maps/<username>.json`, written atomically. Core module: `src/lerni/student/interests.py` (standard library only).

| Field | Meaning |
|---|---|
| Name | Up to 40 characters, letters, digits, spaces, and hyphens; matched without regard to case |
| Kind | `interest` (from the conversation, or uploaded) or `goal` (set by a person) |
| Notes | Optional, goals only: what the educator (or the independent student) wants the agent to know |
| Seconds, mentions | Time spent and times it came up |
| First and last seen | Dates; how recently it came up sets how faded it looks |
| Explained | Goals only: the date the student first explained it back in their own words |
| Backed off until | Goals only: set when they changed the subject right after a bridge; the agent leaves it alone until then (a few days) |
| Links | Two entries and a kind: `related` (came up together) or `bridge` (the agent led from an interest to a goal) |

- **Time** is measured on the server: the gap between one question and the next, capped at 3 minutes, so walking away doesn't count. It goes to the interest or goal the exchange was about. Size comes from seconds.
- **Limits:** about 60 entries per map. An interest that came up once and is more than 30 days old fades from the picture but stays in the file.
- **Saved:** the map and the feedback only. Conversation text still lives in memory only (one ongoing conversation per student, until New conversation or a restart) and never reaches disk or logs.
- Maps and feedback are real student data: they live only on the home server and are never committed (CLAUDE.md rule 8).

## The agent

**Answering** is one streamed call, as Ask Lerni does today. The prompt, in order:

1. the persona for that kind of student (`personas/*.md`);
2. the map, framed as information: the top 5 interests by time; the goals with their notes, least-covered first, minus any backed off; faded goals they once explained; recent bridges;
3. the safety rules, always last.

Steering, in the persona files: answer what they asked first and follow their curiosity. Every few exchanges, when it fits naturally, build one bridge from something they love to one goal (cars, then "if a car does half a lap…", then fractions). Never force it, never announce a lesson, one goal at a time. For an independent student the same reads as mixing what they enjoy with what they're practicing. Narrowing follow-up questions ("top speed or acceleration?") stay.

**Updating the map** is a second, small call after each answer, run in the background so nobody waits, on a fast, cheap model (`LERNI_TAGGER_MODEL`):

- **In:** that one exchange and the names already on the map. Never the username.
- **Out (structured):** which entries the exchange was about (up to 2), new interests (up to 2, named in the student's own words), related links, whether a bridge to a goal happened, whether the student explained a goal back in their own words, and whether they changed the subject right after a bridge.
- **Checked on the server:** short plain names only; it can't create, change, or delete goals; unknown fields are dropped. A failure is ignored, and the map just doesn't update that time.

The map is the agent's memory between days: the chat is forgotten on restart, but the next conversation starts from the map.

## Learning concepts in the design

Each adds one cue on the map or one habit for the agent, and no new screens ([learning concepts](../../docs/learning-concepts.md)):

- **Feynman technique, explain it back:** now and then, after a bridge, the agent asks the student to explain the goal in their own words. A goal they explained is drawn solid. "Explained once" means just that; it isn't mastery.
- **Spaced repetition, fade and revisit:** entries fade when they haven't come up lately. The agent prefers returning to a faded goal they once explained, with a light question about it. Fuller recall is Release 2.
- **Transfer, a second bridge:** once a goal has a bridge, the next one comes from a different interest (fractions through cars, later through pizza), without pointing out the link. Two bridges into one goal show it on the map.
- **Culturally responsive, their words:** interests are named the way the student says them ("monster trucks", not "vehicles").
- **Zone of proximal development, back off:** if they change the subject right after a bridge, the agent leaves that goal alone for a few days and then tries a gentler way in.

Left out to keep the map minimal: stepping-stone ideas between an interest and a goal, and hierarchies ("is a", "part of").

## Supervised students

- The conversation runs through the admin's Claude account, like everything else in the prototype. This is a known exception: Anthropic's consumer terms are for people 18 and over, and consumer Claude has no filtering for children. The admin chose it on 2026-10-09, on the condition that **an educator is beside the supervised student in every session**. An API key is not planned.
- Safety comes from our side: the supervised persona (short, gentle, never "wrong"), and supervised rules in code: subjects on the starting exclusion list (violence, weapons, sexual content, self-harm, drugs) and anything scary or sad get a kind redirect to their educator and something fun instead.
- Replies stream, as for independent students; with the educator present, streaming is accepted.

## Upload (proposed)

- On Maps and on My map (so independent students can use it too), **Upload**: paste notes in any shape, or upload a .txt, .md, .docx, or .pdf, as the plan import accepts today.
- Claude returns a list of proposed entries, each labeled **interest** (something they love, to seed the map) or **goal** (with short notes), for that kind of student. Nothing is saved until the person ticks which to add and presses **Add**. Uploaded interests start at zero time and grow as they come up.
- Same isolation as today's import: no tools (except reading the one PDF), no settings, an empty folder, no saved transcript.
- Pressing Upload is the consent, as with Ask in the family prototype.

## Educator feedback

- On Maps, a **Feedback** box: free text about the app's design or about a map ("he's bored of sharks, lean into soccer"; "the circles are too small on my phone").
- The agent replies with a one- or two-line summary of what it understood, and at most one clarifying question if it's vague. The educator can correct it, then presses **Save feedback**.
- **It never acts on feedback:** it doesn't change the map, the goals, or the app. A rule in code says feedback is summarized, never carried out, and the call has no tools.
- Saved to `<data>/feedback.jsonl`: date, who, which student's map (if any), their text, and the summary.
- The admin processes it in the terminal: `lerni feedback` lists entries, `lerni feedback --summary` asks Claude to group the open ones into themes, `lerni feedback done N` marks one handled. Changes are made by hand.

## Build order (proposed)

One PR per step, each from `main`, in this order. Steps 1–6 are built ([Release 1 plan](../release-1-mvp.md)).

| Step | Ships | Done when |
|---|---|---|
| 7 | **The interest map, for independent students.** `interests.py` and its store; the tagger (adapter call and server checks); the steering prompt; My map and Maps (picture as server-drawn SVG; a list with Add, Rename, Remove); the Topic picker, Learn, Learning plans, Sessions, and the long Guide removed from the screens | The admin talks about their own interests over a few days, sees them on their map sized by time, adds a goal, and sees a bridge |
| 8 | **Upload and feedback.** The import rewritten to propose interests and goals, for educators and independent students; the Feedback box; `lerni feedback` | The educator uploads notes for the supervised student and adds interests and goals; the admin uploads their own; the admin sees the feedback summarized in the terminal |
| 9 | **The supervised conversation.** The supervised student's screen is the conversation; the supervised persona and rules; their map grows | The supervised student has a short conversation with the educator beside them, and the educator sees their map grow |
| 10 | **Remove the old activity path.** `plans.py`, the old import, `catalog.py`, `engine.py`, `domain.py`, `canonical.py`, `lessons/`, `seed/`, the lesson index script, and their tests and docs | Tests pass with them gone; the code manifest matches |

## Tests and evals

Tests (fakes only, minimal, CLAUDE.md rule 4):

- the tagger's output is checked: bad names dropped, goals never created or renamed by it, and only the explained and backed-off fields set on a goal;
- the prompt carries the goals as information and puts the safety rules last;
- time per exchange is capped;
- a student never reaches another student's map; only educators see a supervised student's map;
- feedback is saved and never changes a map.

Evals (real calls, run by hand when instructions or models change; start with 2–3 cases):

- an exchange about cars is tagged "cars";
- with "cars" an interest and "fractions" a goal, a few turns produce a bridge;
- a supervised exchange stays short and gentle;
- uploaded notes become sensible interests and goals, each labeled right (step 8).

## Not in this design

Voice (Release 3); the agent suggesting new goals (Release 4); conversations without an educator present (Release 5); an editable, draggable map; more than one map per student; saving conversation text.
