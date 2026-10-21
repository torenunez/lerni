"""My MentalMap (an independent student's own), plus checks MentalMaps shares.

My MentalMap has the picture, the list (``mentallist.py``), and Upload notes.
Handlers are plain functions over the server-resolved viewer; the username a
page asks for is always checked against it. The picture is inline SVG text.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import gradio as gr

from lerni.student.feedback import FeedbackError, FeedbackStore
from lerni.student.interests import MapError, MapStore
from lerni.student.results import ResultsLog
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import AccountError, Kind, StudentStore
from lerni.student.upload import (
    Proposal,
    Uploader,
    UploadError,
    UploaderUnavailable,
    apply_proposals,
    extract_upload,
    parse_proposals,
    upload_system,
)
from lerni.student.web.accounts import (
    PRIVATE,
    NotAllowed,
    cleared,
    require,
    require_educator,
)
from lerni.student.web.mapdraw import map_svg, owner_key

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


def _act(maps: MapStore, students: StudentStore, viewer: Viewer | None, requested: str | None,
         change: Any, done: str, expected: str | None = None) -> str:
    try:
        owner = map_owner(students, viewer, requested)
        if expected is not None and owner != expected:  # drawn for another account
            raise NotAllowed("This page is for another account; reload it.")
        maps.change(owner, change, by=f"person:{viewer.username}" if viewer else "person")
    except (NotAllowed, MapError) as exc:
        return f"⚠️ {exc}"
    return f"✅ {done}"


def _read_and_delete(upload_path: str | None) -> tuple[str | None, bytes | None]:
    """The uploaded file's name and bytes; the file is deleted at once, whatever happens next."""
    if not upload_path:
        return None, None
    path = Path(upload_path)
    try:
        return path.name, path.read_bytes()
    finally:
        os.remove(path)  # don't keep uploads


def propose_for(
    uploader: Uploader | None, maps: MapStore, students: StudentStore, viewer: Viewer | None,
    requested: str | None, text: str, upload_path: str | None,
) -> tuple[list[Proposal], list[str], str]:
    """Ask Claude for interests and goals from notes, for a map this viewer may edit.

    Returns:
        The proposals to tick, Claude's notes, and a status line. Nothing is saved.
    """
    name, data = _read_and_delete(upload_path)
    try:
        owner = map_owner(students, viewer, requested)
        if uploader is None:
            raise UploaderUnavailable("Claude isn't set up on this server yet.")
        source = extract_upload(text, name, data)
        own = requested is None  # My map: their own notes
        proposals, notes = parse_proposals(uploader.propose(upload_system(own), source))
    except (NotAllowed, UploadError, UploaderUnavailable) as exc:
        return [], [], f"⚠️ {exc}"
    if not proposals:
        return [], notes, "⚠️ Claude didn't find anything to add. Try more detail."
    present = {e.name.casefold() for e in maps.get(owner).entries}
    fresh = [p for p in proposals if p.name.casefold() not in present]  # already there: skip
    return fresh, notes, "Tick what to add, then press Add ticked."


def add_proposals(
    maps: MapStore, students: StudentStore, viewer: Viewer | None, requested: str | None,
    proposals: list[Proposal], picked: list[str], proposed_for: str | None = None,
) -> str:
    """Add the ticked proposals to a map this viewer may edit, if they were made for it."""
    chosen = [p for p in proposals if p.label in set(picked or [])]
    if not chosen:
        return "⚠️ Tick at least one first."
    try:
        owner = map_owner(students, viewer, requested)
    except NotAllowed as exc:
        return f"⚠️ {exc}"
    if proposed_for is not None and owner != proposed_for:
        return "⚠️ Those ideas were for another map. Ask Claude again for this one."
    added, skipped = maps.change(owner, lambda m: apply_proposals(m, chosen), by="upload")
    message = f"✅ Added {added}."
    return message + (" Skipped: " + "; ".join(skipped) if skipped else "")


def save_feedback(
    store: FeedbackStore, students: StudentStore, viewer: Viewer | None,
    requested: str | None, text: str, summary: str,
) -> str:
    """Save an educator's feedback, about a supervised student's map if one is picked."""
    try:
        v = require_educator(viewer)
        about = map_owner(students, v, requested) if requested else None
        store.add(v.username, about, text, "" if summary.startswith("⚠️") else summary)
    except (NotAllowed, FeedbackError) as exc:
        return f"⚠️ {exc}"
    return "✅ Saved for the admin. Nothing changes until they make it by hand."


def map_tab(
    signin: SignIn,
    students: StudentStore,
    maps: MapStore,
    uploader: Uploader | None = None,
    results: ResultsLog | None = None,
) -> tuple[gr.Tab, gr.HTML, gr.State, gr.State]:
    """My MentalMap; hidden until the page loads for an independent student.

    ``results`` are the race results, for each goal's Practice line.

    Returns:
        The tab, its picture, whose map the list shows, and the list's version.
    """
    from lerni.student.web.mentallist import bump, mental_list  # it uses this module's checks

    with gr.Tab("My MentalMap", id="mymap", visible=False) as tab:
        picture = gr.HTML(elem_id="lerni-map-mine", elem_classes="lerni-map")
        owner, version = gr.State(""), gr.State(0)  # set on load, by a checked handler
        mental_list(signin, students, maps, owner, gr.State(None), version, "lerni-pick-mine",
                    results=results)
        with gr.Accordion("Upload notes", open=False):
            pasted = gr.Textbox(label="Paste notes (any shape)", lines=4, max_length=50_000)
            upload = gr.File(label="Or a file (.txt, .md, .docx, .pdf)", type="filepath",
                             file_types=[".txt", ".md", ".docx", ".pdf"],
                             height=90)  # short on a phone, so the ideas stay in view
            propose = gr.Button("Ask Claude for ideas")
            ideas_notes = gr.Markdown()
            ideas = gr.CheckboxGroup(label="Tick what to add", choices=[])
            add_ideas = gr.Button("Add ticked", variant="primary")
            held = gr.State({})  # the ideas shown and whose map they're for, kept on the server
        status = gr.Markdown()

        def show(v: int, request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)  # re-read on every request
            try:
                who = map_owner(students, viewer, None)
            except NotAllowed:
                return ["", "", v]
            return [map_svg(maps.get(who), date.today(), owner_key(who)), who, bump()]

        def on_propose(t: str, path: str | None, request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            found, notes, message = propose_for(uploader, maps, students, viewer, None, t, path)
            shown_notes = "\n".join(f"- {n}" for n in notes)
            labels = [p.label for p in found]
            try:  # remember whose map the ideas are for
                who = map_owner(students, viewer, None)
            except NotAllowed:
                who = None
            # the file is gone from the server either way; clear the box and the picker
            return [message, shown_notes, gr.update(choices=labels, value=[]),
                    {"owner": who, "ideas": found}, *cleared(1, bool(labels)), None]

        def on_add_ideas(picked: list[str], found: Any, v: int,
                         request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            held_ideas = found.get("ideas", []) if isinstance(found, dict) else []
            message = add_proposals(maps, students, viewer, None, held_ideas, picked,
                                    proposed_for=found.get("owner") if held_ideas else None)
            done = message.startswith("✅")
            box = gr.update(choices=[], value=[]) if done else gr.update()
            return [message, box, {} if done else found, *show(v, request)]

        def picture_now(request: gr.Request) -> str:
            try:
                who = map_owner(students, signin.viewer(request.username), None)
            except NotAllowed:
                return ""
            return map_svg(maps.get(who), date.today(), owner_key(who))

        tab.select(show, version, [picture, owner, version], **PRIVATE)  # redraw on opening
        version.change(picture_now, None, picture, **PRIVATE)  # a list edit redraws it
        propose.click(on_propose, [pasted, upload],
                      [status, ideas_notes, ideas, held, pasted, upload], **PRIVATE)
        add_ideas.click(on_add_ideas, [ideas, held, version],
                        [status, ideas, held, picture, owner, version], **PRIVATE)
    return tab, picture, owner, version
