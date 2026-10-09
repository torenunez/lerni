"""My map (an independent student's own) and Maps (an educator's view of supervised students).

Handlers are plain functions over the server-resolved viewer; the username a
page asks for is always checked against it. The picture is inline SVG text.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import gradio as gr

from lerni.student.interests import InterestMap, MapError, MapStore, add_goal, remove, rename
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import AccountError, Kind, StudentStore
from lerni.student.web.accounts import (
    PRIVATE,
    NotAllowed,
    cleared,
    require,
    require_educator,
)
from lerni.student.web.mapdraw import map_svg, map_words

REFRESH_SECONDS = 30  # Maps redraws while open, so the educator sees it grow


def map_owner(students: StudentStore, viewer: Viewer | None, requested: str | None) -> str:
    """Whose map this viewer may see: their own (``requested`` None) or a supervised student's.

    Raises:
        NotAllowed: Anyone else's map.
    """
    if requested is None:
        return require(viewer, Role.INDEPENDENT).username  # My map
    require_educator(viewer)
    try:
        student = students.get(requested)
    except AccountError:
        raise NotAllowed("Pick a student from the list.") from None
    if student.kind is not Kind.SUPERVISED or student.archived:
        raise NotAllowed("Pick a student from the list.")  # never an independent student's map
    return student.username


def supervised_choices(students: StudentStore, viewer: Viewer | None) -> list[tuple[str, str]]:
    """The supervised students an educator can pick on Maps; nothing for anyone else."""
    if viewer is None or not viewer.educator:
        return []
    return [(s.display_name, s.username) for s in students.list_students()
            if s.kind is Kind.SUPERVISED and not s.archived]


def entry_choices(m: InterestMap) -> list[tuple[str, str]]:
    """Every entry, for Rename and Remove."""
    return [(f"{e.name} ({e.kind})", e.id) for e in m.entries]


def entry_update(m: InterestMap, current: str | None) -> Any:
    """The Entry dropdown after a redraw, keeping the pick if it's still on the map."""
    choices = entry_choices(m)
    keep = current if current in {entry_id for _, entry_id in choices} else None
    return gr.update(choices=choices, value=keep)


def _act(maps: MapStore, students: StudentStore, viewer: Viewer | None, requested: str | None,
         change: Any, done: str) -> str:
    try:
        owner = map_owner(students, viewer, requested)
        maps.change(owner, change)
    except (NotAllowed, MapError) as exc:
        return f"⚠️ {exc}"
    return f"✅ {done}"


def add_goal_to(maps, students, viewer, requested, name: str, notes: str) -> str:
    """Add a goal to a map this viewer may edit."""
    return _act(maps, students, viewer, requested, lambda m: add_goal(m, name, notes),
                "Goal added.")


def rename_on(maps, students, viewer, requested, entry_id: str, name: str) -> str:
    """Rename an entry on a map this viewer may edit."""
    return _act(maps, students, viewer, requested, lambda m: rename(m, entry_id or "", name),
                "Renamed.")


def remove_from(maps, students, viewer, requested, entry_id: str) -> str:
    """Remove an entry for good from a map this viewer may edit."""
    return _act(maps, students, viewer, requested, lambda m: remove(m, entry_id or ""),
                "Removed; Lerni won't add it back.")


def map_tab(
    signin: SignIn, students: StudentStore, maps: MapStore, mine: bool
) -> tuple[gr.Tab, gr.Dropdown | None, gr.HTML, gr.Markdown, gr.Dropdown]:
    """My map (``mine``) or Maps; hidden until the page loads for an allowed viewer."""
    with gr.Tab("My map" if mine else "Maps", id="mymap" if mine else "maps",
                visible=False) as tab:
        who = None
        if not mine:
            gr.Markdown("Pick a student. Green: what they love. Coral: your goals. "
                        "Dashed: where Lerni bridged.")
            who = gr.Dropdown(label="Student", choices=[], value=None)  # filled on load
        picture = gr.HTML()
        words = gr.Markdown()
        with gr.Accordion("Add a goal", open=False):
            name = gr.Textbox(label="Goal", max_length=40)
            notes = gr.Textbox(label="Notes for Lerni (optional; say 'the student', not names)",
                               max_length=200)
            add = gr.Button("Add", variant="primary")
        with gr.Accordion("Rename or remove", open=False):
            entry = gr.Dropdown(label="Entry", choices=[], value=None)
            new_name = gr.Textbox(label="New name", max_length=40)
            with gr.Row():
                rename_btn = gr.Button("Rename")
                remove_btn = gr.Button("Remove", variant="stop")
        status = gr.Markdown()

        def requested_of(value: str | None) -> str | None:
            # My map asks for nobody else; Maps with no pick asks for "" (refused, never your own)
            return None if mine else (value or "")

        def show(
            requested: str | None, current: str | None, request: gr.Request
        ) -> list[Any]:
            viewer = signin.viewer(request.username)  # re-read on every request
            try:
                owner = map_owner(students, viewer, requested_of(requested))
            except NotAllowed:
                return ["", "", gr.update(choices=[], value=None)]
            m = maps.get(owner)
            return [map_svg(m, date.today()), map_words(m, date.today()), entry_update(m, current)]

        def on_add(n: str, t: str, requested: str | None, request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            message = add_goal_to(maps, students, viewer, requested_of(requested), n, t)
            return [message, *cleared(2, message.startswith("✅")), *show(requested, None, request)]

        def on_rename(e: str, n: str, requested: str | None, request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            message = rename_on(maps, students, viewer, requested_of(requested), e, n)
            return [message, *cleared(1, message.startswith("✅")), *show(requested, None, request)]

        def on_remove(e: str, requested: str | None, request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            message = remove_from(maps, students, viewer, requested_of(requested), e)
            return [message, *show(requested, None, request)]

        shown = [picture, words, entry]  # order matches show()
        # Gradio needs a component for "which student"; My map passes a hidden empty one
        target = who if who is not None else gr.State(None)
        add.click(on_add, [name, notes, target], [status, name, notes, *shown], **PRIVATE)
        rename_btn.click(on_rename, [entry, new_name, target], [status, new_name, *shown],
                         **PRIVATE)
        remove_btn.click(on_remove, [entry, target], [status, *shown], **PRIVATE)
        tab.select(show, [target, entry], shown, **PRIVATE)  # redraw on opening
        if who is not None:
            who.change(show, [who, entry], shown, **PRIVATE)
            # the redraw keeps the Rename/Remove pick
            gr.Timer(REFRESH_SECONDS).tick(show, [who, entry], shown, **PRIVATE)
    return tab, who, picture, words, entry
