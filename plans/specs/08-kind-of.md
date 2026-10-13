# MentalMaps: "kind of" groups (v2.20)

Approved in conversation on 2026-10-12, after two outside design reviews. Builds on the map in [spec 04](04-interest-map.md) and the list and picture in [spec 07](07-mentalmap-list.md).

**This changes a decision.** Spec 04 kept hierarchies out to keep the map minimal. On a real map, *cars* sat beside seven specific cars and *sharks* beside five specific sharks, each counted alone, so a Great White could look stronger than sharks. Groups fix that without a new kind of data.

## What people see

- **In the list,** kinds are indented (↳) under their group. A group's strength counts its kinds: "sharks · 💪 strong", with "came up on 6 days (4 through bull shark, great white)" in its details.
- **An open item** shows **Kind of:** a pick of the interests it could go under, with **Put under**, and **Not under X** for each group it's in.
- **In the picture,** kinds sit close around their group on short solid lines; a tap on a group lights up the whole family.
- **In the MentalMaps chat,** an educator can ask "group the cars and the sharks"; the agent proposes groups to tick, including a new group name ("sharks") made from items on the map.

## How it works

### Data (`interests.py`), no schema change

- A link of kind **`kind_of`** runs from the specific item to the general one (Great White → sharks): every one of these is one of those. "Part of" (engine → car) is not a kind.
- **Rules, in code:** both ends are interests; at most **2 groups** per item; no loops; at most 3 levels; never a removed name; never a link a person undid.
- **Undone links** are kept as `not_kind_of` links (drawn nowhere), so the tagger never adds them back and old code still loads the file. A person may still put the item under that group.
- **`find` treats "car" and "cars" as one name** (an `s` or `es` ending), for lookups only.

### Strength counts days, once

- `group_days(m, e)`: the set of days the item, or anything under it, came up. A day counts once, whichever kind and however many routes.
- `strength`, `faded`, `details`, the picture size, and the prompt's ranking use it, so every screen agrees. The thresholds stay (4 or more days in the last 30 is strong).
- Worked out when read, never stored: grouping or ungrouping changes nothing else.
- It only goes up: a Great White day says nothing about bull sharks. Goals are unchanged.

### Who groups (rule 5 holds)

- **The tagger** links names already on the map, or one the student just said: up to 2 `kind_of` pairs, only when obvious, never a made-up group. Its links count at once (the admin's choice); a wrong one is undone with **Not under X**.
- **People** name new groups and fix mistakes, in the list or by ticking a chat proposal. A group a person creates starts with no days of its own; its strength comes from its kinds.

### Removing and capacity

- Removing a group leaves its kinds on the map, one level up. Put back restores its links.
- The tagger's `make_room` never drops an item with kinds under it; if nothing else can go, the new interest is skipped.

### What Lerni sees

- "They love" lists top-level groups by group days, each with up to 2 of its most recent kinds: "sharks (bull shark, great white), cars (race car)". Within the 1,500-character cap; the set-aside line still comes first.

## Not in this version

- Goals under goals, or anything that rolls up explained days (never a mastery score).
- Aliases, outside taxonomies, or embeddings.
- A "tidy up" button that asks Claude to group the whole map.

## Testing

- `test_interests.py`: "car" finds "cars"; a group is at least as strong as each kind and a shared day counts once; the tagger can't loop, use goals or removed names, or re-add an undone link; removing a group lifts its kinds; a full map never drops a group.
- `test_web_roles.py`: putting an item under a group goes through the drawn owner's check.
- `scripts/eval_tagger.py`: an obvious pair, and a part-of pair that isn't linked.
- Phone size: group via the chat, move an item, and watch the group's strength; the two-lists-after-restart check.
