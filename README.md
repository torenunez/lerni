# Lerni

Lerni helps people understand ideas by explaining them and returning to them over time. It is built on two techniques: the **Feynman technique** (explain an idea simply to find what you don't understand) and **spaced repetition** (review at growing intervals so it sticks). [Learning concepts](docs/learning-concepts.md) covers these and the other ideas we design with.

Lerni has two parts:

- **Supervised student app — the main product.** A child explores ideas by voice while an adult supervises. An educator seeds the first activities and supervises from the app's supervisor view; a parent approves what the child sees and can stop any session. Adult involvement steps down over time as the system learns to draft activities. We are building it in steps: first text, pictures, and choices; then speaking and listening. The authoring tools and activity engine exist; the app is not built yet.
- **Admin tool — for the builder, in the terminal.** Full access: learn topics with it, try out anything a student would see, and tune the learning mechanics before the student app relies on them. Available now. Educators and parents never need it.

In the code, the student app is `explore` and the admin tool is `study`.

The student app treats knowledge as a map: **nodes** are ideas, and **edges** link them, either by how they relate or by which makes a good next step. A path starts at a child's core interest (cars, music, cooking) and follows edges toward an underlying idea. The map grows by branching to nearby ideas. It strengthens when the same idea is reached again from a different interest, so fractions met through music and again through cooking become one connected idea. Educators build the map today; suggesting where to go next comes later.

## Read in this order

1. [Student app PRD](docs/prd/student.md): what we're building, for whom, and why. The [admin tool PRD](docs/prd/admin.md) covers the builder's side.
2. [Learning concepts](docs/learning-concepts.md): the learning ideas behind Lerni.
3. [Architecture](docs/ARCHITECTURE.md): how the parts fit together.
4. [Roadmap](docs/roadmap.md): what comes next and who owns it.
5. [Progress](docs/progress.md): what exists and what remains unverified.

Educators can then open the [curation guide](curation/README.md) to prepare a path. Builders can use the [implementation index](plans/README.md) to find detailed specifications and tasks. The [admin tool reference](docs/reference/study.md) covers its commands and behavior.

The educator and builder can start now, in parallel. A reviewed activity can be tried without the app; student app use needs the separate preparation described in the product requirements.

## Setup

For builders: run these commands from a repository checkout with Python 3.11 or newer.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
study --help
```

The admin tool stores data locally in `~/.lerni/`. The student app is for supervised use by one family.
