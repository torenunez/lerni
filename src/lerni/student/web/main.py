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


def _show(flag: bool) -> Any:
    return gr.update(visible=flag)


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
        header = gr.Markdown()
        with gr.Tabs():
            with gr.Tab("Learn", visible=False) as learn_tab:
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
            return [
                f"Signed in as **{name}** · [Sign out](/signout)",
                _show(role in (Role.SUPERVISED, Role.INDEPENDENT)),  # Learn
                _show(role is Role.SUPERVISED),  # waiting screen
                _show(is_ind),  # independent's empty Learn
                _show(is_edu or is_ind),  # Guide
                _show(is_edu),  # Sessions
                _show(is_edu),  # Learning plans (independent students get it in step 6)
                _show(is_edu),  # Students
                _show(is_ind),  # My account
                gr.update(choices=plan_choices(store) if is_edu else [], value=None),
                sessions_text(catalog) if is_edu else "",
                student_rows(students) if is_edu else [],
            ]

        blocks.load(
            on_load,
            None,
            [header, learn_tab, waiting, independent, guide_tab, sessions_tab, plans_tab,
             students_tab_, account, plan_dd, sessions, students_table],
            api_visibility="private",
        )
    return blocks
