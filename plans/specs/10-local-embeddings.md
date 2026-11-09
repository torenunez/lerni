# Local embeddings (Version 3, v3.39–v3.40)

Decided on 2026-11-09 from a bake-off ([v3.39 plan](../v3.39-spec10.md)) and the admin's answers. Builds on the race ([spec 09](09-play-and-points.md), [09b](09b-harder-races.md)) and the map ([spec 04](04-interest-map.md)). It lifts [spec 08](08-kind-of.md)'s "no embeddings" for the uses below only.

**Why.** Word matching misses the same idea in other words:
- a set-aside "guns" catches "gun" but not "rifles";
- "how fast a car speeds up" passes as new after "0–60 acceleration".

An embedding turns a short text into numbers, so that texts close in meaning are close in number. It runs on the home server, and nothing is sent anywhere.

## What people see

Nothing new on any screen. Race questions that repeat a recent idea in new words, or that are about a set-aside topic in other words, are dropped before the student sees them, like today's exact repeats. A dropped question is replaced as today: from the held set, or by the next write.

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
- A bootstrap of the pairs:
  - **Gains that hold up:** EmbeddingGemma's on set-aside and Qwen3's on repeats, each against bge-small (their 95% ranges leave out zero).
  - **Within noise:** Qwen3 against EmbeddingGemma, for both uses (repeats narrowly, +0.08).
- Qwen3 was picked because it's better at repeats, keeps one subject's ideas further apart on real labels, and has the plainer licence.
- The Spanish pairs are too few to judge Spanish on its own. Add some when a Spanish miss is seen.

## The adapter (rule 3)

- `Embedder.embed(texts) -> list[list[float]]`: unit vectors, in order.
- **The real one, `LlamaEmbedder`:**
  - **One call per batch:** it runs `llama-embedding -m MODEL --embd-output-format array --embd-separator SEP --embd-normalize 2 -p "<texts joined by SEP>"`, every text starting with `Instruct: Find text with the same meaning. Query: `.
  - **No files:** texts go as an argument, never to a file.
  - **A timeout** of 10 s.
  - **Which model:** `LERNI_EMBED_MODEL` names the file. The default is the file above.
- **Tests** use a fake that makes vectors from words, so no test runs a model.
- **Setup:** `lerni service install` warns when `llama-embedding` or the model is missing, as it does for `whisper-cli`. The admin reference gives the download.
- **Off means today:** with no tool, no model, a timeout, or the wrong number of vectors, the check uses the word match only. The server log gets one line, numbers only ("embedding check skipped: timeout"). A race is never blocked.

## Use 1: set-aside by meaning (v3.40)

- **Where:** the race's set-aside checks, wherever `mentions_set_aside` runs on new text: questions, bonus questions, probe topics, and why lines. It runs beside the word match, never instead of it.
- **What's compared:** each candidate's text (question, idea, and key ideas) against the map's removed names.
- **When it's dropped:** at a cosine of **0.55** or more with any removed name, *and* more than with its own goal's name. A probe has no goal, so the cut alone decides.
  - On the made-up pairs, that catches 63% of close pairs, with 1 false match in 23.
  - On real labels, the rule about the candidate's own goal took the false matches to zero.
- **Goals win:** a removed name at **0.80** or more with an active goal's name or an area is skipped by race checks, by meaning and by word. It still steers Chat away (the map block is unchanged).
  - This is the admin's call (2026-11-09). An interest set aside as something to chat about can share its name with an area that has goals, and its goals are still taught.
  - The word match gains the same skip, so today's checks stop dropping that area's questions.

## Use 2: repeats by meaning (v3.40)

- **Where:** `check_questions`.
- **What's compared:** each new question's idea label against:
  - the recent ideas Claude was told to avoid;
  - the ideas already kept in the same set.
- **When it's dropped:** at a cosine of **0.91** or more with any of them, like today's exact repeats.
  - **The cut comes from real labels, not the made-up pairs.** Short labels on one goal score high together: on real labels, every pair at 0.91 or more was the same idea, while two different ideas on one goal (adding tens and adding hundreds, say) scored 0.90.
  - The made-up pairs' cut (0.66) would drop many real new angles.
- **Ideas due for review are never dropped**, because they're meant to come back (`due` stays as it is today).

## One call per check

- Each question set's checks share one call: every candidate's text and idea, the removed names, the goal names, the areas, and the recent ideas, at about 1.5 s. That sits next to a 25–30 s question write.
- Bonus questions, probe topics, and why lines ride on the same call when they're checked together. Otherwise each gets one call of its own.

## What's kept

- **No vectors on disk, and no cache.** Labels and names are embedded fresh at each check. Rule 6 is unchanged.
- **The models** stay in `~/.lerni/models/`, outside the data folder and the backups.
- **Drops by meaning** go to the server log as counts per set ("2 repeats and 0 set-aside dropped by meaning"), never their text. That way the admin can see whether the cuts are right.

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
