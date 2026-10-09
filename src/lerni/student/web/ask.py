"""The Ask tab: an independent student's text conversation with Claude.

:func:`ask_reply` is a plain function over the server-resolved viewer, so the
role check can be tested without a browser; :func:`ask_tab` wires it to Gradio.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import gradio as gr

from lerni.student.conversation import (
    ConversationError,
    Conversations,
    ConversationUnavailable,
)
from lerni.student.plans import LearningPlan, PlanError, PlanStore
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.web.accounts import PRIVATE, require
from lerni.student.web.educator import plan_choices

ANYTHING = "Anything"
NOTICE = (
    "Your messages go to Claude (Anthropic) through the admin's Claude account. "
    "Don't share personal details."
)


def _topic(store: PlanStore, plan_id: str | None) -> LearningPlan | None:
    if not plan_id or plan_id == ANYTHING:
        return None
    try:
        return store.get(plan_id)
    except PlanError:
        return None  # a plan archived meanwhile: just answer without it


def ask_reply(
    conversations: Conversations,
    store: PlanStore,
    viewer: Viewer | None,
    text: str,
    plan_id: str | None,
    young_voice: bool = False,
) -> Iterator[str]:
    """Answer an independent student's question, a piece at a time.

    Raises:
        NotAllowed: The viewer isn't a signed-in independent student.
        ConversationError: Empty, too long, or a reply is still coming.
        ConversationUnavailable: Claude didn't answer.
    """
    v = require(viewer, Role.INDEPENDENT)
    # educators can try the young-learner voice; everyone else gets their own kind's
    voice = "supervised" if young_voice and v.educator else "independent"
    yield from conversations.ask(v.username, text, _topic(store, plan_id), voice)


def topic_choices(store: PlanStore) -> list[tuple[str, str]]:
    """ "Anything", then the plans a student can pick as a topic."""
    return [(ANYTHING, ANYTHING), *plan_choices(store)]


def _messages(conversations: Conversations, username: str) -> list[dict[str, str]]:
    return [{"role": t.role, "content": t.text} for t in conversations.history(username)]


def ask_tab(
    signin: SignIn, store: PlanStore, conversations: Conversations | None
) -> tuple[gr.Tab, gr.Dropdown, gr.Chatbot, gr.Checkbox]:
    """The Ask tab (hidden for everyone but independent students)."""
    with gr.Tab("Ask", id="ask", visible=False) as tab:
        if conversations is None:
            gr.Markdown("Claude isn't set up on this server yet.")
        # everything fits on one screen, so typing never makes the page scroll
        with gr.Row():
            topic = gr.Dropdown(label="Topic", choices=[], value=None, scale=3)  # filled on load
            young = gr.Checkbox(label="Try the young-learner voice", visible=False, scale=1)
        chat = gr.Chatbot(label="Ask Lerni", height="45vh")
        with gr.Row():
            question = gr.Textbox(
                show_label=False, placeholder="Ask anything…", lines=1, max_length=2000,
                scale=5,
            )
            send = gr.Button("Send", variant="primary", scale=1, min_width=80)
        with gr.Row():
            gr.Markdown(NOTICE)
            clear = gr.Button("Clear", size="sm", scale=0)

        def on_send(
            text: str, plan_id: str | None, young_voice: bool, request: gr.Request
        ) -> Iterator[list[Any]]:
            viewer = signin.viewer(request.username)  # re-read on every question
            if conversations is None or viewer is None or viewer.role is not Role.INDEPENDENT:
                yield [gr.update(), gr.update()]
                return
            # show the question right away, with an empty answer that fills as it streams
            shown = _messages(conversations, viewer.username)
            shown += [{"role": "user", "content": text}, {"role": "assistant", "content": ""}]
            try:
                for piece in ask_reply(conversations, store, viewer, text, plan_id, young_voice):
                    shown[-1]["content"] += piece
                    yield [shown, ""]  # clear the box as soon as the answer starts
            except (ConversationError, ConversationUnavailable) as exc:
                shown[-1]["content"] = f"⚠️ {exc}"
                yield [shown, gr.update()]  # keep their question so they can resend it

        def on_clear(request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            if conversations is not None and viewer is not None:
                conversations.clear(viewer.username)
            return []

        # Send, or Enter in the box
        send.click(on_send, [question, topic, young], [chat, question], **PRIVATE)
        question.submit(on_send, [question, topic, young], [chat, question], **PRIVATE)
        clear.click(on_clear, None, chat, **PRIVATE)
    return tab, topic, chat, young
