# Local embeddings (Version 3, v3.39–v3.40)

Built in v3.40 ([plan](../v3.40-embeddings.md)). Decided on 2026-11-09 from a bake-off ([v3.39 plan](../v3.39-spec10.md)) and the admin's answers. Builds on the race ([spec 09](09-play-and-points.md), [09b](09b-harder-races.md)) and the map ([spec 04](04-interest-map.md)). It lifts [spec 08](08-kind-of.md)'s "no embeddings" for the uses below only (the later ones included, once built).

**Why.** Word matching misses the same idea in other words:
- a set-aside "guns" catches "gun" but not "rifles";
- "plants need the sun's light" passes as new after "plants need sunlight", because normalizing the text doesn't make them match.

At the cut-off below, repeats by meaning catch rewordings this close, which is what real repeats look like. They don't catch a full paraphrase: "how fast a car speeds up" still passes after "0–60 acceleration" (0.70).

An embedding turns a short text into numbers, so that texts close in meaning are close in number. It runs on the home server, and nothing is sent anywhere.

## What people see

Nothing new on any screen. Race questions that reword a recent idea, or that are about a set-aside topic in other words, are dropped before the student sees them, like today's exact repeats. A dropped question is replaced as today: from the held set, or by the next write.

## The model

**Qwen3-Embedding-0.6B** (`Qwen3-Embedding-0.6B-Q8_0.gguf`, 639 MB, Apache 2.0, from `Qwen/Qwen3-Embedding-0.6B-GGUF`), in `~/.lerni/models/`.

| Model | Set-aside AUC | Repeat AUC | 60 texts, one call |
|---|---|---|---|
| all-MiniLM-L6-v2 | 0.79 | 0.65 | 0.16 s |
| bge-small-en-v1.5 | 0.84 | 0.68 | 0.18 s |
| nomic-embed-text-v1.5 | 0.79 | 0.60 | 0.25 s |
| EmbeddingGemma-300m | 0.94 | 0.78 | 0.76 s |
| **Qwen3-Embedding-0.6B** | 0.91 | **0.86** | 1.52 s |

multilingual-e5-small's GGUF wouldn't load in llama.cpp, so it isn't in the table.

**How it was measured:**
- The pairs are about 100 made-up labelled pairs (`scripts/data/embedding_pairs.jsonl`), mostly English, with some Spanish and some mixed. `scripts/bakeoff_embeddings.py` reruns it.
- The script's bootstrap (its 95% range of each model's AUC gap to the best):
  - **Gains that hold up:** EmbeddingGemma's on set-aside and Qwen3's on repeats, each against all three small English models.
  - **Within noise:** Qwen3 against EmbeddingGemma, for both uses (repeats narrowly, +0.08).
- Qwen3 was picked because it's better at repeats, keeps one subject's ideas further apart on real labels, and has the plainer licence.
- **Spanish:** Qwen3's Spanish repeat AUC (0.78) is 0.08 below its English one, which misses the plan's 0.05 margin. That number rests on 3 same and 3 different pairs, too few to judge on, and no model did better on them. Add Spanish pairs when a Spanish miss is seen.

## The adapter (rule 3)

- `Embedder.embed(texts) -> list[list[float]]`: unit vectors, in order.
- **The real one, `LlamaEmbedder`:**
  - **One call per batch:** it runs `llama-embedding -m MODEL --embd-output-format array --embd-separator SEP --embd-normalize 2 -p "<texts joined by SEP>"`, every text starting with `Instruct: Find text with the same meaning. Query: `.
  - **No files:** texts go as an argument, never to a file.
  - **A timeout** of 10 s.
  - **Which model:** `LERNI_EMBED_MODEL` names the file. The default is the file above.
- **Tests** use a fake that makes vectors from words, so no test runs a model.
- **Setup:** `lerni service install` warns when `llama-embedding` isn't on the PATH, as it does for `whisper-cli`. The server's start-up lines say whether embeddings are on (tool and model found), as they do for voice. The admin reference gives the download.
- **Off means today:** with no tool, no model, a timeout, or the wrong number of vectors, the check uses the word match only. The server log gets one line, numbers only ("embedding check skipped: timeout"). A race is never blocked.

## Use 1: set-aside by meaning (v3.40)

- **Where:** in `_write`, on each try's new questions (probes included) and bonus questions (see [When it runs](#when-it-runs)), beside the word match, never instead of it. Every other check stays word-only: the start and prefill re-checks (`fits`), `_take_bonus`, `_due`, and why lines.
- **What's compared:** each candidate's text (question, idea, and key ideas) against the map's removed names.
- **When it's dropped:** at a cosine of **0.55** or more with any removed name, *and* more than with its own goal's name. A probe has no goal, so the cut alone decides.
  - On the made-up pairs, that catches 63% of close pairs, with 1 false match in 23.
  - On real labels, the rule about the candidate's own goal took the false matches to zero.
- **Goals win:** a removed name at **0.80** or more with an active goal's name, or with an area that has goals, is skipped by every race check, by meaning and by word. It still steers Chat away (the map block is unchanged).
  - This is the admin's call (2026-11-09). An interest set aside as something to chat about can share its name with an area that has goals, and its goals are still taught.
  - **The skipped names:** `_write` works them out first and keeps them in memory beside the held set (names only). Race code reads the map through a view without them (`race_view`), so `fits`, `_take_bonus`, `_due`, and the re-checks never drop what the skip let through.
  - **Never for probes:** a probe has no goal to give way to, and its topic can open Chat. So probes, their re-checks, and the topics offered after the finish use the map itself.
  - **Lost on a restart:** the held set and its skipped names go together.
  - **What Claude is told:** `quiz_input`'s "Set aside, never use" line leaves skipped names out.

## Use 2: repeats by meaning (v3.40)

- **Where:** `check_questions`, from the vectors `_write` passes in.
- **What's compared:** each new question's idea label against its own goal's (since v4.2; probes against all):
  - the recent ideas Claude was told to avoid;
  - the ideas already kept in the same set.
- **When it's dropped:** at a cosine of **0.91** or more with any of them, like today's exact repeats.
  - **The cut comes from real labels, not the made-up pairs.** Short labels on one goal score high together: on real labels, every pair at 0.91 or more was the same idea, and two different ideas on one goal scored up to 0.90.
  - The made-up pairs' cut (0.66) would drop many real new angles.
- **Ideas due for review are never dropped**, because they're meant to come back. `_write` passes the due labels to `check_questions`, and a candidate whose idea is the same as a due one (`_same_idea`) skips the check by meaning.

## When it runs

- **Only in `_write`, never under the race lock.** A write makes at most three calls, each about 1.5 s, next to its 25–30 s of question writing.
  - **Before the first try,** when the map has removed names: one call for the skipped names (removed names, goal names, and areas with goals).
  - **On each try** (at most two): one call for that try's raw output, meaning every new question's text and idea, bonus question, and probe topic, plus the removed names, their goals' names, the recent ideas, and the ideas kept so far. `check_bonus` and `check_questions` both get those vectors.
- **A failed call** leaves that try to the word match.

## What's kept

- **No vectors on disk, and no cache.** Labels and names are embedded fresh at each check. Rule 6 is unchanged.
- **The models** stay in `~/.lerni/models/`, outside the data folder and the backups.
- **Drops by meaning** go to the server log as counts per set ("Race checks by meaning: 2 repeats, 0 set aside"), never their text. That way the admin can see whether the cuts are right.

## Later uses (described, not built)

| Use | When it pays | Note |
|---|---|---|
| Chat's goals ranked by the student's message | The admin decides it's wanted | Changes how Lerni steers; each message would be embedded in memory only |
| "Same as" shortlist | Maps fill and items rest | Today the tagger reads every active item |
| Suggestions never repeat a goal | Version 5 | The same 0.91-style cut, measured on goal names |
| Grouping near-duplicate ideas in `lerni stats` | When "ideas missed most" splits one idea in two | Labels only |

## Testing (v3.40)

- **The happy path:** with the fake, a near-repeat idea and a question near a removed name are dropped; a removed name matching an area is skipped.
- **Safety:** an embedder that fails or times out leaves the word match deciding, and the race goes on.
- **Safety:** an idea due for review is kept.
- **By hand:** after v3.40 ships, `scripts/bakeoff_embeddings.py` reruns on the pairs, and the drop counts in the server log are read after a week of races.
