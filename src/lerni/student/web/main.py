"""The one app's page: who's signed in, then tabs by role.

Tabs start hidden and are shown on load for the signed-in viewer; nothing
per-user or from the data is built into the layout, because Gradio sends
every signed-in browser the same page config.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import gradio as gr

from lerni.student.conversation import ChatModel, Conversations
from lerni.student.feedback import FeedbackStore
from lerni.student.interests import MapStore
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import StudentStore
from lerni.student.upload import Uploader
from lerni.student.web.accounts import account_tab, student_rows, students_tab
from lerni.student.web.ask import ask_tab, messages
from lerni.student.web.mapdraw import map_svg, map_words
from lerni.student.web.maps import entry_choices, map_tab, supervised_choices

# Tab ids in page order. A supervised student gets Home: their conversation,
# full screen; independent students get Ask, My map, and My account; educators
# also get Maps and Students.
_TAB_IDS = ("home", "ask", "mymap", "maps", "students", "account")
_EDUCATOR_TABS = {"maps", "students"}
_INDEPENDENT_TABS = {"ask", "mymap", "account"}


def visible_tabs(viewer: Viewer | None) -> tuple[str, ...]:
    """The tab ids ``viewer`` sees, in page order."""
    if viewer is None:
        return ()
    shown = {"home"} if viewer.role is Role.SUPERVISED else set(_INDEPENDENT_TABS)
    if viewer.educator:
        shown |= _EDUCATOR_TABS
    return tuple(tab for tab in _TAB_IDS if tab in shown)


def opening_tab(viewer: Viewer | None) -> str | None:
    """The tab selected on load: Ask for independent students, Home for supervised ones."""
    shown = visible_tabs(viewer)
    return ("ask" if "ask" in shown else shown[0]) if shown else None


def build_main_view(
    signin: SignIn,
    students: StudentStore,
    maps: MapStore,
    conversations: Conversations | None = None,
    uploader: Uploader | None = None,
    feedback: FeedbackStore | None = None,
    model: ChatModel | None = None,
) -> gr.Blocks:
    """Build the page; the tabs each viewer sees are set on load."""
    # uploads picked but never sent expire within two hours (checked hourly)
    with gr.Blocks(title="Lerni", analytics_enabled=False, delete_cache=(3600, 3600)) as blocks:
        with gr.Row():
            header = gr.Markdown()
            # a same-tab button: a Markdown link would open Sign out in a new tab
            gr.Button("Sign out", link="/signout", link_target="_self", size="sm", scale=0)
        with gr.Tabs() as tabs:
            home, home_chat, _ = ask_tab(signin, conversations, supervised=True)
            ask, chat, voice = ask_tab(signin, conversations)
            mymap, _, picture, words, entry = map_tab(signin, students, maps, mine=True,
                                                      uploader=uploader)
            maps_tab, who, _, _, _ = map_tab(signin, students, maps, mine=False,
                                             uploader=uploader, feedback=feedback, model=model)
            students_tab_, students_table = students_tab(signin, students)
            account = account_tab(signin, students)

        def on_load(request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            shown = visible_tabs(viewer)
            is_edu = viewer is not None and viewer.educator
            if viewer is None:
                name = "nobody"
            else:
                name = f"{viewer.display_name} · {viewer.role.value}"
                name += " · educator" if is_edu else ""
            own = ["", "", gr.update(choices=[], value=None)]
            if viewer is not None and "mymap" in shown:
                m = maps.get(viewer.username)
                own = [map_svg(m, date.today()), map_words(m, date.today()),
                       gr.update(choices=entry_choices(m), value=None)]
            return [
                f"Signed in as **{name}**",
                gr.update(selected=opening_tab(viewer)),  # open a tab they can see
                *(gr.update(visible=tab in shown) for tab in _TAB_IDS),
                student_rows(students) if is_edu else [],
                # one ongoing conversation per student: pick up where they left off
                messages(conversations, viewer.username)
                if conversations is not None and viewer is not None and "ask" in shown else [],
                messages(conversations, viewer.username)  # the supervised screen's chat
                if conversations is not None and viewer is not None and "home" in shown else [],
                gr.update(visible=is_edu, value=False),  # educators can try the supervised voice
                *own,  # My map: picture, words, entries
                gr.update(choices=supervised_choices(students, viewer), value=None),  # Maps
            ]

        blocks.load(
            on_load,
            None,
            # order matches on_load: header, tabs, the _TAB_IDS tabs, then the rest
            [header, tabs, home, ask, mymap, maps_tab, students_tab_, account,
             students_table, chat, home_chat, voice, picture, words, entry, who],
            api_visibility="private",
        )
    return blocks
