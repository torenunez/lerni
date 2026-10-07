# Lerni

Lerni helps people understand ideas by explaining them and returning to them over time. It is built on two techniques: the **Feynman technique** (explain an idea simply to find what you don't understand) and **spaced repetition** (review at growing intervals so it sticks). [Learning concepts](docs/learning-concepts.md) covers these and the other ideas we design with.

Lerni has two versions, each built around how its learner works best:

- **Explore — for children, by voice, with an adult in charge.** The app speaks with a child and listens to their answers. Adults direct it: an educator chooses the interest and prepares the path, a parent approves what the child will see, and a parent stays with the child for the whole session and can stop it at any time. The app never decides on its own what a child learns next. We are building it in steps: the first app uses text, pictures, and choices; speaking and listening come next. The authoring tools and lesson engine exist; the app is not built yet.
- **Study — for engineers learning technical topics, in the terminal.** Available now.

Explore treats knowledge as a map: **nodes** are ideas, and **edges** link them, either by how they relate or by which makes a good next step. A path starts at a child's core interest (cars, music, cooking) and follows edges toward an underlying idea. The map grows by branching to nearby ideas. It strengthens when the same idea is reached again from a different interest, so fractions met through music and again through cooking become one connected idea. Educators build the map today; suggesting where to go next comes later.

## Read in this order

1. [Product requirements](docs/PRD.md): what we're building, for whom, and why.
2. [Learning concepts](docs/learning-concepts.md): the learning ideas behind Lerni.
3. [Architecture](docs/ARCHITECTURE.md): how the parts fit together.
4. [Roadmap](docs/roadmap.md): what comes next and who owns it.
5. [Progress](docs/progress.md): what exists and what remains unverified.

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
