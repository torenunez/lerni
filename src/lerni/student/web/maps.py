"""My map (an independent student's own) and Maps (an educator's view of supervised students).

Both have the picture, the list, Add goal, Rename, Remove, and Upload notes;
Maps also has Feedback for the admin. Handlers are plain functions over the
server-resolved viewer; the username a page asks for is always checked against
it. The picture is inline SVG text.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import gradio as gr

from lerni.student.conversation import ChatModel
from lerni.student.feedback import MAX_FEEDBACK, FeedbackError, FeedbackStore, summarize
from lerni.student.interests import InterestMap, MapError, MapStore, add_goal, remove, rename
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
    added, skipped = maps.change(owner, lambda m: apply_proposals(m, chosen))
    message = f"✅ Added {added}."
    return message + (" Skipped: " + "; ".join(skipped) if skipped else "")


def check_feedback(model: ChatModel | None, viewer: Viewer | None, text: str) -> str:
    """Claude's short summary of an educator's feedback, before it's saved."""
    try:
        require_educator(viewer)
    except NotAllowed as exc:
        return f"⚠️ {exc}"
    text = (text or "").strip()
    if not text or len(text) > MAX_FEEDBACK:
        return f"⚠️ Write 1–{MAX_FEEDBACK} characters first."
    if model is None:
        return "⚠️ Claude isn't set up on this server yet; you can still save it."
    try:
        return summarize(model, text)
    except Exception:  # noqa: BLE001 - never echo the text in errors
        return "⚠️ Claude didn't answer; you can still save it."


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
    mine: bool,
    uploader: Uploader | None = None,
    feedback: FeedbackStore | None = None,
    model: ChatModel | None = None,
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
        if not mine:
            with gr.Accordion("Feedback for the admin", open=False):
                fb_text = gr.Textbox(label="What should change? (the app, or this map)",
                                     lines=3, max_length=MAX_FEEDBACK)
                fb_check = gr.Button("Check what Claude understood")
                fb_summary = gr.Markdown()
                fb_save = gr.Button("Save feedback", variant="primary")
                fb_held = gr.State("")
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

        def on_propose(t: str, path: str | None, requested: str | None,
                       request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            found, notes, message = propose_for(uploader, maps, students, viewer,
                                                requested_of(requested), t, path)
            shown_notes = "\n".join(f"- {n}" for n in notes)
            labels = [p.label for p in found]
            try:  # remember whose map the ideas are for
                owner = map_owner(students, viewer, requested_of(requested))
            except NotAllowed:
                owner = None
            found = {"owner": owner, "ideas": found}
            # the file is gone from the server either way; clear the box and the picker
            return [message, shown_notes, gr.update(choices=labels, value=[]), found,
                    *cleared(1, bool(labels)), None]

        def on_add_ideas(picked: list[str], found: list[Any], requested: str | None,
                         current: str | None, request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            held_ideas = found.get("ideas", []) if isinstance(found, dict) else []
            message = add_proposals(maps, students, viewer, requested_of(requested), held_ideas,
                                    picked, proposed_for=found.get("owner") if held_ideas else None)
            done = message.startswith("✅")
            box = gr.update(choices=[], value=[]) if done else gr.update()
            return [message, box, {} if done else found, *show(requested, current, request)]

        shown = [picture, words, entry]  # order matches show()
        # Gradio needs a component for "which student"; My map passes a hidden empty one
        target = who if who is not None else gr.State(None)
        add.click(on_add, [name, notes, target], [status, name, notes, *shown], **PRIVATE)
        rename_btn.click(on_rename, [entry, new_name, target], [status, new_name, *shown],
                         **PRIVATE)
        remove_btn.click(on_remove, [entry, target], [status, *shown], **PRIVATE)
        tab.select(show, [target, entry], shown, **PRIVATE)  # redraw on opening
        propose.click(on_propose, [pasted, upload, target],
                      [status, ideas_notes, ideas, held, pasted, upload], **PRIVATE)
        add_ideas.click(on_add_ideas, [ideas, held, target, entry],
                        [status, ideas, held, *shown], **PRIVATE)
        if not mine:
            def on_check(t: str, request: gr.Request) -> list[Any]:
                summary = check_feedback(model, signin.viewer(request.username), t)
                return [summary, summary]

            def on_save(t: str, summary: str, requested: str | None,
                        request: gr.Request) -> list[Any]:
                viewer = signin.viewer(request.username)
                if feedback is None:  # never fall back to a default folder
                    return ["⚠️ Feedback isn't set up.", gr.update(), summary, gr.update()]
                message = save_feedback(feedback, students, viewer, requested or None, t, summary)
                done = message.startswith("✅")
                # a saved entry clears the box and the summary; an error keeps both
                return [message, *cleared(1, done), "" if done else summary,
                        "" if done else gr.update()]

            fb_check.click(on_check, fb_text, [fb_summary, fb_held], **PRIVATE)
            fb_save.click(on_save, [fb_text, fb_held, who],
                          [status, fb_text, fb_held, fb_summary], **PRIVATE)
        if who is not None:
            who.change(show, [who, entry], shown, **PRIVATE)
            # the redraw keeps the Rename/Remove pick
            gr.Timer(REFRESH_SECONDS).tick(show, [who, entry], shown, **PRIVATE)
    return tab, who, picture, words, entry
