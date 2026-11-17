# Spec 11: new ways to answer

**Goal:** practice beyond multiple choice: typed answers, spelling, math with pictures, reading, and a first paragraph. From the admin's notes after a meeting with the supervised student's teacher (2026-11-17): reading comprehension and spelling need work, and multiplication needs intuition before facts.

## Where it lives

- **One game:** spelling and picture math are typed questions inside races (v4.11): at least one of each kind available, the spare questions to what needs practice most. Reading and Writing come beside them. Each earns ⭐ the same way, so the garage still motivates.
- **Typed answers** use a field with autocorrect, suggestions, and capitals off (they would give spelling away), at 16px.
- **Code grades whatever it can:** spelling, numbers, and choices. Claude grades only the student's own sentences.
- **Rule 6 holds:** the student's typed words stay in the logs. Saved: counts, ✓ or "not yet" per checklist item, mistake labels, and the words Lerni or the educator chose.

## Spelling

- **Two sources of words:**
  - **The class list,** entered by the educator in a Spelling section (one word per line, or a photo through Upload, confirmed before it's saved). A new list replaces the old one; words not yet learned carry over.
  - **Lerni's picks,** a little above the student's level, from their interests: adjectives, and words with prefixes and suffixes ("unhappy", "careful"). They go straight into practice; the educator can remove any word.
- **The class list comes first;** Lerni's picks fill in when it runs low or is mastered.
- **A round:** hear the word, then the word in a short sentence (Claude writes it once, kept), type it, see the right spelling after a miss. Missed words come back sooner, as missed race ideas do.
- **Word building:** "un + happy" typed as one word; tap where a word splits (re · play · ing).
- **The educator sees** the words missed most and the kinds of mistakes (a doubled letter, "ie" or "ei"), as labels.

## Picture math

- **One drawing engine:** Claude (or code) gives what to draw as data, such as `{rows: 3, cols: 4}` or `{bills: [20, 5, 1, 1]}`. Code draws it and grades the typed number, so the answer key is always right.
- **Blocks,** a path toward multiplication: count all the squares → rows and how many in each → the same grid turned sideways (is the total the same?) → 3 × 4 = ? → the missing piece (12 squares in 3 rows, how many in each?).
- **Money:** simple drawn coins (penny, nickel, dime, quarter) and bills ($1, $5, $20, $100), labeled, not copies of real money. Coins first (name them, then count cents), then bills, then both together ($1.35); totals, then making change.
- **Measuring:** an object beside a ruler, read in centimeters, then in inches; later, comparing ("which is longer, 10 cm or 10 inches?").
- **Themed by interests:** "a parking garage with 3 floors of 4 cars", drawn as cars or bricks.

## Reading

- **Passages Claude writes,** about the student's interests, at their reading level. Lerni finds the level itself: it starts easy and moves up as race levels do, checked with a readability formula on the home server.
- **Three kinds, taking turns:** narrative, informational, and opinion.
- **Task 1, what kind of text:** a tap among the three, then "why?" in a few typed words.
- **Task 2, summarize, shaped to the kind:**
  - **Narrative:** the 5 Ws (who, what, where, when, why; "how" at higher levels), events tapped in order, and the main character in 2 adjectives. At lower levels who, where, and when are taps; later all are typed.
  - **Informational:** pick the main idea, type two details that support it.
  - **Opinion:** the author's opinion, and one reason they give.
- **Adjectives:** a typed answer with a bare noun gets one nudge ("What kind of dragon?"). The educator sees how often answers include adjectives, as a count.
- **Later:** a full summary in the student's own words, graded against the main points.

## A paragraph

- **Typed only** (speaking it would skip spelling and punctuation).
- **Two kinds of prompt:** a response to a passage just read ("Would you want a pet sloth? Use one fact from the passage."), or creative, from the student's interests.
- **A checklist, shown first:** a first sentence that says what it's about; 2–3 sentences with details; at least 2 adjectives; capitals and periods; a last sentence that wraps up.
- **Feedback:** ✓ or "not yet" per item, one thing done well, and one thing to try. One revision, and the grade notes the improvement.
- **Misspelled words** go to the educator as suggested spelling words, added only on their tap.

## Order (the admin's call, 2026-11-17)

Spelling and picture math first, since they cost almost nothing against the Claude plan; reading and the paragraph after the usage meter, which measures their grading. Each PR starts with a mockup and is checked on the iPad.
