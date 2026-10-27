# Play and points, part 2: harder races, practice on the map, and probes (Version 3)

Approved in conversation on 2026-10-20. Builds on [spec 09](09-play-and-points.md) (the race, points, the garage, the results log), the map ([spec 04](04-interest-map.md), [spec 08](08-kind-of.md)), and voice ([spec 05](05-voice.md)). Requirements: [student PRD, Version 3](../../docs/prd/student.md#version-3-play-and-points).

**Why.** Since their first car upgrade, the supervised student has finished 1st in every race, with about 84% right. Races should be won by answers, pitched so about half to three quarters are right. Missed ideas should come back, and the student should sometimes explain an idea in their own words. What the race learns should show on the map, and the race should try ideas next to what the student loves, so Version 5 can suggest goals.

**Ships as**, one PR each, in this order:
- v3.16: the race looks and sounds better;
- v3.17: practice on the map;
- v3.18: pitched right;
- v3.22: missed ideas come back;
- v3.24: the bonus round;
- v3.32: probes.

v3.19 (race questions from the garage), v3.20 (a map journal and nightly backups), and v3.21 (Next after a wrong answer) sit between v3.18 and v3.22, v3.23 (Chat's goals take turns) between v3.22 and v3.24, v3.25 and v3.26 (the educator's page), v3.27 (the race starts fast), v3.28 (goal spacing and areas), v3.29 (read-aloud questions), v3.30 (a focused race), and v3.31 (one Chat) between v3.24 and v3.32; each is designed in its own plan, not here. Each version's plan file (`plans/v3.NN-*.md`) is written when it starts, from this spec.

## What people see

### The race (v3.16)

- **The track fills the screen width.** Each car's name is a small label at the start of its lane, readable in dark mode. The white car gets an outline, so it no longer looks faint.
- **The rivals are real cars:**
  - **The faster rival** is the next Showroom car they're saving for. If they own every car, it's their fastest owned car other than the one they drive. Otherwise it's Zippy.
  - **The slower rival** is their fastest owned car that's no faster than the one they drive, or Bolt.
  - Each rival shows its own picture and name.
- **Who wins** depends on right answers, in every car:
  - 4 or 5 right: 1st;
  - 3 right: 2nd;
  - 2 or fewer: 3rd.

  A new car brings new rivals and more ⚡ to show off, not easier wins.
- **The slowed message** names the rival that was actually just ahead ("The Mustang slowed down 💨"), or says "Both slowed down" when none was.
- **Sounds** (the admin's own clips, on the home server only):
  - a short engine roar on a right answer;
  - a soft sputter on a wrong one;
  - a little fanfare at the finish, whatever the place.

  One Sound switch by the track turns them off on that device (and every spoken word), and the choice is remembered there.

### Practice on the map (v3.17)

- **Goals:** tapping a goal on either MentalMap screen shows a **Practice** line, for example "Raced Oct 20 · this week 7/10 · missed lately: halves of odd numbers". From v3.22, "missed lately" becomes "due:".
- **Links:** a related or bridge item in an item's details shows its strength ("volcanoes 💪"), like an item does.
- **Bridges:** a bridge also says how it went: "held 5 days · bounced once".
- **Groups:** a group counts its kinds' bridges and explanations, as it already counts their days.
- **Read-only:** nothing here is written into the map.

### The bonus round (v3.24)

- **When:**
  - if the student is 3rd after question 3, question 4 is a bonus;
  - otherwise about 1 race in 4 has one, as question 4;
  - never more than one a race.
- **The card:**
  - "⭐ Bonus: explain it in your own words!", then a question such as "Explain how a car's brakes slow it down";
  - a text box, and Hold to talk, as in Chat;
  - **Send** and **Skip**.
- **After Send:**
  - a line such as "Nailed it! You got friction and heat. ⭐ +15", or "Good start: you got friction. The heat part: brakes turn motion into heat. ⭐ +7";
  - the car moves.
- **Skip or a blank answer** takes a small step and earns 0. It's never called wrong.

### "Want to find out more?" (v3.32)

- **At the finish,** under the place, there are up to two topic buttons, such as "🌋 Earthquakes".
- **A tap** opens Chat, where Lerni starts on that topic. The topic joins the map only if the student then talks about it.

## Numbers (tuned after trying)

| What | Value |
|---|---|
| Rival pace | set from the student's own car: the faster rival finishes between the student's 3-right and 4-right finishes, the slower one between 2 and 3 |
| Sounds | 3 clips; the roar and sputter play at most 1.5 s, the finish 2.5 s, each faded out |
| Level per goal | 1 to 5, starting at 3 |
| Level change | after 5 answers on a goal since its last change: 4 or 5 right goes one harder, 2 or fewer one easier |
| Review | a miss is due in 1 day; then right answers move it to 3 days, then 7; a right answer at 7 days retires it |
| Due ideas | at most 2 a race |
| Bonus | about 1 race in 4, or when last after question 3; nailed 15 ⭐, partly 7, a real try 2, otherwise 0 |
| Probes | 1 question per race; up to 2 topic buttons after it |

## How it works

### Rivals and pacing (v3.16, `race.py`, `garage.py`)

- **Pace from the student's car:**
  - With the student's boost `b` and `k` right answers, the student finishes at `S(k) = 2.2·b·k + 0.7·(5 − k)`.
  - A rival's whole-race total `T` is spread evenly over the 5 turns. As today, it moves 0.4 less on each turn the student gets right, so it finishes at `T − 0.4·k`.
  - **The faster rival's `T`** sits midway between `S(3) + 1.2` and `S(4) + 1.6`. That makes it `7.7·b + 2.45`.
  - **The slower rival's `T`** sits midway between `S(2) + 0.8` and `S(3) + 1.2`. That makes it `5.5·b + 2.75`.
  - With the starter (b = 1.0), these are steps of about 2.0 and 1.65, close to Zippy's and Bolt's today.
  - Because both rivals scale with the student's boost, the places above hold from ×1.0 to ×1.4.
- **Picking rivals:** `garage.rivals(points, garage)` returns two cars, from the rules above.
  - A cartoon car the student owns can be a rival.
  - A rival never repeats the car being driven.
  - **Pictures:** a real car uses its garage picture (signed-in route, as today); a bot is drawn in code.
- **The race keeps its rivals** from start to finish, like its car.

### Sounds (v3.16, `web/race.js`, `web/games.py`)

- **The clips are private, never in the repo:** `<data>/sounds/roar.mp3`, `sputter.mp3`, and `finish.mp3`, like the car pictures.
  - **Licence:** they come from Pixabay, whose licence allows them in the app with no credit, but not shared as the files themselves. So they're never committed.
  - **The admin's picks (downloaded 2026-10-20), to be checked by ear:**
    - the roar: "car engine roaring" (Dragon Studio);
    - the sputter: "car engine failure" (Universfield);
    - the finish: "sports car acceleration and driving away" (Chrysalyn).

    Four more downloads are spares.
  - **Missing clips:** a missing file just stays silent, and nothing else stops.
- **Serving:** a route serves only those three names, only to someone signed in, as the car pictures are.
- **Playback (`race.js`, Web Audio):**
  - **Unlocking:** iPad Safari plays sound only after a tap, so the Race! tap unlocks it.
  - **Answers:** the roar or the sputter plays when the answer comes back.
  - **The finish:** the fanfare plays with the place.
  - **Length:** each clip plays from its start for at most its time in Numbers, then fades out over 0.3 s. The files aren't trimmed, since there's no audio tool on the home server and none is needed.
  - **Sound:** the setting is kept in the browser's `localStorage` (a per-device setting, never text).
  - With reduced motion, sounds still play. With Sound off, nothing does.

### Read aloud and a focused race (v3.29–v3.30, `race.py`, `web/games.py`, `web/race.js`)

- **A tap on the question card** reads it with the server's voice: "Question 2. … 9, 8, or 6?" (the buttons have no letters), or "Bonus question. …". The card says "· tap to hear". Only the question on screen can be read; each is spoken once and kept in memory with the race.
- **After a wrong answer** the right answer and why are said by itself ("Not this time. It's 6. …"), on the last question too; Next waits until it's said (20 seconds at most). A tap on the card, or on the end note, says it again.
- **🔊 Sound: on/off,** one switch under the track, remembered on the device, turns off the race sounds and every spoken word.
- **A tap that moves on** stops a reading; the Race!, answer, and Next taps keep iPad Safari's player unlocked.
- **The race has the screen:** the track takes at most a third of its height, and My cars and the Showroom show only between races.
- Added after this spec (the admin's decisions of 2026-10-24 and 10-27): for a student who listens more easily than they read, and was distracted by the garage.

### Practice and link days (v3.17, `interests.py`, `results.py`, `web/mentallist.py`)

- **Link days:**
  - `Link` gains `days`, a sorted list of the days the two items came up together; `Link.day` stays as the latest.
  - Old maps load as `[day]` and upgrade on their next write.
  - `_link` adds today to an existing link instead of skipping it.
- **Link strength** uses the item rule (`strength`): 4 or more days in 30 is strong, 2 or more growing, and 1 faint.
- **A bridge's record:**
  - **Held:** the days it came up.
  - **Bounced:** its goal's bounce dates that fall on those days.
  - Merges (v3.12) join link days as they join item days.
- **Groups:** `details` counts bridges and explanations across a group's kinds, as `group_days` does for days.
- **The Practice line** (`results.practice(user, goal_id, today)`):
  - **Raced:** the last day this goal was raced;
  - **This week:** right out of asked over the last 7 days;
  - **Missed lately:** concepts on this goal answered wrong in the last 14 days and not answered right since, at most 3.

  It's read from the results log, and never stored.
- **Who sees it:** the MentalMaps line keeps "This week:" per goal. The Practice line is in a goal's details on both MentalMap screens.

### Levels (v3.18, `race.py`, `concepts.py`)

- **Where levels live:** the concept file gets `levels: {goal_id: n}` (schema 3; older files load with every goal at 3).
  - **What's stored:** goal ids and numbers only.
  - **Never the map:** levels are race data, not the student's interests.
- **The rule:** after each answer, the server counts the goal's answers since its level last changed.
  - At 5 answers, 4 or 5 right goes one harder (up to 5), and 2 or fewer one easier (down to 1).
  - Either way the count starts again.
  - Bonus and probe answers don't count.
- **In the prompt:** each goal line gets its level ("Fractions (level 4)"). `QUIZ_SYSTEM` says what each level means:
  1. one step, in the goal's own words; wrong choices clearly off;
  2. one step, in a new setting;
  3. apply it to one of their interests; wrong choices plausible (today's questions);
  4. two steps, or a comparison; wrong choices are common mistakes;
  5. a what-if, or work back from an answer; wrong choices are near misses.
- **Checks:** the server can't check a level; the eval does.
- **The aim:** about 50–75% right. Two weeks after v3.18, the results log says whether it's working (a to-do item).

### Review (v3.22, `concepts.py`, `race.py`)

- **The ledger:** each concept entry gets `due` (an ISO date, or none) and `step` (0 to 2).
  - **A wrong answer:** `step` 0, due tomorrow.
  - **A right answer on a due concept (its date has come):** the next step: due in 3 days, then 7.
  - **A right answer at step 2:** retires the concept (no `due`).
  - **A right answer on a concept that isn't due:** changes nothing.
  - **A "partly" bonus answer:** counts as a miss.
- **In the prompt:**
  - "Due for review (ask each idea in new words): …", for at most 4 concepts per set of 10 (about 2 a race), oldest due first;
  - only concepts whose goal is still on the map and that mention nothing set aside.
- **Repeat rules:**
  - A due concept is exempt from the 14-day concept rule (v3.9).
  - It's never exempt from the near-same-words rule, so it's asked in new words.
  - A question whose concept matches a due one counts as its review.
- **Unanswered reviews:** if Claude skips a due concept, it stays due. Nothing is lost for being overdue.

### Goal spacing (v3.28, `concepts.py`, `race.py`)

- **Each goal has a box,** kept beside its level: 1, 3, 7, or 14 days. A goal never raced is due now.
- **After a race,** for each goal it asked: all right on a due goal moves it up a box; half or fewer back to box 0 (tomorrow); otherwise, or when it was asked early (a set's second race), it stays. Bonus answers don't move boxes.
- **Each set of 10** goes to about 5 goals (about 2 each, one in each of its two races): due ones first, most overdue then least practiced in 14 days, one subject area at a time, then the soonest due. Due ideas (v3.22) add their goals.

### The bonus round (v3.24, `race.py`, `web/games.py`, `web/talk.js`)

- **Writing:** the same call that writes 10 questions writes up to 2 bonus questions (`bonus`: goal, concept, question, `key_ideas` of 2 or 3 short phrases).
  - **Checks:** like a question (lengths, goal on the map, set-asides, repeats); a key idea is at most 60 characters.
  - **Kept:** in memory only, like questions.
- **When:** the server decides at question 4: the student is 3rd, or this race drew the 1-in-4 chance at its start.
  - The multiple-choice question it replaces goes back into the set.
  - With no bonus written, the race goes on as normal.
- **Grading:** one small-model call (`GRADE_SYSTEM`, `GRADE_SCHEMA`) with:
  - **in:** the question, the key ideas, the answer, and which voice they have (supervised or independent);
  - **out:**
    - `tier`: nailed, partly, tried, or none;
    - `line`: one kind sentence, at most 120 characters;
    - `care`: true if the answer says they're hurt or unsafe.
  - **The tiers:**
    - nailed: every key idea, correct;
    - partly: at least one key idea;
    - tried: a real attempt in their own words;
    - none: blank, emojis, or off-topic.
- **Safety:**
  - The grader follows the supervised safety rules.
  - With `care`, the card shows Chat's caring words instead of feedback, with no points; that one answer goes to the conversation log, as a worrying message in Chat does, and the results log gets a `care` flag (changed in review).
- **Failures:** if the call fails or takes over 20 seconds, the answer counts as tried: "Lerni couldn't read that one. ⭐ +2 for trying."
- **Movement:**
  - nailed and partly move the car like a right answer, and count as right for the place;
  - nailed also slows both rivals a second time;
  - tried and none take the small step.
- **Points:**
  - The bonus ⭐ is a separate award with id `<race>-bonus`, so it's applied once.
  - A nailed answer marks the goal explained today, as a good explanation in Chat does.
- **Kept:**
  - the answer stays in memory until graded, then it's dropped;
  - the results log gets the tier, goal, concept, and the question's hash.
- **Speaking:** the card reuses Chat's Hold to talk (`talk.js`, `voice.py`). Whisper turns the speech into text, and the text is graded.
- **Cost:** one small-model call per bonus.

### Probes (v3.32, `race.py`, `results.py`, `web/games.py`)

- **What the server gives Claude:** "Nearby ideas to try", built from:
  - the strong interests, with their groups and those groups' other kinds;
  - goals explained in the last 30 days.

  With none of these, there are no probes.
- **What Claude writes:** up to 2 of the 10 questions carry `probe`, a short topic name not on the map ("earthquakes" next to volcanoes; "multiplying fractions" after an explained "adding fractions").
- **The server drops a probe** (it can stay as a normal question) if its topic:
  - is on the map;
  - breaks the name rules;
  - mentions anything set aside;
  - was probed in the last 30 days.
- **In the race:** one probe per race, at question 2, 3, or 4.
  - It counts for the place like any question.
  - It never counts toward the goal's level or review.
- **After the race:** up to two topic buttons: this race's probe, and the latest other probe from the last 7 days that hasn't been tapped.
  - **A tap** opens Chat with a fixed opener: "Let's talk about earthquakes! What do you already know about them?" No Claude call.
  - The tagger adds the topic to the map only from the student's own words.
- **Kept, as labels and numbers in the results log:**
  - the probe answer's line gets `probe`;
  - a tap adds `{"day", "probe_tap": topic}`.

  Version 5 reads both: what they got right without being taught, and what they chose to explore.

## Rules that still hold

- **Only people set goals:**
  - levels, review, probes, and the Practice line never add or change a goal;
  - a probe topic joins the map only from the student's words in Chat.
- **Text on disk:** the concept file holds labels, ids, dates, and numbers; the results log, labels and numbers. Question texts and bonus answers stay in memory.
- **Safety and set-asides:** the supervised safety rules cover questions, bonus questions, grading, and probes. Nothing set aside is asked, probed, or reviewed.
- **Points:** no point is taken away for a wrong or skipped answer, and no screen compares one student with another.

## Not in this version

- An engine sound loop, or music.
- Games and probes for independent students.
- Goal suggestions (Version 5).
- FSRS or SM-2 (Version 4).

## Testing (minimal, per rule 4)

- **v3.16 (`test_race.py`, `test_garage.py`):**
  - the place outcomes for 5, 4, 3 and 2 right answers at ×1.0 and ×1.4. This replaces v3.3's "at ×1.4, 3 right wins";
  - `rivals` picks the next Showroom car, an owned slower car, and the bots as fallbacks.
- **v3.17 (`test_interests.py`):**
  - an old map's link loads with its day;
  - a second day strengthens it;
  - a bridge counts held days and bounces.
- **v3.18 (`test_race.py`):** five answers at 4 right raise a goal's level, five at 2 lower it, and the level reaches the prompt.
- **v3.22 (`test_race.py`):**
  - a miss is due tomorrow and reaches the prompt;
  - a due concept isn't refused as a repeat;
  - a right answer at 7 days retires it.
- **v3.24 (`test_race.py`):**
  - last after question 3 gets the bonus;
  - each tier moves the car and awards once;
  - the answer is on disk nowhere.
- **v3.32 (`test_race.py`):**
  - a probe on the map or set aside is dropped;
  - a probe answer leaves the level alone;
  - a tap is logged.
- **Evals (real calls, by hand):**
  - `eval_race.py` gains a level 1 vs level 5 case, a due-concept case, and a probe that stays clear of a set-aside;
  - a new `eval_bonus.py` has 3 cases: nailed, partly, and emojis graded none.
- **Phone size:**
  - a race with sound, Sound off, and a spoken bonus on the iPad;
  - the Practice line on both MentalMap screens, as an educator with both lists right after a restart (rule 9).

## Decisions

- **2026-10-20, rivals:** paced from the student's own car, so a win always takes 4 or 5 right. A faster car brings new rivals and ⚡, not easier wins. This replaces spec 09's "a faster car turns 3 right answers into a win".
- **2026-10-20, sounds:** the admin's Pixabay clips, kept in the data folder and never in the repo, since Pixabay's licence doesn't allow sharing the files themselves. This replaces "CC0 clips in the repo".
- **2026-10-20, the bonus:** it moves the car. Nailed and partly count as right answers, and nailed also slows both rivals. So it's a way back from last.
