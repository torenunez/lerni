"""The conversation for both kinds of student: an independent student's Chat tab, and a
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


def typed_reply(
    conversations: Conversations,
    speech: Speech | None,
    viewer: Viewer | None,
    text: str,
    supervised_voice: bool = False,
) -> Iterator[tuple[str, bytes | None]]:
    """Answer a typed question a piece at a time; with ``speech``, aloud too.

    Raises:
        NotAllowed, ConversationError, ConversationUnavailable: as :func:`ask_reply`.
    """
    pieces = ask_reply(conversations, viewer, text, supervised_voice)
    return spoken_reply(speech, pieces) if speech else ((p, None) for p in pieces)


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


def _clip(count: int, audio: bytes) -> str:
    """A spoken sentence for the page: ``[count, base64]``, new each time so it always plays."""
    return json.dumps([count, base64.b64encode(audio).decode()])


def messages(conversations: Conversations, username: str) -> list[dict[str, str]]:
    """``username``'s conversation in the Chatbot's format."""
    return [{"role": t.role, "content": t.text} for t in conversations.history(username)]


def ask_tab(
    signin: SignIn,
    conversations: Conversations | None,
    supervised: bool = False,
    speech: Speech | None = None,
) -> tuple[gr.Tab, gr.Chatbot, gr.Checkbox]:
    """Chat (independent students) or, with ``supervised``, a supervised student's whole screen.

    With ``speech``, a Hold to talk button too (the browser side is ``talk.js``).
    """
    ready = conversations is not None
    label, tab_id = ("Chat", "home") if supervised else ("Chat", "ask")
    with gr.Tab(label, id=tab_id, visible=False) as tab:
        if not ready:
            gr.Markdown("Claude isn't set up on this server yet.")
        voice = gr.Checkbox(label="Try the supervised-student voice", visible=False)
        # no toolbar or like buttons: one way to start over, below
        chat = gr.Chatbot(
            label="Chat with Lerni",
            show_label=False,
            height=None,  # the page's style fills the screen above the dock
            max_height=None,
            placeholder=SUPERVISED_EMPTY if supervised else EMPTY,
            buttons=[],
            feedback_options=None,
            elem_id="lerni-home-chat" if supervised else "lerni-ask-chat",
        )
        talks = speech is not None and ready
        suffix = "home" if supervised else "ask"  # talk.js finds each panel's parts by id
        # the dock at the bottom: with voice, a big talk button or typing, chosen by a toggle
        with gr.Column(
            elem_id=f"lerni-dock-{suffix}",
            elem_classes="lerni-dock lerni-voice" if talks else "lerni-dock",
        ):
            if talks:
                preview = gr.Markdown(elem_id=f"lerni-preview-{suffix}")  # what's heard so far
                gr.Button(
                    "🎤\nHold to talk", elem_id=f"lerni-talk-{suffix}", elem_classes="lerni-talk"
                )
            with gr.Row(elem_classes="lerni-type"):
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
                    elem_id=f"lerni-question-{suffix}",
                )
                # one button: Send, which becomes Stop while Lerni answers
                send = gr.Button(
                    "Send",
                    variant="primary",
                    scale=1,
                    min_width=70,
                    interactive=ready,
                    elem_id=f"lerni-send-{suffix}",
                )
                stop = gr.Button("Stop", variant="stop", scale=1, min_width=70, visible=False)
            if talks:
                # Talk or Type; talk.js switches the dock and remembers the choice on this device
                gr.HTML(
                    '<div class="lerni-mode" role="group" aria-label="Talk or type">'
                    '<button type="button" data-mode="talk">🎤 Talk</button>'
                    '<button type="button" data-mode="type">⌨️ Type</button></div>'
                )
                # hidden fields and buttons the browser script fills and presses
                hide = {"elem_classes": "lerni-hide", "container": False}
                clip = gr.Textbox(elem_id=f"lerni-clip-{suffix}", **hide)
                partial = gr.Textbox(elem_id=f"lerni-partial-{suffix}", **hide)
                spoken = gr.Textbox(elem_id=f"lerni-spoken-{suffix}", **hide)
                heard_btn = gr.Button(elem_id=f"lerni-heard-{suffix}", elem_classes="lerni-hide")
                peek = gr.Button(elem_id=f"lerni-peek-{suffix}", elem_classes="lerni-hide")
                hush = gr.Button(elem_id=f"lerni-hush-{suffix}", elem_classes="lerni-hide")
        # the supervised screen has no way to start over; Chat does
        new = gr.Button("New conversation", size="sm", visible=not supervised)
        asked = gr.State("")  # the question being answered, so the box can be freed at once
        controls = [question, send, stop]  # order matches start and unlock

        def start(text: str) -> list[Any]:
            # take the question once: empty and lock the box, and swap Send for Stop
            locked = gr.update(value="", interactive=False)
            return [locked, gr.update(visible=False), gr.update(visible=True), text]

        def on_send(text: str, supervised_voice: bool, request: gr.Request) -> Iterator[list[Any]]:
            same = [gr.update()] * talks  # with voice, the spoken field is an output too
            viewer = signin.viewer(request.username)  # re-read on every question
            if not ready or viewer is None:  # the role check lives in ask_reply
                yield [gr.update(), gr.update(), *same]
                return
            # show the question right away, with an answer that fills as it streams
            shown = messages(conversations, viewer.username)
            shown += [{"role": "user", "content": text}, {"role": "assistant", "content": "…"}]
            yield [shown, gr.update(), *same]
            # with voice on, typed questions are answered aloud too
            reply = typed_reply(conversations, speech if talks else None, viewer, text,
                                supervised_voice)
            answer, sent = "", 0
            try:
                for piece, audio in reply:
                    answer += piece
                    shown[-1]["content"] = answer or "…"
                    if audio:
                        sent += 1  # a new value each time, so the page always plays it
                        yield [shown, gr.update(), _clip(sent, audio)]
                    else:
                        yield [shown, gr.update(), *same]  # only the answer changes
                if talks and answer and not sent:  # text came, but no voice at all
                    shown[-1]["content"] += f"\n\n🔇 {SPOKE_NOTHING}"
                    yield [shown, gr.update(), *same]
            except (ConversationError, ConversationUnavailable) as exc:
                # keep any partial answer, and put the question back to send again
                shown[-1]["content"] = f"{answer}\n\n⚠️ {exc}" if answer else f"⚠️ {exc}"
                yield [shown, gr.update(value=text), *same]
            finally:
                reply.close()  # Stop: frees the conversation for the next question

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
            [chat, question, spoken] if talks else [chat, question],
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
                    yield [shown + [{"role": "assistant", "content": f"⚠️ {exc}"}], gr.update(), ""]
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
                            yield [shown, _clip(sent, audio), ""]
                        else:
                            yield [shown, gr.update(), ""]
                    if answer and not sent:  # text came, but no voice at all
                        shown[-1]["content"] += f"\n\n🔇 {SPOKE_NOTHING}"
                except (ConversationError, ConversationUnavailable) as exc:
                    shown[-1]["content"] = f"{answer}\n\n⚠️ {exc}" if answer else f"⚠️ {exc}"
                finally:
                    reply.close()  # interrupted: frees the conversation for the next question
                yield [shown, gr.update(), ""]

            def lock() -> list[Any]:
                # like Send: lock the box and show Stop while Lerni answers
                return [
                    gr.update(interactive=False),
                    gr.update(visible=False),
                    gr.update(visible=True),
                ]

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
        if talks:
            # pressing the talk button stops any answer, like Stop (the page presses hush)
            hush.click(unlock, None, controls, cancels=events, **PRIVATE)
    return tab, chat, voice
