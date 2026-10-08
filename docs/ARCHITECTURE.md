# Architecture

The student app and the admin tool share a repository and Python. Today they keep their sessions, data, and scheduling separate; the student app will come to rely on mechanics the admin tunes in the admin tool, and which parts they share is still open. The student app uses its own engine: code that decides which prepared step of an activity comes next.

## From an idea to an activity

```text
Authoring tables [available]
        ↓ prepare and review one activity
        ├→ educator-led walkthrough [no app needed]
        └→ prepare app lesson → approve exact content
                                  ↓
                     Catalog + engine [available]
                                  ↓
                Web app on iPad + educator view [planned]
```

These are the steps in the process, not completed reviews. The [product requirements](prd/student.md#release-1-run-a-seeded-activity) define readiness for student app use; [progress](progress.md) records what exists.

## Four responsibilities

**Authoring:** six tables hold concepts (nodes), subject relationships, teaching connections, paths, path steps, and sources. A node is a reusable idea. A relationship describes how ideas relate. A directional connection explains why one idea is a useful next stop. The path sets activity order. Concepts can be shared, branched from, or revisited. Interest, bridge, and fundamental describe a concept's role in a path, not a permanent category.

**Preparing app content:** the educator and admin manually turn one path step into one lesson. A lesson may contain several presentation steps. A separate record links the path and activity IDs, activity revision, and lesson revision. There is no automatic importer yet. The catalog loads lessons and checks their exact content, human approvals, and files before making them available.

**Running an activity:** the engine controls progression. The planned web app, used in Safari on an iPad, adds an educator view with Start/Stop/Reset and keeps actions tied to the correct session. Separating the activity from the interface lets different interests use the same engine.

**Learning from observations:** early learner notes stay in a private manual log outside the repository. Only generalized educational improvements return to the curriculum.

Later recommendations should explain existing reviewed options first. Proposed concepts or connections need duplicate checks and educator review; activities built from them still need their own approval. Educator involvement steps down in stages (see the [educator PRD](prd/educator.md#how-educator-involvement-changes)); at every stage, nothing silently changes the curriculum.

Details: [authoring fields](../plans/specs/08c-educator-path-authoring.md) and [implementation plans](../plans/README.md).
