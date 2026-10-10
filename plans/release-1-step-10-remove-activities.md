# Release 1, step 10: remove the old activity path — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the activity cards, learning plans, plan import, catalog, engine, packaged lessons, and example plans, which have been off the screens since step 7, so the code is only what Lerni runs today.

**Architecture:** Two guard tests first, which pass before and after: an older account file (with the retired `explore_freely` key) still loads, and the installed package carries the persona files byte for byte (the distribution test, retargeted from the lessons it used to check). Then one removal commit: the old modules, their tests and fixtures, the drafter adapter, the lesson index script, and their package data. Then the docs. No behavior changes for anyone using the app.

**Tech Stack:** Python 3.11+, setuptools package data, pytest.

**Spec:** [plans/specs/04-interest-map.md](specs/04-interest-map.md) ("Build order" step 10).

## Global Constraints

- Remove: `plans.py`, `plan_import.py`, `catalog.py`, `engine.py`, `domain.py`, `canonical.py`, `lessons/`, `seed/`, `web/educator.py`, `web/guide.md`, `scripts/generate_lesson_index.py`; and what depends on them: `explore_freely` in `students.py`, `ClaudeCodeDrafter`, the package data in `pyproject.toml`, `test_core_imports.py`'s list, `test_distribution.py` (retargeted, not deleted), the chain-1 content tests, the old modules' tests and `conftest.py` fixtures, `plans/specs/02-lesson-core.md`, and `plans/runbooks/`.
- Nothing a person sees changes; every remaining test passes; the code manifest matches (a test checks it).
- Account files on the home server written before this step may contain `"explore_freely"`; they must still load.
- Old plan files in `~/.lerni/student/plans/` on the home server are not touched by code; deleting them is the admin's choice (a to-do item).
- Tests minimal (CLAUDE.md rule 4). Line length 100. Update `docs/code-manifest.md` for every removed file. No private details.

## Review Focus

- **An account file from before this step** (with `explore_freely`): still signs in. (Task 1 guard test.)
- **An installed wheel or sdist** (not the source checkout): still carries the personas, which every conversation reads. (Task 1 retargeted distribution test.)
- **Anything still importing a removed module** (a forgotten import in `web/`, `adapters/`, `commands/`, a script, or a test): caught by the full suite plus a grep. (Task 2 Step 3.)
- **Docs that still describe Learn, Learning plans, Sessions, cards, or the lesson index as current:** none after Task 3. (Task 3 grep.)
- **`lerni serve` on a fresh data folder:** starts without the example-plan seeding it used to do. (Task 2: `test_web_signin.py` builds the app on an empty folder.)

---

### Task 1: Guard tests that hold before and after

**Files:**
- Modify: `tests/student/test_students.py` (append)
- Modify: `tests/student/test_distribution.py` (retarget to the personas)

- [ ] **Step 1: Add the older-account guard**

```python
def test_an_account_saved_before_step_10_still_loads(tmp_path):
    # account files from before step 10 carry a retired "explore_freely" key
    import json

    store = StudentStore(tmp_path)
    store.add("sam", "Sam", Kind.INDEPENDENT, "long enough")
    path = tmp_path / "students" / "sam.json"
    data = json.loads(path.read_text())
    data["explore_freely"] = "2026-10-09"
    path.write_text(json.dumps(data))
    assert verify_password("long enough", store.get("sam").password)
```

- [ ] **Step 2: Retarget the distribution test to the personas**

Read `tests/student/test_distribution.py`. Keep its build-and-install machinery (`built`, `_install`, `_load_from`, `_digest`). Change:
- the module docstring: "A persona that loads from the source checkout but not from an installed wheel is a conversation that works for developers and fails for everyone else. …" (keep the rest);
- `LESSONS`/`LESSON_ID` → `PERSONAS = REPO / "src/lerni/student/personas"`;
- `LOAD_SNIPPET`:

```python
LOAD_SNIPPET = """
import hashlib
from lerni.student.conversation import persona
for voice in ("independent", "supervised"):
    print(hashlib.sha256(persona(voice).encode("utf-8")).hexdigest())
"""
```

- the test:

```python
@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_installed_distribution_carries_exact_persona_bytes(built, kind):
    site = _install(built[kind])
    hashes = _load_from(site, LOAD_SNIPPET).splitlines()
    assert hashes == [_digest(PERSONAS / "independent.md"), _digest(PERSONAS / "supervised.md")]
```

(`persona()` reads the file as UTF-8 text; `_digest` hashes the bytes. If a persona file has anything that changes on a decode/encode round trip, compare `read_text` hashes instead and record a ruling.)

- [ ] **Step 3: Run them**

Run: `.venv/bin/python -m pytest -q tests/student/test_students.py tests/student/test_distribution.py`
Expected: all pass (both guards hold today).

- [ ] **Step 4: Commit**

Update the manifest rows for `test_students.py` ("…and an account saved before step 10 still loads") and `test_distribution.py` ("Builds the wheel and sdist, installs each outside the repo, and checks the personas ship byte for byte.").

```bash
git add tests/student/test_students.py tests/student/test_distribution.py docs/code-manifest.md
git commit -m "Guard tests before removing the old activity path"
```

---

### Task 2: Remove the old activity path

**Files:**
- Delete: `src/lerni/student/{plans,plan_import,catalog,engine,domain,canonical}.py`, `src/lerni/student/lessons/`, `src/lerni/student/seed/`, `src/lerni/student/web/educator.py`, `src/lerni/student/web/guide.md`, `scripts/generate_lesson_index.py`, `tests/student/test_{canonical,catalog,catalog_listing,chain_1_content,domain,engine,plan_import,plans}.py`, `plans/specs/02-lesson-core.md`, `plans/runbooks/`
- Modify: `src/lerni/student/students.py`, `src/lerni/student/adapters/claude_code.py`, `src/lerni/student/__init__.py`, `tests/student/conftest.py`, `tests/student/test_claude_code_adapter.py`, `tests/student/test_core_imports.py`, `pyproject.toml`, `docs/code-manifest.md`

- [ ] **Step 1: Delete the files**

```bash
git rm -q src/lerni/student/plans.py src/lerni/student/plan_import.py src/lerni/student/catalog.py \
  src/lerni/student/engine.py src/lerni/student/domain.py src/lerni/student/canonical.py \
  src/lerni/student/web/educator.py src/lerni/student/web/guide.md \
  scripts/generate_lesson_index.py plans/specs/02-lesson-core.md
git rm -rq src/lerni/student/lessons src/lerni/student/seed plans/runbooks
git rm -q tests/student/test_canonical.py tests/student/test_catalog.py \
  tests/student/test_catalog_listing.py tests/student/test_chain_1_content.py \
  tests/student/test_domain.py tests/student/test_engine.py tests/student/test_plan_import.py \
  tests/student/test_plans.py
```

- [ ] **Step 2: Fix what depended on them**

- `students.py`: delete the `explore_freely` field, its line in `_to_dict`, and its read in `_from_dict` (the `.get("explore_freely")` line and the keyword argument). `_from_dict` must ignore unknown keys, which the Task 1 guard proves; if it passes `**data`, filter to the dataclass's fields instead.
- `adapters/claude_code.py`: delete `ClaudeCodeDrafter`, `TIMEOUT_SECONDS` only if nothing else uses it (the uploader does — keep it), and the `plan_import` import. Docstring: "Three uses: Ask Lerni's conversation, tagging each exchange for the interest map, and proposing map entries from uploaded notes."
- `tests/student/test_claude_code_adapter.py`: drop `ClaudeCodeDrafter` from the import and the parameter list.
- `tests/student/conftest.py`: keep only the module docstring (reworded: "Shared fixtures for student app tests: every test gets its own data folder."), the imports it needs, and `isolated_student_data`; delete the `domain` import and every lesson fixture.
- `tests/student/test_core_imports.py`: `CORE_MODULES` becomes `["__init__.py", "jsonfiles.py", "students.py", "signin.py", "conversation.py", "interests.py", "tagging.py", "logs.py", "upload.py", "feedback.py"]`.
- `src/lerni/student/__init__.py` docstring: "The student app: Lerni's conversation and interest maps. The core modules use the standard library only: no provider, model, credential, or network dependency. The ``web`` subpackage holds the Gradio screens and is the only place that may import Gradio; ``adapters`` holds the provider SDKs."
- `pyproject.toml` `[tool.setuptools.package-data]`: delete the `lerni.student.lessons`, `lerni.student.seed`, and `lerni.student.web` entries; keep `lerni.student.personas`.
- `docs/code-manifest.md`: delete the rows for every removed file (code, tests, script, lessons, seed, guide); remove the "Content shipped with the app" lines for lessons and seed (keep personas).

- [ ] **Step 3: Check nothing still points at them**

Run: `grep -rnE "lerni\.student\.(plans|plan_import|catalog|engine|domain|canonical|lessons|seed)|web\.educator|ClaudeCodeDrafter|PlanDrafter|explore_freely|generate_lesson_index|guide\.md" src tests scripts pyproject.toml`
Expected: no output.

- [ ] **Step 4: Run everything**

Run: `.venv/bin/python -m pytest -q && .venv/bin/python -m ruff check src/lerni/student tests`
Expected: all pass, no xfails left (the chain-1 xfails are gone); ruff clean on `src/lerni/student` and `tests`.

- [ ] **Step 5: Commit**

```bash
git add -A src tests scripts plans pyproject.toml docs/code-manifest.md
git commit -m "Remove the old activity path: plans, import, catalog, engine, lessons, seed"
```

---

### Task 3: Docs

**Files:**
- Modify: `CLAUDE.md`, `docs/ARCHITECTURE.md`, `plans/README.md`, `plans/release-1-mvp.md`, `docs/roadmap.md`, `docs/todo.md`, `docs/progress.md`

- [ ] **Step 1: Update**

- `CLAUDE.md`:
  - "What's here": drop "The older activity path … removed in step 10" and the `scripts/` lesson index sentence (scripts now holds the evals);
  - Commands: delete the `generate_lesson_index.py` line; add `.venv/bin/python scripts/eval_tagger.py   # evals: real Claude calls, run by hand` (one line naming the three eval scripts);
  - rule 1's history exceptions: drop `plans/specs/02-lesson-core.md` (keep `docs/progress.md`'s log, `plans/later/`, and git history).
- `docs/ARCHITECTURE.md`: "Built (steps 1–10)"; remove the "Planned" line; "Who owns" drops the "Learning plans, packaged activities" row; the codemap drops "Removed in step 10: …" and `educator.py`.
- `plans/README.md`: drop the spec 02 bullet and the runbooks mention; list the step 7–10 plans.
- `plans/release-1-mvp.md`: step 10 "*(Built.)*"; note that Release 1's code is complete and what remains is sessions.
- `docs/roadmap.md`: Release 1 status "In progress: steps 1–10 built; the first supervised sessions next".
- `docs/todo.md`: delete the step 10 row (the Upcoming PRs table is then empty: say "None queued; Release 2 (voice) starts with its spec"); add under Admin: "Optionally delete the old plan files on the home server (`~/.lerni/student/plans/`); nothing reads them since step 10."
- `docs/progress.md`: Current state (steps 1–9 merged; step 10 built on its branch; Built line without the older activity path); a log entry headed with the build date, "### <date> (PRs #16 and #17 merged; step 10 built: the old activity path removed)", with the test count.

- [ ] **Step 2: Check for stale descriptions**

Run: `grep -rnE "Learning plans tab|Sessions tab|activity card|lesson index|Learn tab|removed in step 10|step 10" CLAUDE.md README.md docs/ARCHITECTURE.md docs/roadmap.md docs/todo.md docs/code-manifest.md docs/prd plans/README.md`
Expected: only history (dated PRD decisions marked "Replaced") or nothing.

- [ ] **Step 3: Run the gate and commit**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass.

```bash
git add CLAUDE.md docs plans
git commit -m "Docs: Release 1's code is complete"
```

---

## Done when (from the spec)

Tests pass with the old path gone, and the code manifest matches. The app behaves exactly as after step 9.
