"""The conversation for both kinds of student: an independent student's Ask tab, and a
supervised student's whole screen.

:func:`ask_reply` is a plain function over the server-resolved viewer, so the
role check can be tested without a browser; :func:`ask_tab` wires it to Gradio.
Their map reaches Claude through :class:`Conversations`, never from the page.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from typing import Any

import gradio as gr

from lerni.student.conversation import (
    ConversationError,
    Conversations,
    ConversationUnavailable,
)
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.voice import (
    SPOKE_NOTHING,
    ClipRefused,
    Speech,
    SpeechUnavailable,
    heard,
    spoken_reply,
)
from lerni.student.web.accounts import PRIVATE, require

EMPTY = "Ask Lerni anything."  # no fine print in the family prototype
SUPERVISED_EMPTY = "Hi! What would you like to talk about?"
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


def talk_reply(
    conversations: Conversations,
    speech: Speech,
    viewer: Viewer | None,
    clip_b64: str,
    supervised_voice: bool = False,
) -> tuple[str, Iterator[tuple[str, bytes | None]]]:
    """Hear a spoken question, then answer it a piece at a time with audio per sentence.

    Raises:
        NotAllowed: Nobody is signed in (checked before anything is heard).
        ClipRefused, SpeechUnavailable: Nothing usable was heard.
    """
    require(viewer, Role.INDEPENDENT, Role.SUPERVISED)
    text = heard(speech, clip_b64)
    return text, spoken_reply(speech, ask_reply(conversations, viewer, text, supervised_voice))


def talk_preview(speech: Speech, viewer: Viewer | None, clip_b64: str) -> str:
    """What has been heard so far while the button is held; "" if nothing usable.

    Raises:
        NotAllowed: Nobody is signed in.
    """
    require(viewer, Role.INDEPENDENT, Role.SUPERVISED)
    try:
        return heard(speech, clip_b64)
    except (ClipRefused, SpeechUnavailable):
        return ""


def messages(conversations: Conversations, username: str) -> list[dict[str, str]]:
    """``username``'s conversation in the Chatbot's format."""
    return [{"role": t.role, "content": t.text} for t in conversations.history(username)]


def ask_tab(
    signin: SignIn,
    conversations: Conversations | None,
    supervised: bool = False,
    speech: Speech | None = None,
) -> tuple[gr.Tab, gr.Chatbot, gr.Checkbox]:
    """Ask (independent students) or, with ``supervised``, a supervised student's whole screen.

    With ``speech``, a Hold to talk button too (the browser side is ``talk.js``).
    """
    ready = conversations is not None
    label, tab_id = ("Lerni", "home") if supervised else ("Ask", "ask")
    with gr.Tab(label, id=tab_id, visible=False) as tab:
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
            placeholder=SUPERVISED_EMPTY if supervised else EMPTY,
            buttons=[],
            feedback_options=None,
            elem_id="lerni-home-chat" if supervised else "lerni-ask-chat",
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
        talks = speech is not None and ready
        if talks:
            suffix = "home" if supervised else "ask"  # talk.js finds each panel's parts by id
            gr.Button("🎤 Hold to talk", elem_id=f"lerni-talk-{suffix}", size="lg")
            preview = gr.Markdown(elem_id=f"lerni-preview-{suffix}")  # what's heard so far
            # hidden fields and buttons the browser script fills and presses
            hide = {"elem_classes": "lerni-hide", "container": False}
            clip = gr.Textbox(elem_id=f"lerni-clip-{suffix}", **hide)
            partial = gr.Textbox(elem_id=f"lerni-partial-{suffix}", **hide)
            spoken = gr.Textbox(elem_id=f"lerni-spoken-{suffix}", **hide)
            heard_btn = gr.Button(elem_id=f"lerni-heard-{suffix}", elem_classes="lerni-hide")
            peek = gr.Button(elem_id=f"lerni-peek-{suffix}", elem_classes="lerni-hide")
        # the supervised screen keeps only the chat, the box, and Send/Stop
        new = gr.Button("New conversation", size="sm", visible=not supervised)
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
        events = [answering]

        if talks:

            def on_peek(b64: str, request: gr.Request) -> str:
                viewer = signin.viewer(request.username)
                return f"🎤 {talk_preview(speech, viewer, b64)}" if viewer else ""

            def on_talk(
                b64: str, supervised_voice: bool, request: gr.Request
            ) -> Iterator[list[Any]]:
                viewer = signin.viewer(request.username)  # re-read on every clip
                if viewer is None:  # the role check lives in talk_reply
                    yield [gr.update(), gr.update(), ""]
                    return
                shown = messages(conversations, viewer.username)
                try:
                    text, reply = talk_reply(conversations, speech, viewer, b64, supervised_voice)
                except (ClipRefused, SpeechUnavailable) as exc:
                    yield [shown + [{"role": "assistant", "content": f"⚠️ {exc}"}],
                           gr.update(), ""]
                    return
                shown += [{"role": "user", "content": text}, {"role": "assistant", "content": "…"}]
                yield [shown, gr.update(), ""]
                answer, sent = "", 0
                try:
                    for piece, audio in reply:
                        answer += piece
                        shown[-1]["content"] = answer or "…"
                        if audio:
                            sent += 1  # a new value each time, so the page always plays it
                            yield [shown, json.dumps([sent, base64.b64encode(audio).decode()]), ""]
                        else:
                            yield [shown, gr.update(), ""]
                    if answer and not sent:  # text came, but no voice at all
                        shown[-1]["content"] += f"\n\n🔇 {SPOKE_NOTHING}"
                except (ConversationError, ConversationUnavailable) as exc:
                    shown[-1]["content"] = f"{answer}\n\n⚠️ {exc}" if answer else f"⚠️ {exc}"
                yield [shown, gr.update(), ""]

            def lock() -> list[Any]:
                # like Send: lock the box and show Stop while Lerni answers
                return [gr.update(interactive=False), gr.update(visible=False),
                        gr.update(visible=True)]

            # only the newest preview runs; older ones are dropped
            peek.click(on_peek, partial, preview, trigger_mode="always_last", **PRIVATE)
            talking = heard_btn.click(lock, None, controls, **PRIVATE).then(
                on_talk,
                [clip, voice],
                [chat, spoken, preview],
                concurrency_limit=MAX_AT_ONCE,
                **PRIVATE,
            )
            talking.then(unlock, None, controls, **PRIVATE)
            spoken.change(None, spoken, None, js="(v) => { window.lerniTalk?.play(v); }")
            events.append(talking)
            # Stop and New conversation silence the voice too
            for button in (stop, new):
                button.click(None, None, None, js="() => { window.lerniTalk?.stop(); }")

        # Stop keeps what was said so far; New conversation forgets it, even mid-answer
        stop.click(unlock, None, controls, cancels=events, **PRIVATE)
        new.click(on_new, None, [chat, *controls], cancels=events, **PRIVATE)
    return tab, chat, voice
