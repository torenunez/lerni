"""A MentalMap as a list: add, open, rename, and remove goals and interests, or put them back.

The handlers are plain functions over the server-resolved viewer, so their role
checks can be tested without a browser; :func:`mental_list` draws the list with
``gr.render`` on My MentalMap and MentalMaps. The render itself gets no request,
so whose map it shows comes from a server-side State that only checked handlers set.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import gradio as gr

from lerni.student.interests import (
    MAX_NAME,
    MAX_NOTES,
    STRENGTH_LABELS,
    MapStore,
    add_goal,
    add_interest,
    details,
    put_back,
    remove,
    rename,
    set_notes,
    strength,
)
from lerni.student.signin import SignIn
from lerni.student.students import StudentStore
from lerni.student.web.accounts import PRIVATE, cleared
from lerni.student.web.maps import _act


def add_item(maps, students, viewer, requested, kind: str, name: str, notes: str) -> str:
    """Add a goal or an interest to a MentalMap this viewer may edit."""
    if kind == "Goal":
        return _act(
            maps, students, viewer, requested, lambda m: add_goal(m, name, notes), "Goal added."
        )
    return _act(
        maps, students, viewer, requested, lambda m: add_interest(m, name), "Interest added."
    )


def remove_item(maps, students, viewer, requested, entry_id: str) -> str:
    """Remove an item; it waits in Removed, and Lerni steers away from a removed interest."""
    return _act(
        maps,
        students,
        viewer,
        requested,
        lambda m: remove(m, entry_id or ""),
        "Removed. Put it back from Removed any time.",
    )


def put_back_item(maps, students, viewer, requested, name: str) -> str:
    """Put a removed item back."""
    return _act(maps, students, viewer, requested, lambda m: put_back(m, name or ""), "Put back.")


def rename_item(maps, students, viewer, requested, entry_id: str, name: str) -> str:
    """Rename an item."""
    return _act(
        maps, students, viewer, requested, lambda m: rename(m, entry_id or "", name), "Renamed."
    )


def save_notes(maps, students, viewer, requested, entry_id: str, notes: str) -> str:
    """Save a goal's notes for Lerni."""
    return _act(
        maps,
        students,
        viewer,
        requested,
        lambda m: set_notes(m, entry_id or "", notes),
        "Notes saved.",
    )


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' * (n != 1)}"


def mental_list(
    signin: SignIn,
    students: StudentStore,
    maps: MapStore,
    owner: gr.State,
    requested: Any,
    version: gr.State,
) -> None:
    """The add form, then 🎯 Goals and 💚 Interests as rows to open, rename, or remove.

    Args:
        owner: Whose map to draw, set only by checked handlers ("" for none yet).
        requested: What edits ask :func:`map_owner` for: a ``gr.State(None)`` for
            My MentalMap, or the student dropdown on MentalMaps.
        version: Bumped by every change, so the list redraws.
    """
    opened = gr.State(None)  # the open item's id
    with gr.Row(elem_classes="lerni-add"):
        kind = gr.Radio(["Goal", "Interest"], value="Goal", show_label=False, scale=0)
        name = gr.Textbox(show_label=False, placeholder="Name", max_length=MAX_NAME, scale=2)
        notes = gr.Textbox(
            show_label=False, placeholder="Notes for Lerni (goals)", max_length=MAX_NOTES, scale=2
        )
        add = gr.Button("Add", variant="primary", scale=0, min_width=70)
    status = gr.Markdown()

    def run(action: Any, req: Any, *args: Any, request: gr.Request) -> str:
        # every edit re-checks who's asking and whose map it is
        return action(maps, students, signin.viewer(request.username), req, *args)

    def done(message: str, v: int) -> list[Any]:
        return [message, v + message.startswith("✅")]

    def on_add(k: str, n: str, t: str, req: Any, v: int, request: gr.Request) -> list[Any]:
        message = run(add_item, req, k, n, t, request=request)
        return [message, *cleared(2, message.startswith("✅")), done(message, v)[1]]

    add.click(
        on_add, [kind, name, notes, requested, version], [status, name, notes, version], **PRIVATE
    )

    def wire(e_id: str, row: Any, trash: Any, edits: tuple[Any, ...] = ()) -> None:
        """One item's events; edits are (name box, Rename, notes box, Save) when it's open."""

        def on_remove(req: Any, v: int, request: gr.Request) -> list[Any]:
            return done(run(remove_item, req, e_id, request=request), v)

        trash.click(on_remove, [requested, version], [status, version], **PRIVATE)
        row.click(lambda o: None if o == e_id else e_id, opened, opened, **PRIVATE)
        if not edits:
            return
        name_box, rename_btn, notes_box, notes_btn = edits

        def on_rename(new: str, req: Any, v: int, request: gr.Request) -> list[Any]:
            return done(run(rename_item, req, e_id, new, request=request), v)

        rename_btn.click(on_rename, [name_box, requested, version], [status, version], **PRIVATE)
        if notes_btn is not None:

            def on_notes(text: str, req: Any, v: int, request: gr.Request) -> list[Any]:
                return done(run(save_notes, req, e_id, text, request=request), v)

            notes_btn.click(on_notes, [notes_box, requested, version], [status, version], **PRIVATE)

    def back_button(gone: str) -> None:
        """A removed item's row with Put back."""
        with gr.Row(elem_classes="lerni-item"):
            gr.Markdown(gone, key=f"gone-{gone}")
            back = gr.Button("Put back", size="sm", scale=0, min_width=90, key=f"back-{gone}")

        def on_back(req: Any, v: int, request: gr.Request) -> list[Any]:
            return done(run(put_back_item, req, gone, request=request), v)

        back.click(on_back, [requested, version], [status, version], **PRIVATE)

    @gr.render(inputs=[owner, version, opened])
    def draw(who: str, _v: int, open_id: str | None) -> None:
        if not who:
            gr.Markdown("Pick a student.")
            return
        m, today = maps.get(who), date.today()
        for title, kind_ in (("🎯 Goals", "goal"), ("💚 Interests", "interest")):
            items = [e for e in m.entries if e.kind == kind_]
            gr.Markdown(f"**{title}**" + ("" if items else ": none yet"), key=f"h-{kind_}")
            for e in items:
                with gr.Row(elem_classes="lerni-item"):
                    label = f"{e.name} · {STRENGTH_LABELS[strength(e, today)]}"
                    row = gr.Button(label, scale=1, key=f"open-{e.id}")
                    trash = gr.Button("🗑", scale=0, min_width=48, key=f"rm-{e.id}")
                if open_id != e.id:
                    wire(e.id, row, trash)
                    continue
                d = details(m, e.id, today)  # the open item: its facts, then edits and links
                facts = [
                    STRENGTH_LABELS[d.strength],
                    f"came up on {_plural(d.days, 'day')}"
                    + (f", last on {d.last}" if d.last else ""),
                ]
                if e.kind == "goal":
                    facts.append(f"explained on {_plural(d.explained, 'day')} (Lerni's guess)")
                    facts += ["Lerni is giving it a rest"] if d.resting else []
                with gr.Column(elem_classes="lerni-detail", key=f"d-{e.id}"):
                    gr.Markdown(" · ".join(facts), key=f"facts-{e.id}")
                    notes_box = notes_btn = None
                    if e.kind == "goal":
                        notes_box = gr.Textbox(
                            e.notes,
                            label="Notes for Lerni",
                            max_length=MAX_NOTES,
                            key=f"notes-{e.id}",
                        )
                        notes_btn = gr.Button("Save notes", size="sm", key=f"save-{e.id}")
                    name_box = gr.Textbox(
                        e.name, label="Name", max_length=MAX_NAME, key=f"name-{e.id}"
                    )
                    rename_btn = gr.Button("Rename", size="sm", key=f"ren-{e.id}")
                    for heading, ends in (("Bridges", d.bridges), ("Related", d.related)):
                        if ends:
                            gr.Markdown(f"**{heading}**", key=f"{heading}-{e.id}")
                        for other_id, other in ends:  # a tap opens the other end
                            jump = gr.Button(
                                f"→ {other}", size="sm", key=f"j-{e.id}-{heading}-{other_id}"
                            )
                            jump.click(lambda i=other_id: i, None, opened, **PRIVATE)
                wire(e.id, row, trash, (name_box, rename_btn, notes_box, notes_btn))
        if m.removed:
            with gr.Accordion(f"Removed ({len(m.removed)})", open=False, key="removed"):
                for gone in m.removed:
                    back_button(gone)
