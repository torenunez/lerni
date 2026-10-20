"""Games: race two silly bots by answering questions, and spend points on cars (spec 09).

Handlers are plain functions over the server-resolved viewer, so role checks can be
tested without a browser. The page never holds an answer: a tap sends the race id,
the question number, and which button, and the server decides.
"""

from __future__ import annotations

import html
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
from lerni.student.points import STARTER, Points, PointsError, PointsStore
from lerni.student.race import (
    BOTS,
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
from lerni.student.results import ResultsLog, week_line
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import StudentStore
from lerni.student.web.accounts import PRIVATE, NotAllowed
from lerni.student.web.ask import MAX_AT_ONCE
from lerni.student.web.maps import map_owner

LANES = (12, 55, 98)  # the student's lane, then Zippy's and Bolt's
BOT_LOOKS = (("formula", "#7F77DD"), ("muscle", "#888780"))  # how the bots are drawn
START, END = 40, 248  # a car's left edge at the start and at the finish, in track units
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


def start_race(desk: RaceDesk, viewer: Viewer | None, gas: float = 1.0,
               car: str = "") -> tuple[Race | None, str]:
    """A new race in this car with its gas boost, or why there can't be one."""
    try:
        v = require_player(viewer)
        return desk.start(v.username, supervised=v.role is Role.SUPERVISED, boost=gas,
                          car=car), ""
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


def student_points(points: PointsStore, garage: Garage, students: StudentStore,
                   viewer: Viewer | None, requested: str | None,
                   results: ResultsLog | None = None) -> str:
    """A supervised student's points, cars, and this week's race results, for their educator."""
    try:
        owner = map_owner(students, viewer, requested or "")
    except NotAllowed:
        return ""
    p = points.get(owner)
    known = {c.id: c.name for c in garage.cars}
    names = ", ".join(known[c] for c in p.cars if c in known)
    week = week_line(results, owner, date.today()) if results else ""
    return f"⭐ {p.balance} · cars: {names}" + (f"  \n{week}" if week else "")


def track_svg(race: Race | None, car_id: str, garage: Garage) -> str:
    """The track: the student's car and two bots, placed by how far each has come."""

    full = QUESTIONS_PER_RACE * STEP_RIGHT * (race.boost if race else 1.0)  # 5 right in this car

    def x(pos: float) -> float:  # nothing reaches the line before the fifth answer
        return START + min(pos, full) / full * (END - START)

    car_id = (race.car or car_id) if race else car_id  # the car it started in

    me, bots = (race.me, race.bots) if race else (0.0, [0.0 for _ in BOTS])
    where = f"You're {ORDINAL[place(race)]}" if race and race.answered else "At the start line"
    parts = [f'<svg viewBox="0 0 320 130" width="100%" role="img" aria-label="{where}" '
             f'data-race="{html.escape(race.id if race else "")}" '
             f'data-car="{html.escape(car_id)}">',
             '<rect width="320" height="130" rx="8" fill="#E1F5EE"/>',
             '<line x1="0" y1="43" x2="320" y2="43" stroke="#9FE1CB" stroke-dasharray="6 6"/>',
             '<line x1="0" y1="86" x2="320" y2="86" stroke="#9FE1CB" stroke-dasharray="6 6"/>',
             f'<rect x="{END + 58}" y="0" width="6" height="130" fill="#444441"/>']  # finish line
    for label, y in zip(("You", *(name for name, _ in BOTS)), LANES, strict=True):
        parts.append(f'<text x="4" y="{y + 26}" font-size="10" fill="#085041">{label}</text>')
    parts.append(garage.svg(car_id, x(me), LANES[0], "me"))
    for (name, _), (look, color), pos, y in zip(BOTS, BOT_LOOKS, bots, LANES[1:], strict=True):
        parts.append(car_svg(look, x(pos), y, name, color))
    return "".join(parts) + "</svg>"


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


def _feedback(race: Race, turn: Turn, awarded: int, goal: str = "") -> str:
    line = (f"Right answer: boost! {turn.slowed} slowed down 💨" if turn.right
            else f"Not this time: it's **{turn.answer}**. {turn.why}")
    if race.done:
        line += f"\n\nYou finished {ORDINAL[place(race)]}! ⭐ +{awarded}"
        line += f"\n\n{goal}" if goal else ""
    return line


def games_tab(signin: SignIn, desk: RaceDesk | None, points: PointsStore,
              header_stars: gr.Markdown,
              garage: Garage) -> tuple[gr.Tab, Callable[..., list[Any]], list[Any]]:
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
        question = gr.Markdown(elem_classes="lerni-question")
        choices = [gr.Button(visible=False, elem_classes="lerni-choice") for _ in range(3)]
        note = gr.Markdown(elem_id="lerni-note")
        go = gr.Button("Race!", variant="primary", elem_classes="lerni-go")
        shown = gr.State(("", 0))  # the race id and question number on screen
        # tiles are built once at startup, one per car in each list; each player sees theirs
        mine_title = gr.Markdown("### 🅿️ My cars")
        with gr.Row(elem_classes="lerni-tiles"):
            mine = {c.id: tile(c) for c in garage.cars}
        gr.Markdown("### 🛒 Showroom")
        with gr.Row(elem_classes="lerni-tiles"):
            shop = {c.id: shop_tile(c) for c in garage.cars}

    outputs = [header_stars, hero, track, question, *choices, note, go, shown, mine_title,
               *(x for pair in mine.values() for x in pair),
               *(x for parts in shop.values() for x in parts)]

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

    def screen(viewer: Viewer | None, race: Race | None, line: str) -> list[Any]:
        """Every output, in order."""
        p = points.get(viewer.username) if viewer else None
        driving = p.car if p else STARTER
        if race is None or race.done:
            ask, buttons = "", [gr.update(visible=False) for _ in choices]
            go_update = gr.update(visible=True, value="Race again!" if race else "Race!")
            ref = (race.id, race.answered) if race else ("", 0)
        else:
            view = public(race)
            ask = f"Question {view['number'] + 1} of {QUESTIONS_PER_RACE}\n\n**{view['question']}**"
            buttons = [gr.update(visible=True, value=c) for c in view["choices"]]
            go_update, ref = gr.update(visible=False), (race.id, race.answered)
        mine = stars(points, viewer)
        return [gr.update(value=mine, visible=bool(mine)),
                gr.update(value=hero_html(garage, p), visible=race is None),
                gr.update(value=track_svg(race, driving, garage), visible=race is not None),
                ask, *buttons, line, go_update, ref, *garage_updates(p)]

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
        driving = points.get(viewer.username).car if viewer else STARTER
        try:  # the driven car's gas; a car gone from the garage file drives like the starter
            gas = boost(garage.car(driving))
        except KeyError:
            gas = 1.0
        race, message = start_race(desk, viewer, gas, driving)
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
            return screen(viewer, *shown)
        return handler

    def on_garage(car_id: str) -> Callable[..., list[Any]]:
        def handler(request: gr.Request) -> list[Any]:
            viewer = viewer_of(request)
            message = garage_tap(points, garage, viewer, car_id)
            race = desk.current(viewer.username) if desk is not None and viewer else None
            return screen(viewer, race, message)
        return handler

    tab.select(on_open, None, outputs, **PRIVATE)
    # Race hides while questions are written, so extra taps can't start more races
    go.click(lambda: ["Pumping the tires… 🛞", gr.update(visible=False)], None, [note, go],
             **PRIVATE).then(
        on_go, None, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)  # side by side
    for i, button in enumerate(choices):
        button.click(on_choice(i), shown, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    for car_id, button in [*((i, t[-1]) for i, t in mine.items()),
                           *((i, t[-1]) for i, t in shop.items())]:
        button.click(on_garage(car_id), None, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    return tab, refresh, outputs
