# Play and points, part 3: a garage worth coming back to (Version 3)

Agreed with the admin on 2026-11-19. Builds on [spec 09](09-play-and-points.md) (points, the garage) and [part 2](09b-harder-races.md). Order and status: [upcoming versions](../../docs/todo.md#upcoming-versions).

**Why.** What the student cares about most is a new car in the garage. Every measurement version after this one needs the student racing: checking raced questions, Chat finding interests, the difficulty model, and forgetting curves. So engagement comes first. None of this calls Claude, so it doesn't use the plan's limits.

**What the research supports:**
- learning that is the game itself, not a reward bolted on ([Habgood & Ainsworth](https://nottingham-repository.worktribe.com/output/23577510));
- a head start helps people finish ([Nunes & Drèze](https://msbfile03.usc.edu/digitalmeasures/jnunes/intellcont/Endowed%20Progress%20Effect-1.pdf));
- choice and feedback that informs, not pressure ([overjustification](https://pmc.ncbi.nlm.nih.gov/articles/PMC8924733));
- slack, not rigid streaks.

**Never:** paid or random rewards, leaderboards, points that go down, streak shame, or limited-time offers.

**Ships as**, one PR each:

| Version | What the student sees |
|---|---|
| v4.17, New arrivals | Covered cars under the Showroom, a ❤️ on each, and the one coming next marked "Arrives Friday" |
| v4.19, Spec cards and a garage to park in | The same stats on every car, and the garage as parking bays |
| v4.20, Stat duel | A card game with their own cars |

## New arrivals (v4.17)

- **`"coming": true`** on a car in `garage.json` covers it. One covered car arrives each week on a set weekday (the admin's call, 2026-11-19): the day is shown ahead and never moves, never random, and a covered car can't be bought (the one test beyond the happy path).
- **❤️ picks which:** the cheapest car the student hearts comes next, or the cheapest when none is, so an affordable car keeps coming. The car that would come shows "Arrives Friday", so a heart moves it at once. The educator sees the hearts and the next car. Only car ids and days are kept.
- **One deploy loads every covered car,** so new cars keep coming while deploys pause; weeks away bring one car, not several.
- **Prices stay real:** the US price when new, at `PRICE_PER_STAR` dollars per ⭐. New cars between about $50k and $300k keep one car always a few days of ⭐ away.
- **The cars:** Claude finds side-on photos with free licences on Wikimedia Commons (the admin approves each download) and drafts each car's stats with a source per number, for the admin to check. The photos are cut out with `scripts/lift_car.swift`, and each one's credit is kept in the private garage file on the home server. They're loaded at a "ship it" deploy.

## Spec cards and a garage to park in (v4.19)

- **The same stats on every real car:** top speed, 0–60, horsepower, weight, year, country, and price. Horsepower, 0–60 and price exist; the rest are new optional fields.
- **🏆 on the best value** in the student's garage for each stat.
- **The garage as parking bays,** with grey outlines of the cars not owned yet ("N of M"), in place of the tile list.

## Stat duel (v4.20)

- **A game in Games** with only the student's own cards, against a bot: pick a stat, the higher one wins.
- **Later levels** ask how many seconds faster, rounding, or horsepower per tonne.
- **Fixed maths and no Claude calls,** like Pit stop.

## Measured

Days with races per week, and races on each day played, from `stats.sqlite`. The month before v4.17 is the baseline. Each arrival date is a before-and-after point (an interrupted time series). No counts in tracked files.

## Later

Ideas for after these, each waiting for a reason: [to-do list](../../docs/todo.md) (Garage extras).
