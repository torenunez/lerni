# Curation: start here

This is where the educator plans what the student will learn. You need a spreadsheet app and a text editor, nothing else: no code, no IDs, no special formats.

## What you do

1. **Pick an interest and a goal.** Something the student cares about right now, and what you'd like them to understand through it. Cars, sharks, and soccer are only examples.
2. **Fill in the plan sheet.** Copy [LEARNING_PLAN.csv](learning-plan/LEARNING_PLAN.csv), one sheet per interest, and add 3–5 rows, one per activity, in the order you'd teach them. Each row says where you start from, the idea to learn, why it's a good next step, and the big question.
3. **Fill in one activity card.** Copy [ACTIVITY_CARD.md](learning-plan/ACTIVITY_CARD.md) for the next activity only, and write it the way you'd say it to the student: the short explanation, the question, the choices, the hints, and the picture idea.
4. **Send both to the admin.** The admin turns them into the app's format and tells you if anything is missing.
5. **Approve it.** Preview the activity in the educator view on your own phone or laptop (a draft never appears on the student's iPad), then check four things: the science is right, the wording suits the student, the picture works and is described in words, and it's OK to use. The admin records your approval. If anything changes afterward, you approve it again.
6. **Watch the student try it** (below), then revise one thing and fill in the next card.

**Example:** a [cars plan](examples/cars-learning-plan/LEARNING_PLAN.csv) with four rows, and the [activity card](examples/cars-learning-plan/ACTIVITY_CARD.md) for its acceleration activity. Meeting the same idea through another interest (speed through sharks) gets its own sheet.

## Watching the student try it

- The student uses the app on the iPad, with you beside them. You start, stop, and reset it from your own phone or laptop.
- Offer it in one sentence. The student may say no or stop at any time.
- About 5–10 minutes. Finishing is not the goal.
- Afterward, write brief private notes: what caught their interest, what confused them, what to change. Keep what happened separate from what you think it means.

What to watch for, and what each one shapes:

| Watch for | Shapes |
|---|---|
| Whether the student would rather talk, point, or tap | How soon voice matters |
| Where they get stuck, and which hints help | Hint design |
| When attention drops | Activity length and step size |
| Whether the pictures help | Which visuals the app needs |
| What you had to do: re-read, rephrase, encourage | What the app must do itself vs. leave to you |
| Whether they can explain, not just pick | How understanding is checked |
| What confused the student about the screen itself | The app's design, separate from the content |
| How long prep took and what confused you | These templates |

Record only what actually happened; leave gaps blank. A correct choice alone is not mastery.

## Never write in the plan or the card

This repository is public. Never write a student's name or initials, birthday, school, address, contact details, photos, audio, transcripts, a student's exact words, what a particular student liked or did, or anything medical or behavioral. A topic ("sharks") is curriculum. "My student loves sharks" is a private note, and it stays with you.

## For the admin

The admin turns the plan sheet and activity card into two things:

- **The authoring tables:** one path per plan sheet, in six linked spreadsheets (ideas, how they relate, teaching moves, paths, path steps, sources) that the checker can verify. How: [table templates](templates/educator-paths-v1/README.md); [six example paths](examples/educator-paths-v1-draft/README.md); [field definitions](../plans/specs/08c-educator-path-authoring.md). Run `scripts/validate_curation_templates.py`. A clean result means the files are consistent, not that the content is correct or approved.
- **The activity file** for the app, in `src/lerni/student/lessons/`, where the educator's four approvals are recorded against its exact content ([Approve an activity](../docs/prd/educator.md#story-approve-an-activity)). A row marked `reviewed` in the tables is a drafting note, not an approval.

Older formats, for reference only: [`templates/v1/`](templates/v1/README.md), [`examples/chain-1-v1-draft/`](examples/chain-1-v1-draft/).
