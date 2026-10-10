# Architecture

How Lerni works: what runs where, how a conversation grows a student's interest map, who owns which data, and which boundaries must hold. What to build is in the [PRDs](prd/); the design is the [interest map spec](../plans/specs/04-interest-map.md); what's done is in [progress](progress.md). Parts that don't exist yet are marked *planned*.

## Bird's-eye view

**Built (Release 1, steps 1–10):** everyone signs in at `/signin` to one app at `/app/`.

- **Independent students** (educators included) have **Ask**, one ongoing text conversation with Claude. After each exchange, a small background call (the tagger) updates their **interest map**: interests (sized by the days they come up), links, and bridges. They see it on **My map**, set their own goals there, and can **Upload** notes that Claude turns into proposed interests and goals to tick. Each exchange is kept 7 days in logs the admin reads (`lerni logs`).
- **Educators** also have **Maps**, where they add goals to a supervised student's map (by hand or by Upload), watch it, and leave **feedback** for the admin (`lerni feedback`), and **Students**.
- **Supervised students** see only the conversation, full screen, in the supervised voice, with an adult nearby (a household rule). Their map grows on the educator's Maps.


It assumes one household, a few students, one map per student. Students use an iPad or any browser on the home network. The admin tool (`lerni` in a terminal) is separate: the admin's own learning tool with its own data, plus `lerni student` and (planned) `lerni feedback`.

## Context

```mermaid
flowchart LR
    student([Supervised student]) -- "types" --> ipad["iPad<br/>the conversation"]
    indep([Independent student]) -- "types, goals" --> idev["Own device<br/>Ask, My map, My account"]
    educator([Educator]) -- "accounts, goals, feedback" --> edev["Phone or laptop<br/>Ask, Maps, Students"]
    subgraph home[Home network only]
        ipad -- "HTTP, sign-in" --> server["Home server<br/>always-on Mac"]
        idev -- "HTTP, sign-in" --> server
        edev -- "HTTP, sign-in" --> server
        admin([Admin]) -- "lerni serve, lerni feedback" --> server
    end
    server -. "adapter: the admin's Claude account" .-> ai[Claude]
```

The app runs on the home network only and is never exposed to the internet. It serves plain HTTP, or HTTPS when `lerni serve` gets `--cert` and `--key` (a certificate made with mkcert and installed once on each device; Release 2), and voice needs HTTPS on the same server, because browsers allow the microphone only over HTTPS ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)).

## How a conversation grows the map

```mermaid
flowchart LR
    screen["Ask / conversation"] -- "1 question" --> convo["Conversations<br/>memory only"]
    maps[("Interest maps")] -- "2 map as information" --> convo
    convo -- "3 prompt" --> claude["Claude: answer<br/>(streamed)"]
    claude -- "4 answer" --> screen
    convo -. "5 the exchange" .-> tagger["Claude: tagger<br/>(small, background)"]
    tagger -. "6 interests, links, bridge" .-> check["Server checks"] --> maps
    edev["Maps tab"] -- "goals, rename, remove" --> maps
```

1. The student sends a question.
2. The prompt is the persona for their kind, then their map as information (top interests, goals with notes, recent bridges), then the safety rules, always last.
3. Claude answers, streamed. It follows their curiosity and, every few exchanges, bridges toward one goal.
4. The answer is shown; the conversation stays in memory only.
5. In the background, a small call gets this exchange, Lerni's previous message, and the map's entries (never the username).
6. It returns which entries the exchange was about, new interests, links, and whether a bridge happened. The server applies only the observations the [spec](../plans/specs/04-interest-map.md#the-agent) lists (people control goals), under one lock per map, and throws away a result that started before a person's edit. The exchange and what the tagger did go to the 7-day log. A failure is ignored.

## Trust boundaries

- **The home network is the outer boundary:** no port forwarding, never Gradio's public share links.
- **Everyone signs in** on our own sign-in page, and Gradio's `auth_dependency` re-checks the account on every request, so after an archive or password reset every device is refused at its next request (an answer already streaming finishes).
- **Every handler resolves the signed-in account on the server** and checks every id the page sends against it. Hiding a tab, a component, or an event (`api_visibility="private"`) is not protection. Nothing per-user is built into the page layout, because Gradio sends every signed-in browser the same config. Passwords travel unencrypted on the home network until HTTPS (Release 3), which is accepted.
- **Who can do what:**

  | Who | Can |
  |---|---|
  | Admin | Everything an educator can, plus run the server, read every file on it, add or recover accounts, and read feedback in the terminal |
  | Educator (an independent account with educator access) | Everything an independent student can, plus manage every account, set goals on and watch supervised students' maps, and leave feedback |
  | Independent student | Talk with Lerni; see their own map and set its goals; change their own account |
  | Supervised student | Talk with Lerni (a household rule keeps an adult nearby) |

  No educator screen shows an independent student's map. That is privacy by default, not a protection: the educator can reset a password and sign in as that student, and the admin can read every file.
- **Devices are a household rule:** a supervised student's iPad is signed in only as that student.
- **Outbound:** all calls go to Claude (Anthropic) through the admin's Claude account, behind an adapter: the answers, the tagger, the upload, and the feedback summary. No account details are added, and Claude Code keeps no transcript on the server (Anthropic's retention still applies). A supervised student's conversation through this consumer account is a choice the admin made for the household; an API key is not planned, revisit before anyone outside the family uses the app ([spec](../plans/specs/04-interest-map.md#supervised-students)). Release 1 has no automatic reply check; the adult nearby and the 7-day logs are the check.
- **Files:** uploads are read and deleted at once; maps, feedback, and logs are written only by the server. Gradio serves cached files to anyone signed in, so nothing private is ever served as a file: the map picture is inline.

## Who owns each kind of data

| Data | What it is | Owner | Where |
|---|---|---|---|
| Student accounts | Username, display name, kind, password hash, session version, educator flag, archived flag | Educator manages; an independent student changes their own name and password | `~/.lerni/student/students/` (built) |
| Interest map | Entries (name, interest or goal, notes, days, mentions, explained and bounce dates) and links (related or bridge) | Educators for a supervised student; an independent student for their own | `~/.lerni/student/maps/<username>.json` (built) |
| Conversation | The last 20 messages, one ongoing conversation per student | That student | Memory only; gone on New conversation or a server restart (built) |
| Conversation logs | Each exchange and what the tagger did with it | The admin reads them (`lerni logs`) | `~/.lerni/student/logs/<username>/<date>.jsonl`, deleted after 7 days (built) |
| Feedback | Date, who, which map, the educator's text, the agent's summary | The admin processes it | `~/.lerni/student/feedback.jsonl` (built) |
| Sign-in | The signing secret; wrong-password delays | The app | `~/.lerni/student/secret.key`; delays in memory (built) |
| Admin data | The admin's own questions, concepts, and reviews | Admin | SQLite at `~/.lerni/lerni.db` (built) |

## Boundaries that must hold

If a change would break one of these, stop and ask.

1. **Only people set goals.** Goals and their notes come only from a signed-in educator (or an independent student for their own map), through the server. The tagger can add interests, time, and links, never goals. Feedback is summarized, never acted on.
2. **Conversation text is kept only in the 7-day logs** on the home server: never in other files, server output, or browser storage. Also saved: accounts; maps (short names drawn from the conversation, plus dates and links); feedback (an educator's own words and a summary).
3. **The safety rules come last** in every prompt, after the persona and the map, and live in code, not in the editable persona files. That's how the prompt is built, not a guarantee of what Claude says; the evals check it.
4. **Home network only.** See [trust boundaries](#trust-boundaries).
5. **Every request resolves the signed-in account on the server** by re-reading its record. A student never reaches another student's map or conversation, or an educator action.
6. **Outside services go behind an adapter**, with credentials as `env:VAR` references. Tests use fakes.
7. **The core never imports Gradio.** The core (`students`, `signin`, `jsonfiles`, `conversation`, `interests`, `tagging`, `logs`) uses only the standard library. Provider SDKs live only in `adapters/`; screens (`web/`) may import Gradio, an optional install. The student package never opens the admin tool's database.

## Codemap

Every code file, one line each: [code manifest](code-manifest.md).

- `src/lerni/student/`: `students.py` (accounts and passwords), `signin.py` (the signed cookie, who's signed in), `jsonfiles.py` (atomic JSON writes), `conversation.py` (the prompt, in-memory conversations), `personas/` (one starting persona per kind of student), `interests.py` (the map, its rules, and its store), `tagging.py` (the tagger and the map keeper), `logs.py` (7-day conversation logs), `upload.py` (reading notes, checking and adding proposals), `feedback.py` (educator feedback, summarized, never acted on), `adapters/claude_code.py` (Claude through the Claude Code CLI, including the tagger; prototype).
- `src/lerni/student/web/`: the Gradio screens: `signin_page.py`, `main.py` (tabs by role), `ask.py`, `maps.py` (My map and Maps), `mapdraw.py` (the inline SVG picture and the list), `accounts.py`.
- `src/lerni/cli.py`, `commands/`, `db.py`, `sm2.py`: the admin tool, plus `commands/student.py`, `commands/logs.py`, and `commands/feedback.py` for the student app.
- `tests/`: pytest, fakes only. `plans/`: build plans and specs.

## Later releases

| Piece | Release | Seam to leave room for now |
|---|---|---|
| Voice and HTTPS | 2 | Nothing depends on a particular address. Speech-to-text and text-to-speech run as helper programs on the home server behind two calls (`transcribe`, `speak`, set by environment variables, like every outside service); what was heard enters the conversation like typing; audio stays in memory. |
| Remembering preferences, recall | 3 | The map is the memory; preferences and recall build on it. |
| Suggested goals | 4 | Suggestions are shown for the educator to accept; they never become goals on their own (boundary 1). |
| Curated or checked content | — | None planned; if ever needed, it arrives as information in the map block, never as a separate path. |
| Without an educator present | 5 | Needs a safety review first: checked replies for supervised students and consent for sensitive subjects. |
