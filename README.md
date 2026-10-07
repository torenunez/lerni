# Lerni

Lerni helps people understand ideas by explaining them and returning to them over time.

**Study** is the available adult study tool, used from a terminal. **Explore** starts with a child's interest and a learning path prepared by an educator. Its authoring tools and lesson engine exist; the local app is not built yet.

## Read in this order

1. [Product requirements](docs/PRD.md): what we're building, for whom, and why.
2. [Architecture](docs/ARCHITECTURE.md): how the parts fit together.
3. [Roadmap](docs/roadmap.md): what comes next and who owns it.
4. [Progress](docs/progress.md): what exists and what remains unverified.

Educators can then open the [curation guide](curation/README.md) to prepare a path. Builders can use the [implementation index](plans/README.md) to find detailed specifications and tasks. The [Study reference](docs/reference/study.md) covers its commands and behavior.

The educator and builder can start now, in parallel. A reviewed activity can be tried without the app; student app use needs the separate preparation described in the product requirements.

## Setup

For builders: run these commands from a repository checkout with Python 3.11 or newer.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
study --help
```

Study stores data locally in `~/.lerni/`. Explore's first app is intended for supervised use by one family.
