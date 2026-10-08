# Lerni

Lerni is a learning app that facilitates interest exploration, provides users a deeper understanding of these interests, and helps them connect key concepts, reinforce them, and commit them to memory. It is built on key learning concepts such as the **Feynman technique** (explain an idea simply to find what you don't understand) and **spaced repetition** (review at growing intervals so it sticks). [Learning concepts](docs/learning-concepts.md) covers these and the other ideas we design with.

Lerni has two parts:

- **Educator-supervised student app — the main product.** A student explores ideas by voice on an iPad while an educator supervises. The educator seeds the first activities, approves what the student sees, supervises from the educator view, and can stop any session. Educator involvement steps down over time: at first the app explores only concepts on the educator's allowlist; eventually the student converses freely about anything not on the educator's exclusion list, and the educator reviews a map of the concepts explored, blocks paths, and answers the rare consent request for a sensitive subject. We are building it in steps: first text, pictures, and choices; then remembering what the student explored and building on it; then speaking and listening. The authoring tools and activity engine exist; the app is not built yet.
- **Admin tool — in the terminal.** Full access: learn topics with it, try out anything a student would see, and tune the learning mechanics before the student app relies on them. Available now. Educators never need it.

The student app treats knowledge as a map: **nodes** are ideas, and **edges** link them, either by how they relate or by which makes a good next step. A path starts at a student's core interest (cars, sharks, soccer) and follows edges toward an underlying idea. The map grows by branching to nearby ideas. It strengthens when the same idea is reached again from a different interest, so speed met through cars and again through sharks becomes one connected idea. Educators build the map today; suggesting where to go next comes later.

## Read in this order

1. [Student app PRD](docs/prd/student.md): what we're building, for whom, and why.
2. [Educator PRD](docs/prd/educator.md): every educator task.
3. [Admin tool PRD](docs/prd/admin.md): the terminal tool.
4. [Learning concepts](docs/learning-concepts.md): the learning ideas behind Lerni.
5. [Architecture](docs/ARCHITECTURE.md): how the parts fit together.
6. [Roadmap](docs/roadmap.md): what comes next and who owns it.
7. [Progress](docs/progress.md): what exists and what remains unverified.

Educators can then open the [curation guide](curation/README.md) to prepare a path. Admins can use the [implementation index](plans/README.md) to find detailed specifications and tasks. The [admin tool reference](docs/reference/admin.md) covers its commands and behavior.

The educator and admin can start now, in parallel. The first thing the student tries is the MVP app (Release 1); it needs an approved activity and the preparation described in the [student app PRD](docs/prd/student.md).

## Setup

For admins: run these commands from a repository checkout with Python 3.11 or newer.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
lerni --help
```

The admin tool stores data locally in `~/.lerni/`. The student app is designed for supervised use.
