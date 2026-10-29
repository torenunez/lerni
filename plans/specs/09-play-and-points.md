# Play and points: a race, a garage, and points for real answers (Version 3)

Approved in conversation on 2026-10-12. Requirements: [student PRD, Version 3](../../docs/prd/student.md#version-3-play-and-points) and [educator PRD](../../docs/prd/educator.md#version-3-play-and-points). Builds on the map ([spec 04](04-interest-map.md), [spec 08](08-kind-of.md)).

**Why.** The supervised student answers Lerni's goal questions with random emojis. Points they can spend on cars give those questions a reason, from two places: a race in Games and real answers in Chat. Points never go down for a wrong answer, are never compared between students, and stay apart from the map.

**Ships as:** v3.1 (the race, points, and the garage), v3.3 (real cars in the garage), and v3.7 (points in Chat, and Ask renamed Chat). Part 2 (v3.16–v3.36): [spec 09b](09b-harder-races.md).

## What people see

### Games (supervised students and educators)

- **Top (v3.5):** the car they're driving, big, with its ⚡ and the next car to save for ("Next car: … · ⭐ 280 / 400 · about 10 races" over a bar); then **Race!**. While a race runs, the track takes its place.
- **The race:**
  - Their car and two silly bots (Zippy and Bolt) on a three-lane track, with a finish flag (rival cars from v3.16, [part 2](09b-harder-races.md)).
  - A question card under it: "Question 3 of 5", the question, and **three big buttons**. No typing and no chat in a race (until the bonus round, v3.24).
  - A right pick: their car leaps ahead and the bot in front slows ("Right answer: boost! Zippy slowed down 💨").
  - Another pick: a small step, and (from v3.21) the question stays on screen with the right answer and a one-line why ("It's acceleration: speeding up"); **Next** shows the next question. A wrong last answer shows the finish instead.
  - Cars glide to their new places after each answer; nothing moves on a clock.
  - After the fifth answer: "You finished 2nd! ⭐ +13", the next car to save for, then **Race again**.
- **The garage (v3.5):** always open below Race!, as tiles (2 across on a phone): **My cars**, then the **Showroom**, cheapest first. No decimals on screen.
  - A tile: the picture, the name, speed as ⚡ to ⚡⚡⚡⚡⚡, and, for sale, the dollar price with a comparison ("as much as 92 family cars 🚗"). **Car facts** (closed) holds the engine, power, drive, 0–60 time, and the $ to ⭐ maths.
  - A car they can't afford yet shows only its picture, name, and price; its ⚡ and facts come once it's in reach.
  - Owned cars say **Drive**; others **Buy · 140 ⭐**, or "60 more ⭐" (not tappable).
  - Buying asks nothing more: it takes the price off their points, and the car is theirs for good.
- **Starting a race** is quick: the next race's questions are written ahead, at sign-in, at server start, and after each race, and unused ones are kept past midnight (v3.27). Writing a set takes about a minute; Race! always shows "Pumping the tires… New questions can take a minute to write." until the race appears. Held sets are used oldest first, so a goal added today reaches races once those are used.
- **Limits:**
  - After 10 races in a day: "The track is closed for today 🌙 Come back tomorrow."
  - While Lerni is resting (usage limits): "Lerni is resting until Mon 6:00 pm."
  - Earlier points and cars stay either way.
- **The header** shows ⭐ points on every screen for a player (supervised students and educators). From v3.7, tapping it opens a short "How to earn ⭐": 🏁 race in Games, or 💬 answer Lerni's questions in your own words in Chat.

### Chat (built in v3.7; Ask is renamed Chat, and so is the supervised screen's menu item)

- Chat stays a conversation, typed or spoken, with no multiple choice.
- When the student really answers Lerni's question, "⭐ +3" (a right answer) or "⭐ +1" (a real try in their own words) appears by their points a few seconds later. Emojis, "idk", or a new subject earn nothing, and nothing says "wrong".
- Lerni knows good answers earn ⭐ and may say so ("⭐ for whoever figures out…"). It never decides the points.

### MentalMaps (educators)

- Under the student picker: the student's ⭐ points and their cars.
- The educator's own races earn the educator's own points.

## Numbers (tuned after trying)

| What | Value |
|---|---|
| Race | 5 questions, 3 choices each |
| Race points | 1st 15, 2nd 10, 3rd 5, plus 1 per right answer (5 to 20) |
| Chat points | 3 for a right answer, 1 for a real try; at most 30 a day |
| Races a day | 10 per person |
| Cars and prices | the starter free; real cars at 1 ⭐ per $2,500, rounded to tens (v3.3; until then 8 cartoon cars, 30 to 400) |
| Gas boost | √(4.0 s ÷ 0–60), ×1.0 to ×1.4; shown as ⚡ 1–5 |
| Family car | $50,000, for the price comparison |
| A race, for "about N races" | 13 ⭐ |

At about 50 ⭐ a day, a $100,000 car comes on day 1 and a $5 million one after about six weeks.

## How it works

### Race rules (`race.py`, no screens)

- **A race is server state:** an id, 5 checked questions with their answers, the three positions, and how many have been answered.
  - It lives in memory, per person; one race at a time.
  - The page gets only the question and the three choices, never the answer.
  - A tap sends the choice; the server checks it and moves the cars.
- **Movement is fixed per answer, with no randomness and no clock.**
  - Right: the student moves a big step times their car's **gas boost**, and both bots move a little less that turn (the message names the one in front as slowed).
  - Wrong: the student moves a small step.
  - Bots move at their own steady speeds.
  - So the finish depends only on how many were right and the car, not the order. **With the starter (boost ×1.0) the constants are tuned so that:**
    - 4 or 5 right wins;
    - 3 right finishes 2nd;
    - 2 or fewer finish 3rd.
  - **The gas boost** comes from the car's 0–60 time: √(4.0 s ÷ its 0–60), from ×1.0 (the starter, or 4.0 s and slower) to at most ×1.4. Until v3.16 (then rivals are paced from the student's car, [spec 09b](09b-harder-races.md)), a faster car turns 3 right answers into a win and 2 into 2nd, but 1 right never wins: the questions still matter.
  - A test pins those outcomes.
- **The place after the fifth answer sets the points.** The award id is the race id, so a double tap, a refresh, or a late repeat never awards twice.
- **Leaving mid-race** (another tab, or signing out) drops it: no points, and it still counts toward the day's 10.

### Questions (one Claude call per 2 races)

- **Model:** a new adapter method, like the tagger's: the small model (Haiku) with structured output, no tools, isolated, and the same usage pause.
- **One call writes 10 questions:** two races' worth.
- **Input:**
  - the student's goals and their notes;
  - their top interests, group-aware ([spec 08](08-kind-of.md));
  - the set-aside line;
  - which voice they have (supervised or independent);
  - the ideas asked recently (v3.9);
  - each goal's level, 1 to 5 (v3.18, [part 2](09b-harder-races.md));
  - the cars they own or can afford, with their exact facts, for about 1 question in 5 that compares two of them (v3.19);
  - ideas due for review (v3.22): missed ones back after 1, 3, then 7 days, up to 4 a set (about 2 a race), exempt from the 14-day idea rule but never from the near-same-words rule.
  - No conversation text.
- **Instructions (kept in code):**
  - each question practices one goal, set in an interest ("halves with pizza slices"), and tests a different idea from a varied angle, never one asked recently;
  - one right answer and two plausible wrong ones, plus a one-line why;
  - short, kind words;
  - never excluded subjects (violence, weapons, sexual content, self-harm, drugs), anything set aside, a real name, or a trick.
  - With no goals: questions about their interests (how things work), never trivia that needs a date or a number to memorize.
  - With cars in reach (at most 4) and a goal that works with numbers or how things move: about 1 question in 5 for it compares two cars by a listed number (0–60, horsepower, price), adding no other fact about a car (v3.19).
- **Schema:** `questions`, a list of objects, each with:
  - `goal`;
  - `concept` (the idea it tests, in a few words; never shown; v3.9);
  - `question`;
  - `choices` (3 strings);
  - `answer` (0, 1 or 2);
  - `why`.
- **The server checks every question.** It drops one if:
  - the question is over 140 characters, or a choice over 40, or the why over 120;
  - the choices aren't 3 different, non-empty strings;
  - the answer index is out of range;
  - the goal isn't on the map (when the map has goals);
  - **its key is wrong (v3.14):** Claude's `math` for a worked-out number ("400 / 2") gives another value than the keyed choice (the server works it out with an `ast` walk, never `eval`), or a blind second call that sees only the questions and choices (lettered A to C, with a few words of working before each pick) picks another answer (one more small call per set, 20 seconds at most; if it fails, or disagrees with most of a set, the set races, since the check is then the likelier fault); a sum that won't read is ignored;
  - **it repeats (v3.9):** its concept matches one asked in the last 14 days or one held, or its words are nearly the same (a `difflib` ratio of 0.9) as one of the last 60 asked since the server started, held, or earlier in the set. If Claude can only repeat, the race tops up with repeats (never one question twice), since a race beats no race.
- **The results log (v3.14):** each answer goes into `<data>/results/<user>.jsonl`, kept for good: day, race, goal, concept, a 12-character hash of the question (never its words), right or wrong, and seconds; each finish adds place, points, and version. The educator's student page shows this week per goal as Goal progress this week (a bar per goal, "7 of 10").
- **What's remembered:** when a race starts, its 5 concepts go into `<data>/concepts/<user>.json`, a ledger kept for good (label, goal, first and last date, times asked and right, and from v3.22 a review due date and step; never question text; v3.10), and the question texts stay in memory only. "Asked lately" is the last 40 asked within 14 days.
- **Then it shuffles the choices**, so the right one isn't always first, and a race takes turns across the goals. A goal's notes, if Claude copies them into `goal`, are ignored when matching. If fewer than 5 survive, it asks again once and keeps the good ones from both; then: "The track needs a minute. Try again soon."
- **Writing ahead:** the next set is written in the background when Games opens, and after each race, but not once the day's races are used. A set is kept in memory for the day only, and checked against the map again when a race starts, so a goal or set-aside changed since still counts.

### Points (`points.py`)

- **One JSON file per person,** `<data>/points/<user>.json`, written atomically under a per-person lock, like maps:
  - `balance`;
  - `cars` (owned ids) and `car` (driving);
  - `awards` (id, source `race`, `chat` or `buy`, amount (negative for a purchase), day): ids and numbers only, no text, kept 90 days for de-duplication;
  - `races` (today's date and count).
- **Calls:**
  - `award(user, award_id, source, amount)`: applies once per id. A Chat award is held to the day's cap.
  - `buy(user, car_id)`: only if the car exists, isn't owned, and the balance covers it. The award id is `buy-<car>`, so a double tap charges once.
  - `drive(user, car_id)`: only an owned car.
  - `start_race(user)`: refuses after 10 today.
- **Every handler** resolves the signed-in viewer on the server. A student acts only on their own points; an educator only reads a supervised student's.
- **Points never touch the MentalMap,** and the map never reads points.

### The garage (`garage.py`)

- **Cartoon cars in the repo,** drawn in code (the same side view facing right, same scale, wheels on one line; no licenses, nothing fetched). Since v3.3 only the free starter is sold; a cartoon car someone already bought stays theirs to drive. The bots stay cartoon.
- **Real cars in a private garage file** (v3.3), `<data>/garage.json`, never in the repo: each car's id, name, price in dollars, 0–60 seconds, engine, power, drive, an optional note ("Limited to 250 cars"), and a picture in `<data>/cars/`.
  - **Price in ⭐:** dollars ÷ 2,500, rounded to the nearest 10, at least 10 (a $100,000 car is 40 ⭐; a $5 million one, 2,000).
  - **Pictures:** side profiles facing right with the background lifted off by Apple's Vision on the home server (`scripts/lift_car.swift`), saved as WebP about 600 px wide. They're served only to someone signed in, from a route that knows only the garage's ids.
  - A broken or missing file leaves the cartoon garage; nothing else stops.

### The screen (`web/games.py`, `web/race.js`)

- **The Games tab replaces the placeholder,** for supervised students and educators.
- **The track is server-drawn SVG,** like the map picture.
  - `race.js` slides each car from its old place to its new one when the picture is redrawn (the same restore-on-redraw pattern as `mapview.js`).
  - With reduced motion it jumps.
- **Buttons are at least 48 px tall,** with the choice as the label, so a screen reader reads question and choices in order.
  - The track has a text label ("You're 2nd").
  - Nothing relies on color alone.
- **Rendering:** the race card and garage are ordinary components, not `gr.render`, so the draw queue isn't involved: each car has a tile in both lists, built once, shown by ownership.
- **The track** is scaled to the car's perfect run, so nobody reaches the finish line before the fifth answer, and a race keeps the car it started in.

### Chat points (v3.7, `tagging.py`)

- **The tagger gets one more field, `answered`:**
  - `right`: Lerni's previous message asked a question and the student answered it correctly;
  - `tried`: a real attempt in their own words;
  - empty: anything else.
  - This is Claude's judgment, not a check; it's spot-checked in the logs.
- **Each exchange gets an id;** that is the award id.
- **The award is applied even if the map update is stale** (a person edited the map meanwhile), but not after New conversation.
- **The ⭐ total refreshes** with a short timer that runs for a few seconds after each answer, then stops.
- **One line in Lerni's fixed rules:** good answers earn ⭐; Lerni never promises or counts points.

## Rules that still hold

- Only people set goals; nothing here changes the map.
- Conversation text stays only in the logs: points files hold ids and numbers, concept files labels and counts; race questions live in memory for the day.
- The supervised safety rules apply to race questions, and the disclosure rule still comes first in Chat.
- No point is ever taken away for a wrong answer, and no screen compares one student with another.

## Not in this version

- Voice in the race ("🔊 Read it to me").
- Pit stop.
- An educator "reset points".
- Games for independent students.
- Bridge Trip (Version 4).

## Testing (minimal, per rule 4)

- **`test_points.py`:**
  - an award applies once;
  - Chat is held to its cap;
  - a buy charges once and never below zero;
  - drive only an owned car.
- **`test_race.py`:**
  - the place outcomes above for 5, 4, 3 and 2 right answers;
  - bad questions are dropped;
  - the page's view never includes the answer.
- **`test_web_roles.py`:**
  - a viewer can't buy or race for someone else;
  - a supervised viewer can't read another student's points.
- **`scripts/eval_race.py`** (real calls, by hand), 3 cases:
  - questions practice the map's goals;
  - each has 3 distinct choices with the right one among them;
  - a supervised set stays clear of a set-aside interest.
- **v3.3:** `test_garage.py`: the private file loads with prices at $2,500 a ⭐ and boosts from ×1.0 to ×1.4, and a broken file leaves the cartoon garage; `test_race.py`: at ×1.4, 3 right wins, 2 right is 2nd, 1 right is 3rd (replaced in v3.16 by [part 2](09b-harder-races.md)'s matched rivals); the picture route refuses someone signed out and an id not in the garage.
- **`test_tagging.py`** (v3.7): `answered` awards once per exchange and respects the cap.
- **Phone size** (iPhone and iPad):
  - a race to the end, Race again, buying and driving a car;
  - the 10-race limit;
  - an educator with both MentalMap lists right after a restart (rule 9).
