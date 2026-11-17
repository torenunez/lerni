"""Spelling (v4.10): the student's screen, and the educator's fold on the student's page.

Handlers re-read the viewer on every request. The page never holds the word: it shows
"word 2 of 5" and plays the clip; a typed answer goes to the server, which grades it and
keeps only whether it was right and the kind of mistake (rule 6).
"""

from __future__ import annotations

import base64
import html
import json
import time
from difflib import SequenceMatcher
from typing import Any

import gradio as gr

from lerni.student.points import PointsStore
from lerni.student.signin import SignIn, Viewer
from lerni.student.spelling import (
    MAX_TYPED,
    MISTAKES,
    PERFECT_BONUS,
    WORDS_PER_ROUND,
    SpellingDesk,
    SpellingUnavailable,
    Turn,
)
from lerni.student.students import StudentStore
from lerni.student.web.accounts import PRIVATE, NotAllowed, require_educator
from lerni.student.web.ask import MAX_AT_ONCE
from lerni.student.web.games import require_player, stars
from lerni.student.web.maps import map_owner

UNLOCK = "() => { window.lerniTalk?.unlock(); }"  # a tap unlocks sound (iPad Safari)
# a clip arrives: played unless the 🔊 switch is off (race.js keeps it on this device)
PLAY = (
    "(v) => { let on = true; try { on = localStorage.getItem('lerni-sound') !== 'off'; }"
    " catch {} if (on) window.lerniTalk?.say(v); }"
)
INTRO = "Hear a word, then type it. 🔊 says it again."


def _card(number: int, total: int) -> str:
    return (
        f'<div class="lerni-spell-card"><p class="lerni-spell-count">word {number + 1} of '
        f"{total}</p><p>Type the word you hear</p></div>"
    )


def _spelled(word: str, typed: str) -> str:
    # the right spelling, marking only the letters the typed one lacks (on screen only)
    match = SequenceMatcher(None, typed.strip().casefold(), word.casefold(), autojunk=False)
    kept = {j for _, b, size in match.get_matching_blocks() for j in range(b, b + size)}
    marks = "".join(
        html.escape(c) if i in kept else f"<mark>{html.escape(c)}</mark>"
        for i, c in enumerate(word)
    )  # "fosil": only fossil's second s
    return f'<span class="lerni-spell-word">{marks}</span>'


def feedback(turn: Turn, typed: str) -> str:
    """The line after an answer: ✓ and ⭐, or the right spelling and when it comes back."""
    if turn.right:
        star = f" +{turn.awarded} ⭐" if turn.awarded else ""
        parts = (
            f'<p class="lerni-spell-parts">{" · ".join(map(html.escape, turn.parts))}</p>'
            if turn.parts
            else ""
        )
        return (
            f'<div class="lerni-spell-card"><p class="lerni-spell-right">✓ '
            f"{html.escape(turn.word)}{star}</p>{parts}</div>"
        )
    shown = html.escape(" ".join(typed.split())[:MAX_TYPED]) or "nothing"
    return (
        f'<div class="lerni-spell-card"><p>You wrote <code>{shown}</code></p>'
        f"<p>It's {_spelled(turn.word, typed)}</p><p>It comes back tomorrow.</p></div>"
    )


def finish(right: int, awarded: int) -> str:
    """The round's end: how many right and the ⭐."""
    bonus = (  # a nudge toward the perfect round, unless they just made one
        ""
        if right == WORDS_PER_ROUND
        else f"<p>All {WORDS_PER_ROUND} right gives +{PERFECT_BONUS} more</p>"
    )
    star = f"<p>+{awarded} ⭐</p>" if awarded else ""  # no line when nothing was added
    return (
        f'<div class="lerni-spell-card"><p class="lerni-spell-score">{right} of '
        f"{WORDS_PER_ROUND}</p>{star}{bonus}</div>"
    )


def spelling_tab(signin: SignIn, desk: SpellingDesk, header_stars: gr.Button | None = None,
                 points: PointsStore | None = None) -> gr.Tab:
    """The Spelling section: Start, hear a word, type it, Check, Next, the round's score."""
    with gr.Tab("Spelling", id="spelling", visible=False) as tab:
        note = gr.Markdown(INTRO)  # the intro, or why a round can't start
        card = gr.HTML()  # "word 2 of 5": never the word itself
        hear = gr.Button("🔊 Hear it again", visible=False)  # a replay costs nothing
        with gr.Row(elem_classes="lerni-type"):
            typed = gr.Textbox(
                show_label=False,
                elem_id="lerni-spell",  # race.js turns autocorrect and the rest off
                lines=1,
                max_lines=1,
                max_length=MAX_TYPED,
                container=False,
                visible=False,  # shown with each word
                scale=4,
            )
            check = gr.Button("Check", variant="primary", visible=False, scale=1, min_width=80)
        result = gr.HTML()  # ✓, or the right spelling, then the round's score
        go = gr.Button("Start", variant="primary")  # "Start again" after a round
        nxt = gr.Button("Next", variant="primary", visible=False)  # after each answer
        clip = gr.Textbox(elem_classes="lerni-hide", container=False)  # for talk.js to play
        shown = gr.State(("", 0))  # the round and the word on screen

        def viewer_of(request: gr.Request) -> Viewer | None:
            try:
                return require_player(signin.viewer(request.username))  # re-read every time
            except NotAllowed:
                return None  # not a supervised student or an educator

        def asking(round_id: str, number: int, total: int) -> list[Any]:
            # a word on screen: the field empty and ready, Check showing, Next and Start hidden
            return [
                "",  # note
                _card(number, total),
                gr.update(visible=True),  # 🔊
                gr.update(value="", visible=True),  # the answer field
                gr.update(visible=True),  # Check
                "",  # last word's result cleared
                gr.update(visible=False),  # Start
                gr.update(visible=False),  # Next
                (round_id, number),
            ]

        outputs = [note, card, hear, typed, check, result, go, nxt, shown]  # every handler's order

        def on_start(request: gr.Request) -> list[Any]:
            viewer = viewer_of(request)
            if viewer is None:  # the rest of the screen stays as it is
                return ["Spelling isn't on for this account.", *(gr.update() for _ in range(8))]
            try:
                r = desk.start(viewer.username)  # may wait for Lerni's first words
            except SpellingUnavailable as exc:
                return [str(exc), *(gr.update() for _ in range(8))]  # "try again in a minute"
            return asking(r.id, 0, len(r.words))  # the first word

        def on_check(text: str, ref: tuple[str, int], request: gr.Request) -> list[Any]:
            viewer = viewer_of(request)
            if viewer is None or not ref[0]:
                return [gr.update() for _ in outputs]  # no round: nothing to grade
            if not text.strip():  # nothing typed: ask again, nothing graded
                return ["Type the word first.", *(gr.update() for _ in range(8))]
            turn = desk.answer(viewer.username, ref[0], ref[1], text)
            if turn is None:  # a double tap, or an old round: nothing changes
                return [gr.update() for _ in outputs]
            r = desk.current(viewer.username)
            line = feedback(turn, text)
            if turn.done and r is not None:  # the fifth word: the score below it
                line += finish(sum(r.marks), r.awarded)
            # the answer box clears at once: what was typed lives only in this line
            return [
                "",  # note
                gr.update(),  # the card stays
                gr.update(visible=False),  # 🔊
                gr.update(value="", visible=False),  # the answer field, emptied
                gr.update(visible=False),  # Check
                line,
                gr.update(visible=turn.done, value="Start again"),  # after the last word
                gr.update(visible=not turn.done),  # Next, otherwise
                (ref[0], ref[1] + 1),  # the next word's number
            ]

        def on_next(ref: tuple[str, int], request: gr.Request) -> list[Any]:
            viewer = viewer_of(request)
            r = desk.current(viewer.username) if viewer is not None else None
            if r is None or r.id != ref[0] or ref[1] >= len(r.words):
                return [gr.update() for _ in outputs]  # an old page or a new round elsewhere
            return asking(r.id, ref[1], len(r.words))

        def on_speak(ref: tuple[str, int], request: gr.Request) -> Any:
            viewer = viewer_of(request)
            if viewer is None or not ref[0]:
                return gr.update()
            audio = desk.read_word(viewer.username, ref[0], ref[1])
            if not audio:
                return gr.update()  # the voice failed: the word stays unspoken
            return json.dumps([time.monotonic(), base64.b64encode(audio).decode()])  # replays

        speak = {  # one reading, chained after Start and Next, or on 🔊
            "fn": on_speak,
            "inputs": shown,
            "outputs": clip,
            "concurrency_limit": MAX_AT_ONCE,
            **PRIVATE,
        }
        for button in (go, nxt, hear, check):  # each tap unlocks sound for the reading
            button.click(None, js=UNLOCK)
        go.click(on_start, None, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE).then(**speak)
        nxt.click(on_next, shown, outputs, **PRIVATE).then(**speak)
        hear.click(**speak)
        def header(request: gr.Request) -> Any:  # the header's ⭐ after a word pays
            viewer = viewer_of(request)
            return stars(points, viewer) if points is not None and viewer else gr.update()

        for trigger in (check.click, typed.submit):  # Return checks too
            checked = trigger(on_check, [typed, shown], outputs, concurrency_limit=MAX_AT_ONCE,
                              **PRIVATE)
            if header_stars is not None:
                checked.then(header, None, header_stars, **PRIVATE)
        clip.change(None, clip, None, js=PLAY)  # a new clip plays in the browser
        tab.select(None, js=UNLOCK)  # opening Spelling is a tap too
    return tab


def _summary_md(s: dict[str, Any]) -> str:
    # the educator's lines: level and counts, the words missed most, and kinds of mistakes
    missed = " · ".join(f"{html.escape(w)} {n}" for w, n in s["missed"]) or "none yet"
    kinds = " · ".join(f"{MISTAKES.get(k, k)} {n}" for k, n in s["mistakes"]) or "none yet"
    return (
        f"Level {s['level']} · {len(s['practice'])} words in practice · "
        f"{s['learned']} learned\n\n**Missed most:** {missed}\n\n**Kinds of mistakes:** "
        f"{kinds}"
    )


def spelling_fold(
    signin: SignIn, students: StudentStore, desk: SpellingDesk, who: gr.Dropdown, tab: gr.Tab
) -> None:
    """The educator's Spelling fold on the student's page (inside its tab's layout)."""
    with gr.Accordion("Spelling", open=False):
        box = gr.Textbox(
            label="This week's class list, one word per line",
            lines=4,
            max_lines=12,
            max_length=1200,  # about 40 words
        )
        save = gr.Button("Save list", min_width=90)
        status = gr.Markdown()  # saved, skipped, or why not
        stats = gr.Markdown()  # level, missed most, kinds of mistakes
        words = gr.CheckboxGroup(label="Words in practice (tick to remove)", choices=[])
        remove = gr.Button("Remove ticked", min_width=90)

    def student(requested: str | None, request: gr.Request) -> str:
        # checked again on every request, as for every change on this page
        return map_owner(
            students, require_educator(signin.viewer(request.username)), requested or ""
        )

    def show(requested: str | None, request: gr.Request) -> list[Any]:
        try:
            s = desk.summary(student(requested, request))
        except NotAllowed:
            return ["", "", gr.update(choices=[], value=[])]  # no student picked: empty
        return ["\n".join(s["class"]), _summary_md(s), gr.update(choices=s["practice"], value=[])]

    def on_save(text: str, requested: str | None, request: gr.Request) -> list[Any]:
        try:
            n, carried, refused = desk.set_class_list(student(requested, request), text)
        except (NotAllowed, SpellingUnavailable) as exc:  # the typed list stays to try again
            return [gr.update(), f"⚠️ {exc}", gr.update(), gr.update()]
        line = f"✅ Saved {n} words." + (
            f" {carried} still-missed words carried over." if carried else ""
        )
        if refused:  # name a few, so the educator can fix them
            line += " Skipped (one word per line, letters only): " + ", ".join(refused[:5])
        box_text, summary, practice = show(requested, request)  # the list as now saved
        return [box_text, line, summary, practice]

    def on_remove(picked: list[str], requested: str | None, request: gr.Request) -> list[Any]:
        if not picked:
            return [gr.update(), "⚠️ Tick one first.", gr.update(), gr.update()]
        try:
            gone = desk.remove(student(requested, request), picked)  # for good
        except (NotAllowed, SpellingUnavailable) as exc:
            return [gr.update(), f"⚠️ {exc}", gr.update(), gr.update()]
        box_text, summary, practice = show(requested, request)
        return [box_text, f"Removed {gone}.", summary, practice]

    out = [box, stats, words]
    who.change(show, who, out, **PRIVATE)  # the student picked: their words
    tab.select(show, who, out, **PRIVATE)  # and fresh counts each time the page opens
    save.click(on_save, [box, who], [box, status, stats, words], **PRIVATE)
    remove.click(on_remove, [words, who], [box, status, stats, words], **PRIVATE)
