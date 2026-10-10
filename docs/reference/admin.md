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

## Running the student app

`lerni serve` runs the student app on the home server (Release 1: sign-in; Ask, My map, and My account for independent students; Maps and Students for educators; the conversation, full screen, for a supervised student).

```bash
pip install -e ".[student]"                # once: installs Gradio
lerni serve                                 # binds 0.0.0.0:7860
```

- Every device opens `http://<home-server>:7860/` and signs in at `/signin`; the app itself is at `/app/`.
- **First start:** add the first educator on the home server, then that educator adds everyone else in the **Students** tab:

  ```bash
  lerni student add USERNAME --name NAME --kind independent --educator   # asks for the password
  ```

  `lerni student list`, `lerni student reset-password USERNAME`, and `lerni student educator USERNAME [--off]` cover recovery.
- A supervised student's iPad is signed in only as that student. Try the app as yourself on your own device or in a private tab.
- Data lives in `~/.lerni/student/` (or `$LERNI_STUDENT_DATA`): `students/` (accounts, password hashes only), `secret.key` (signs the sign-in cookie; keep it private; deleting it signs everyone out), `maps/` (interest maps), `logs/` (each exchange, deleted after 7 days), and `feedback.jsonl`.
- `--port` changes the default port; `--host 127.0.0.1` keeps it on this computer only; `--label Development` marks a development server on every page. Startup prints the running version (branch, commit, date), and the sign-in page shows it at the bottom: check it there after updating.
- If you start it over SSH, allow the virtual environment's Python through the macOS firewall first (nobody sees the prompt), and run it inside `tmux` so it keeps running after you disconnect.
- It never touches the admin tool's database.
- **Claude** (Ask, the map's tagger, and Upload) turns on when the `claude` CLI is installed and logged in on this computer; it uses that Claude account, so there's no API key. `LERNI_CLAUDE_MODEL` picks the answering and upload model (default `claude-sonnet-5-5`), `LERNI_TAGGER_MODEL` the tagger's (default `claude-haiku-5-5`). Startup prints whether it's on.
- `lerni logs [USERNAME]` shows the last 7 days of conversations and what the tagger did; `lerni feedback` lists educators' feedback (`--summary` groups it, `done N` closes one).
- Evals (real Claude calls, run by hand when instructions or models change): `scripts/eval_tagger.py`, `scripts/eval_upload.py`, `scripts/eval_supervised.py`.

### Two environments

- **Production:** the home server, on `main`, port 7860, the real data folder (`~/.lerni/student/`). The family uses it; on the student's iPad, open it in Safari and use Share → Add to Home Screen.
- **Development:** the computer where changes are built, on a branch, port 7861, its own data folder and made-up test accounts: `LERNI_STUDENT_DATA=~/.lerni/student-dev lerni serve --port 7861 --label Development` (add accounts the same way: `LERNI_STUDENT_DATA=~/.lerni/student-dev lerni student add tester …`). Bookmark it on the admin's phone; it's up only while it's started.
- Never point development at `~/.lerni/student/`, or test conversations land in the real maps and logs. Both use the admin's Claude account, so heavy testing uses the same plan.

### Updating the home server

The family uses whatever is on `main` while new features are built on branches. Production runs from its own checkout, so building never changes it, even on the same computer (once: `git worktree add -b production ~/lerni-prod origin/main`, then its own `.venv`). To put a merged change on the home server:

1. In the production checkout: `git pull`.
2. `.venv/bin/pip install -e ".[student]"` (only needed when a PR says dependencies or package files changed, but always safe).
3. In the server's `tmux` session: Ctrl-C, then start `lerni serve` again (with `--cert` and `--key` once HTTPS is set up).

Caveats:

- A restart clears open conversations (they live in memory); accounts, maps, logs, and feedback stay. Restart between sessions, not during one.
- Never run a branch as production; test branches as development ("Two environments" above).
- Each PR's Deploying section says whether it's safe to use yet and anything extra to do; if it says not yet, leave the server on the previous `main` (the merge can wait, or `git checkout <the previous merge>` on the server).

### HTTPS (for voice)

iPad Safari allows the microphone only over HTTPS. Lerni uses its own certificate, made once with [mkcert](https://github.com/FiloSottile/mkcert) on the home server:

1. `brew install mkcert`, then `mkcert -install` (creates a small private certificate authority on this Mac).
2. Make the server's certificate, naming every way devices reach it: `mkcert -cert-file ~/.lerni/student/https.pem -key-file ~/.lerni/student/https-key.pem <home-server>.local <its-IP> localhost`. The key stays on the home server; never copy it into the repo.
3. On each device (iPad, phones): send it the authority's certificate, `"$(mkcert -CAROOT)/rootCA.pem"` (AirDrop works), open it to install the profile (Settings → Profile Downloaded → Install), then turn on full trust (Settings → General → About → Certificate Trust Settings).
4. Start with `lerni serve --cert ~/.lerni/student/https.pem --key ~/.lerni/student/https-key.pem` and open `https://<home-server>.local:7860/`.

Safari's saved password is for the old `http://` address; sign in once more and let it save again. Replace any bookmark or home-screen icon with the `https://` address (the old one stops working). If the server's IP changes, make the certificate again (step 2); a fixed address for the server in the router avoids that.

Once a device has signed in over HTTPS, keep serving HTTPS: if the server goes back to plain HTTP (started without `--cert`, or rolled back to a `main` from before HTTPS), that device may fail to sign in until its website data for the server is cleared (Safari: Settings → Apps → Safari → Advanced → Website Data).

## Maintenance

Open work is tracked in [todo.md](../todo.md#admin-tool-maintenance). Existing scheduling tests do not establish complete application coverage.

Implementation detail: [models](../../src/lerni/models.py), [database](../../src/lerni/db.py), [scheduler](../../src/lerni/sm2.py), [commands](../../src/lerni/commands).
