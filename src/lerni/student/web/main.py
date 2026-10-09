"""The one app's page: who's signed in, then tabs by role.

Tabs start hidden and are shown on load for the signed-in viewer; nothing
per-user or from the data is built into the layout, because Gradio sends
every signed-in browser the same page config.
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from lerni.student.catalog import PackageLessonCatalog
from lerni.student.conversation import Conversations
from lerni.student.plan_import import PlanDrafter
from lerni.student.plans import PlanStore
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import StudentStore
from lerni.student.web.accounts import account_tab, student_rows, students_tab
from lerni.student.web.ask import ANYTHING, ask_tab, topic_choices
from lerni.student.web.educator import educator_tabs, plan_choices, sessions_text

# Tab ids in page order. Everyone gets Learn; independent students also get
# Ask, Guide, and My account; educators also get Sessions, Learning plans, and
# Students. Independent students' own Learning plans arrive in step 7.
_TAB_IDS = ("learn", "ask", "guide", "sessions", "plans", "students", "account")
_EDUCATOR_TABS = {"sessions", "plans", "students"}
_INDEPENDENT_TABS = {"learn", "ask", "guide", "account"}


def visible_tabs(viewer: Viewer | None) -> tuple[str, ...]:
    """The tab ids ``viewer`` sees, in page order."""
    if viewer is None:
        return ()
    shown = {"learn"}
    if viewer.role is Role.INDEPENDENT:
        shown |= _INDEPENDENT_TABS
    if viewer.educator:
        shown |= _EDUCATOR_TABS
    return tuple(tab for tab in _TAB_IDS if tab in shown)


def opening_tab(viewer: Viewer | None) -> str | None:
    """The tab selected on load: the Guide for educators, otherwise Learn."""
    shown = visible_tabs(viewer)
    if not shown:
        return None
    return "guide" if viewer is not None and viewer.educator else shown[0]


def build_main_view(
    signin: SignIn,
    store: PlanStore,
    catalog: PackageLessonCatalog,
    students: StudentStore,
    drafter: PlanDrafter | None,
    conversations: Conversations | None = None,
    welcome_html: str = "",
    independent_html: str = "",
) -> gr.Blocks:
    """Build the page; the tabs each viewer sees are set on load."""
    store.seed_if_empty()  # first run: copy in the example plans
    with gr.Blocks(title="Lerni", analytics_enabled=False) as blocks:
        with gr.Row():
            header = gr.Markdown()
            # a same-tab button: a Markdown link would open Sign out in a new tab
            gr.Button("Sign out", link="/signout", link_target="_self", size="sm", scale=0)
        with gr.Tabs() as tabs:
            with gr.Tab("Learn", id="learn", visible=False) as learn_tab:
                waiting = gr.HTML(welcome_html, visible=False)
                independent = gr.HTML(independent_html, visible=False)
            ask, topic, chat, young = ask_tab(signin, store, conversations)
            (guide_tab, sessions_tab, plans_tab), plan_dd, sessions = educator_tabs(
                signin, store, catalog, drafter
            )
            students_tab_, students_table = students_tab(signin, students)
            account = account_tab(signin, students)

        def on_load(request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            shown = visible_tabs(viewer)
            is_edu = viewer is not None and viewer.educator
            if conversations is not None and viewer is not None:
                conversations.clear(viewer.username)  # each visit starts a fresh conversation
            if viewer is None:
                name = "nobody"
            else:
                name = f"{viewer.display_name} · {viewer.role.value}"
                name += " · educator" if is_edu else ""
            return [
                f"Signed in as **{name}**",
                gr.update(selected=opening_tab(viewer)),  # open a tab they can see
                *(gr.update(visible=tab in shown) for tab in _TAB_IDS),
                gr.update(visible=viewer is not None and viewer.role is Role.SUPERVISED),
                # an independent student's empty Learn, until step 7
                gr.update(visible=viewer is not None and viewer.role is Role.INDEPENDENT),
                gr.update(choices=plan_choices(store) if is_edu else [], value=None),
                sessions_text(catalog) if is_edu else "",
                student_rows(students) if is_edu else [],
                gr.update(choices=topic_choices(store) if "ask" in shown else [],
                          value=ANYTHING),
                [],  # an empty conversation
                gr.update(visible=is_edu, value=False),  # educators can try the young voice
            ]

        blocks.load(
            on_load,
            None,
            # order matches on_load: header, tabs, the _TAB_IDS tabs, then the rest
            [header, tabs, learn_tab, ask, guide_tab, sessions_tab, plans_tab, students_tab_,
             account, waiting, independent, plan_dd, sessions, students_table, topic, chat, young],
            api_visibility="private",
        )
    return blocks
