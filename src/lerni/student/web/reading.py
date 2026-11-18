"""Reading and writing: the educator's read-only fold on the student's page (v4.13): the
reading level, how each kind of question went, how often open answers used describing words,
and, from v4.14, the paragraphs' checklists.

Numbers only: what a student said or typed is never shown or kept (rule 6).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import gradio as gr

from lerni.student.reading import ReadingDesk, summary, summary_lines
from lerni.student.results import ResultsLog
from lerni.student.signin import SignIn
from lerni.student.students import StudentStore
from lerni.student.web.accounts import PRIVATE, NotAllowed, require_educator
from lerni.student.web.maps import map_owner
from lerni.student.writing import summary as writing_summary
from lerni.student.writing import summary_lines as writing_lines


def reading_fold(
    signin: SignIn,
    students: StudentStore,
    desk: ReadingDesk,
    results: ResultsLog | None,
    who: gr.Dropdown,
    tab: gr.Tab,
    writing: Any = None,
) -> None:
    """The educator's Reading and writing fold on the student's page (inside its tab's
    layout); ``writing`` is the WritingDesk, when writing races are on."""
    with gr.Accordion("Reading and writing", open=False):
        lines = gr.Markdown()  # the level and last week's counts

    def show(requested: str | None, request: gr.Request) -> str:
        try:  # checked again on every request, as for every part of this page
            username = map_owner(
                students, require_educator(signin.viewer(request.username)), requested or ""
            )
        except NotAllowed:
            return ""  # no student picked: empty
        rows = results.read(username) if results is not None else []
        out = summary_lines(summary(desk.store, rows, username, date.today()))
        if writing is not None:  # the paragraphs' checklists (v4.14), numbers only
            out += ["", *writing_lines(writing_summary(writing.store, username, date.today()))]
        return "\n".join(out)

    who.change(show, who, lines, **PRIVATE)  # the student picked: their numbers
    tab.select(show, who, lines, **PRIVATE)  # fresh each time the page opens
