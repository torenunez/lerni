# Lerni

A local-first, privacy-preserving learning system. One repository, two modes:
**Study**, a Feynman-technique and spaced-repetition CLI for adults, and
**Explore**, a parent-supervised experience that walks a child from something
they already care about down to the idea underneath it.

## Modes

| | Study | Explore |
|---|---|---|
| For | A self-directed adult | A child (~7–9) with a parent present |
| Interface | Terminal — `study` | Local browser page, `127.0.0.1` only |
| Status | Feature-complete, maintenance-only | **In development — not usable yet** |

**Study** — capture what you know, explain it simply, find the gaps, refine, then
review on an SM-2 schedule.

**Explore** — an educator-curated path takes a child from an interest they already
have (cars, music, cooking, plants, building…) to an underlying idea, one short
reviewed activity at a time. The application owns the lesson; any AI capability is optional,
replaceable, and cannot decide what is taught or whether an answer was right.

## Current Status

**Study Phase 1 is complete and working.** Data layer, Feynman workflow, SM-2
scheduling, concept graph, and CLI are all functional. It receives fixes, not new
features. Feature-complete is not the same as hardened — see [`docs/todo.md`](docs/todo.md)
for open test and lint debt.

**Explore has a lesson core but no app yet.** The lesson domain, catalog, and
deterministic engine exist in `src/lerni/explore/`, with one draft (unreviewed)
lesson. Educators can outline learning paths today with the templates in
[`curation/`](curation/README.md) and check them offline. There is no app to run;
see [`docs/roadmap.md`](docs/roadmap.md) for milestones M1–M6.

## Study Quick Start

```bash
study new "How does TCP congestion control work?"   # 4-step Feynman flow
study new "Quick thought" --quick                   # capture step 1 only
study today                                         # what's due
study review                                        # run a review session
study list --due                                    # filter by due date
study search "congestion"                           # full-text search

study concept new "Networking"                      # knowledge graph
study concept link "TCP" "Networking" --type parent
study concept list
```

Data lives in `~/.lerni/`. Nothing leaves your machine.

## Explore — Development Status

> **Not usable.** Explore is under active development and has no working entry
> point. It is being built for one family, for supervised use on a single machine.

When it does run, it will bind to `127.0.0.1` only, with no share URL and no
public deployment. It is a prototype with prototype guardrails plus a parent in
the room — it is **not** a moderation system, **not** a COPPA compliance posture,
and **not** production-ready software. Any use outside the immediate family would
require a separate privacy, safety, and legal review that has not been done.

No model, provider, or hosted service is required. Text generation and
speech-to-text are optional capabilities selected by explicit runtime
qualification. With none configured, the lesson still runs on authored content.

## Installation

```bash
git clone https://github.com/torenunez/lerni.git
cd lerni
python3 -m venv .venv && source .venv/bin/activate
```

**Core (Study)** — everything needed for the CLI:

```bash
pip install -e .
```

**Development** — adds pytest, mypy, and ruff:

```bash
pip install -e ".[dev]"
```

**Explore UI** — *planned, not yet available.* Will install the local UI
framework as an optional extra; the core install will not require it.

**Optional runtime adapters** — *planned, environment-specific.* Any tutor,
speech-to-text, or additional harm-gate capability is installed separately as its
own reviewed distribution, chosen by the operator. None is bundled, and none is
required. Credentials are supplied as environment references, never written into
configuration files or committed.

Requires Python 3.11+.

## Testing

```bash
pytest                       # full suite
pytest tests/test_sm2.py -v  # one file
pytest -k "interval"         # one pattern
ruff check src/              # lint (carries known debt — see docs/todo.md)
mypy src/                    # types
```

## Documentation

- [Mission](docs/mission.md) — vision, two modes, core beliefs
- [Product Requirements](docs/PRD.md) — requirements and safety boundaries
- [Technical Specification](docs/spec.md) — data model, CLI, Explore contracts
- [Roadmap](docs/roadmap.md) — Explore milestones M1–M6; parked Study phases
- [Backlog](docs/todo.md) — active Explore work, parked Study work
- [Curation](curation/README.md) — educator path-authoring templates, examples, and offline checker
- [Progress Log](docs/progress.md) — dated implementation history
- [`plans/`](plans/) — Explore implementation bundle: [master plan](plans/cursor_master_plan.plan.md), plus `prs/` (execution units), `specs/` (technical contracts), and `runbooks/` (manual procedures)

## License

[MIT](LICENSE)
