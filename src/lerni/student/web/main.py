"""The one app's page: who's signed in, then tabs by role.

Tabs start hidden and are shown on load for the signed-in viewer; nothing
per-user or from the data is built into the layout, because Gradio sends
every signed-in browser the same page config.
"""

from __future__ import annotations

import html
from collections.abc import Callable
from datetime import date
from typing import Any

import gradio as gr

from lerni.student.conversation import Conversations
from lerni.student.educator_agent import EducatorChats
from lerni.student.feedback import FeedbackStore
from lerni.student.garage import Garage
from lerni.student.interests import MapStore
from lerni.student.points import PointsStore
from lerni.student.race import RaceDesk
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import StudentStore
from lerni.student.upload import Uploader
from lerni.student.usage import Usage
from lerni.student.voice import Speech
from lerni.student.web.accounts import settings_tab, student_rows
from lerni.student.web.ask import ask_tab, messages
from lerni.student.web.educator import educator_tab
from lerni.student.web.games import games_tab, require_player
from lerni.student.web.mapdraw import map_svg, owner_key
from lerni.student.web.maps import map_tab, supervised_choices

# Tab ids in page order. A supervised student gets Home (their conversation,
# full screen, shown as Chat) and Games; independent students get Chat, My MentalMap,
# and Settings; educators also get their student's page (maps) and Games, and Settings
# holds Students for them.
_TAB_IDS = ("home", "games", "ask", "mymap", "maps", "account")
_SUPERVISED_TABS = {"home", "games"}
_EDUCATOR_TABS = {"maps", "games"}
_INDEPENDENT_TABS = {"ask", "mymap", "account"}
_LABELS = {"home": "Chat", "games": "Games", "ask": "Chat", "mymap": "My MentalMap",
           "maps": "MentalMaps", "account": "Settings"}  # the menu's names for the tabs
EARN = ("**How to earn ⭐**\n\n🏁 **Race** in Games: get answers right to win.\n\n"
        "💬 **Chat** with Lerni: answer its questions in your own words. "
        "⭐ +3 for a right answer, ⭐ +1 for a good try.")
WATCH_TICKS = 20  # after an answer, look for new ⭐ every 2 s, past the tagger's 30 s limit
TOGGLE_EARN = "() => document.getElementById('lerni-earn')?.classList.toggle('lerni-hide')"


def visible_tabs(viewer: Viewer | None) -> tuple[str, ...]:
    """The tab ids ``viewer`` sees, in page order."""
    if viewer is None:
        return ()
    shown = set(_SUPERVISED_TABS) if viewer.role is Role.SUPERVISED else set(_INDEPENDENT_TABS)
    if viewer.educator:
        shown |= _EDUCATOR_TABS
    return tuple(tab for tab in _TAB_IDS if tab in shown)


def opening_tab(viewer: Viewer | None, students: StudentStore | None = None) -> str | None:
    """The tab selected on load: an educator's student page when they have a supervised
    student, Chat for other independent accounts, Home for supervised ones."""
    shown = visible_tabs(viewer)
    if "maps" in shown and students is not None and supervised_choices(students, viewer):
        return "maps"
    return ("ask" if "ask" in shown else shown[0]) if shown else None


def picker(choices: list[tuple[str, str]]) -> Any:
    """The student dropdown: with one supervised student, already on them and out of sight."""
    only = choices[0][1] if len(choices) == 1 else None
    return gr.update(choices=choices, value=only, visible=len(choices) != 1)


def menu_label(tab: str, viewer: Viewer | None, students: StudentStore | None = None) -> str:
    """A section's name in the menu: the student's own name for their page, when there's one."""
    if tab == "maps" and students is not None:
        picks = supervised_choices(students, viewer)
        if len(picks) == 1:
            return picks[0][0]  # their display name, from the account
    return _LABELS[tab]


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
    points: PointsStore | None = None,
    races: RaceDesk | None = None,
    garage: Garage | None = None,
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
            # a player's ⭐ (games.py); a tap says how to earn more
            stars = gr.Button(elem_classes="lerni-stars", size="sm", visible=False)
            # one switch for every sound in the app (race.js keeps it on this device)
            gr.HTML('<button type="button" id="lerni-mute" class="lerni-mute" aria-pressed="true"'
                    ' aria-label="Sound on">🔊</button>', padding=False)
        with gr.Column(elem_id="lerni-earn", elem_classes="lerni-hide"):
            gr.Markdown(EARN)
            got_it = gr.Button("Got it", size="sm")
        for button in (stars, got_it):  # opens and closes in the page: no server call
            button.click(None, js=TOGGLE_EARN)
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
            home, home_chat, _, home_done = ask_tab(signin, conversations, supervised=True,
                                                    speech=speech)
            if points is not None:
                games, games_refresh, games_outputs = games_tab(signin, races, points, stars,
                                                                garage or Garage(),
                                                                speech=speech)
            else:  # built without a points store (tests): the old placeholder
                with gr.Tab("Games", id="games", visible=False) as games:
                    gr.HTML('<div class="lerni-soon"><div aria-hidden="true">🎮</div>'
                            "<p>Games are coming soon!</p></div>")
                games_refresh, games_outputs = None, []
            ask, chat, voice, ask_done = ask_tab(signin, conversations, speech=speech)
            mymap, picture, owner, version = map_tab(signin, students, maps, uploader,
                                                      races.results if races else None)
            maps_tab, who = educator_tab(signin, students, maps, educator_chats, feedback, points,
                                         garage or Garage(), races.results if races else None)
            account, students_table, students_box = settings_tab(signin, students)

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
                me = viewer.username
                own = [map_svg(maps.get(me), date.today(), owner_key(me)), me, 1]
            opening = opening_tab(viewer, students)
            if races is not None and viewer is not None and "games" in shown:
                try:  # write the next race's questions now, in the background, not at Race
                    races.prefill(viewer.username, supervised=viewer.role is Role.SUPERVISED)
                except Exception:  # noqa: BLE001 - best effort: the page loads regardless
                    pass
            return [
                f"Signed in as **{name}**",
                f"**{menu_label(opening, viewer, students)}**" if opening else "",
                gr.update(selected=opening),  # open a tab they can see
                *(gr.update(visible=tab in shown) for tab in _TAB_IDS),
                # the menu lists their sections; one section needs no list
                *(gr.update(visible=tab in shown and len(shown) > 1,
                            value=menu_label(tab, viewer, students)) for tab in _TAB_IDS),
                student_rows(students) if is_edu else [],
                gr.update(visible=is_edu),  # Students, inside Settings
                # one ongoing conversation per student: pick up where they left off
                messages(conversations, viewer.username)
                if conversations is not None and viewer is not None and "ask" in shown else [],
                messages(conversations, viewer.username)  # the supervised screen's chat
                if conversations is not None and viewer is not None and "home" in shown else [],
                gr.update(visible=is_edu, value=False),  # educators can try the supervised voice
                *own,  # My MentalMap: picture, whose list, its version
                picker(supervised_choices(students, viewer)),  # the student's page
            ]

        blocks.load(
            on_load,
            None,
            # order matches on_load: header, title, tabs, the _TAB_IDS tabs, their menu
            # buttons, then the rest
            [header, title, tabs, home, games, ask, mymap, maps_tab, account,
             *nav.values(),
             students_table, students_box, chat, home_chat, voice, picture, owner, version, who],
            api_visibility="private",
        )
        if games_refresh is not None:  # the ⭐, the track, and the garage on page load
            blocks.load(games_refresh, None, games_outputs, api_visibility="private")
        blocks.load(usage_notice, None, notice, api_visibility="private")
        if usage is not None:  # usage changes with each call: check again every minute
            gr.Timer(60).tick(usage_notice, None, notice, api_visibility="private")

        # after each answer, look for new ⭐ for a few seconds (the tagger runs in the background)
        watch, before, ticks = gr.Timer(2, active=False), gr.State(0), gr.State(0)

        def balance(request: gr.Request) -> int | None:
            try:
                viewer = require_player(signin.viewer(request.username))
            except Exception:  # noqa: BLE001 - not a player: no ⭐ to watch
                return None
            return points.get(viewer.username).balance if points is not None else None

        def start_watch(request: gr.Request) -> list[Any]:
            now = balance(request)
            return [gr.Timer(active=now is not None), now or 0, 0]

        def on_tick(was: int, n: int, request: gr.Request) -> list[Any]:
            now = balance(request)
            if now is not None and now > was:  # "⭐ 183 +3", then stop looking
                return [gr.update(value=f"⭐ {now} +{now - was}"), gr.Timer(active=False), 0]
            if now is None or n + 1 >= WATCH_TICKS:
                return [gr.update(), gr.Timer(active=False), 0]
            return [gr.update(), gr.update(), n + 1]

        for event in [*home_done, *ask_done]:
            event.then(start_watch, None, [watch, before, ticks], api_visibility="private")
        watch.tick(on_tick, [before, ticks], [stars, watch, ticks], api_visibility="private")

        # a menu button opens its section and closes the menu
        def opener(tab: str) -> Callable[..., list[Any]]:
            def open_tab(request: gr.Request) -> list[Any]:  # the title says the menu's name
                label = menu_label(tab, signin.viewer(request.username), students)
                return [gr.update(selected=tab), f"**{label}**"]
            return open_tab

        for tab, button in nav.items():
            button.click(
                opener(tab),
                None,
                [tabs, title],
                js="() => { window.lerniMenu?.(false); }",
                api_visibility="private",
            )
    return blocks
