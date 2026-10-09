"""The one app's page: who's signed in, then tabs by role."""

from __future__ import annotations

from typing import Any

import gradio as gr


def build_main_view(
    signin: Any, store: Any, catalog: Any, students: Any, drafter: Any
) -> gr.Blocks:
    """Build the app's page (temporary: a header only)."""
    with gr.Blocks(title="Lerni", analytics_enabled=False) as blocks:
        gr.Markdown("Lerni")
    return blocks
