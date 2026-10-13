"""Games: race two silly bots by answering questions, and spend points on cars (spec 09).

Handlers are plain functions over the server-resolved viewer, so role checks can be
tested without a browser. The page never holds an answer: a tap sends the race id,
the question number, and which button, and the server decides.
"""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import gradio as gr

from lerni.student.garage import CARS, car, car_card_svg, car_svg
from lerni.student.points import STARTER, PointsError, PointsStore
from lerni.student.race import (
    BOTS,
    FINISH,
    QUESTIONS_PER_RACE,
    Race,
    RaceDesk,
    RaceUnavailable,
    Turn,
    place,
    public,
)
from lerni.student.signin import Role, SignIn, Viewer
from lerni.student.students import StudentStore
from lerni.student.web.accounts import PRIVATE, NotAllowed
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


def start_race(desk: RaceDesk, viewer: Viewer | None) -> tuple[Race | None, str]:
    """A new race, or why there can't be one."""
    try:
        v = require_player(viewer)
        return desk.start(v.username, supervised=v.role is Role.SUPERVISED), ""
    except (NotAllowed, PointsError, RaceUnavailable) as exc:
        return None, str(exc)


def pick(desk: RaceDesk, viewer: Viewer | None, race_id: str, number: int,
         choice: int) -> tuple[Race | None, Turn | None, int]:
    """Answer the question on screen; the desk ignores stale or repeat taps."""
    return desk.pick(require_player(viewer).username, race_id, number, choice)


def garage_tap(points: PointsStore, viewer: Viewer | None, car_id: str) -> str:
    """Drive a car they own, or buy it and drive it."""
    try:
        v, c = require_player(viewer), car(car_id)
        if car_id not in points.get(v.username).cars:
            points.buy(v.username, car_id, c.price)
            points.drive(v.username, car_id)
            return f"🎉 The {c.name} is yours!"
        points.drive(v.username, car_id)
        return f"Driving the {c.name}."
    except (NotAllowed, PointsError) as exc:
        return f"⚠️ {exc}"
    except KeyError:
        return "⚠️ No such car."


def student_points(points: PointsStore, students: StudentStore, viewer: Viewer | None,
                   requested: str | None) -> str:
    """A supervised student's points and cars, for their educator on MentalMaps."""
    try:
        p = points.get(map_owner(students, viewer, requested or ""))
    except NotAllowed:
        return ""
    names = ", ".join(car(c).name for c in p.cars if c in {x.id for x in CARS})
    return f"⭐ {p.balance} · cars: {names}"


def track_svg(race: Race | None, car_id: str) -> str:
    """The track: the student's car and two bots, placed by how far each has come."""

    def x(pos: float) -> float:
        return START + min(pos, FINISH) / FINISH * (END - START)

    me, bots = (race.me, race.bots) if race else (0.0, [0.0 for _ in BOTS])
    where = f"You're {ORDINAL[place(race)]}" if race and race.answered else "At the start line"
    parts = [f'<svg viewBox="0 0 320 130" width="100%" role="img" aria-label="{where}" '
             f'data-race="{html.escape(race.id if race else "")}">',
             '<rect width="320" height="130" rx="8" fill="#E1F5EE"/>',
             '<line x1="0" y1="43" x2="320" y2="43" stroke="#9FE1CB" stroke-dasharray="6 6"/>',
             '<line x1="0" y1="86" x2="320" y2="86" stroke="#9FE1CB" stroke-dasharray="6 6"/>',
             f'<rect x="{END + 58}" y="0" width="6" height="130" fill="#444441"/>']  # finish line
    for label, y in zip(("You", *(name for name, _ in BOTS)), LANES, strict=True):
        parts.append(f'<text x="4" y="{y + 26}" font-size="10" fill="#085041">{label}</text>')
    parts.append(car_svg(car_id, x(me), LANES[0], "me"))
    for (name, _), (look, color), pos, y in zip(BOTS, BOT_LOOKS, bots, LANES[1:], strict=True):
        parts.append(car_svg(look, x(pos), y, name, color))
    return "".join(parts) + "</svg>"


def after_tap(race: Race | None, ref: tuple[str, int], turn: Turn | None,
              awarded: int = 0) -> tuple[Race | None, str] | None:
    """What an answer tap shows: the race and a line, or None when nothing changes (a repeat)."""
    if turn is not None:
        return race, _feedback(race, turn, awarded) if race else ""
    if race is None or race.id != ref[0]:  # a restart or another screen ended it
        return None, "That race ended. Tap Race! 🏁"
    return None


def _feedback(race: Race, turn: Turn, awarded: int) -> str:
    line = (f"Right answer: boost! {turn.slowed} slowed down 💨" if turn.right
            else f"Not this time: it's **{turn.answer}**. {turn.why}")
    if race.done:
        line += f"\n\nYou finished {ORDINAL[place(race)]}! ⭐ +{awarded}"
    return line


def games_tab(signin: SignIn, desk: RaceDesk | None, points: PointsStore,
              header_stars: gr.Markdown) -> tuple[gr.Tab, Callable[..., list[Any]], list[Any]]:
    """The Games tab: the race, then the garage.

    Returns:
        The tab, a refresh for page load (no Claude call), and the components it fills.
    """
    with gr.Tab("Games", id="games", visible=False) as tab:
        track = gr.HTML(elem_id="lerni-track")
        question = gr.Markdown(elem_classes="lerni-question")
        choices = [gr.Button(visible=False, elem_classes="lerni-choice") for _ in range(3)]
        note = gr.Markdown()
        go = gr.Button("Race!", variant="primary", elem_classes="lerni-go")
        shown = gr.State(("", 0))  # the race id and question number on screen
        with gr.Accordion("Garage", open=False):
            garage = {}
            for c in CARS:  # the cars never change, so they're built once
                with gr.Row(elem_classes="lerni-item"):
                    gr.HTML(f"{car_card_svg(c.id)} {html.escape(c.name)}", padding=False)
                    garage[c.id] = gr.Button(size="sm", scale=0, min_width=120)

    outputs = [header_stars, track, question, *choices, note, go, shown, *garage.values()]

    def garage_labels(viewer: Viewer | None) -> list[Any]:
        p = points.get(viewer.username) if viewer else None
        labels = []
        for c in CARS:
            if p is None:
                labels.append(gr.update(value=f"⭐ {c.price}"))
            elif c.id == p.car:
                labels.append(gr.update(value="Driving"))
            elif c.id in p.cars:
                labels.append(gr.update(value="Drive"))
            elif p.balance >= c.price:
                labels.append(gr.update(value=f"Buy · ⭐ {c.price}"))
            else:
                labels.append(gr.update(value=f"{c.price - p.balance} more ⭐"))
        return labels

    def screen(viewer: Viewer | None, race: Race | None, line: str) -> list[Any]:
        """Every output, in order."""
        driving = points.get(viewer.username).car if viewer else STARTER
        if race is None or race.done:
            ask, buttons = "", [gr.update(visible=False) for _ in choices]
            go_update = gr.update(visible=True, value="Race again!" if race else "Race!")
            ref = (race.id, race.answered) if race else ("", 0)
        else:
            view = public(race)
            ask = f"Question {view['number'] + 1} of {QUESTIONS_PER_RACE}\n\n**{view['question']}**"
            buttons = [gr.update(visible=True, value=c) for c in view["choices"]]
            go_update, ref = gr.update(visible=False), (race.id, race.answered)
        return [stars(points, viewer), track_svg(race, driving), ask, *buttons, line, go_update,
                ref, *garage_labels(viewer)]

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
        race, message = start_race(desk, viewer)
        return screen(viewer, race, message)

    def on_choice(i: int) -> Callable[..., list[Any]]:
        def handler(ref: tuple[str, int], request: gr.Request) -> list[Any]:
            viewer = viewer_of(request)
            if desk is None or viewer is None:
                return screen(viewer, None, "")
            race, turn, awarded = pick(desk, viewer, ref[0], ref[1], i)
            shown = after_tap(race, ref, turn, awarded)
            if shown is None:
                return [gr.update() for _ in outputs]  # a repeat tap: nothing changes
            return screen(viewer, *shown)
        return handler

    def on_garage(car_id: str) -> Callable[..., list[Any]]:
        def handler(request: gr.Request) -> list[Any]:
            viewer = viewer_of(request)
            message = garage_tap(points, viewer, car_id)
            race = desk.current(viewer.username) if desk is not None and viewer else None
            return screen(viewer, race, message)
        return handler

    tab.select(on_open, None, outputs, **PRIVATE)
    # Race hides while questions are written, so extra taps can't start more races
    go.click(lambda: ["Pumping the tires… 🛞", gr.update(visible=False)], None, [note, go],
             **PRIVATE).then(
        on_go, None, outputs, **PRIVATE)
    for i, button in enumerate(choices):
        button.click(on_choice(i), shown, outputs, **PRIVATE)
    for car_id, button in garage.items():
        button.click(on_garage(car_id), None, outputs, **PRIVATE)
    return tab, refresh, outputs
