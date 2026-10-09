"""The one app's page: who's signed in, then tabs by role.

Tabs start hidden and are shown on load for the signed-in viewer; nothing
per-user or from the data is built into the layout, because Gradio sends
every signed-in browser the same page config.
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from lerni.student.catalog import PackageLessonCatalog
from lerni.student.plan_import import PlanDrafter
from lerni.student.plans import PlanStore
from lerni.student.signin import Role, SignIn
from lerni.student.students import StudentStore
from lerni.student.web.accounts import account_tab, student_rows, students_tab
from lerni.student.web.educator import educator_tabs, plan_choices, sessions_text

# Tab ids in page order, and which roles see each. Learning plans opens to
# independent students in step 6.
_TABS = (
    ("learn", {Role.SUPERVISED, Role.INDEPENDENT}),
    ("guide", {Role.EDUCATOR, Role.INDEPENDENT}),
    ("sessions", {Role.EDUCATOR}),
    ("plans", {Role.EDUCATOR}),
    ("students", {Role.EDUCATOR}),
    ("account", {Role.INDEPENDENT}),
)


def visible_tabs(role: Role | None) -> tuple[str, ...]:
    """The tab ids ``role`` sees, in page order; the first one opens on load."""
    return tuple(tab for tab, roles in _TABS if role in roles)


def build_main_view(
    signin: SignIn,
    store: PlanStore,
    catalog: PackageLessonCatalog,
    students: StudentStore,
    drafter: PlanDrafter | None,
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
            (guide_tab, sessions_tab, plans_tab), plan_dd, sessions = educator_tabs(
                signin, store, catalog, drafter
            )
            students_tab_, students_table = students_tab(signin, students)
            account = account_tab(signin, students)

        def on_load(request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            role = viewer.role if viewer else None
            is_edu, is_ind = role is Role.EDUCATOR, role is Role.INDEPENDENT
            name = f"{viewer.display_name} · {viewer.role.value}" if viewer else "nobody"
            shown = visible_tabs(role)
            return [
                f"Signed in as **{name}**",
                gr.update(selected=shown[0] if shown else None),  # open a tab they can see
                *(gr.update(visible=tab in shown) for tab, _ in _TABS),
                gr.update(visible=role is Role.SUPERVISED),  # waiting screen
                gr.update(visible=is_ind),  # independent's empty Learn
                gr.update(choices=plan_choices(store) if is_edu else [], value=None),
                sessions_text(catalog) if is_edu else "",
                student_rows(students) if is_edu else [],
            ]

        blocks.load(
            on_load,
            None,
            # order matches on_load: header, tabs, the _TABS tabs, then the rest
            [header, tabs, learn_tab, guide_tab, sessions_tab, plans_tab, students_tab_,
             account, waiting, independent, plan_dd, sessions, students_table],
            api_visibility="private",
        )
    return blocks
