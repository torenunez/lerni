# MentalMaps: an editable list of goals and interests (v2.17)

Approved in conversation on 2026-10-11 (approach A). Builds on the map from [spec 04](04-interest-map.md) and the Maps chat from [spec 06](06-educator-chat.md). Requirements: [educator PRD](../../docs/prd/educator.md) and [student PRD](../../docs/prd/student.md). The picture stays as it is for now.

## What people see

**The name.** The map is a **MentalMap** on screen and in the docs: the menu says **My MentalMap** (independent students and educators, for their own) and **MentalMaps** (educators, for supervised students). The code and data folders keep `map`.

**The list,** one component on both screens, under the picture:

- **Add:** Goal or Interest, a name, notes (goals only), and **Add**.
- **🎯 Goals,** then **💚 Interests:** a row per item with its name and a 🗑. Tapping the name opens its details right under it:
  - the strength label: 💪 strong, 🌱 growing, 🌫️ faint, or ⏳ not yet;
  - the facts:
    - the days it came up and the last time;
    - for a goal, the days Lerni thought it was explained, and whether Lerni is giving it a rest;
  - for a goal: its notes for Lerni, editable, with **Save**;
  - **Rename**;
  - its **bridges** (interest → goal) and **related** items, each a button that opens that item.
- **Removed** (closed until tapped): each removed item with **Put back**.

It replaces My map's "Add a goal" and "Rename or remove" panels and the word list. Upload notes stays on My MentalMap. On **MentalMaps** the order is: the student picker, the picture strip, the list, then the chat.

## Decisions

| Question | Decision | Why |
|---|---|---|
| Rename | Screens and docs only | No data migration; the code's names stay consistent |
| Removing an interest | Lerni never raises it, and steers away gently if the student does | What the person removing it wants; the tagger already never re-adds it |
| Undo | A Removed list with Put back | A mis-tap shouldn't be permanent |
| Strength | A label plus the facts | Quick to read, with the evidence beside it |
| Approach | A row per item with `gr.render` | A real list on a phone, and every tap is a normal server event with its role check |

## How it works

### Data (`interests.py`)

- **Removed items keep what Put back needs.**
  - `removed` (the names) stays as it is.
  - A new `removed_info` maps each removed name to its kind, notes, days, explained days, and links.
  - Older files have no `removed_info`, so their items come back as interests.
  - No schema change: the field is optional.
- **`put_back(m, name)`:**
  - takes the name off `removed`;
  - adds the item again with its kind, notes, and history, plus each link whose other end is still on the map, and counts as a person's edit (a mis-tap undone loses nothing);
  - follows the same rules as adding: name checks and the 60-entry cap.
- **`strength(entry, today)`,** from the days it came up in the last 30 days:
  - 4 or more → strong;
  - 2–3 → growing;
  - 1, or none recently but some before → faint;
  - never → not yet.
- **`details(m, entry_id, today)`:**
  - strength, days, the last day, explained days, and whether Lerni is giving it a rest;
  - its bridges and related entries as (id, name) pairs.

### Lerni's prompt

- **`map_block` gets one more line,** listing up to 8 removed **interests** as information: "Set aside by a person: …" (removed goals just stop being steered toward). The rule to act on it is in Lerni's fixed rules (`conversation.py`): never bring one up, and if the student does, acknowledge it in a few words and turn to something else they love. (Built that way because the map is never instructions; the first wording, inside the map, was ignored in the eval.)
- **The 1,500-character cap still holds,** and this line comes before "Recent bridges", so the cut drops bridges first.
- **The Maps chat agent** (`educator_map_text`) lists removed items too, so it doesn't propose them again.

### Screens (`web/mentallist.py`, new)

- **`mental_list(...)`** builds the list with `gr.render`:
  - its inputs are the map's owner, a version counter, and the open item's id;
  - after any change, the counter goes up and the list redraws.
- **Every event resolves the viewer on the server** and checks the owner with `map_owner`, as `_act` does today:
  - My MentalMap: only the viewer's own map;
  - MentalMaps: an educator, and a supervised student.
  - Item ids from the page are looked up in that map; an unknown id gets "That's no longer on the map."
- **The handlers** are plain functions over the resolved viewer, so tests need no browser:
  - add, remove, put back, rename, and save notes;
  - each reuses `add_goal`, `add_interest`, `remove`, `rename` and `set_notes`, each inside `maps.change`.
- **Removing asks nothing;** Put back is the undo.
- **On a phone:** each row is a full-width button with the 🗑 at the right end, and fields use 16px text.
- **MentalMaps redraws the picture every 30 seconds,** as today; the list redraws after each edit, a chat **Add**, opening the tab, or picking a student, since a timed redraw would wipe a half-typed rename. Each list edit also redraws the picture.

### Rule 5 still holds

People add goals; the tagger only records interests, days, and links. Adding an interest by hand is a person's choice about their own map (an independent student) or a supervised student's (an educator), like the Maps chat's ticked interests.

## Testing

Minimal, per CLAUDE.md rule 4:

- **`test_interests.py`:**
  - put back restores a removed goal with its notes;
  - an older file without `removed_info` still loads;
  - `strength` and `details` on a small map.
- **`test_tagging.py` (or wherever `map_block` is tested):** a removed interest appears as "set aside", and a removed goal doesn't.
- **`test_web_roles.py`:**
  - a supervised viewer can't add, remove, or put back;
  - an educator can't edit an independent student's MentalMap.
- **Eval (`scripts/eval_supervised.py`):** one new case where the student brings up a removed interest, and Lerni acknowledges it briefly and turns elsewhere.
- **Phone-size check:** add, open, rename, remove, put back, and jump through a bridge, on both screens.

## Not in this version

- A better picture.
- Interest notes.
- Reordering items.
- Any notice to a supervised student that something was removed (they see no map).
