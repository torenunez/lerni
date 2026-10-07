# Product requirements

Explore turns a child's interest into a short path toward understanding an underlying idea. We are starting with one family and a child around ages 7–9. Study remains the separate adult study tool.

## First learning loop

The educator chooses an interest and goal, sketches 3–5 activities, and prepares the first. Educator and parent review the wording and materials. The student may try a short walkthrough without the app and stop whenever they want. The team records observations privately and revises one thing.

The builder uses test content while the educator prepares the activity. The parent supervises student use and authorizes app sessions. Record genuine reviews and observed results; leave missing evidence unfilled.

Success means the educator can author independently, observations improve an activity, and a second interest reuses concepts without special-case changes. Look for explanation and later recall; a correct choice alone is not mastery.

## First app

One prepared activity becomes one short lesson. Keep the first app small:

| ID | Required behavior |
|---|---|
| APP-01 | Reuse the existing lesson format, catalog, and engine; load approved lessons and intended files from the installed app. |
| APP-02 | Show prepared text, visuals with text alternatives, choices, hints, and completion. |
| APP-03 | Parent Start/Stop/Reset. Stop ends interaction and prevents pending actions from taking effect. Reset clears progress and returns to the parent screen; another activity requires Start. |
| APP-04 | Keep actions tied to their session. Delayed, repeated, or previous-session actions cannot change a stopped, reset, or replacement session. |
| APP-05 | Reject unapproved or damaged lesson content and files. |
| APP-06 | Bind to localhost (this computer only); use bundled files with no outbound requests, sharing, analytics, or remote assets. |
| APP-07 | Keep session state in memory; save no responses, progress, or observations to disk. Logs contain no learner content. |
| APP-08 | Keep Study commands and data compatible; distinguish existing failures from new ones. |

Humans approve the exact lesson wording and assets installed in the app. Student app use also needs technical checks, adult rehearsal, and parent authorization. Spreadsheet review is separate; changed content needs re-review.

AI, voice, accounts, cloud sync, automatic import, graph traversal, and saved learner records are outside this first app.

These controls are prototype guardrails plus a present parent. They are not production moderation, and the app is for one supervised family, not public use.
