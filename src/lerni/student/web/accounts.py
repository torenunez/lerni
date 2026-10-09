"""Accounts in the app: the educator's Students tab and an independent student's My account.

Handlers are plain functions that take the viewer, resolved on the server,
so role checks can be tested without a browser.
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import AccountError, Kind, StudentStore

PRIVATE = {"api_visibility": "private"}
STUDENT_COLUMNS = ["Username", "Display name", "Kind", "Status"]


class NotAllowed(Exception):
    """The signed-in viewer may not do this."""


def require(viewer: Viewer | None, *roles: Role) -> Viewer:
    """Return ``viewer`` if it has one of ``roles``; refuse a missing or archived one."""
    if viewer is None or viewer.role not in roles:
        raise NotAllowed("You can't do that from this account.")
    return viewer


def student_rows(students: StudentStore) -> list[list[str]]:
    """The Students table: names and kinds only, never plans or sessions."""
    return [
        [s.username, s.display_name, s.kind.value, "archived" if s.archived else "active"]
        for s in students.list_students()
    ] or [["", "No students yet.", "", ""]]


def add_student(
    students: StudentStore, viewer: Viewer | None, username: str, display_name: str,
    kind: str, password: str,
) -> str:
    require(viewer, Role.EDUCATOR)
    s = students.add(username, display_name, Kind(kind), password)
    return f"✅ Added {s.display_name} ({s.kind.value})."


def reset_student(
    students: StudentStore, viewer: Viewer | None, username: str, password: str
) -> str:
    require(viewer, Role.EDUCATOR)
    students.reset_password(username, password)
    return f"✅ New password set for {username}. Their devices are signed out."


def archive_student(students: StudentStore, viewer: Viewer | None, username: str) -> str:
    require(viewer, Role.EDUCATOR)
    students.archive(username)
    return f"✅ Archived {username}. They can't sign in, and the username stays taken."


def change_own_password(
    students: StudentStore, viewer: Viewer | None, current: str, new: str
) -> str:
    v = require(viewer, Role.INDEPENDENT)
    students.change_password(v.username, current, new)
    return "✅ Password changed."


def rename_self(students: StudentStore, viewer: Viewer | None, display_name: str) -> str:
    v = require(viewer, Role.INDEPENDENT)
    students.rename(v.username, display_name)
    return "✅ Name changed."


def _run(fn: Any, *args: Any) -> str:
    """Call a handler and turn refusals into a message for the screen."""
    try:
        return fn(*args)
    except (NotAllowed, AccountError) as exc:
        return f"⚠️ {exc}"


def students_tab(signin: SignIn, students: StudentStore) -> tuple[gr.Tab, gr.Dataframe]:
    """The educator's Students tab (hidden for everyone else)."""
    with gr.Tab("Students", id="students", visible=False) as tab:
        table = gr.Dataframe(headers=STUDENT_COLUMNS, interactive=False, type="array")
        gr.Markdown("### Add a student")
        username = gr.Textbox(label="Username (lowercase, e.g. sam)")
        display = gr.Textbox(label="Display name (a nickname is fine)")
        kind = gr.Radio(["supervised", "independent"], value="supervised", label="Kind")
        password = gr.Textbox(label="Starting password (4+ for supervised, 8+ for independent)",
                              type="password")
        add_btn = gr.Button("Add student", variant="primary")
        gr.Markdown("### Reset a password or archive")
        who = gr.Textbox(label="Username")
        new_password = gr.Textbox(label="New password", type="password")
        with gr.Row():
            reset_btn = gr.Button("Reset password")
            archive_btn = gr.Button("Archive", variant="stop")
        status = gr.Markdown()

        def viewer(request: gr.Request) -> Viewer | None:
            return signin.viewer(request.username)

        def on_add(u: str, d: str, k: str, p: str, request: gr.Request) -> list[Any]:
            message = _run(add_student, students, viewer(request), u.strip(), d, k, p)
            return [message, student_rows(students)]

        def on_reset(u: str, p: str, request: gr.Request) -> list[Any]:
            message = _run(reset_student, students, viewer(request), u.strip(), p)
            return [message, student_rows(students)]

        def on_archive(u: str, request: gr.Request) -> list[Any]:
            message = _run(archive_student, students, viewer(request), u.strip())
            return [message, student_rows(students)]

        add_btn.click(on_add, [username, display, kind, password], [status, table], **PRIVATE)
        reset_btn.click(on_reset, [who, new_password], [status, table], **PRIVATE)
        archive_btn.click(on_archive, who, [status, table], **PRIVATE)
    return tab, table  # main.py fills the table on page load


def account_tab(signin: SignIn, students: StudentStore) -> gr.Tab:
    """An independent student's My account tab (hidden for everyone else)."""
    with gr.Tab("My account", id="account", visible=False) as tab:
        name = gr.Textbox(label="Display name")
        name_btn = gr.Button("Change name")
        current = gr.Textbox(label="Current password", type="password")
        new = gr.Textbox(label="New password (8+ characters)", type="password")
        pw_btn = gr.Button("Change password", variant="primary")
        status = gr.Markdown()

        def on_name(d: str, request: gr.Request) -> str:
            return _run(rename_self, students, signin.viewer(request.username), d)

        def on_password(c: str, n: str, request: gr.Request) -> str:
            return _run(change_own_password, students, signin.viewer(request.username), c, n)

        name_btn.click(on_name, name, status, **PRIVATE)
        pw_btn.click(on_password, [current, new], status, **PRIVATE)
    return tab
