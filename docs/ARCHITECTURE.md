# Architecture

Study and Explore share a repository and Python, but keep their learning sessions, data, and scheduling separate. Explore uses its own lesson engine: code that decides which prepared lesson step comes next.

## From an idea to an activity

```text
Authoring tables [available]
        ↓ prepare and review one activity
        ├→ educator-led walkthrough [no app needed]
        └→ prepare app lesson → approve exact content
                                  ↓
                     Catalog + engine [available]
                                  ↓
                Local app + parent controls [planned]
```

These are the steps in the process, not completed reviews. The [product requirements](PRD.md#first-app) define readiness for student app use; [progress](progress.md) records what exists.

## Four responsibilities

**Authoring:** six tables hold concepts (nodes), subject relationships, teaching connections, paths, path steps, and sources. A node is a reusable idea. A relationship describes how ideas relate. A directional connection explains why one idea is a useful next stop. The path sets activity order. Concepts can be shared, branched from, or revisited. Interest, bridge, and fundamental describe a concept's role in a path, not a permanent category.

**Preparing app content:** the educator and builder manually turn one path step into one lesson. A lesson may contain several presentation steps. A separate record links the path and activity IDs, activity revision, and lesson revision. There is no automatic importer yet. The catalog loads lessons and checks their exact content, human approvals, and files before making them available.

**Running the lesson:** the engine controls progression. The planned local browser app, built with Gradio, adds parent Start/Stop/Reset and keeps actions tied to the correct session. Separating the lesson from the interface lets different interests use the same engine.

**Learning from observations:** early learner notes stay in a private manual log outside the repository. Only generalized educational improvements return to the curriculum.

Later recommendations should explain existing reviewed options first. Proposed concepts or connections need duplicate checks and educator review; activities built from them still need their own approval. AI never decides progression or silently changes curriculum.

Details: [authoring fields](../plans/specs/08c-educator-path-authoring.md) and [implementation plans](../plans/README.md).
