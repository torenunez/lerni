"""The one app's page: who's signed in, then tabs by role.

Tabs start hidden and are shown on load for the signed-in viewer; nothing
per-user or from the data is built into the layout, because Gradio sends
every signed-in browser the same page config.
"""

from __future__ import annotations

import html
from datetime import date
from typing import Any

import gradio as gr

from lerni.student.conversation import Conversations
from lerni.student.educator_agent import EducatorChats
from lerni.student.feedback import FeedbackStore
from lerni.student.interests import MapStore
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import StudentStore
from lerni.student.upload import Uploader
from lerni.student.usage import Usage
from lerni.student.voice import Speech
from lerni.student.web.accounts import account_tab, student_rows, students_tab
from lerni.student.web.ask import ask_tab, messages
from lerni.student.web.educator import educator_tab
from lerni.student.web.mapdraw import map_svg
from lerni.student.web.maps import map_tab, supervised_choices

# Tab ids in page order. A supervised student gets Home (their conversation,
# full screen) and Games; independent students get Ask, My MentalMap, and My account;
# educators also get MentalMaps and Students.
_TAB_IDS = ("home", "games", "ask", "mymap", "maps", "students", "account")
_SUPERVISED_TABS = {"home", "games"}
_EDUCATOR_TABS = {"maps", "students"}
_INDEPENDENT_TABS = {"ask", "mymap", "account"}
_LABELS = {"home": "Lerni", "games": "Games", "ask": "Ask", "mymap": "My MentalMap",
           "maps": "MentalMaps",
           "students": "Students", "account": "My account"}  # the menu's names for the tabs


def visible_tabs(viewer: Viewer | None) -> tuple[str, ...]:
    """The tab ids ``viewer`` sees, in page order."""
    if viewer is None:
        return ()
    shown = set(_SUPERVISED_TABS) if viewer.role is Role.SUPERVISED else set(_INDEPENDENT_TABS)
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
    label: str = "",
    speech: Speech | None = None,
    educator_chats: EducatorChats | None = None,
    usage: Usage | None = None,
) -> gr.Blocks:
    """Build the page; the tabs each viewer sees are set on load."""
    # uploads picked but never sent expire within two hours (checked hourly)
    with gr.Blocks(title="Lerni", analytics_enabled=False, delete_cache=(3600, 3600)) as blocks:
        if label:  # a development server says so on every page (the same for everyone)
            gr.HTML(f'<div style="background:#6b21a8;color:white;font-weight:700;'
                    f'text-align:center;padding:.3rem;border-radius:8px">{html.escape(label)}</div>')
        # the header: a menu button and the open section's name (nav.js opens the menu)
        with gr.Row(elem_classes="lerni-header"):
            gr.HTML('<button type="button" class="lerni-menu-btn" aria-label="Menu"'
                    ' aria-expanded="false">☰</button>', padding=False)
            title = gr.Markdown(elem_classes="lerni-title")
        # the menu: who's signed in, a button per section they can see, and Sign out
        with gr.Column(elem_id="lerni-drawer"):
            header = gr.Markdown()
            nav = {tab: gr.Button(_LABELS[tab], visible=False, elem_classes="lerni-nav-item")
                   for tab in _TAB_IDS}
            # a same-tab button: a Markdown link would open Sign out in a new tab
            gr.Button("Sign out", link="/signout", link_target="_self", size="sm")
        gr.HTML('<div class="lerni-backdrop"></div>', padding=False)  # a tap closes the menu
        notice = gr.Markdown(visible=False, elem_classes="lerni-usage")  # educators only

        def usage_notice(request: gr.Request) -> Any:
            viewer = signin.viewer(request.username)
            line = ""
            if usage is not None and viewer is not None and viewer.educator:
                line = usage.paused() or usage.warning()
            return gr.update(value=line, visible=bool(line))

        with gr.Tabs() as tabs:
            home, home_chat, _ = ask_tab(signin, conversations, supervised=True, speech=speech)
            with gr.Tab("Games", id="games", visible=False) as games:  # a placeholder for now
                gr.HTML('<div class="lerni-soon"><div aria-hidden="true">🎮</div>'
                        "<p>Games are coming soon!</p></div>")
            ask, chat, voice = ask_tab(signin, conversations, speech=speech)
            mymap, picture, owner, version = map_tab(signin, students, maps, uploader)
            maps_tab, who = educator_tab(signin, students, maps, educator_chats, feedback)
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
            own = ["", "", 0]  # My MentalMap: picture, whose list, its version
            if viewer is not None and "mymap" in shown:
                own = [map_svg(maps.get(viewer.username), date.today()), viewer.username, 1]
            opening = opening_tab(viewer)
            return [
                f"Signed in as **{name}**",
                f"**{_LABELS[opening]}**" if opening else "",
                gr.update(selected=opening),  # open a tab they can see
                *(gr.update(visible=tab in shown) for tab in _TAB_IDS),
                # the menu lists their sections; one section needs no list
                *(gr.update(visible=tab in shown and len(shown) > 1) for tab in _TAB_IDS),
                student_rows(students) if is_edu else [],
                # one ongoing conversation per student: pick up where they left off
                messages(conversations, viewer.username)
                if conversations is not None and viewer is not None and "ask" in shown else [],
                messages(conversations, viewer.username)  # the supervised screen's chat
                if conversations is not None and viewer is not None and "home" in shown else [],
                gr.update(visible=is_edu, value=False),  # educators can try the supervised voice
                *own,  # My MentalMap: picture, whose list, its version
                gr.update(choices=supervised_choices(students, viewer), value=None),  # MentalMaps
            ]

        blocks.load(
            on_load,
            None,
            # order matches on_load: header, title, tabs, the _TAB_IDS tabs, their menu
            # buttons, then the rest
            [header, title, tabs, home, games, ask, mymap, maps_tab, students_tab_, account,
             *nav.values(),
             students_table, chat, home_chat, voice, picture, owner, version, who],
            api_visibility="private",
        )
        blocks.load(usage_notice, None, notice, api_visibility="private")
        if usage is not None:  # usage changes with each call: check again every minute
            gr.Timer(60).tick(usage_notice, None, notice, api_visibility="private")

        # a menu button opens its section and closes the menu
        for tab, button in nav.items():
            button.click(
                lambda tab=tab: [gr.update(selected=tab), f"**{_LABELS[tab]}**"],
                None,
                [tabs, title],
                js="() => { window.lerniMenu?.(false); }",
                api_visibility="private",
            )
    return blocks
