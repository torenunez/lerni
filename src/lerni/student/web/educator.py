"""MentalMaps for educators: suggest or change a goal, then racing, the list, and the picture.

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
from lerni.student.garage import Garage
from lerni.student.interests import MapStore
from lerni.student.points import PointsStore
from lerni.student.results import ResultsLog
from lerni.student.signin import SignIn, Viewer
from lerni.student.students import StudentStore
from lerni.student.upload import UploadError, extract_upload
from lerni.student.web.accounts import PRIVATE, NotAllowed, require_educator
from lerni.student.web.games import student_progress
from lerni.student.web.mapdraw import map_svg, owner_key
from lerni.student.web.maps import REFRESH_SECONDS, map_owner, save_feedback
from lerni.student.web.mentallist import bump, mental_list


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
        done, skipped = maps.change(owner, lambda m: apply_educator_proposals(m, on_map),
                                    by="educator chat")
    sent = 0
    for p in chosen:
        if p.kind == "feedback" and feedback is not None:
            sent += save_feedback(feedback, students, v, owner, p.notes, "").startswith("✅")
    chats.taken(v.username, owner, chosen)
    lines = [f"✅ Added {done} to the map."] if done else []
    lines += [f"📨 Sent {sent} to the admin."] if sent else []
    lines += [f"Skipped {s}" for s in skipped]
    return "\n\n".join(lines) or "⚠️ Nothing was added."


def preticked(found: list[Any]) -> list[str]:
    """The suggestions ticked on arrival: additions and tidying, never a removal or feedback."""
    return [p.label for p in found if p.kind not in ("remove", "feedback")]


def add_button(n: int) -> Any:
    """The Add button for ``n`` ticked suggestions: "Add 2 to the map", hidden for none."""
    return gr.update(value=f"Add {n} to the map", visible=n > 0)


def educator_tab(
    signin: SignIn,
    students: StudentStore,
    maps: MapStore,
    chats: EducatorChats | None,
    feedback: FeedbackStore | None,
    points: PointsStore | None = None,
    garage: Garage | None = None,
    results: ResultsLog | None = None,
) -> tuple[gr.Tab, gr.Dropdown]:
    """The student's page: suggest or change a goal, then racing this week, the list, the picture.

    With one supervised student it opens on them (main.py picks and hides the dropdown).
    """
    with gr.Tab("MentalMaps", id="maps", visible=False) as tab:
        # any value: a page open across a restart sends its old pick; map_owner checks it
        who = gr.Dropdown(label="Student", choices=[], value=None, allow_custom_value=True)
        # suggest a goal: first on the page, so the phone keyboard never pushes it around
        gr.Markdown("### Suggest or change a goal")
        with gr.Row(elem_classes="lerni-type"):
            text = gr.Textbox(
                show_label=False,
                placeholder="New goal, or 'easier notes for Fractions'…",
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
        reply = gr.Markdown()  # Lerni's answer, right under the box
        # suggestions come ticked: untick any, then one tap adds them (nothing before it)
        ticks = gr.CheckboxGroup(show_label=False, choices=[], visible=False)
        add = gr.Button("Add to the map", variant="primary", visible=False)
        status = gr.Markdown()
        points_line = gr.HTML()  # their racing this week, ⭐, and car
        list_owner, version = gr.State(""), gr.State(0)  # set only after map_owner's check
        # edits go to the student the list shows, never a newer dropdown pick
        mental_list(signin, students, maps, list_owner, list_owner, version, "lerni-pick-maps",
                    "Pick a student, or add one in Settings.", results, folded=True,
                    add_form=False)
        picture = gr.HTML(elem_id="lerni-map-maps", elem_classes="lerni-map")  # last
        held_file = gr.State(None)  # an attached file's temp path, until it's sent
        owner_state = gr.State("")  # whose map the shown proposals are for

        def draw(requested: str | None, request: gr.Request) -> str:
            viewer = signin.viewer(request.username)  # re-read on every request
            try:
                who = map_owner(students, viewer, requested or "")
            except NotAllowed:
                return ""
            return map_svg(maps.get(who), date.today(), owner_key(who))

        def progress(requested: str | None, request: gr.Request) -> str:
            viewer = signin.viewer(request.username)  # re-read on every request
            return (student_progress(points, garage or Garage(), students, viewer, requested,
                                     results, maps) if points else "")

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
            stars = progress(requested, request)
            return [draw(requested, request), checked_owner(requested, request), bump(), hidden,
                    gr.update(visible=False), "", "", None, stars, ""]

        def on_attach(path: str | None) -> list[Any]:
            return [path, f"📎 {Path(path).name}, sent with your next message" if path else ""]

        def on_send(
            message: str, path: str | None, requested: str | None, request: gr.Request
        ) -> Iterator[list[Any]]:
            viewer = signin.viewer(request.username)
            hidden = gr.update(choices=[], value=[], visible=False)
            if chats is None or viewer is None:
                yield [hidden, gr.update(visible=False), "", "", message, path, ""]
                return
            yield [hidden, gr.update(visible=False), "", "", "", None, "…"]  # the box clears
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
                    yield [hidden, gr.update(visible=False), "", "", "", None, answer or "…"]
            except (NotAllowed, UploadError, ConversationUnavailable) as exc:
                yield [hidden, gr.update(visible=False), "", "", message, None, f"⚠️ {exc}"]
                return
            except Exception:  # noqa: BLE001 - never echo the text in errors
                yield [hidden, gr.update(visible=False), "", "", message, None,
                       "⚠️ Claude didn't answer. Try again in a moment."]
                return
            finally:
                if path:
                    Path(path).unlink(missing_ok=True)  # files are never kept
            try:
                owner = map_owner(students, viewer, requested or "")
            except NotAllowed:  # archived or no longer theirs while it answered
                yield [hidden, gr.update(visible=False), "", "", "", None, answer]
                return
            found = chats.proposals(viewer.username, owner)
            labels = [p.label for p in found]
            yield [
                gr.update(choices=labels, value=preticked(found), visible=bool(labels)),
                add_button(len(preticked(found))),
                "",
                owner,
                "",
                None,
                answer,
            ]

        def on_add(picked: list[str], owner: str, v: int, request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            if chats is None or not owner:
                return ["", gr.update(), gr.update(), draw(owner, request), v]
            message = educator_add(chats, maps, feedback, students, viewer, owner, picked or [])
            left = [p.label for p in chats.proposals(viewer.username, owner)] if viewer else []
            return [
                message,
                gr.update(choices=left, value=[], visible=bool(left)),  # left out on purpose
                add_button(0),
                draw(owner, request),
                bump(),  # the list shows what was added
            ]

        sending = gr.on(
            [send.click, text.submit],
            on_send,
            [text, held_file, who],
            [ticks, add, status, owner_state, text, held_file, reply],
            **PRIVATE,
        )
        # a new student stops a reply still coming for the last one, and drops its notes
        who.change(
            on_pick,
            [who, owner_state, held_file, version],
            [picture, list_owner, version, ticks, add, status, owner_state, held_file,
             points_line, reply],
            cancels=[sending],
            **PRIVATE,
        )
        attach.upload(on_attach, attach, [held_file, status], **PRIVATE)
        add.click(on_add, [ticks, owner_state, version], [status, ticks, add, picture, version],
                  **PRIVATE)
        ticks.change(lambda picked: add_button(len(picked or [])), ticks, add, **PRIVATE)
        tab.select(bump, None, version, **PRIVATE)  # opening redraws the picture and the list
        tab.select(progress, who, points_line, **PRIVATE)  # and racing, while races go on
        version.change(draw, who, picture, **PRIVATE)  # a list edit redraws it
        # the picture only: redrawing the list would wipe a half-typed rename
        gr.Timer(REFRESH_SECONDS).tick(draw, who, picture, **PRIVATE)
    return tab, who
