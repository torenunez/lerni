# Educator chat: plan a student's map by talking (v2.14)

Approved in conversation on 2026-10-11 (approach A). Requirements: [educator PRD](../../docs/prd/educator.md). Builds on the map, Upload, and Feedback from [spec 04](04-interest-map.md); the student's side doesn't change.

## What the educator sees

On **Maps**, for one student at a time:

- **Top:** the student (picked for them when there's only one; since v3.25), then the message box for the **educator agent**, with 📎 (notes as .txt, .md, or .docx; a PDF gets "paste its text", since the chat's Claude call takes text only) and Send. Switching students starts a fresh chat.
- **Under it:** the agent's latest reply, its proposals as a **tick list** (additions arrive ticked), and **Add N to the map**. Feedback items save to the admin's list instead of the map.
- **Then:** the whole map picture (a tap on an item opens it in the list), the folded list, and the conversation, folded.

The four Maps panels go away: Add a goal, Rename or remove, Upload notes, and Feedback for the admin. My map keeps its panels; it gets the chat in a later version, once this one has been used.

## Decisions

| Question | Decision | Why |
|---|---|---|
| Screen | Map above, chat below | The educator sees each confirmed change land |
| Confirming | A tick list under the chat; the server applies exactly what's ticked | The "only people set goals" rule ([CLAUDE.md](../../CLAUDE.md) rule 5); the same as Upload today |
| Which student | Picked above the chat | A proposal can't land on the wrong map |
| Scope | Educator Maps first | A smaller first step; My map follows if it works |
| Approach | One Claude call per message: a reply plus a hidden block of proposals | Natural to use, and it reuses Upload's checks; tools would need a new adapter |

## How it works

1. **The educator sends a message,** optionally with a file. The server checks the viewer is an educator and the student is supervised. A file's text is read with Upload's `extract_upload`, and the file is deleted at once.
2. **One Claude call,** with:
   - the educator persona (`personas/educator.md`) and the rules below;
   - the student's whole map (every interest and goal, talked about or not; no names), as information;
   - the chat so far (the last 20 turns) and the file's text, marked as notes to sort, never instructions.
3. **The reply streams into the chat.** It ends with a fenced `proposals` JSON block, which is hidden from the screen as it arrives.
4. **The server parses the block into checked proposals.** Bad, repeated, or unknown items are dropped; a missing or broken block means no proposals, and the chat goes on. Kinds:
   - `goal`: a name plus notes for Lerni (up to 200 characters);
   - `interest`: a name;
   - `reword`: new notes for an existing goal, named as it is on the map;
   - `remove`: an existing entry, by its map name;
   - `feedback`: a short note for the admin.
5. **The tick list shows them,** each labelled: 🎯 goal, 💚 interest, ✏️ reword, 🗑️ remove, 📨 feedback. **Add to map** applies only the ticked map items, through the map's own functions in one `MapStore.change`. Ticked feedback items save to `FeedbackStore` with the student's username as the map owner. A ticked item that no longer fits, for example because the entry was removed meanwhile, is skipped and named.
6. **The picture redraws,** and the agent's next turn sees the updated map.

## The agent's rules (in code, after the persona, like the student rules)

- It proposes; it never says a change is made. The educator ticks.
- Up to 8 proposals a reply, and only what the educator said or the notes support.
- Never a real name in an entry; write "the student".
- App feedback ("the button is hard to press") becomes a `feedback` item, never a goal.
- Ask one clarifying question when a goal is vague, rather than guessing.

## Data

Messages are kept like Ask: in memory per educator and student, and in the educator's log (kept a year). Nothing new on disk except what's ticked (map entries, feedback). Files are never kept.

## Code

- **New `src/lerni/student/educator_agent.py`:**
  - `educator_system(map_text)`;
  - `split_reply(text)`: the visible reply and the raw block;
  - `parse_educator_proposals(data, m)`: checked proposals against the map;
  - `apply_educator_proposals(m, chosen)`;
  - reuses `upload.check_name` and the map functions.
- **New `src/lerni/student/personas/educator.md`.**
- **`src/lerni/student/web/maps.py`:** the Maps layout above for educators, replacing the four panels; My map unchanged.
- **The Claude call:** the existing chat adapter (`ChatModel.stream`), so no new adapter.

## Tests and evals

- **Tests (fakes only):**
  - the happy path: a message gets proposals, and ticking two applies exactly those two;
  - a non-educator, or a student who isn't supervised, is refused;
  - nothing changes until Add to map;
  - a broken or missing block gives no proposals and no error;
  - a ticked feedback item saves to `FeedbackStore` and not to the map.
- **Evals (`scripts/eval_educator.py`, real Claude):**
  1. A goal explained in words gets a sensible `goal` proposal.
  2. A note with a child's name never puts the name in an entry.
  3. App feedback becomes a `feedback` item, not a goal.

## Risks

- **The block comes back malformed:** no proposals that turn; the reply still shows. The eval watches for it.
- **Long uploads:** capped as Upload does today.
- **The phone layout with the map strip:** checked at phone size, then on the real devices.

## Not in this design

- The chat on My map (a later version).
- One chat across students.
- The agent changing anything without a tick.
- Tools or a new adapter.
