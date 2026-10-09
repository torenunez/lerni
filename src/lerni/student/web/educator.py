"""The educator view: Guide, Sessions, and Learning plans.

The handlers below are plain functions over a :class:`PlanStore` so they can
be tested without a browser; :func:`build_educator_view` wires them to Gradio.
Every event is ``api_visibility="private"``, and the whole app sits behind the
educator passcode (see ``app.py``).
"""

from __future__ import annotations

import os
from dataclasses import replace
from importlib import resources
from pathlib import Path
from typing import Any

import gradio as gr

from lerni.student.catalog import PackageLessonCatalog
from lerni.student.plan_import import (
    DrafterUnavailable,
    PlanDrafter,
    extract_source,
    proposal_notes,
    proposal_to_plan,
)
from lerni.student.plans import (
    MAX_ACTIVITIES,
    ActivityCard,
    LearningPlan,
    PlanError,
    PlannedActivity,
    PlanStore,
    drafting_notes,
    new_plan_id,
)

COLUMNS = ["Start from", "Idea to learn", "Why it's a good next step", "Big question"]
PRIVATE = {"api_visibility": "private"}
NEVER_WRITE = (
    "Plans are about ideas, not about the student: never write a name, initials, "
    "or anything personal."
)


def guide_text() -> str:
    """Return the in-app guide (``guide.md``, shipped with the package)."""
    return resources.files("lerni.student.web").joinpath("guide.md").read_text("utf-8")


# --- plan handlers -----------------------------------------------------------


def plan_choices(store: PlanStore) -> list[tuple[str, str]]:
    """Dropdown entries ``(label, plan_id)``; examples are labeled."""
    return [
        (f"{p.interest or 'Untitled plan'}{' (example)' if p.is_example else ''}", p.plan_id)
        for p in store.list_plans()
    ]


def plan_rows(plan: LearningPlan) -> list[list[str]]:
    """The activities as table rows, in teaching order."""
    return [[a.start_from, a.idea, a.why, a.big_question] for a in plan.activities]


def activity_choices(plan: LearningPlan) -> list[tuple[str, int]]:
    """Dropdown entries ``(label, index)`` for picking an activity's card."""
    return [
        (f"{i + 1}. {a.idea or 'Untitled activity'}{'' if a.card else ' (no card yet)'}", i)
        for i, a in enumerate(plan.activities)
    ]


def _clean_rows(rows: Any) -> list[list[str]]:
    cleaned: list[list[str]] = []
    for row in rows or []:
        cells = [("" if c is None else str(c)).strip() for c in list(row)[: len(COLUMNS)]]
        cells += [""] * (len(COLUMNS) - len(cells))
        if any(cells):
            cleaned.append(cells)
    return cleaned


def save_plan(
    store: PlanStore, plan_id: str, interest: str, goal: str, rows: Any
) -> tuple[LearningPlan, str]:
    """Save the plan's interest, goal, and activity rows.

    Activity cards stay with their activity when rows are reordered: a card
    moves with the row whose "start from" and "idea" match. Saving an example
    makes it the educator's own plan.

    Returns:
        The saved plan and a status message.

    Raises:
        PlanError: Too many activities or a field too long.
    """
    plan = store.get(plan_id)
    cleaned = _clean_rows(rows)
    if len(cleaned) > MAX_ACTIVITIES:
        raise PlanError(f"A plan can have at most {MAX_ACTIVITIES} activities.")
    cards = {(a.start_from, a.idea): a.card for a in plan.activities if a.card}
    activities = tuple(
        PlannedActivity(
            start_from=r[0], idea=r[1], why=r[2], big_question=r[3], card=cards.get((r[0], r[1]))
        )
        for r in cleaned
    )
    saved = store.save(
        replace(plan, interest=interest, goal=goal, activities=activities, is_example=False)
    )
    return saved, f"Saved {len(activities)} activities."


def new_plan(store: PlanStore) -> LearningPlan:
    """Create and save an empty plan."""
    return store.save(LearningPlan(plan_id=new_plan_id("plan")))


def copy_plan(store: PlanStore, plan_id: str) -> LearningPlan:
    """Save a copy of a plan as the educator's own (not an example)."""
    plan = store.get(plan_id)
    return store.save(
        replace(
            plan,
            plan_id=new_plan_id(plan.interest),
            interest=f"{plan.interest} (copy)".strip(),
            is_example=False,
        )
    )


def card_fields(plan: LearningPlan, index: int) -> dict[str, Any]:
    """The card of activity ``index`` as form values (blank if none yet)."""
    card = plan.activities[index].card or ActivityCard()

    def pad(values: tuple[str, ...], n: int) -> list[str]:
        return list(values) + [""] * (n - len(values))

    return {
        "explanation": pad(card.explanation, 3),
        "question": card.question,
        "choices": pad(card.choices, 3),
        "answer": card.answer,
        "hints": pad(card.hints, 2),
        "right_text": card.right_text,
        "hints_run_out_text": card.hints_run_out_text,
        "picture_idea": card.picture_idea,
        "picture_description": card.picture_description,
        "how_youll_know": card.how_youll_know,
        "sources": card.sources,
        "avoid": card.avoid,
    }


def save_card(
    store: PlanStore, plan_id: str, index: int, values: dict[str, Any]
) -> tuple[LearningPlan, list[str]]:
    """Save the card for activity ``index`` and return what's still missing."""
    plan = store.get(plan_id)
    if not 0 <= index < len(plan.activities):
        raise PlanError("Pick an activity first.")
    card = ActivityCard(
        explanation=tuple(v.strip() for v in values["explanation"] if v and v.strip()),
        question=values["question"].strip(),
        choices=tuple(v.strip() for v in values["choices"] if v and v.strip()),
        answer=(values["answer"] or "").strip(),
        hints=tuple(v.strip() for v in values["hints"] if v and v.strip()),
        right_text=values["right_text"].strip(),
        hints_run_out_text=values["hints_run_out_text"].strip(),
        picture_idea=values["picture_idea"].strip(),
        picture_description=values["picture_description"].strip(),
        how_youll_know=values["how_youll_know"].strip(),
        sources=values["sources"].strip(),
        avoid=values["avoid"].strip(),
    )
    activities = list(plan.activities)
    activities[index] = replace(activities[index], card=card)
    saved = store.save(replace(plan, activities=tuple(activities), is_example=False))
    return saved, drafting_notes(card)


def notes_text(notes: list[str]) -> str:
    """Render drafting notes for the card form."""
    if not notes:
        return "✅ This card has everything it needs. The admin can package it."
    return "**Still missing:**\n" + "\n".join(f"- {n}" for n in notes)


IMPORT_TIPS = """\
Paste your notes in any shape, or upload a file (.txt, .md, .docx, .pdf). Claude \
organizes them into a plan, and you check it before anything is saved.

**What helps most** (any of these; none is required):
- the interest you're starting from, like *cars* or *sharks*;
- what you'd like them to understand by the end;
- what they already know;
- ideas you already have: activities, questions, examples, things to compare;
- a book or website you trust for the facts.

Messy is fine: bullet points, half sentences, a list of ideas. Even one line works; \
Claude suggests a starting plan and asks you a few questions. **Don't include the \
student's name or anything personal.**

*Example:* "loves sharks. want: fast vs slow, then speed = distance and time. knows \
counting to 100. maybe compare shark vs car? kids' ocean encyclopedia."
"""

CONSENT = (
    "Send this to Claude (Anthropic) to structure it. "
    "I haven't included the student's name or personal details."
)


def import_preview(
    drafter: PlanDrafter | None, text: str, upload_path: str | None, agreed: bool
) -> tuple[LearningPlan, list[str]]:
    """Ask the drafter for a plan from rough notes; nothing is saved.

    Args:
        drafter: Claude behind an adapter, or ``None`` if not set up.
        text: Pasted notes.
        upload_path: Gradio's temp path for an uploaded file, deleted after reading.
        agreed: Whether the educator ticked the consent box.

    Returns:
        The proposed (unsaved) plan and Claude's notes.

    Raises:
        PlanError: Not agreed, nothing to import, a bad file, or a bad proposal.
        DrafterUnavailable: Claude isn't set up or didn't answer.
    """
    data = name = None
    if upload_path:
        path = Path(upload_path)
        name, data = path.name, path.read_bytes()
        os.remove(path)  # don't keep uploads
    if drafter is None:
        raise DrafterUnavailable("Claude isn't set up on this server yet.")
    if not agreed:
        raise PlanError("Tick the box to send your notes to Claude.")
    result = drafter.draft(extract_source(text, name, data))
    return proposal_to_plan(result.proposal), proposal_notes(result)


def preview_text(plan: LearningPlan, notes: list[str]) -> str:
    """Show a proposed plan for the educator to check before saving."""
    lines = [f"### {plan.interest or 'Untitled plan'}", f"**Goal:** {plan.goal or '—'}", ""]
    lines += [
        "| # | Start from | Idea to learn | Why | Big question | Card |",
        "|---|---|---|---|---|---|",
    ]
    for i, a in enumerate(plan.activities, 1):
        card = "drafted" if a.card else "—"
        lines.append(f"| {i} | {a.start_from} | {a.idea} | {a.why} | {a.big_question} | {card} |")
    questions = [n.removeprefix("Question:").strip() for n in notes if n.startswith("Question:")]
    others = [n for n in notes if not n.startswith("Question:")]
    if others:
        lines += ["", "**Claude's notes:**"] + [f"- {n}" for n in others]
    if questions:  # gaps Claude couldn't fill; answering them makes the next import better
        lines += ["", "**Claude's questions for you:**"] + [f"- {q}" for q in questions]
    lines += ["", "Nothing is saved yet. Save it to edit it below, or discard it."]
    return "\n".join(lines)


def sessions_text(catalog: PackageLessonCatalog) -> str:
    """What the Sessions tab lists: approved activities, then drafts to preview."""
    approved = catalog.list_approved()
    drafts = catalog.list_drafts()
    lines = ["### Approved activities"]
    lines += [f"- {a.title}" for a in approved] or ["No approved activities yet."]
    lines += ["", "### Drafts (preview only, coming soon)"]
    lines += [f"- {d.title}" for d in drafts] or ["No drafts."]
    return "\n".join(lines)


# --- Gradio wiring -----------------------------------------------------------


def build_educator_view(
    store: PlanStore, catalog: PackageLessonCatalog, drafter: PlanDrafter | None = None
) -> gr.Blocks:
    """Build the educator view's three tabs."""
    store.seed_if_empty()  # first run: copy in the example plans

    # Layout first; event wiring below.
    with gr.Blocks(title="Lerni: educator view", analytics_enabled=False) as blocks:
        gr.Markdown("## Educator view")
        with gr.Tabs():
            with gr.Tab("Guide"):
                gr.Markdown(guide_text())

            with gr.Tab("Sessions"):
                gr.Markdown(sessions_text(catalog))

            with gr.Tab("Learning plans"):
                gr.Markdown(NEVER_WRITE)
                with gr.Accordion("Import a rough plan with Claude", open=False):
                    if drafter is None:
                        gr.Markdown("Claude isn't set up on this server yet.")
                    gr.Markdown(IMPORT_TIPS)
                    rough = gr.Textbox(label="Your notes", lines=10)
                    upload = gr.File(
                        label="Or upload a file", file_types=[".txt", ".md", ".docx", ".pdf"],
                        type="filepath",
                    )
                    agree = gr.Checkbox(label=CONSENT)
                    import_btn = gr.Button("Structure with Claude", variant="primary")
                    preview = gr.Markdown()
                    with gr.Row():
                        keep_btn = gr.Button("Save as a new plan", visible=False)
                        drop_btn = gr.Button("Discard", visible=False)
                    proposal = gr.State(None)  # unsaved plan, held on the server per page
                with gr.Row():
                    plan_dd = gr.Dropdown(label="Plan", choices=plan_choices(store), scale=3)
                    new_btn = gr.Button("New plan", scale=1)
                    copy_btn = gr.Button("Copy", scale=1)
                    archive_btn = gr.Button("Archive", scale=1, variant="stop")
                interest = gr.Textbox(label="Interest", placeholder="e.g. Cars")
                goal = gr.Textbox(label="Goal", placeholder="What should they understand?")
                table = gr.Dataframe(
                    headers=COLUMNS,
                    column_count=len(COLUMNS),
                    row_count=1,
                    type="array",  # rows arrive as lists, not a pandas table
                    interactive=True,
                    wrap=True,
                    label="Activities, in teaching order (add or remove rows as needed)",
                )
                save_btn = gr.Button("Save plan", variant="primary")
                plan_status = gr.Markdown()

                gr.Markdown("### Activity card")
                act_dd = gr.Dropdown(label="Activity", choices=[], type="value")
                expl = [gr.Textbox(label=f"Explanation screen {i + 1}", lines=2) for i in range(3)]
                question = gr.Textbox(label="Question", lines=2)
                choices = [gr.Textbox(label=f"Choice {i + 1}") for i in range(3)]
                # options follow whatever is typed in the choice boxes
                answer = gr.Dropdown(label="Right answer", choices=[], allow_custom_value=True)
                hints = [gr.Textbox(label=f"Hint {i + 1}") for i in range(2)]
                right_text = gr.Textbox(label="If they get it right, say")
                out_text = gr.Textbox(label="If the hints run out, say")
                pic_idea = gr.Textbox(label="Picture idea")
                pic_desc = gr.Textbox(label="What the picture shows, in words")
                know = gr.Textbox(label="How you'll know they really get it")
                sources = gr.Textbox(label="Where the facts come from")
                avoid = gr.Textbox(label="Anything to avoid or be careful about")
                card_btn = gr.Button("Save card", variant="primary")
                card_notes = gr.Markdown()

        def on_import(text: str, path: str | None, agreed: bool) -> list[Any]:
            try:
                plan, notes = import_preview(drafter, text, path, agreed)
            except (PlanError, DrafterUnavailable) as exc:
                hide = gr.update(visible=False)
                return [None, f"⚠️ {exc}", hide, hide, None]
            show = gr.update(visible=True)
            return [plan, preview_text(plan, notes), show, show, None]  # None clears the upload box

        import_btn.click(
            on_import, [rough, upload, agree], [proposal, preview, keep_btn, drop_btn, upload],
            **PRIVATE,
        )

        def on_keep(plan: LearningPlan | None) -> list[Any]:
            hide = gr.update(visible=False)
            if plan is None:
                return [None, "", hide, hide, gr.update()]
            saved = store.save(plan)
            return [None, "✅ Saved. It's selected below for editing.", hide, hide,
                    gr.update(choices=plan_choices(store), value=saved.plan_id)]

        def on_drop() -> list[Any]:
            hide = gr.update(visible=False)
            return [None, "Discarded.", hide, hide]

        keep_btn.click(on_keep, proposal, [proposal, preview, keep_btn, drop_btn, plan_dd],
                       **PRIVATE)
        drop_btn.click(on_drop, None, [proposal, preview, keep_btn, drop_btn], **PRIVATE)

        # Order must match what show_card returns.
        card_outputs = [
            *expl,
            question,
            *choices,
            answer,
            *hints,
            right_text,
            out_text,
            pic_idea,
            pic_desc,
            know,
            sources,
            avoid,
            card_notes,
        ]

        def show_plan(plan_id: str | None) -> list[Any]:
            if not plan_id:
                return ["", "", [["", "", "", ""]], gr.update(choices=[], value=None), ""]
            plan = store.get(plan_id)
            return [
                plan.interest,
                plan.goal,
                plan_rows(plan) or [["", "", "", ""]],
                gr.update(choices=activity_choices(plan), value=None),
                "",
            ]

        plan_outputs = [interest, goal, table, act_dd, plan_status]
        plan_dd.change(show_plan, plan_dd, plan_outputs, **PRIVATE)  # picking a plan fills the form

        def on_new() -> Any:
            plan = new_plan(store)
            return gr.update(choices=plan_choices(store), value=plan.plan_id)

        def on_copy(plan_id: str | None) -> Any:
            if not plan_id:
                return gr.update()
            plan = copy_plan(store, plan_id)
            return gr.update(choices=plan_choices(store), value=plan.plan_id)

        def on_archive(plan_id: str | None) -> Any:
            if plan_id:
                store.archive(plan_id)
            return gr.update(choices=plan_choices(store), value=None)

        new_btn.click(on_new, None, plan_dd, **PRIVATE)
        copy_btn.click(on_copy, plan_dd, plan_dd, **PRIVATE)
        archive_btn.click(on_archive, plan_dd, plan_dd, **PRIVATE)

        def on_save(plan_id: str | None, i: str, g: str, rows: Any) -> list[Any]:
            if not plan_id:
                return [gr.update(), gr.update(), "Pick or create a plan first."]
            try:
                plan, message = save_plan(store, plan_id, i, g, rows)
            except PlanError as exc:
                return [gr.update(), gr.update(), f"⚠️ {exc}"]
            return [
                gr.update(choices=plan_choices(store), value=plan.plan_id),
                gr.update(choices=activity_choices(plan), value=None),
                f"✅ {message}",
            ]

        save_btn.click(
            on_save, [plan_dd, interest, goal, table], [plan_dd, act_dd, plan_status], **PRIVATE
        )

        def show_card(plan_id: str | None, index: int | None) -> list[Any]:
            if not plan_id or index is None:
                return [gr.update()] * len(card_outputs)
            plan = store.get(plan_id)
            f = card_fields(plan, int(index))
            card_choices = [c for c in f["choices"] if c]
            return [
                *f["explanation"],
                f["question"],
                *f["choices"],
                gr.update(choices=card_choices, value=f["answer"] or None),
                *f["hints"],
                f["right_text"],
                f["hints_run_out_text"],
                f["picture_idea"],
                f["picture_description"],
                f["how_youll_know"],
                f["sources"],
                f["avoid"],
                notes_text(drafting_notes(plan.activities[int(index)].card)),
            ]

        act_dd.change(show_card, [plan_dd, act_dd], card_outputs, **PRIVATE)

        def refresh_answer(c1: str, c2: str, c3: str, current: str | None) -> Any:
            options = [c for c in (c1, c2, c3) if c and c.strip()]
            return gr.update(choices=options, value=current if current in options else None)

        # refresh the answer options when a choice box loses focus
        for box in choices:
            box.blur(refresh_answer, [*choices, answer], answer, **PRIVATE)

        def on_save_card(plan_id: str | None, index: int | None, *vals: str) -> list[Any]:
            if not plan_id or index is None:
                return [gr.update(), "Pick an activity first."]
            # positions match card_inputs below
            values = {
                "explanation": vals[0:3],
                "question": vals[3],
                "choices": vals[4:7],
                "answer": vals[7],
                "hints": vals[8:10],
                "right_text": vals[10],
                "hints_run_out_text": vals[11],
                "picture_idea": vals[12],
                "picture_description": vals[13],
                "how_youll_know": vals[14],
                "sources": vals[15],
                "avoid": vals[16],
            }
            try:
                plan, notes = save_card(store, plan_id, int(index), values)
            except PlanError as exc:
                return [gr.update(), f"⚠️ {exc}"]
            return [gr.update(choices=activity_choices(plan), value=int(index)), notes_text(notes)]

        card_inputs = [
            plan_dd,
            act_dd,
            *expl,
            question,
            *choices,
            answer,
            *hints,
            right_text,
            out_text,
            pic_idea,
            pic_desc,
            know,
            sources,
            avoid,
        ]
        card_btn.click(on_save_card, card_inputs, [act_dd, card_notes], **PRIVATE)

    return blocks
