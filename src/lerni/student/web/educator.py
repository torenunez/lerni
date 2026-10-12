"""MentalMaps for educators: a student's picture and list, then a chat with the educator agent.

:func:`educator_send` and :func:`educator_add` are plain functions over the
server-resolved viewer, so the role checks can be tested without a browser;
:func:`educator_tab` wires them to Gradio.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import gradio as gr

from lerni.student.conversation import MAX_MESSAGE, ConversationUnavailable
from lerni.student.educator_agent import EducatorChats, apply_educator_proposals
from lerni.student.feedback import FeedbackStore
from lerni.student.interests import MapStore
from lerni.student.signin import SignIn, Viewer
from lerni.student.students import StudentStore
from lerni.student.upload import UploadError, extract_upload
from lerni.student.web.accounts import PRIVATE, NotAllowed, require_educator
from lerni.student.web.mapdraw import map_svg
from lerni.student.web.maps import REFRESH_SECONDS, map_owner, save_feedback
from lerni.student.web.mentallist import bump, mental_list

NOTES_MARK = "\n\nAttached notes"  # where a message's attached notes begin
EMPTY = "Tell me what you'd like for this student, or attach notes with 📎."


def educator_send(
    chats: EducatorChats,
    students: StudentStore,
    viewer: Viewer | None,
    requested: str | None,
    text: str,
    filename: str | None = None,
    data: bytes | None = None,
) -> Iterator[str]:
    """Send an educator's message (and any file) about a supervised student; yield the reply.

    Raises:
        NotAllowed: Not an educator, or not a supervised student.
        UploadError: Nothing to send, too long, or a file that can't be read here.
    """
    v = require_educator(viewer)
    owner = map_owner(students, v, requested or "")
    notes = ""
    if data is not None:
        if (filename or "").lower().endswith(".pdf"):  # the chat sends text only, for now
            raise UploadError("PDFs can't be read here yet: paste its text, or save it as .docx.")
        notes = extract_upload("", filename, data).text
    text = (text or "").strip()
    if not text and not notes:
        raise UploadError("Write a message first.")
    if len(text) > MAX_MESSAGE:
        raise UploadError(f"That's too long; keep it under {MAX_MESSAGE} characters.")
    yield from chats.ask(v.username, owner, text or "Here are my notes.", notes)


def educator_add(
    chats: EducatorChats,
    maps: MapStore,
    feedback: FeedbackStore | None,
    students: StudentStore,
    viewer: Viewer | None,
    owner: str,
    ticked: list[str],
) -> str:
    """Apply the ticked proposals for ``owner``, the student they were made for."""
    try:
        v = require_educator(viewer)
        map_owner(students, v, owner)  # still a supervised student they may plan for
    except NotAllowed as exc:
        return f"⚠️ {exc}"
    chosen = [p for p in chats.proposals(v.username, owner) if p.label in set(ticked)]
    if not chosen:
        return "⚠️ Tick something to add first."
    on_map = [p for p in chosen if p.kind != "feedback"]
    done, skipped = 0, []
    if on_map:  # one change: nothing else edits the map in between
        done, skipped = maps.change(owner, lambda m: apply_educator_proposals(m, on_map))
    sent = 0
    for p in chosen:
        if p.kind == "feedback" and feedback is not None:
            sent += save_feedback(feedback, students, v, owner, p.notes, "").startswith("✅")
    chats.taken(v.username, owner, chosen)
    lines = [f"✅ Added {done} to the map."] if done else []
    lines += [f"📨 Sent {sent} to the admin."] if sent else []
    lines += [f"Skipped {s}" for s in skipped]
    return "\n\n".join(lines) or "⚠️ Nothing was added."


def chat_messages(chats: EducatorChats, educator: str, owner: str) -> list[dict[str, str]]:
    """The chat in the Chatbot's format; attached notes show as one short line."""
    shown = []
    for t in chats.history(educator, owner):
        text = t.text
        if t.role == "user" and NOTES_MARK in text:
            text = text.split(NOTES_MARK)[0] + "\n\n📎 notes attached"
        shown.append({"role": t.role, "content": text})
    return shown


def educator_tab(
    signin: SignIn,
    students: StudentStore,
    maps: MapStore,
    chats: EducatorChats | None,
    feedback: FeedbackStore | None,
) -> tuple[gr.Tab, gr.Dropdown]:
    """MentalMaps: pick a supervised student, see and edit their list, and plan it by talking."""
    with gr.Tab("MentalMaps", id="maps", visible=False) as tab:
        who = gr.Dropdown(label="Student", choices=[], value=None)  # filled on load
        # a strip on a phone; a tap opens the whole picture (nav.js)
        picture = gr.HTML(elem_classes="lerni-map-strip")
        list_owner, version = gr.State(""), gr.State(0)  # set only after map_owner's check
        # edits go to the student the list shows, never a newer dropdown pick
        mental_list(signin, students, maps, list_owner, list_owner, version, "Pick a student.")
        chat = gr.Chatbot(
            show_label=False,
            placeholder=EMPTY,
            buttons=[],
            feedback_options=None,
            elem_id="lerni-edu-chat",
            height=360,
        )
        ticks = gr.CheckboxGroup(label="Tick what to add", choices=[], visible=False)
        add = gr.Button("Add to MentalMap", variant="primary", visible=False)
        status = gr.Markdown()
        with gr.Row(elem_classes="lerni-type"):
            text = gr.Textbox(
                show_label=False,
                placeholder="Tell me about a goal…",
                lines=1,
                max_lines=4,
                max_length=MAX_MESSAGE,
                scale=4,
                container=False,
                interactive=chats is not None,
            )
            attach = gr.UploadButton(
                "📎",
                file_types=[".txt", ".md", ".docx"],  # the chat sends text only, for now
                type="filepath",
                scale=0,
                min_width=48,
            )
            send = gr.Button(
                "Send", variant="primary", scale=1, min_width=70, interactive=chats is not None
            )
        held_file = gr.State(None)  # an attached file's temp path, until it's sent
        owner_state = gr.State("")  # whose map the shown proposals are for

        def draw(requested: str | None, request: gr.Request) -> str:
            viewer = signin.viewer(request.username)  # re-read on every request
            try:
                m = maps.get(map_owner(students, viewer, requested or ""))
            except NotAllowed:
                return ""
            return map_svg(m, date.today())

        def checked_owner(requested: str | None, request: gr.Request) -> str:
            try:  # whose list to draw: only after the check
                return map_owner(students, signin.viewer(request.username), requested or "")
            except NotAllowed:
                return ""

        def on_pick(
            requested: str | None, previous: str, path: str | None, v: int, request: gr.Request
        ) -> list[Any]:
            viewer = signin.viewer(request.username)
            if chats is not None and viewer is not None and previous:
                chats.clear(viewer.username, previous)  # a new student starts a fresh chat
            if path:
                Path(path).unlink(missing_ok=True)  # notes attached for the last student
            hidden = gr.update(choices=[], value=[], visible=False)
            return [draw(requested, request), checked_owner(requested, request), bump(), [], hidden,
                    gr.update(visible=False), "", "", None]

        def on_attach(path: str | None) -> list[Any]:
            return [path, f"📎 {Path(path).name}, sent with your next message" if path else ""]

        def on_send(
            message: str, path: str | None, requested: str | None, request: gr.Request
        ) -> Iterator[list[Any]]:
            viewer = signin.viewer(request.username)
            hidden = gr.update(choices=[], value=[], visible=False)
            if chats is None or viewer is None:
                yield [gr.update(), hidden, gr.update(visible=False), "", "", message, path]
                return
            shown = chat_messages(chats, viewer.username, requested or "")
            shown += [
                {"role": "user", "content": message or "📎 notes attached"},
                {"role": "assistant", "content": "…"},
            ]
            yield [shown, hidden, gr.update(visible=False), "", "", "", None]
            try:
                data = Path(path).read_bytes() if path else None
                answer = ""
                for piece in educator_send(
                    chats,
                    students,
                    viewer,
                    requested,
                    message,
                    Path(path).name if path else None,
                    data,
                ):
                    answer += piece
                    shown[-1]["content"] = answer or "…"
                    yield [shown, hidden, gr.update(visible=False), "", "", "", None]
            except (NotAllowed, UploadError, ConversationUnavailable) as exc:
                shown[-1]["content"] = f"⚠️ {exc}"
                yield [shown, hidden, gr.update(visible=False), "", "", message, None]
                return
            except Exception:  # noqa: BLE001 - never echo the text in errors
                shown[-1]["content"] = "⚠️ Claude didn't answer. Try again in a moment."
                yield [shown, hidden, gr.update(visible=False), "", "", message, None]
                return
            finally:
                if path:
                    Path(path).unlink(missing_ok=True)  # files are never kept
            try:
                owner = map_owner(students, viewer, requested or "")
            except NotAllowed:  # archived or no longer theirs while it answered
                yield [shown, hidden, gr.update(visible=False), "", "", "", None]
                return
            found = chats.proposals(viewer.username, owner)
            labels = [p.label for p in found]
            yield [
                shown,
                gr.update(choices=labels, value=[], visible=bool(labels)),
                gr.update(visible=bool(labels)),
                "",
                owner,
                "",
                None,
            ]

        def on_add(picked: list[str], owner: str, v: int, request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            if chats is None or not owner:
                return ["", gr.update(), gr.update(), draw(owner, request), v]
            message = educator_add(chats, maps, feedback, students, viewer, owner, picked or [])
            left = [p.label for p in chats.proposals(viewer.username, owner)] if viewer else []
            return [
                message,
                gr.update(choices=left, value=[], visible=bool(left)),
                gr.update(visible=bool(left)),
                draw(owner, request),
                bump(),  # the list shows what was added
            ]

        sending = gr.on(
            [send.click, text.submit],
            on_send,
            [text, held_file, who],
            [chat, ticks, add, status, owner_state, text, held_file],
            **PRIVATE,
        )
        # a new student stops a reply still coming for the last one, and drops its notes
        who.change(
            on_pick,
            [who, owner_state, held_file, version],
            [picture, list_owner, version, chat, ticks, add, status, owner_state, held_file],
            cancels=[sending],
            **PRIVATE,
        )
        attach.upload(on_attach, attach, [held_file, status], **PRIVATE)
        add.click(on_add, [ticks, owner_state, version], [status, ticks, add, picture, version],
                  **PRIVATE)
        tab.select(draw, who, picture, **PRIVATE)  # redraw on opening
        version.change(draw, who, picture, **PRIVATE)  # a list edit redraws it
        # the picture only: redrawing the list would wipe a half-typed rename
        gr.Timer(REFRESH_SECONDS).tick(draw, who, picture, **PRIVATE)
    return tab, who
