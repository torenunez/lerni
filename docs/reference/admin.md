# Admin tool reference

The admin tool (the `lerni` command) runs in the terminal. Its current features test two learning mechanics: explaining an idea to find gaps, and returning to it later. It is available and maintained while the student app is built. This reference describes the checked implementation; it does not promise the parked AI, analytics, export, or native-app features.

## Daily use

After the [repository setup](../../README.md#setup), run:

```bash
lerni new                  # prompts for the question and explanation
lerni new --quick          # question and raw notes only
lerni today
lerni review               # due questions
lerni review <id>           # one question
lerni skip <id>             # tomorrow; SM-2 state unchanged
```

The full authoring flow collects raw notes, a simple explanation, gaps/questions, a refined explanation, and analogies. Add `--editor` to new, edit, snapshot, or review to use an external editor instead of inline input.

A review hides the previous answer while you explain from memory. If you report recall, choose grade 3–5. Otherwise, read the previous explanation, identify gaps, and choose 0–2. The grade is your assessment; the program does not judge correctness.

| Task | Command |
|---|---|
| Revise current answer in place | `lerni edit <id>` |
| Preserve an earlier version | `lerni snapshot <id>` |
| Inspect content or versions | `lerni show <id>`, `lerni history <id>` |
| Remove a question | `lerni delete <id>` |
| Browse or search | `lerni list`, `lerni list --due`, `lerni list --concept "Name"`, `lerni search "text"` |
| Organize | `lerni assign <id> "Concept"`, `lerni meta <id> --difficulty 3 --source "citation"` |
| Manage concepts | `lerni concept new "Name"`, `list`, `show <id>`, `delete <id>` |
| Link concepts | `lerni concept link "A" "B" --type prerequisite` |
| Remove links | `lerni concept unlink "A" "B"` |
| macOS notification | `lerni notify`, `lerni notify --setup` |

Concept subcommands share the `lerni concept` prefix. `notify --setup` prints scheduling instructions; it does not install a schedule. Use a command's `--help` for its options.

## Records and storage

The SQLite database is `~/.lerni/lerni.db`; optional settings are in `~/.lerni/config.toml`. The admin tool has no implemented AI runtime or cloud synchronization. These are the admin tool's records, separate from the student app's curriculum and learner observations.

- **Concept:** unique name, aliases, description, identifier, creation time.
- **ConceptEdge:** source concept, destination concept, relationship. `parent` points from a narrower concept to a broader one; `prerequisite` points from concept to prerequisite; `related` is interpreted bidirectionally.
- **Question:** prompt, optional concept, current answer, next review, schedule state, difficulty, references, timestamps.
- **Answer:** question, the five explanation fields, identifier, creation time. A snapshot adds a version; `edit` mutates the existing answer, so history is not strictly immutable.
- **Review:** question/answer references, scheduled/completed times, status, grade, attempted explanation, recall flag, gaps, notes. Status is pending, completed, or skipped. The AI-session field is unused.

The graph is intended to be acyclic; the current link command does not enforce cycle rejection. These links do not control the student app's activity order.

## Scheduling

SM-2 starts with easiness factor `EF = 2.5`, interval `0`, and repetitions `0`. New questions are due immediately. For grade `g` from 0 to 5:

```text
new_EF = max(1.3, EF + 0.1 - (5-g) * (0.08 + (5-g) * 0.02))
```

Grades below 3 reset repetitions to zero and schedule one day later. Successful reviews use intervals of one day, then six days, then `round(previous_interval * new_EF)`. Repetitions increase after success. The next review is calculated from the actual review time.

Grades mean blackout (0), recognition after seeing the answer (1), apparent ease after seeing it (2), difficult recall (3), hesitant recall (4), and perfect recall (5).

## Maintenance

Open work is tracked in [todo.md](../todo.md#admin-tool-maintenance). Existing scheduling tests do not establish complete application coverage.

Implementation detail: [models](../../src/lerni/models.py), [database](../../src/lerni/db.py), [scheduler](../../src/lerni/sm2.py), [commands](../../src/lerni/commands).
