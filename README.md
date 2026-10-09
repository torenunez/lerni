# Lerni

Lerni is a learning app that facilitates interest exploration, provides users a deeper understanding of these interests, and helps them connect key concepts, reinforce them, and commit them to memory. It is built on key learning concepts such as the **Feynman technique** (explain an idea simply to find what you don't understand) and **spaced repetition** (review at growing intervals so it sticks). [Learning concepts](docs/learning-concepts.md) covers these and the other ideas we design with.

Lerni has two parts:

- **Student app — the main product.** Everyone signs in, and there are two kinds of student, set by supervision rather than age:
  - A **supervised student** talks with Lerni on an iPad, with an educator beside them. The educator chooses a few **goals**, and Lerni bridges toward them from what the student already loves. Educator involvement steps down over time, until the student talks with Lerni on their own and the educator only glances at their map.
  - An **independent student** is their own educator: they talk with Lerni and set their own goals: things to practice. The educator and admin use the app this way too, which tests it before a supervised student relies on it.

  We are building it in steps: first a text conversation and the interest map; then a companion that remembers what each student likes; then speaking and listening. Sign-in and the text conversation exist; the interest map comes next.
- **Admin tool — in the terminal.** Full access: learn topics with it, try out activities, and tune the learning mechanics before the student app relies on them. Available now. Educators never need it. To use the app as a learner, the admin has their own independent student account.

Each student has an **interest map**. **Interests** grow out of the conversation (cars, sharks, soccer), drawn bigger the more days they come up. **Goals** are what the educator would like them to explore (fractions, reading clocks), in coral, while interests are green. **Bridges** show where Lerni led from one to the other, so fractions met through cars becomes part of what the student loves. Design: [interest map spec](plans/specs/04-interest-map.md).

## Read in this order

1. [Student app PRD](docs/prd/student.md): what we're building, for whom, and why.
2. [Educator PRD](docs/prd/educator.md): every educator task.
3. [Admin tool PRD](docs/prd/admin.md): the terminal tool.
4. [Learning concepts](docs/learning-concepts.md): the learning ideas behind Lerni.
5. [Architecture](docs/ARCHITECTURE.md): how the parts fit together.
6. [Roadmap](docs/roadmap.md): what comes next and who owns it.
7. [Progress](docs/progress.md): where things stand, and a dated log of what was done.

Educators don't need this repository: everything for them is in the app. Admins can use the [implementation index](plans/README.md) to find detailed specifications and tasks. The [admin tool reference](docs/reference/admin.md) covers its commands and behavior.

The first thing anyone tries is the MVP app (Release 1): the admin and educator first, as independent students, then a supervised student with the educator beside them ([educator PRD](docs/prd/educator.md#release-1-set-goals-watch-and-give-feedback)). The design: [interest map spec](plans/specs/04-interest-map.md); accounts and sign-in: [student accounts spec](plans/specs/03-student-accounts.md).

## Setup

For admins: run these commands from a repository checkout with Python 3.11 or newer.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,student]"   # [student] adds Gradio; without it, the web tests are skipped
pytest
lerni --help
```

The admin tool stores data locally in `~/.lerni/`. The student app is for one household on its home network.
