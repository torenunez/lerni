"""Games: race two rival cars by answering questions, and spend points on cars (spec 09).

Handlers are plain functions over the server-resolved viewer, so role checks can be
tested without a browser. The page never holds an answer: a tap sends the race id,
the question number, and which button, and the server decides.
"""

from __future__ import annotations

import base64
import html
import json
import time
from collections.abc import Callable
from datetime import date
from typing import Any

import gradio as gr

from lerni.student.garage import (
    Car,
    Garage,
    bolts,
    boost,
    car_card_svg,
    car_svg,
    family_cars,
    next_goal,
)
from lerni.student.interests import MapStore
from lerni.student.points import STARTER, Points, PointsError, PointsStore
from lerni.student.race import (
    BOT_RIVALS,
    MAX_ANSWER,
    NOT_READY,
    QUESTIONS_PER_RACE,
    STEP_RIGHT,
    Race,
    RaceDesk,
    RaceUnavailable,
    Turn,
    place,
    public,
)
from lerni.student.results import ResultsLog
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import StudentStore
from lerni.student.voice import ClipRefused, Speech, SpeechUnavailable, heard
from lerni.student.web.accounts import PRIVATE, NotAllowed
from lerni.student.web.ask import MAX_AT_ONCE, talk_preview
from lerni.student.web.maps import map_owner

LANES = (12, 55, 98)  # the student's lane, then the fast and slow rivals'
BOT_COLORS = {"Zippy": "#7F77DD", "Bolt": "#888780"}  # the bots' own paint
START, END = 8, 248  # a car's left edge at the start and at the finish, in track units
MAX_LABEL = 18  # characters of a car's name on the track
WAIT_LINE = "Pumping the tires… 🛞 New questions can take a minute to write."
SOUNDS = ("roar", "sputter", "finish")  # <data>/sounds/<name>.mp3, played by race.js
EDGE = ('<defs><filter id="lerni-edge" x="-10%" y="-10%" width="120%" height="120%">'
        '<feDropShadow dx="0" dy="0" stdDeviation="0.7" flood-color="#2C2C2A" '
        'flood-opacity="0.9"/></filter></defs>')  # a thin dark edge, so a white car shows
MUTE = ('<button type="button" id="lerni-mute" class="lerni-mute" '
        'aria-label="Sound on">🔊</button>')  # race.js handles it
READ = ('<button type="button" id="lerni-read" class="lerni-read" '
        'aria-pressed="false">📖 Read aloud: off</button>')  # race.js: each question reads itself
ORDINAL = {1: "1st", 2: "2nd", 3: "3rd"}
NO_CLAUDE = "Games need Claude, which isn't set up on this server."


def require_player(viewer: Viewer | None) -> Viewer:
    """Supervised students and educators play; refuse anyone else."""
    if viewer is None or not (viewer.role is Role.SUPERVISED or viewer.educator):
        raise NotAllowed("Games aren't on for this account yet.")
    return viewer


def stars(points: PointsStore, viewer: Viewer | None) -> str:
    """The ⭐ for the header: players only."""
    try:
        return f"⭐ {points.get(require_player(viewer).username).balance}"
    except NotAllowed:
        return ""


def start_race(desk: RaceDesk, viewer: Viewer | None, gas: float = 1.0, car: str = "",
               rivals: tuple[tuple[str, str], ...] = BOT_RIVALS) -> tuple[Race | None, str]:
    """A new race in this car with its gas boost, or why there can't be one."""
    try:
        v = require_player(viewer)
        return desk.start(v.username, supervised=v.role is Role.SUPERVISED, boost=gas,
                          car=car, rivals=rivals), ""
    except (NotAllowed, PointsError, RaceUnavailable) as exc:
        return None, str(exc)
    except Exception:  # never stuck on "Pumping the tires"
        return None, NOT_READY


def pick(desk: RaceDesk, viewer: Viewer | None, race_id: str, number: int,
         choice: int) -> tuple[Race | None, Turn | None, int]:
    """Answer the question on screen; the desk ignores stale or repeat taps."""
    return desk.pick(require_player(viewer).username, race_id, number, choice)


def garage_tap(points: PointsStore, garage: Garage, viewer: Viewer | None, car_id: str) -> str:
    """Drive a car they own, or buy it and drive it."""
    try:
        v, c = require_player(viewer), garage.car(car_id)
        owned = points.get(v.username).cars
        if c not in garage.sold(owned):
            return "⚠️ That car isn't sold here."
        if car_id not in owned:
            points.buy(v.username, car_id, c.price)
            points.drive(v.username, car_id)
            return f"🎉 The {c.name} is yours!"
        points.drive(v.username, car_id)
        return f"Driving the {c.name}."
    except (NotAllowed, PointsError) as exc:
        return f"⚠️ {exc}"
    except KeyError:
        return "⚠️ No such car."


def student_progress(points: PointsStore, garage: Garage, students: StudentStore,
                     viewer: Viewer | None, requested: str | None,
                     results: ResultsLog | None = None, maps: MapStore | None = None) -> str:
    """A supervised student's goal progress this week, grouped by area (the most practiced
    first, no area last), then ⭐ and the car they drive, as HTML for their educator ("" for
    anyone else)."""
    try:
        owner = map_owner(students, viewer, requested or "")
    except NotAllowed:
        return ""
    p = points.get(owner)
    week = results.week(owner, date.today()) if results else []
    m = maps.get(owner) if maps else None

    def area(goal_id: str, name: str) -> str:  # by id first, so a renamed goal keeps its area
        if m is None:
            return ""
        e = next((x for x in m.entries if goal_id and x.id == goal_id), None) or m.find(name)
        return e.area if e is not None and e.kind == "goal" else ""

    groups: dict[str, list[tuple[str, int, int]]] = {}
    for goal_id, goal, right, asked in week:
        if asked:
            groups.setdefault(area(goal_id, goal), []).append((goal, right, asked))
    order = sorted(groups, key=lambda a: (a == "", -sum(n for *_, n in groups[a])))
    rows = []
    for a in order:
        items = sorted(groups[a], key=lambda g: -g[2])
        if len(groups) > 1 or a:  # an area heading with its total, unless there are no areas
            right, asked = sum(g[1] for g in items), sum(g[2] for g in items)
            rows.append(f'<div class="lerni-week-area"><span>{html.escape(a or "Other")}</span>'
                        f'<span class="lerni-of">{right} of {asked}</span></div>')
        rows += [f'<div class="lerni-week-row"><span>{html.escape(goal)}</span>'
                 f'<span class="lerni-week-bar">'
                 f'<i style="width:{round(100 * right / asked)}%"></i></span>'
                 f'<span class="lerni-of">{right} of {asked}</span></div>'
                 for goal, right, asked in items]
    try:  # a car gone from the garage file gets no chip
        car = f'<span class="lerni-chip">🚗 {html.escape(garage.car(p.car).name)}</span>'
    except KeyError:
        car = ""
    body = "".join(rows) or '<p class="lerni-of">No races this week.</p>'
    return (f'<div class="lerni-week"><h3>Goal progress this week</h3>{body}'
            f'<div><span class="lerni-chip">⭐ {p.balance}</span>{car}</div></div>')


def rival_pairs(garage: Garage, p: Points) -> tuple[tuple[str, str], ...]:
    """The two rivals as (name, car id), fast lane first; a bot fills a lane with no car."""
    cars = garage.rivals(p.cars, p.car, p.balance)
    return tuple((c.name, c.id) if c else bot for c, bot in zip(cars, BOT_RIVALS, strict=True))


def _label(text: str, y: int) -> str:
    # a small name on a pill at the top-left of its lane, readable in either theme
    name = text if len(text) <= MAX_LABEL else text[:MAX_LABEL - 1] + "…"
    return (f'<rect x="2" y="{y - 10}" width="{len(name) * 4.6 + 6:.0f}" height="11" rx="5" '
            f'fill="#FFFFFF" fill-opacity="0.8"/><text x="5" y="{y - 2}" font-size="8" '
            f'fill="#085041">{html.escape(name)}</text>')


def track_svg(race: Race | None, car_id: str, garage: Garage, reads: bool = False) -> str:
    """The track: the student's car and two rivals, placed by how far each has come; under it
    🔇, and 📖 Read aloud when the server has a voice."""

    full = QUESTIONS_PER_RACE * STEP_RIGHT * (race.boost if race else 1.0)  # 5 right in this car

    def x(pos: float) -> float:  # nothing reaches the line before the fifth answer
        return START + min(pos, full) / full * (END - START)

    car_id = (race.car or car_id) if race else car_id  # the car it started in
    rivals = race.rivals if race else ()
    where = f"You're {ORDINAL[place(race)]}" if race and race.answered else "At the start line"
    parts = [f'<svg viewBox="0 0 320 130" width="100%" role="img" aria-label="{where}" '
             f'data-race="{html.escape(race.id if race else "")}" '
             f'data-step="{race.answered if race else 0}" data-right="{race.right if race else 0}" '
             f'data-total="{QUESTIONS_PER_RACE}" data-car="{html.escape(car_id)}">', EDGE,
             '<rect width="320" height="130" rx="8" fill="#E1F5EE"/>',
             '<line x1="0" y1="43" x2="320" y2="43" stroke="#9FE1CB" stroke-dasharray="6 6"/>',
             '<line x1="0" y1="86" x2="320" y2="86" stroke="#9FE1CB" stroke-dasharray="6 6"/>',
             f'<rect x="{END + 58}" y="0" width="6" height="130" fill="#444441"/>',  # finish line
             '<g filter="url(#lerni-edge)">', garage.svg(car_id, x(race.me if race else 0.0),
                                                          LANES[0], "me")]
    for rival, pos, y, lane in zip(rivals, race.at if race else (), LANES[1:], ("fast", "slow"),
                                   strict=False):  # no rivals at the start line
        if (rival.name, rival.car) in BOT_RIVALS:  # a bot, in its own paint
            parts.append(car_svg(rival.car, x(pos), y, lane, BOT_COLORS[rival.name]))
        else:
            parts.append(garage.svg(rival.car, x(pos), y, lane))
    parts.append("</g>")
    names = ("You", *(r.name for r in rivals))
    parts += [_label(name, y) for name, y in zip(names, LANES, strict=False)]
    switches = f'<div class="lerni-switches">{READ if reads else ""}{MUTE}</div>'
    return "".join(parts) + "</svg>" + switches


def _picture(c: Car) -> str:
    return (f'<img src="/cars/{c.id}" alt="{html.escape(c.name)}">' if c.picture
            else car_card_svg(c.id))


def _zap(c: Car) -> str:
    return f'<span class="lerni-zap" aria-label="speed {bolts(c)} of 5">{"⚡" * bolts(c)}</span>'


def card_html(c: Car, owned: bool = False, locked: bool = False) -> str:
    """One tile: the picture, the name, ⚡, the price while it's for sale, and Car facts.

    A car they can't afford yet (``locked``) shows only its picture, name, and price.
    """
    price = ""
    if not owned and c.usd:
        price = (f'<span class="lerni-usd">${c.usd:,}</span>'
                 f'<span class="lerni-like">{family_cars(c.usd)}</span>')
    hp = f"{c.power_hp:,} hp" if c.power_hp else ""
    secs = f"{c.zero_to_60:g} seconds" if c.zero_to_60 else ""
    facts = [f"{k}: {v}" for k, v in (("Engine", c.engine), ("Power", hp), ("Drive", c.drive),
                                      ("0–60 mph", secs)) if v]
    facts += [c.note] if c.note else []
    if c.usd:
        facts.append(f"${c.usd:,} ÷ $2,500 a star ≈ {c.price:,} ⭐")
    facts.append("More ⚡ moves your car farther with each right answer.")
    details = ("<details><summary>Car facts</summary>"
               + "".join(f"<div>{html.escape(f)}</div>" for f in facts) + "</details>")
    if locked:  # ⚡ and the facts are earned by saving up
        return f'<div class="lerni-card">{_picture(c)}<b>{html.escape(c.name)}</b>{price}</div>'
    return (f'<div class="lerni-card">{_picture(c)}<b>{html.escape(c.name)}</b>{_zap(c)}'
            f"{price}{details}</div>")


def goal_line(garage: Garage, p: Points) -> str:
    """The next car to save for, as one line ("" when nothing is left to get)."""
    goal, line = next_goal(garage.sold(p.cars), p.cars, p.balance)
    return f"Next car: {line}" if goal is not None and goal.price > p.balance else line


def hero_html(garage: Garage, p: Points | None) -> str:
    """The top of Games: the car they drive, big, and the next car to save for."""
    if p is None:
        return ""
    try:
        c = garage.car(p.car)
    except KeyError:  # gone from the garage file: the starter drives
        c = garage.car(STARTER)
    goal, _ = next_goal(garage.sold(p.cars), p.cars, p.balance)
    bar = ""
    if goal is not None and goal.price > p.balance:
        pct = min(100, p.balance * 100 // goal.price)
        bar = f'<div class="lerni-bar" aria-hidden="true"><span style="width:{pct}%"></span></div>'
    return (f'<div class="lerni-hero-car">{_picture(c)}</div>'
            f'<div class="lerni-hero-name"><b>{html.escape(c.name)}</b> {_zap(c)}</div>'
            f'<div class="lerni-goal">{html.escape(goal_line(garage, p))}{bar}</div>')


def after_tap(race: Race | None, ref: tuple[str, int], turn: Turn | None,
              awarded: int = 0, goal: str = "") -> tuple[Race | None, str] | None:
    """What an answer tap shows: the race and a line, or None when nothing changes (a repeat)."""
    if turn is not None:
        return race, _feedback(race, turn, awarded, goal) if race else ""
    if race is None or race.id != ref[0]:  # a restart or another screen ended it
        return None, "That race ended. Tap Race! 🏁"
    return None


def _why_first(race: Race, last: tuple[int, Turn] | None) -> bool:
    # a multiple-choice miss just now, mid-race: its right answer and why wait for Next
    return (last is not None and bool(last[1].answer) and not last[1].right and not race.done
            and last[0] == race.answered - 1)


def question_card(race: Race, last: tuple[int, Turn] | None = None) -> tuple[str, bool]:
    """The question card, and whether its choices show: right after a wrong answer mid-race,
    the question just answered with its right answer and why (the next waits for Next);
    otherwise the current question. The bonus shows its question alone, then its grade."""
    if _why_first(race, last):  # a wrong answer's why comes before anything, the bonus too
        number, turn = last
        return (f"Question {number + 1} of {QUESTIONS_PER_RACE}\n\n"
                f"**{race.questions[number].question}**\n\n"
                f"Not this time: it's **{turn.answer}**. {turn.why}", False)
    if race.bonus_live and race.bonus is not None:  # typed or spoken: no choices
        return (f"Question {race.answered + 1} of {QUESTIONS_PER_RACE}\n\n⭐ **Bonus: explain "
                f"it in your own words!**\n\n**{race.bonus.question}**", False)
    if last is not None and not last[1].answer and race.bonus is not None and not race.done:
        number, turn = last  # a graded bonus waits for Next too, so its line is read
        return (f"Question {number + 1} of {QUESTIONS_PER_RACE}\n\n⭐ **{race.bonus.question}**"
                f"\n\n{turn.why}", False)
    if last is not None and not last[1].right and not race.done:
        number, turn = last
        return (f"Question {number + 1} of {QUESTIONS_PER_RACE}\n\n"
                f"**{race.questions[number].question}**\n\n"
                f"Not this time: it's **{turn.answer}**. {turn.why}", False)
    view = public(race)
    return f"Question {view['number'] + 1} of {QUESTIONS_PER_RACE}\n\n**{view['question']}**", True


def _feedback(race: Race, turn: Turn, awarded: int, goal: str = "") -> str:
    slowed = f"{turn.slowed} slowed down" if turn.slowed else "Both slowed down"
    if not turn.right and not race.done:
        return ""  # the card shows the right answer and its why, until Next
    line = (f"Right answer: boost! {slowed} 💨" if turn.right
            else f"Not this time: it's **{turn.answer}**. {turn.why}")
    if race.done:
        line += f"\n\nYou finished {ORDINAL[place(race)]}! ⭐ +{awarded}"
        line += f"\n\n{goal}" if goal else ""
    return line


def games_tab(signin: SignIn, desk: RaceDesk | None, points: PointsStore,
              header_stars: gr.Markdown, garage: Garage,
              speech: Speech | None = None) -> tuple[gr.Tab, Callable[..., list[Any]], list[Any]]:
    """The Games tab: your car and the next goal, the race, then My cars and Showroom.

    Returns:
        The tab, a refresh for page load (no Claude call), and the components it fills.
    """
    def tile(c: Car) -> tuple[gr.Column, gr.Button]:
        with gr.Column(elem_classes="lerni-tile", min_width=0, visible=False) as col:
            gr.HTML(card_html(c, owned=True), padding=False)
            return col, gr.Button(elem_classes="lerni-buy")

    def shop_tile(c: Car) -> tuple[gr.Column, gr.HTML, gr.HTML, gr.Button]:
        with gr.Column(elem_classes="lerni-tile", min_width=0, visible=False) as col:
            full = gr.HTML(card_html(c), padding=False)
            locked = gr.HTML(card_html(c, locked=True), padding=False, visible=False)
            return col, full, locked, gr.Button(elem_classes="lerni-buy")

    with gr.Tab("Games", id="games", visible=False) as tab:
        hero = gr.HTML(elem_id="lerni-hero")  # your car and the next goal, when not racing
        track = gr.HTML(elem_id="lerni-track", visible=False)  # once a race starts
        with gr.Row(elem_classes="lerni-qrow"):
            question = gr.Markdown(elem_classes="lerni-question")
            # 🔊 reads the question on screen; race.js presses it when Read aloud is on (v3.29)
            speak = gr.Button("🔊", elem_id="lerni-read-go", scale=0, min_width=48, visible=False)
        read_clip = gr.Textbox(elem_id="lerni-clip-read", elem_classes="lerni-hide",
                               container=False)  # the clip for talk.js to play
        choices = [gr.Button(visible=False, elem_classes="lerni-choice") for _ in range(3)]
        talks = speech is not None
        # the bonus: typed or spoken, like Chat's dock (talk.js drives the "bonus" parts)
        with gr.Column(elem_id="lerni-dock-bonus", visible=False,
                       elem_classes="lerni-dock lerni-voice" if talks else "lerni-dock") as dock:
            if talks:
                preview = gr.Markdown(elem_id="lerni-preview-bonus")  # what's heard so far
                gr.Button("🎤\nHold to talk", elem_id="lerni-talk-bonus", elem_classes="lerni-talk")
            with gr.Row(elem_classes="lerni-type"):
                answer_box = gr.Textbox(
                    show_label=False, placeholder="Explain it in your own words…", lines=1,
                    max_lines=4, max_length=MAX_ANSWER, container=False, scale=4,
                    elem_id="lerni-question-bonus")
                send = gr.Button("Send", variant="primary", scale=1, min_width=70,
                                 elem_id="lerni-send-bonus")
            if talks:
                gr.HTML('<div class="lerni-mode" role="group" aria-label="Talk or type">'
                        '<button type="button" data-mode="talk">🎤 Talk</button>'
                        '<button type="button" data-mode="type">⌨️ Type</button></div>')
                hide = {"elem_classes": "lerni-hide", "container": False}
                clip = gr.Textbox(elem_id="lerni-clip-bonus", **hide)
                partial = gr.Textbox(elem_id="lerni-partial-bonus", **hide)
                heard_btn = gr.Button(elem_id="lerni-heard-bonus", elem_classes="lerni-hide")
                peek = gr.Button(elem_id="lerni-peek-bonus", elem_classes="lerni-hide")
            skip = gr.Button("Skip", size="sm")
        note = gr.Markdown(elem_id="lerni-note")
        go = gr.Button("Race!", variant="primary", elem_classes="lerni-go")
        next_btn = gr.Button("Next", variant="primary", elem_classes="lerni-go", visible=False)
        shown = gr.State(("", 0))  # the race id and question number on screen
        # tiles are built once at startup, one per car in each list; each player sees theirs
        mine_title = gr.Markdown("### 🅿️ My cars")
        with gr.Row(elem_classes="lerni-tiles"):
            mine = {c.id: tile(c) for c in garage.cars}
        gr.Markdown("### 🛒 Showroom")
        with gr.Row(elem_classes="lerni-tiles"):
            shop = {c.id: shop_tile(c) for c in garage.cars}

    outputs = [header_stars, hero, track, question, *choices, dock, answer_box, send, note, go,
               next_btn, shown, mine_title,
               *(x for pair in mine.values() for x in pair),
               *(x for parts in shop.values() for x in parts), speak]

    def garage_updates(p: Points | None) -> list[Any]:
        """The My cars title, then each car's tile and button in both lists."""
        sold = garage.sold(p.cars) if p else []
        owned = [c for c in garage.cars if p and c.id in p.cars]
        ups: list[Any] = [f"### 🅿️ My cars ({len(owned)})"]
        for c in garage.cars:  # My cars
            if c not in owned:
                ups += [gr.update(visible=False), gr.update()]
            elif c.id == p.car:
                ups += [gr.update(visible=True), gr.update(value="Driving", interactive=False)]
            else:
                ups += [gr.update(visible=True), gr.update(value="Drive", interactive=True)]
        for c in garage.cars:  # Showroom: tile, full card, locked card, button
            if p is None or c not in sold or c in owned:
                ups += [gr.update(visible=False), gr.update(), gr.update(), gr.update()]
            elif p.balance >= c.price:
                ups += [gr.update(visible=True), gr.update(visible=True), gr.update(visible=False),
                        gr.update(value=f"Buy · {c.price:,} ⭐", interactive=True)]
            else:
                ups += [gr.update(visible=True), gr.update(visible=False), gr.update(visible=True),
                        gr.update(value=f"{c.price - p.balance:,} more ⭐", interactive=False)]
        return ups

    def screen(viewer: Viewer | None, race: Race | None, line: str,
               last: tuple[int, Turn] | None = None) -> list[Any]:
        """Every output, in order; ``last`` is the answer just given, for the waiting card."""
        p = points.get(viewer.username) if viewer else None
        driving = p.car if p else STARTER
        if race is None or race.done:
            ask, buttons = "", [gr.update(visible=False) for _ in choices]
            go_update = gr.update(visible=True, value="Race again!" if race else "Race!")
            ref, waiting, live = (race.id, race.answered) if race else ("", 0), False, False
            heard = False
        else:
            ask, show = question_card(race, last)
            # while the why shows, the hidden buttons don't get the next question yet
            buttons = ([gr.update(visible=True, value=c) for c in public(race)["choices"]] if show
                       else [gr.update(visible=False) for _ in choices])
            live = race.bonus_live and not _why_first(race, last)  # the dock, not Next
            go_update, ref, waiting = gr.update(visible=False), (race.id, race.answered), not (
                show or live)
            heard = show or live  # a question (or the bonus) is on the card: 🔊 can read it
        mine = stars(points, viewer)
        return [gr.update(value=mine, visible=bool(mine)),
                gr.update(value=hero_html(garage, p), visible=race is None),
                gr.update(value=track_svg(race, driving, garage, reads=talks),
                          visible=race is not None),
                ask, *buttons, gr.update(visible=live), gr.update(value=""),
                gr.update(interactive=True), line, go_update, gr.update(visible=waiting), ref,
                *garage_updates(p), gr.update(visible=talks and heard)]

    def viewer_of(request: gr.Request) -> Viewer | None:
        viewer = signin.viewer(request.username)  # re-read on every request
        try:
            return require_player(viewer)
        except NotAllowed:
            return None

    def refresh(request: gr.Request) -> list[Any]:
        return screen(viewer_of(request), None, "")

    def on_open(request: gr.Request) -> list[Any]:
        viewer = viewer_of(request)
        if desk is not None and viewer is not None:
            desk.drop(viewer.username)  # leaving a race drops it
            desk.prefill(viewer.username, supervised=viewer.role is Role.SUPERVISED)
        return screen(viewer, None, "" if desk else NO_CLAUDE)

    def on_go(request: gr.Request) -> list[Any]:
        viewer = viewer_of(request)
        if desk is None:
            return screen(viewer, None, NO_CLAUDE)
        try:  # anything odd here: the Race button comes back, never a stuck waiting note
            driving = points.get(viewer.username).car if viewer else STARTER
            try:  # the driven car's gas; a car gone from the garage file drives like the starter
                gas = boost(garage.car(driving))
            except KeyError:
                gas = 1.0
            rivals = rival_pairs(garage, points.get(viewer.username)) if viewer else BOT_RIVALS
        except Exception:  # noqa: BLE001 - never show what went wrong inside
            return screen(viewer, None, NOT_READY)
        race, message = start_race(desk, viewer, gas, driving, rivals)
        return screen(viewer, race, message)

    def on_choice(i: int) -> Callable[..., list[Any]]:
        def handler(ref: tuple[str, int], request: gr.Request) -> list[Any]:
            viewer = viewer_of(request)
            if desk is None or viewer is None:
                return screen(viewer, None, "")
            race, turn, awarded = pick(desk, viewer, ref[0], ref[1], i)
            goal = goal_line(garage, points.get(viewer.username)) if race and race.done else ""
            shown = after_tap(race, ref, turn, awarded, goal)
            if shown is None:
                return [gr.update() for _ in outputs]  # a repeat tap: nothing changes
            return screen(viewer, *shown, last=(ref[1], turn) if turn else None)
        return handler

    def on_bonus(text: str, ref: tuple[str, int], request: gr.Request,
                 said: str = "") -> list[Any]:
        # grade the answer once (it stays in memory), then show the grade until Next
        viewer = viewer_of(request)
        if desk is None or viewer is None:
            return screen(viewer, None, "")
        race, turn, awarded = desk.answer_bonus(viewer.username, ref[0], ref[1], text or "",
                                                supervised=viewer.role is Role.SUPERVISED)
        if turn is None and race is not None and desk.grading(race.id):
            return [gr.update() for _ in outputs]  # the first answer is still being read
        if turn is None:  # a double send, or the race ended
            return screen(viewer, race, "" if race else "That race ended. Tap Race! 🏁")
        line = (f"🎤 {said}\n\n" if said else "") + (f"⭐ +{awarded}" if awarded else "")
        return screen(viewer, race, line, last=(ref[1], turn))

    def on_next(request: gr.Request) -> list[Any]:
        # the next question, after the right answer and its why (a dropped race: the start)
        viewer = viewer_of(request)
        if desk and viewer and desk.just_answered(viewer.username):
            return [gr.update() for _ in outputs]  # a double tap's second half: read the why
        race = desk.current(viewer.username) if desk and viewer else None
        ended = "" if race or viewer is None else "That race ended. Tap Race! 🏁"
        return screen(viewer, race, ended)

    def on_garage(car_id: str) -> Callable[..., list[Any]]:
        def handler(request: gr.Request) -> list[Any]:
            viewer = viewer_of(request)
            message = garage_tap(points, garage, viewer, car_id)
            race = desk.current(viewer.username) if desk is not None and viewer else None
            return screen(viewer, race, message)
        return handler

    def on_speak(ref: tuple[str, int], request: gr.Request) -> Any:
        # the question on screen, spoken; a fresh value each time, so a second tap replays it
        viewer = viewer_of(request)
        audio = desk.read_aloud(viewer.username, ref[0], ref[1]) if desk and viewer else None
        if not audio:
            return gr.update()
        return json.dumps([time.monotonic(), base64.b64encode(audio).decode()])

    speak.click(on_speak, shown, read_clip, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    read_clip.change(None, read_clip, None,  # one reading at a time: a new one replaces it
                     js="(v) => { window.lerniTalk?.stop(); window.lerniTalk?.play(v); }")
    tab.select(on_open, None, outputs, **PRIVATE)
    # Race hides while questions are written, so extra taps can't start more races
    # the note says why it waits; progress only on the hidden Race button, so no "processing"
    # over the hero, the card, and every garage car ("hidden" still shows it on HTML)
    go.click(lambda: [WAIT_LINE, gr.update(visible=False)], None, [note, go], queue=False,
             **PRIVATE).then(
        on_go, None, outputs, concurrency_limit=MAX_AT_ONCE, show_progress_on=[go],
        **PRIVATE)  # side by side
    for i, button in enumerate(choices):
        button.click(on_choice(i), shown, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    next_btn.click(on_next, None, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    reading = (lambda: ["Lerni is reading your answer… ⭐", gr.update(interactive=False)],
               None, [note, send])  # Send waits while Claude grades
    for trigger in (send.click, answer_box.submit):
        trigger(*reading, **PRIVATE).then(on_bonus, [answer_box, shown], outputs,
                                          concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    def on_skip(ref: tuple[str, int], request: gr.Request) -> list[Any]:
        return on_bonus("", ref, request)  # nothing to grade: no points, never called wrong

    skip.click(on_skip, [shown], outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    if talks:
        def on_heard(b64: str, ref: tuple[str, int], request: gr.Request) -> list[Any]:
            # what Whisper heard is sent at once, as in Chat; nothing heard: try again
            if viewer_of(request) is None:  # who's asking, before anything is heard
                return screen(None, None, "")
            try:
                text = heard(speech, b64)
            except (ClipRefused, SpeechUnavailable):
                ups = [gr.update() for _ in outputs]  # the bonus stays; only the note changes
                ups[outputs.index(note)] = "I didn't catch that. Hold to talk again, or type it."
                return ups
            return on_bonus(text, ref, request, said=text)

        heard_btn.click(lambda: "", None, [preview], **PRIVATE).then(  # the last words go
            on_heard, [clip, shown], outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
        def on_peek(b64: str, request: gr.Request) -> str:
            viewer = viewer_of(request)  # what's heard so far, while the button is held
            return f"🎤 {talk_preview(speech, viewer, b64)}" if viewer else ""

        peek.click(on_peek, [partial], [preview], trigger_mode="always_last", **PRIVATE)
    for car_id, button in [*((i, t[-1]) for i, t in mine.items()),
                           *((i, t[-1]) for i, t in shop.items())]:
        button.click(on_garage(car_id), None, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    return tab, refresh, outputs
