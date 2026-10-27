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

`lerni serve` runs the student app on the home server (Version 1: sign-in; Chat, My MentalMap, and Settings for independent students; the student's page (named after them when there's one) and Games for educators, with Students inside Settings; Chat, full screen, and Games for a supervised student).

```bash
pip install -e ".[student]"                # once: installs Gradio
lerni serve                                 # binds 0.0.0.0:7860
```

- Every device opens `http://<home-server>:7860/` and signs in at `/signin`; the app itself is at `/app/`.
- **First start:** add the first educator on the home server, then that educator adds everyone else in **Settings → Students** (☰ menu):

  ```bash
  lerni student add USERNAME --name NAME --kind independent --educator   # asks for the password
  ```

  `lerni student list`, `lerni student reset-password USERNAME`, and `lerni student educator USERNAME [--off]` cover recovery.
- A supervised student's iPad is signed in only as that student. Try the app as yourself on your own device or in a private tab.
- Data lives in `~/.lerni/student/` (or `$LERNI_STUDENT_DATA`): `students/` (accounts, password hashes only), `secret.key` (signs the sign-in cookie; keep it private; deleting it signs everyone out), `maps/` (interest maps, with resting items), `logs/` (each exchange, deleted after a year), `concepts/` (every race idea and how it went), and `feedback.jsonl`.
- `--port` changes the default port; `--host 127.0.0.1` keeps it on this computer only; `--label Development` marks a development server on every page. Startup prints the running version (number, branch, commit, date), and the sign-in page shows it at the bottom: check it there after updating.
- Run it with `lerni service` ("Running on its own" below), or in a Terminal window on the home server's own desktop; never inside `tmux` or over SSH: there macOS `say` makes empty audio, so answers show as text but are never spoken.
- It never touches the admin tool's database.
- **Claude** (Chat, the map's tagger, Upload, and the MentalMaps chat) turns on when the `claude` CLI is installed and logged in on this computer; it uses that Claude account, so there's no API key. `LERNI_CLAUDE_MODEL` picks the answering and upload model (default `claude-sonnet-5-5`), `LERNI_TAGGER_MODEL` the tagger's (default `claude-haiku-5-5`). Startup prints whether it's on.
- **Claude usage:** Lerni shares the account's limits with the admin's own Claude use. Educators see a warning at 75% of the weekly limit or 80% of the 5-hour one, with the reset time; at 95%, or if a call ever uses paid extra usage, Lerni rests until the reset. Turn off extra usage on the Claude account too, so Lerni can never spend credits.
- **Points and Games:** each player's points, cars, and today's races are in `~/.lerni/student/points/<username>.json` (ids and numbers only). To give or take points, stop the server, edit `balance`, and start it again. A race writes and checks its questions with the small model, about ten short calls a day per player; 10 races a day. With voice on, a tap on the question reads it, and a wrong answer's right answer is said, with `say` (no Claude call; memory only). Every idea a question tested, and how often it was right, is kept in `concepts/` (labels and counts only), so new questions ask about others. Each answer and finish is in `results/<username>.jsonl` (labels and numbers, kept for good). A blind second call checks each set's answers, and the server works out sums itself, so a question with a wrong key never races. **The bonus round:** now and then question 4 asks the student to explain an idea in their own words (typed or spoken); one more small call grades it (nailed 15 ⭐, partly 7, a real try 2), and the answer itself is never saved, except one that says the student is hurt or unsafe: that shows Chat's caring words and goes to the conversation logs (`lerni logs`), as a worrying Chat message does.
- **Race sounds:** `roar.mp3`, `sputter.mp3`, and `finish.mp3` in `~/.lerni/student/sounds/` (and `student-dev/`), served only to someone signed in; the race plays the first 1.5 s (the finish 2.5 s) of each. To swap one, copy any mp3 over it with the same name; the next race plays it. A missing clip is silent. Never commit them: they're Pixabay clips, and its licence forbids sharing the files.
- **Adding a real car:** cut it out of a side-on picture facing right with `swift scripts/lift_car.swift picture.png car.png [x y width height]` (the crop from the top-left), save it as WebP about 600 px wide in `~/.lerni/student/cars/`, and add it to `~/.lerni/student/garage.json`: `{"cars": [{"id", "name", "usd", "zero_to_60", "engine", "power_hp", "drive", "note", "picture"}]}`. Its price is dollars ÷ 2,500, rounded to tens of ⭐, and its gas boost comes from the 0–60. Restart to load it, and copy both into `~/.lerni/student-dev/` so development matches. Keep these files out of the repo.
- `lerni logs [USERNAME]` shows the last 7 days of conversations and what the tagger did (including `same_as`, a name it joined to an item) (`--days N` for more; a year is kept); `lerni feedback` lists educators' feedback (`--summary` groups it, `done N` closes one).
- Evals (real Claude calls, run by hand when instructions or models change): `scripts/eval_tagger.py`, `scripts/eval_upload.py`, `scripts/eval_supervised.py`, `scripts/eval_voice.py`, `scripts/eval_educator.py`.

### Two environments

- **Production:** the home server, on `main`, port 7860, the real data folder (`~/.lerni/student/`). The family uses it; on the student's iPad, open it in Safari and use Share → Add to Home Screen.
- **Development:** the computer where changes are built, on a branch, port 7861, its own data folder and made-up test accounts, run with `lerni service install dev` ("Running on its own" below), so its address stays `https://` too (add accounts the same way: `LERNI_STUDENT_DATA=~/.lerni/student-dev lerni student add tester …`). Bookmark it on the admin's phone; it has its own sign-in, so both bookmarks stay signed in.
- Never point development at `~/.lerni/student/`, or test conversations land in the real maps and logs. Both use the admin's Claude account, so heavy testing uses the same plan.

### Updating the home server

The family uses whatever is on `main` while new features are built on branches. Production runs from its own checkout, so building never changes it, even on the same computer (once: `git worktree add -b production ~/lerni-prod origin/main`, then its own `.venv`). To put a merged change on the home server:

1. In the production checkout: `git pull`.
2. `.venv/bin/pip install -e ".[student]"` (only needed when a PR says dependencies or package files changed, but always safe).
3. `.venv/bin/lerni service restart prod` (install it once first: "Running on its own" below).

Caveats:

- A restart clears open conversations (they live in memory); accounts, maps, logs, and feedback stay. Restart between sessions, not during one.
- Never run a branch as production; test branches as development ("Two environments" above).
- Each PR's Deploying section says whether it's safe to use yet and anything extra to do; if it says not yet, leave the server on the previous `main` (the merge can wait, or `git checkout <the previous merge>` on the server).

### Running on its own

Both servers run as macOS LaunchAgents: they start when the admin logs in (after a reboot too, once someone logs in) and restart within 30 seconds of a crash, whatever happens to a Terminal window. Install once, from each checkout, after stopping any copy running in a Terminal window (otherwise its port is taken):

- Production, in the production checkout: `.venv/bin/lerni service install prod --cert ~/.lerni/student/https.pem --key ~/.lerni/student/https-key.pem`.
- Development, in the development checkout: `.venv/bin/lerni service install dev` with the same `--cert` and `--key` (its data folder is `~/.lerni/student-dev`; it refuses production's).
- Install from a Terminal on this Mac, not over SSH: it saves this shell's PATH and its `LERNI_*` settings (the voice, the models; the data folder only from `--data`) for the server, says which it saved or dropped, and warns if `claude` or `whisper-cli` can't be found, or if production's checkout holds code that isn't on `main`. It refuses either server on the other's data folder or port. To change a setting, install again with the same `--cert` and `--key`; the last log is kept as `<name>.log.1`.
- Then `lerni service status` (running and answering?), `restart prod|dev` (after an update or a branch change; also starts a stopped one), `stop`, or `uninstall`. `install` and `restart` wait up to 75 seconds for the server to answer, and if it doesn't, show the end of its log. Output goes to `~/Library/Logs/lerni/<name>.log`; on restart a log over 5 MB moves to `<name>.log.1`.

### Backups and undo

- **Nightly copies:** `lerni backup install` (once, in the production checkout) copies `~/.lerni/student` to `~/.lerni/backups/student/nightly-<date>/` every night at 03:00 and keeps the newest 30; `lerni backup run` copies now (`--to /Volumes/Drive/lerni` also copies to a drive: use an encrypted one, since the copy holds the logs, accounts, and keys); `lerni service status` shows the newest copy. They're on the same disk: they cover a bad change or deploy, not a broken disk.
- **Restore:** `lerni service stop prod`, move `~/.lerni/student` aside, copy a nightly folder back as `~/.lerni/student`, then `lerni service restart prod`.
- **Undo one map change:** `lerni map log USER` lists each change (number, when, who: the tagger, a person, Upload, the MentalMaps chat, or the admin, and which items); `lerni map undo USER N` reverses one, as a new change, keeping what only grew since (new days, mentions, other names), and refuses when a later change renamed, removed, or regrouped the same items, or when the result would break the map's rules; then `lerni map rebuild USER --upto N` returns the whole map to just after change N. `lerni map rebuild USER` alone checks the journal still matches the map. All three are safe while the server runs.

### HTTPS (for voice)

iPad Safari allows the microphone only over HTTPS. Lerni uses its own certificate, made once with [mkcert](https://github.com/FiloSottile/mkcert) on the home server:

1. `brew install mkcert`. Its first run creates a small private certificate authority on this Mac; skip `mkcert -install`, which only makes this Mac trust it.
2. Make the server's certificate, naming every way devices reach it: `mkcert -cert-file ~/.lerni/student/https.pem -key-file ~/.lerni/student/https-key.pem <home-server>.local <its-IP> localhost`. The key stays on the home server; never copy it into the repo.
3. On each device (iPad, phones): send it the authority's certificate, `"$(mkcert -CAROOT)/rootCA.pem"` (AirDrop works), open it to install the profile (Settings → Profile Downloaded, or General → VPN & Device Management → Install), then turn on full trust (Settings → General → About → Certificate Trust Settings).
4. Install the service with `--cert ~/.lerni/student/https.pem --key ~/.lerni/student/https-key.pem` ("Running on its own" above) and open `https://<home-server>.local:7860/`.

Safari's saved password is for the old `http://` address; sign in once more and let it save again. Replace any bookmark or home-screen icon with the `https://` address (the old one stops working). If the server's IP changes, make the certificate again (step 2); a fixed address for the server in the router avoids that.

Once a device has signed in over HTTPS, keep serving HTTPS: if the server goes back to plain HTTP (started without `--cert`, or rolled back to a `main` from before HTTPS), that device may fail to sign in until its website data for the server is cleared (Safari: Settings → Apps → Safari → Advanced → Website Data).

### Voice

Hold to talk needs HTTPS and two tools on the home server, run as commands (nothing else to keep running):

1. `brew install whisper.cpp` (speech to text), then its model, about 0.5 GB: `mkdir -p ~/.lerni/models && curl -L -o ~/.lerni/models/ggml-small.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin`. Another place: set `LERNI_WHISPER_MODEL`.
2. Lerni speaks with the Mac's own voice (`say`). To pick one, list them with `say -v '?'`, try one with `say -v NAME "Sharks are amazing swimmers!"`, and set `LERNI_SAY_VOICE=NAME`, then install the service again with its `--cert` and `--key` ("Running on its own"). Nicer voices download in System Settings → Accessibility → Spoken Content → System Voice.
3. Its log prints `Voice (hold to talk): on`, or `off` with the reason (the tools are missing, `say` makes no sound, or `say` failed, often a misspelled `LERNI_SAY_VOICE`). Check it with `.venv/bin/python scripts/eval_voice.py`.
4. On each device, so Safari stops asking for the microphone: on the Lerni page, the page menu in the address bar → Website Settings → Microphone → Allow.

If answers show but are never spoken, on every device: the server was started inside `tmux` or over SSH, where `say` makes no sound; startup then says voice is off. Run it with `lerni service` instead. (Whisper runs as fast under the service as in Terminal: about 0.75 s for a 6-second clip.)

Audio stays on the home server: each clip's temp file is deleted once it's heard, and spoken sentences are never saved.

## Maintenance

Open work is tracked in [todo.md](../todo.md#admin-tool-maintenance). Existing scheduling tests do not establish complete application coverage.

Implementation detail: [models](../../src/lerni/models.py), [database](../../src/lerni/db.py), [scheduler](../../src/lerni/sm2.py), [commands](../../src/lerni/commands).
