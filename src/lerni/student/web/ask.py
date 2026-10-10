"""The conversation for both kinds of student: an independent student's Ask tab, and a
supervised student's whole screen.

:func:`ask_reply` is a plain function over the server-resolved viewer, so the
role check can be tested without a browser; :func:`ask_tab` wires it to Gradio.
Their map reaches Claude through :class:`Conversations`, never from the page.
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
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.web.accounts import PRIVATE, require

EMPTY = "Ask Lerni anything."  # no fine print in the family prototype
MAX_AT_ONCE = 4  # answers streaming at the same time, across the household


def ask_reply(
    conversations: Conversations,
    viewer: Viewer | None,
    text: str,
    supervised_voice: bool = False,
) -> Iterator[str]:
    """Answer a student's question, a piece at a time.

    A supervised student always gets the supervised voice; an educator can try it.

    Raises:
        NotAllowed: Nobody is signed in.
        ConversationError: Empty, too long, or a reply is still coming.
        ConversationUnavailable: Claude didn't answer.
    """
    v = require(viewer, Role.INDEPENDENT, Role.SUPERVISED)
    supervised = v.role is Role.SUPERVISED or (supervised_voice and v.educator)
    yield from conversations.ask(v.username, text, "supervised" if supervised else "independent")


def messages(conversations: Conversations, username: str) -> list[dict[str, str]]:
    """``username``'s conversation in the Chatbot's format."""
    return [{"role": t.role, "content": t.text} for t in conversations.history(username)]


def ask_tab(
    signin: SignIn, conversations: Conversations | None
) -> tuple[gr.Tab, gr.Chatbot, gr.Checkbox]:
    """The Ask tab (hidden for everyone but independent students)."""
    ready = conversations is not None
    with gr.Tab("Ask", id="ask", visible=False) as tab:
        if not ready:
            gr.Markdown("Claude isn't set up on this server yet.")
        # phone first: the chat grows with its messages, so the question box stays near the top
        voice = gr.Checkbox(label="Try the supervised-student voice", visible=False)
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
            text: str, supervised_voice: bool, request: gr.Request
        ) -> Iterator[list[Any]]:
            viewer = signin.viewer(request.username)  # re-read on every question
            if not ready or viewer is None:  # the role check lives in ask_reply
                yield [gr.update(), gr.update()]
                return
            # show the question right away, with an answer that fills as it streams
            shown = messages(conversations, viewer.username)
            shown += [{"role": "user", "content": text}, {"role": "assistant", "content": "…"}]
            yield [shown, gr.update()]
            answer = ""
            try:
                for piece in ask_reply(conversations, viewer, text, supervised_voice):
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
            [asked, voice],
            [chat, question],
            concurrency_limit=MAX_AT_ONCE,
            **PRIVATE,
        )
        answering.then(unlock, None, controls, **PRIVATE)
        # Stop keeps what was said so far; New conversation forgets it, even mid-answer
        stop.click(unlock, None, controls, cancels=[answering], **PRIVATE)
        new.click(on_new, None, [chat, *controls], cancels=[answering], **PRIVATE)
    return tab, chat, voice
