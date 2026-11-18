"""Spelling: the educator's fold on the student's page, and a missed word marked for the race
card (v4.10; the student's own section moved into races in v4.11).

Handlers re-read the viewer on every request. A typed answer is shown only on screen and
never kept (rule 6).
"""

from __future__ import annotations

import html
from difflib import SequenceMatcher
from typing import Any

import gradio as gr

from lerni.student.signin import SignIn
from lerni.student.spelling import MISTAKES, SpellingDesk, SpellingUnavailable
from lerni.student.students import StudentStore
from lerni.student.web.accounts import PRIVATE, NotAllowed, require_educator
from lerni.student.web.maps import map_owner


def spelled_html(word: str, typed: str) -> str:
    """The right spelling, marking only the letters the typed one lacks (on screen only)."""
    match = SequenceMatcher(None, typed.strip().casefold(), word.casefold(), autojunk=False)
    kept = {j for _, b, size in match.get_matching_blocks() for j in range(b, b + size)}
    marks = "".join(
        html.escape(c) if i in kept else f"<mark>{html.escape(c)}</mark>"
        for i, c in enumerate(word)
    )  # "fosil": only fossil's second s
    return f'<span class="lerni-spell-word">{marks}</span>'


def _summary_md(s: dict[str, Any]) -> str:
    # the educator's lines: level and counts, the words missed most, and kinds of mistakes
    missed = " · ".join(f"{html.escape(w)} {n}" for w, n in s["missed"]) or "none yet"
    kinds = " · ".join(f"{MISTAKES.get(k, k)} {n}" for k, n in s["mistakes"]) or "none yet"
    return (
        f"Level {s['level']} · {len(s['practice'])} words in practice · "
        f"{s['learned']} learned\n\n**Missed most:** {missed}\n\n**Kinds of mistakes:** "
        f"{kinds}"
    )


def spelling_fold(
    signin: SignIn, students: StudentStore, desk: SpellingDesk, who: gr.Dropdown, tab: gr.Tab
) -> None:
    """The educator's Spelling fold on the student's page (inside its tab's layout)."""
    with gr.Accordion("Spelling", open=False):
        box = gr.Textbox(
            label="This week's class list, one word per line",
            lines=4,
            max_lines=12,
            max_length=1200,  # about 40 words
        )
        save = gr.Button("Save list", min_width=90)
        status = gr.Markdown()  # saved, skipped, or why not
        stats = gr.Markdown()  # level, missed most, kinds of mistakes
        words = gr.CheckboxGroup(label="Words in practice (tick to remove)", choices=[])
        remove = gr.Button("Remove ticked", min_width=90)
        # a paragraph's misspelled words (v4.14): added only on the educator's tap (rule 5)
        suggested = gr.CheckboxGroup(
            label="Suggested from writing (tick to add)", choices=[], visible=False
        )
        add = gr.Button("Add ticked", min_width=90, visible=False)

    def student(requested: str | None, request: gr.Request) -> str:
        # checked again on every request, as for every change on this page
        return map_owner(
            students, require_educator(signin.viewer(request.username)), requested or ""
        )

    def show(requested: str | None, request: gr.Request) -> list[Any]:
        try:
            s = desk.summary(student(requested, request))
        except NotAllowed:
            return ["", "", gr.update(choices=[], value=[])]  # no student picked: empty
        return ["\n".join(s["class"]), _summary_md(s), gr.update(choices=s["practice"], value=[])]

    def on_save(text: str, requested: str | None, request: gr.Request) -> list[Any]:
        try:
            n, carried, refused = desk.set_class_list(student(requested, request), text)
        except (NotAllowed, SpellingUnavailable) as exc:  # the typed list stays to try again
            return [gr.update(), f"⚠️ {exc}", gr.update(), gr.update()]
        line = f"✅ Saved {n} words." + (
            f" {carried} still-missed words carried over." if carried else ""
        )
        if refused:  # name a few, so the educator can fix them
            line += " Skipped (one word per line, letters only): " + ", ".join(refused[:5])
        box_text, summary, practice = show(requested, request)  # the list as now saved
        return [box_text, line, summary, practice]

    def on_remove(picked: list[str], requested: str | None, request: gr.Request) -> list[Any]:
        if not picked:
            return [gr.update(), "⚠️ Tick one first.", gr.update(), gr.update()]
        try:
            gone = desk.remove(student(requested, request), picked)  # for good
        except (NotAllowed, SpellingUnavailable) as exc:
            return [gr.update(), f"⚠️ {exc}", gr.update(), gr.update()]
        box_text, summary, practice = show(requested, request)
        return [box_text, f"Removed {gone}.", summary, practice]

    def show_suggested(requested: str | None, request: gr.Request) -> list[Any]:
        # shown only when there are some
        try:
            words = desk.summary(student(requested, request))["suggested"]
        except NotAllowed:
            words = []
        return [gr.update(choices=words, value=[], visible=bool(words)),
                gr.update(visible=bool(words))]

    def on_add(picked: list[str], requested: str | None, request: gr.Request) -> list[Any]:
        if not picked:
            return [gr.update(), gr.update(), "⚠️ Tick one first.", gr.update(), gr.update()]
        try:
            n = desk.add_suggested(student(requested, request), picked)
        except (NotAllowed, SpellingUnavailable) as exc:
            return [gr.update(), gr.update(), f"⚠️ {exc}", gr.update(), gr.update()]
        _, summary, practice = show(requested, request)  # the words now in practice
        return [*show_suggested(requested, request), f"✅ Added {n}.", summary, practice]

    out = [box, stats, words]
    for event in (who.change, tab.select):  # the suggestions, beside the words
        event(show_suggested, who, [suggested, add], **PRIVATE)
    add.click(on_add, [suggested, who], [suggested, add, status, stats, words], **PRIVATE)
    who.change(show, who, out, **PRIVATE)  # the student picked: their words
    tab.select(show, who, out, **PRIVATE)  # and fresh counts each time the page opens
    save.click(on_save, [box, who], [box, status, stats, words], **PRIVATE)
    remove.click(on_remove, [words, who], [box, status, stats, words], **PRIVATE)
