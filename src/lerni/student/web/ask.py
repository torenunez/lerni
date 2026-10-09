"""The Ask tab: an independent student's text conversation with Claude.

:func:`ask_reply` is a plain function over the server-resolved viewer, so the
role and topic checks can be tested without a browser; :func:`ask_tab` wires
it to Gradio.
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
EMPTY = "Ask Lerni anything, or pick a topic."  # no fine print in the family prototype
MAX_AT_ONCE = 4  # answers streaming at the same time, across the household


def topic_choices(store: PlanStore, viewer: Viewer | None) -> list[tuple[str, str]]:
    """ "Anything", then the plans this viewer may use: all for educators, else examples."""
    if viewer is not None and viewer.educator:
        plans = plan_choices(store)
    else:
        plans = [(f"{p.interest} (example)", p.plan_id) for p in store.list_plans() if p.is_example]
    return [(ANYTHING, ANYTHING), *plans]


def _topic(store: PlanStore, viewer: Viewer, plan_id: str | None) -> LearningPlan | None:
    if not plan_id or plan_id == ANYTHING:
        return None
    # the id comes from the page, so check it against what this viewer may use
    if plan_id not in {pid for _, pid in topic_choices(store, viewer)}:
        raise ConversationError("That topic isn't available. Pick another.")
    try:
        return store.get(plan_id)
    except PlanError:
        raise ConversationError("That topic isn't available. Pick another.") from None


def ask_reply(
    conversations: Conversations,
    store: PlanStore,
    viewer: Viewer | None,
    text: str,
    plan_id: str | None,
    supervised_voice: bool = False,
) -> Iterator[str]:
    """Answer an independent student's question, a piece at a time.

    Raises:
        NotAllowed: The viewer isn't a signed-in independent student.
        ConversationError: Empty, too long, a topic they can't use, or a reply is still coming.
        ConversationUnavailable: Claude didn't answer.
    """
    v = require(viewer, Role.INDEPENDENT)
    # educators can try the supervised-student voice; everyone else gets their own kind's
    voice = "supervised" if supervised_voice and v.educator else "independent"
    yield from conversations.ask(v.username, text, _topic(store, v, plan_id), voice)


def messages(conversations: Conversations, username: str) -> list[dict[str, str]]:
    """``username``'s conversation in the Chatbot's format."""
    return [{"role": t.role, "content": t.text} for t in conversations.history(username)]


def ask_tab(
    signin: SignIn, store: PlanStore, conversations: Conversations | None
) -> tuple[gr.Tab, gr.Dropdown, gr.Chatbot, gr.Checkbox]:
    """The Ask tab (hidden for everyone but independent students)."""
    ready = conversations is not None
    with gr.Tab("Ask", id="ask", visible=False) as tab:
        if not ready:
            gr.Markdown("Claude isn't set up on this server yet.")
        # phone first: the chat grows with its messages, so the question box stays near the top
        with gr.Row():
            topic = gr.Dropdown(label="Topic", choices=[], value=None, scale=3)  # filled on load
            voice = gr.Checkbox(label="Try the supervised-student voice", visible=False, scale=1)
        # no toolbar or like buttons: one way to start over, below
        chat = gr.Chatbot(
            label="Ask Lerni",
            show_label=False,
            height=None,  # grows with its messages...
            min_height=120,
            max_height="55dvh",  # ...up to about half the visible screen, then scrolls
            placeholder=EMPTY,
            buttons=[],
            feedback_options=None,
            elem_id="lerni-ask-chat",
        )
        with gr.Row():
            question = gr.Textbox(
                label="Question",
                show_label=False,
                placeholder="Ask anything…",
                lines=1,
                max_lines=4,  # grows as they type; Enter still sends
                max_length=2000,
                scale=4,
                container=False,  # no frame around the box: more room to type on a phone
                interactive=ready,
            )
            # one button: Send, which becomes Stop while Lerni answers
            send = gr.Button("Send", variant="primary", scale=1, min_width=70, interactive=ready)
            stop = gr.Button("Stop", variant="stop", scale=1, min_width=70, visible=False)
        new = gr.Button("New conversation", size="sm")
        asked = gr.State("")  # the question being answered, so the box can be freed at once
        controls = [question, send, stop]  # order matches start and unlock

        def start(text: str) -> list[Any]:
            # take the question once: empty and lock the box, and swap Send for Stop
            locked = gr.update(value="", interactive=False)
            return [locked, gr.update(visible=False), gr.update(visible=True), text]

        def on_send(
            text: str, plan_id: str | None, supervised_voice: bool, request: gr.Request
        ) -> Iterator[list[Any]]:
            viewer = signin.viewer(request.username)  # re-read on every question
            if not ready or viewer is None or viewer.role is not Role.INDEPENDENT:
                yield [gr.update(), gr.update()]
                return
            # show the question right away, with an answer that fills as it streams
            shown = messages(conversations, viewer.username)
            shown += [{"role": "user", "content": text}, {"role": "assistant", "content": "…"}]
            yield [shown, gr.update()]
            answer = ""
            try:
                for piece in ask_reply(
                    conversations, store, viewer, text, plan_id, supervised_voice
                ):
                    answer += piece
                    shown[-1]["content"] = answer
                    yield [shown, gr.update()]  # only the answer changes
            except (ConversationError, ConversationUnavailable) as exc:
                # keep any partial answer, and put the question back to send again
                shown[-1]["content"] = f"{answer}\n\n⚠️ {exc}" if answer else f"⚠️ {exc}"
                yield [shown, gr.update(value=text)]

        def unlock() -> list[Any]:
            # the answer ended: free the box, and Stop turns back into Send
            return [gr.update(interactive=ready), gr.update(visible=True), gr.update(visible=False)]

        def on_new(request: gr.Request) -> list[Any]:
            viewer = signin.viewer(request.username)
            if ready and viewer is not None:
                conversations.clear(viewer.username)
            return [[], *unlock()]

        # Send or Enter: one event, so a click then Enter can't race
        answering = gr.on(
            [send.click, question.submit], start, question, [*controls, asked], **PRIVATE
        ).then(
            on_send,
            [asked, topic, voice],
            [chat, question],
            concurrency_limit=MAX_AT_ONCE,
            **PRIVATE,
        )
        answering.then(unlock, None, controls, **PRIVATE)
        # Stop keeps what was said so far; New conversation forgets it, even mid-answer
        stop.click(unlock, None, controls, cancels=[answering], **PRIVATE)
        new.click(on_new, None, [chat, *controls], cancels=[answering], **PRIVATE)
    return tab, topic, chat, voice
