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
    arrival_day,
    bolts,
    boost,
    car_card_svg,
    car_svg,
    family_cars,
    next_goal,
    next_pick,
)
from lerni.student.interests import MapStore, area_group
from lerni.student.money import COIN_PX, say_cents
from lerni.student.points import STARTER, Points, PointsError, PointsStore
from lerni.student.race import (
    BOT_RIVALS,
    CARE_LINE,
    MAX_ANSWER,
    NOT_READY,
    QUESTIONS_PER_RACE,
    STEP_RIGHT,
    Race,
    RaceDesk,
    RaceUnavailable,
    Turn,
    miss_opener,
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
from lerni.student.web.spelling import spelled_html
from lerni.student.writing import CHECKLIST, MAX_PARAGRAPH, WRITE_FIRST

LANES = (12, 55, 98)  # the student's lane, then the fast and slow rivals'
BOT_COLORS = {"Zippy": "#7F77DD", "Bolt": "#888780"}  # the bots' own paint
START, END = 8, 248  # a car's left edge at the start and at the finish, in track units
MAX_LABEL = 18  # characters of a car's name on the track
WAIT_LINE = "Pumping the tires… 🛞 New questions can take a minute to write."
SOUNDS = ("roar", "sputter", "finish", "zoom")  # <data>/sounds/<name>.mp3, played by race.js
BONUS_SOUNDS = {"nailed": "zoom", "partly": "roar", "tried": "rev"}  # rev: a short, soft roar
EDGE = (
    '<defs><filter id="lerni-edge" x="-10%" y="-10%" width="120%" height="120%">'
    '<feDropShadow dx="0" dy="0" stdDeviation="0.7" flood-color="#2C2C2A" '
    'flood-opacity="0.9"/></filter></defs>'
)  # a thin dark edge, so a white car shows
READS = {"why": ' data-why="1"', "question": ' data-ask="1"'}  # what race.js says by itself
HEAR = " · tap to hear"  # on a card the server can read aloud
ORDINAL = {1: "1st", 2: "2nd", 3: "3rd"}
NO_CLAUDE = "Games need Claude, which isn't set up on this server."
TYPED_MAX = 40  # characters of a typed answer (a word or a number)
TYPE_FIRST = "Type your answer first, then tap Check."
PLACEHOLDER = {"spell": "Type the word", "picture": "Type your answer", "read": ""}


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


def start_race(
    desk: RaceDesk,
    viewer: Viewer | None,
    gas: float = 1.0,
    car: str = "",
    rivals: tuple[tuple[str, str], ...] = BOT_RIVALS,
) -> tuple[Race | None, str]:
    """A new race in this car with its gas boost, or why there can't be one."""
    try:
        v = require_player(viewer)
        return desk.start(
            v.username, supervised=v.role is Role.SUPERVISED, boost=gas, car=car, rivals=rivals
        ), ""
    except (NotAllowed, PointsError, RaceUnavailable) as exc:
        return None, str(exc)
    except Exception:  # never stuck on "Pumping the tires"
        return None, NOT_READY


def pick(
    desk: RaceDesk, viewer: Viewer | None, race_id: str, number: int, choice: int
) -> tuple[Race | None, Turn | None, int]:
    """Answer the question on screen; the desk ignores stale or repeat taps."""
    return desk.pick(require_player(viewer).username, race_id, number, choice)


def settled(
    points: PointsStore, garage: Garage, username: str, today: date | None = None
) -> tuple[Points, Car | None]:
    """Their points with deliveries up to date, and the car that just arrived (v4.17)."""
    day = today or date.today()  # tests pass a fixed day
    p, car_id = points.settle(
        username, lambda q: garage.deliver(q.cars, q.hearts, q.arrived, q.delivery, day)
    )
    try:
        return p, garage.car(car_id) if car_id else None
    except KeyError:  # gone from the garage file since
        return p, None


def covered_html(c: Car, when: str) -> str:
    """A covered car: its dark shape, name, and price, with "Arrives Friday" on the one coming
    next (``when``), or how to pick it."""
    tag = f"Arrives {when}" if when else "❤️ it to pick it"  # the others say how to choose
    return (
        f'<div class="lerni-card lerni-covered">{_picture(c)}<b>{html.escape(c.name)}</b>'
        f'<span class="lerni-like">⭐ {c.price:,}</span>'
        f'<span class="lerni-when{" lerni-next" if when else ""}">{html.escape(tag)}</span></div>'
    )


def delivery_chip(garage: Garage, p: Points, today: date | None = None) -> str:
    """For the educator: the next delivery, the car it would bring, and the cars wanted."""
    waiting = garage.waiting(p.cars, p.arrived)
    if not waiting or not p.delivery:
        return ""  # nothing to come, or not shown to the student yet
    try:
        when = arrival_day(date.fromisoformat(p.delivery), today or date.today())
    except ValueError:
        return ""
    wanted = [c.name for c in waiting if c.id in p.hearts]  # still to come, so still wishes
    hearts = f" · ❤️ {', '.join(wanted)}" if wanted else ""
    text = f"🚚 {when}: {next_pick(waiting, p.hearts).name}{hearts}"
    return f'<span class="lerni-chip">{html.escape(text)}</span>'


def garage_tap(
    points: PointsStore, garage: Garage, viewer: Viewer | None, car_id: str,
    today: date | None = None, wants: bool = False,
) -> str:
    """Drive a car they own, buy it and drive it, or heart a covered one (v4.17).

    ``wants`` is a tap on a covered tile's ❤️: it never buys, even when that car arrives
    during the tap (the screen was drawn before its delivery).
    """
    try:
        v, c = require_player(viewer), garage.car(car_id)
        p, came = settled(points, garage, v.username, today)  # a car due today arrives first
        news = f"🚚 The {came.name} just arrived in the Showroom! " if came else ""
        owned = p.cars
        if c in garage.waiting(owned, p.arrived):  # covered: a tap wants it, never buys it
            if points.heart(v.username, car_id):
                return f"{news}❤️ You want the {c.name}."
            return f"{news}The {c.name} is off your list."
        if wants:  # a ❤️ on a car that's here now: say so, buy nothing
            return news or f"The {c.name} is in the Showroom now."
        if c not in garage.sold(owned, p.arrived):
            return "⚠️ That car isn't sold here."
        if car_id not in owned:
            points.buy(v.username, car_id, c.price)
            points.drive(v.username, car_id)
            return f"{news}🎉 The {c.name} is yours!"
        points.drive(v.username, car_id)
        return f"{news}Driving the {c.name}."
    except (NotAllowed, PointsError) as exc:
        return f"⚠️ {exc}"
    except KeyError:
        return "⚠️ No such car."


def student_progress(
    points: PointsStore,
    garage: Garage,
    students: StudentStore,
    viewer: Viewer | None,
    requested: str | None,
    results: ResultsLog | None = None,
    maps: MapStore | None = None,
) -> str:
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
        return area_group(e.area) if e is not None and e.kind == "goal" else ""

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
            rows.append(
                f'<div class="lerni-week-area"><span>{html.escape(a or "Other")}</span>'
                f'<span class="lerni-of">{right} of {asked}</span></div>'
            )
        rows += [
            f'<div class="lerni-week-row"><span>{html.escape(goal)}</span>'
            f'<span class="lerni-week-bar">'
            f'<i style="width:{round(100 * right / asked)}%"></i></span>'
            f'<span class="lerni-of">{right} of {asked}</span></div>'
            for goal, right, asked in items
        ]
    try:  # a car gone from the garage file gets no chip
        car = f'<span class="lerni-chip">🚗 {html.escape(garage.car(p.car).name)}</span>'
    except KeyError:
        car = ""
    body = "".join(rows) or '<p class="lerni-of">No races this week.</p>'
    return (
        f'<div class="lerni-week"><h3>Goal progress this week</h3>{body}'
        f'<div><span class="lerni-chip">⭐ {p.balance}</span>{car}{delivery_chip(garage, p)}'
        "</div></div>"
    )


def rival_pairs(garage: Garage, p: Points) -> tuple[tuple[str, str], ...]:
    """The two rivals as (name, car id), fast lane first; a bot fills a lane with no car."""
    cars = garage.rivals(p.cars, p.car, p.balance, p.arrived)
    return tuple((c.name, c.id) if c else bot for c, bot in zip(cars, BOT_RIVALS, strict=True))


def _label(text: str, y: int) -> str:
    # a small name on a pill at the top-left of its lane, readable in either theme
    name = text if len(text) <= MAX_LABEL else text[: MAX_LABEL - 1] + "…"
    return (
        f'<rect x="2" y="{y - 10}" width="{len(name) * 4.6 + 6:.0f}" height="11" rx="5" '
        f'fill="#FFFFFF" fill-opacity="0.8"/><text x="5" y="{y - 2}" font-size="8" '
        f'fill="#085041">{html.escape(name)}</text>'
    )


def step_sound(race: Race) -> str:
    """The sound for the answer just given: the finish, a roar or sputter, or for the bonus
    one chosen by its grade (never a sputter); "" for none."""
    if race.done:
        return "finish"
    if not race.marks:
        return ""
    if (race.answered - 1) in race.typed:  # a typed answer sounds like a choice
        return "roar" if race.typed_right.get(race.answered - 1) else "sputter"
    if race.marks[-1] is None:  # the bonus
        return BONUS_SOUNDS.get(race.bonus_tier, "")
    return "roar" if race.marks[-1] else "sputter"


def track_svg(race: Race | None, car_id: str, garage: Garage, reads: str = "") -> str:
    """The track: the student's car and two rivals, placed by how far each has come, with the
    sound for the answer just given. ``reads``: "why" or "question", for race.js to say."""

    full = QUESTIONS_PER_RACE * STEP_RIGHT * (race.boost if race else 1.0)  # 5 right in this car

    def x(pos: float) -> float:  # nothing reaches the line before the fifth answer
        return START + min(pos, full) / full * (END - START)

    car_id = (race.car or car_id) if race else car_id  # the car it started in
    rivals = race.rivals if race else ()
    where = f"You're {ORDINAL[place(race)]}" if race and race.answered else "At the start line"
    parts = [
        f'<svg viewBox="0 0 320 130" width="100%" role="img" aria-label="{where}" '
        f'data-race="{html.escape(race.id if race else "")}" '
        f'data-step="{race.answered if race else 0}" data-right="{race.right if race else 0}" '
        f'data-total="{QUESTIONS_PER_RACE}" data-car="{html.escape(car_id)}" '
        f'data-sound="{step_sound(race) if race else ""}"{READS.get(reads, "")}>',
        EDGE,
        '<rect width="320" height="130" rx="8" fill="#E1F5EE"/>',
        '<line x1="0" y1="43" x2="320" y2="43" stroke="#9FE1CB" stroke-dasharray="6 6"/>',
        '<line x1="0" y1="86" x2="320" y2="86" stroke="#9FE1CB" stroke-dasharray="6 6"/>',
        f'<rect x="{END + 58}" y="0" width="6" height="130" fill="#444441"/>',  # finish line
        '<g filter="url(#lerni-edge)">',
        garage.svg(car_id, x(race.me if race else 0.0), LANES[0], "me"),
    ]
    for rival, pos, y, lane in zip(
        rivals, race.at if race else (), LANES[1:], ("fast", "slow"), strict=False
    ):  # no rivals at the start line
        if (rival.name, rival.car) in BOT_RIVALS:  # a bot, in its own paint
            parts.append(car_svg(rival.car, x(pos), y, lane, BOT_COLORS[rival.name]))
        else:
            parts.append(garage.svg(rival.car, x(pos), y, lane))
    parts.append("</g>")
    names = ("You", *(r.name for r in rivals))
    parts += [_label(name, y) for name, y in zip(names, LANES, strict=False)]
    return "".join(parts) + "</svg>"


def _picture(c: Car) -> str:
    return (
        f'<img src="/cars/{c.id}" alt="{html.escape(c.name)}">' if c.picture else car_card_svg(c.id)
    )


def _zap(c: Car) -> str:
    return f'<span class="lerni-zap" aria-label="speed {bolts(c)} of 5">{"⚡" * bolts(c)}</span>'


def card_html(c: Car, owned: bool = False, locked: bool = False) -> str:
    """One tile: the picture, the name, ⚡, the price while it's for sale, and Car facts.

    A car they can't afford yet (``locked``) shows only its picture, name, and price.
    """
    price = ""
    if not owned and c.usd:
        price = (
            f'<span class="lerni-usd">${c.usd:,}</span>'
            f'<span class="lerni-like">{family_cars(c.usd)}</span>'
        )
    hp = f"{c.power_hp:,} hp" if c.power_hp else ""
    secs = f"{c.zero_to_60:g} seconds" if c.zero_to_60 else ""
    facts = [
        f"{k}: {v}"
        for k, v in (("Engine", c.engine), ("Power", hp), ("Drive", c.drive), ("0–60 mph", secs))
        if v
    ]
    facts += [c.note] if c.note else []
    if c.usd:
        facts.append(f"${c.usd:,} ÷ $2,500 a star ≈ {c.price:,} ⭐")
    facts.append("More ⚡ moves your car farther with each right answer.")
    details = (
        "<details><summary>Car facts</summary>"
        + "".join(f"<div>{html.escape(f)}</div>" for f in facts)
        + "</details>"
    )
    if locked:  # ⚡ and the facts are earned by saving up
        return f'<div class="lerni-card">{_picture(c)}<b>{html.escape(c.name)}</b>{price}</div>'
    return (
        f'<div class="lerni-card">{_picture(c)}<b>{html.escape(c.name)}</b>{_zap(c)}'
        f"{price}{details}</div>"
    )


def goal_line(garage: Garage, p: Points) -> str:
    """The next car to save for, as one line ("" when nothing is left to get)."""
    goal, line = next_goal(garage.sold(p.cars, p.arrived), p.cars, p.balance)
    return f"Next car: {line}" if goal is not None and goal.price > p.balance else line


def hero_html(garage: Garage, p: Points | None) -> str:
    """The top of Games: the car they drive, big, and the next car to save for."""
    if p is None:
        return ""
    try:
        c = garage.car(p.car)
    except KeyError:  # gone from the garage file: the starter drives
        c = garage.car(STARTER)
    goal, _ = next_goal(garage.sold(p.cars, p.arrived), p.cars, p.balance)
    bar = ""
    if goal is not None and goal.price > p.balance:
        pct = min(100, p.balance * 100 // goal.price)
        bar = f'<div class="lerni-bar" aria-hidden="true"><span style="width:{pct}%"></span></div>'
    return (
        f'<div class="lerni-hero-car">{_picture(c)}</div>'
        f'<div class="lerni-hero-name"><b>{html.escape(c.name)}</b> {_zap(c)}</div>'
        f'<div class="lerni-goal">{html.escape(goal_line(garage, p))}{bar}</div>'
    )


def passage_html(p: Any, opened: bool = True) -> str:
    """A reading race's passage (v4.13): its title and paragraphs, folded by a tap; no kind
    label, since question 1 asks it. A writing race shows it folded (v4.14)."""
    if p is None:
        return ""
    paras = "".join(f"<p>{html.escape(para)}</p>" for para in p.text.split("\n\n"))
    fold = " open" if opened else ""  # a writing race: the prompt and the field come first
    return (
        f'<details class="lerni-passage"{fold}><summary>📖 {html.escape(p.title)}</summary>'
        f'<div class="lerni-passage-text">{paras}</div></details>'
    )


def checklist_html(graded: Any) -> str:
    """A writing race's checklist (v4.14): empty boxes before the first Check, then ✓ or
    "not yet" per item, with one thing done well and one to try."""
    if graded is not None and graded.care:  # a worry: the caring words alone
        return f'<div class="lerni-checklist"><p>{html.escape(graded.well)}</p></div>'
    rows = []
    for n, (_, name) in enumerate(CHECKLIST):
        if graded is None:
            rows.append(f"<li>⬜ {html.escape(name)}</li>")  # before writing: what to aim for
        elif graded.marks[n]:
            rows.append(f'<li class="lerni-met">✅ {html.escape(name)}</li>')
        else:
            rows.append(f'<li class="lerni-not-yet">🔸 {html.escape(name)}: not yet</li>')
    lines = ""
    if graded is not None:  # Claude's two lines, and what the revision fixed
        if graded.better:
            lines += f"<p>Better than before: {html.escape(', '.join(graded.better))} ✅</p>"
        lines += f"<p>Done well: {html.escape(graded.well)}</p>" if graded.well else ""
        lines += f"<p>Try: {html.escape(graded.tip)}</p>" if graded.tip else ""
    return f'<div class="lerni-checklist"><ul>{"".join(rows)}</ul>{lines}</div>'


def order_html(pic: dict[str, Any]) -> str:
    """Sentences to tap in order (v4.13): race.js numbers each tap and fills the answer."""
    items = [str(x) for x in pic.get("items") or []]
    cards = "".join(
        f'<button type="button" class="lerni-order-item" data-i="{i}">'
        f'<b aria-hidden="true"></b><span>{html.escape(t)}</span></button>'
        for i, t in enumerate(items)
    )  # escaped, though Claude wrote them
    return (
        f'<div class="lerni-order" data-n="{len(items)}">{cards}'
        '<p class="lerni-order-hint">Tap again to undo.</p></div>'
    )


def picture_html(pic: dict[str, Any] | None) -> str:
    """A picture question's blocks: a grid of emoji or squares, or for a missing piece, the
    pile and the empty rows to share it into; sentences to put in order; "" for none."""
    if not pic or pic.get("kind") == "open":
        return ""  # a spelling word or an open answer: nothing to draw
    if pic.get("kind") == "order":
        return order_html(pic)
    if pic.get("kind") == "money":
        return money_html(pic)
    if pic.get("kind") == "ruler":
        return ruler_svg(pic)
    emoji = html.escape(str(pic.get("emoji") or ""))  # escaped, though it comes from code
    one = f"<span>{emoji}</span>" if emoji else '<span class="lerni-sq"></span>'  # a block
    rows, cols = int(pic.get("rows", 0)), int(pic.get("cols", 0))
    if pic.get("empty"):  # the pile, then one empty row per row
        pile = one * int(pic.get("total", 0))
        empty = '<div class="lerni-row-empty"></div>' * rows
        return (
            f'<div class="lerni-pic"><div class="lerni-pile">{pile}</div></div>'
            f'<div class="lerni-pic-rows">{empty}</div>'
        )
    # a grid: one column per block in a row, so the rows line up
    return (
        f'<div class="lerni-pic" style="grid-template-columns:repeat({cols},36px)" '
        f'aria-label="{rows} rows of {cols}">{one * (rows * cols)}</div>'
    )


RULER_X, PX_CM = 30, 22  # the ruler's 0, and pixels per centimeter (an inch: 2.54 × 22)
BAR_ROW, RULER_H = 20, 72  # each object's row above the ruler, and the ruler's height


def ruler_svg(pic: dict[str, Any]) -> str:
    """A two-sided ruler (centimeters on top, inches below, one real scale) with each object
    above it, a dashed line from its end across both edges, and the units named at the left."""
    bars = pic.get("bars", [])[:2]
    top = 4 + BAR_ROW * len(bars)  # the ruler starts below the objects
    px = lambda cm: RULER_X + float(cm) * PX_CM  # noqa: E731 - centimeters to x
    out, ends = [], []  # the dashed lines go last, over the ruler
    for i, b in enumerate(bars):  # each object: a bar, its emoji at the end, a dashed line
        y, end = 4 + BAR_ROW * i, px(b["end"])
        out.append(
            f'<rect x="{px(b["start"]):.1f}" y="{y}" width="{end - px(b["start"]):.1f}" '
            f'height="12" rx="4" fill="#1D9E75"/>'
            f'<text x="{end + 3:.1f}" y="{y + 12}" font-size="16">'
            f"{html.escape(str(b.get('emoji', '')))}</text>"
        )
        for x in (px(b["start"]), end) if b["start"] else (end,):  # its start too, past 0
            ends.append(
                f'<line x1="{x:.1f}" y1="{y}" x2="{x:.1f}" y2="{top + RULER_H}" '
                f'stroke="#0F6E56" stroke-width="1.5" stroke-dasharray="3 2"/>'
            )
        if b.get("label"):  # 1 or 2, when two are compared
            out.append(
                f'<text x="2" y="{y + 11}" font-size="12" fill="currentColor">'
                f"{html.escape(str(b['label']))}</text>"
            )
    out.append(
        f'<rect x="{RULER_X - 8}" y="{top}" width="282" height="{RULER_H}" rx="4" '
        f'fill="#FAC775" stroke="#BA7517"/>'
    )  # the ruler itself
    for cm in range(13):  # the top edge: every centimeter, numbered
        x = px(cm)
        out.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + 16}" stroke="#633806"/>'
            f'<text x="{x:.1f}" y="{top + 28}" font-size="10" text-anchor="middle" '
            f'fill="#412402">{cm}</text>'
        )
    for half in range(10):  # the bottom edge: every half inch, whole inches numbered
        x, whole = px(half * 1.27), half % 2 == 0  # half an inch is 1.27 cm
        out.append(
            f'<line x1="{x:.1f}" y1="{top + RULER_H}" x2="{x:.1f}" '
            f'y2="{top + RULER_H - (18 if whole else 10)}" stroke="#633806"/>'
        )
        if whole:
            out.append(
                f'<text x="{x:.1f}" y="{top + RULER_H - 22}" font-size="10" '
                f'text-anchor="middle" fill="#412402">{half // 2}</text>'
            )
    # outside the ruler, so in the page's own text color (light or dark)
    out.append(
        f'<text x="0" y="{top + 28}" font-size="11" fill="currentColor">cm</text>'
        f'<text x="4" y="{top + RULER_H - 22}" font-size="11" fill="currentColor">in</text>'
    )
    out += ends  # across both edges, so either can be read
    height = top + RULER_H + 4
    return (
        f'<svg class="lerni-ruler" viewBox="0 0 320 {height}" role="img" '
        f'aria-label="A ruler: centimeters on top, inches below">{"".join(out)}</svg>'
    )


def money_html(pic: dict[str, Any]) -> str:
    """Coins at their real sizes beside each other, bills drawn, and a price for change."""
    bills = "".join(f'<span class="lerni-bill">${int(b)}</span>' for b in pic.get("bills", []))
    coins = "".join(  # the Mint's photo, named, never its worth
        f'<span class="lerni-coin"><img src="/coins/{c}.png" alt="{c}" '
        f'width="{COIN_PX[c]}" height="{COIN_PX[c]}"><small>{c}</small></span>'
        for c in pic.get("coins", [])
        if c in COIN_PX
    )
    price = ""
    if pic.get("price"):  # making change: what's bought and its price tag
        price = (
            f'<span class="lerni-price"><span>{html.escape(str(pic.get("item", "")))}'
            f"</span><small>{say_cents(int(pic['price']), True)}</small></span>"
        )
    credit = (
        '<p class="lerni-credit">United States coin images from the United States Mint.</p>'
        if coins
        else ""
    )  # the Mint asks for this line
    return f'<div class="lerni-money">{bills}{price}{coins}</div>{credit}'


def after_tap(
    race: Race | None, ref: tuple[str, int], turn: Turn | None, awarded: int = 0, goal: str = ""
) -> tuple[Race | None, str] | None:
    """What an answer tap shows: the race and a line, or None when nothing changes (a repeat)."""
    if turn is not None:
        return race, _feedback(race, turn, awarded, goal) if race else ""
    if race is None or race.id != ref[0]:  # a restart or another screen ended it
        return None, "That race ended. Tap Race! 🏁"
    return None


def _why_first(race: Race, last: tuple[int, Turn] | None) -> bool:
    # a multiple-choice miss just now, mid-race: its right answer and why wait for Next
    return (
        last is not None
        and bool(last[1].answer)
        and not last[1].right
        and not race.done
        and last[0] == race.answered - 1
    )


def _read_miss(t: Any, turn: Turn, opener: str) -> str:
    # a reading answer not right (v4.13): the order, or a hint and one answer that fits
    if turn.answer == CARE_LINE:  # a worry: the caring words alone
        return CARE_LINE
    if t.label.endswith(":order"):
        return f"{opener} The order is:\n\n{turn.answer}"
    return f"{opener} {turn.why} One answer: **{turn.answer}**".replace("  ", " ")


def _typed_miss(race: Race, number: int, turn: Turn, typed: str) -> str:
    # a missed typed answer: its question, then the right answer (a word's missed letters marked)
    t = race.typed[number]
    if t.kind == "read":
        return f"Question {number + 1} of {QUESTIONS_PER_RACE}\n\n**{t.prompt}**\n\n" + _read_miss(
            t, turn, miss_opener(race, number)
        )
    right = spelled_html(turn.answer, typed) if t.kind == "spell" else f"**{turn.answer}**"
    return (
        f"Question {number + 1} of {QUESTIONS_PER_RACE}\n\n**{t.prompt}**\n\n"
        f"{miss_opener(race, number)} It's {right}. {turn.why}"
    ).rstrip()


def question_card(
    race: Race, last: tuple[int, Turn] | None = None, hear: str = "", typed: str = ""
) -> tuple[str, bool]:
    """The question card, and whether its choices show: right after a wrong answer mid-race,
    the question just answered with its right answer and why (the next waits for Next);
    otherwise the current question. The bonus shows its question alone, then its grade.
    ``hear`` ends the first line of a card that can be heard; ``typed`` is a typed answer
    just checked, for marking a missed word (on screen only)."""
    if race.paragraph is not None:  # a writing race (v4.14): the prompt, the dock below
        return f"✏️ **Write a paragraph**\n\n**{race.paragraph.prompt}**", False
    if _why_first(race, last) and last[0] in race.typed:  # a missed word or picture
        return _typed_miss(race, *last, typed), False
    if _why_first(race, last):  # a wrong answer's why comes before anything, the bonus too
        number, turn = last
        return (
            f"Question {number + 1} of {QUESTIONS_PER_RACE}{hear}\n\n"
            f"**{race.questions[number].question}**\n\n"
            f"{miss_opener(race, number)} It's **{turn.answer}**. {turn.why}",
            False,
        )
    if race.bonus_live and race.bonus is not None:  # typed or spoken: no choices
        return (
            f"Question {race.answered + 1} of {QUESTIONS_PER_RACE}{hear}\n\n"
            f"⭐ **Bonus: explain it in your own words!**\n\n**{race.bonus.question}**",
            False,
        )
    if last is not None and not last[1].answer and race.bonus is not None and not race.done:
        number, turn = last  # a graded bonus waits for Next too, so its line is read
        return (
            f"Question {number + 1} of {QUESTIONS_PER_RACE}\n\n⭐ **{race.bonus.question}**"
            f"\n\n{turn.why}",
            False,
        )
    if last is not None and not last[1].right and not race.done and last[0] in race.typed:
        return _typed_miss(race, *last, typed), False
    if (t := race.typed.get(race.answered)) is not None:  # typed: the dock shows, no choices
        return (
            f"Question {race.answered + 1} of {QUESTIONS_PER_RACE}{hear}\n\n**{t.prompt}**",
            False,
        )
    if last is not None and not last[1].right and not race.done:
        number, turn = last
        return (
            f"Question {number + 1} of {QUESTIONS_PER_RACE}\n\n"
            f"**{race.questions[number].question}**\n\n"
            f"{miss_opener(race, number)} It's **{turn.answer}**. {turn.why}",
            False,
        )
    view = public(race)
    return (
        f"Question {view['number'] + 1} of {QUESTIONS_PER_RACE}{hear}\n\n**{view['question']}**",
        True,
    )


def _feedback(race: Race, turn: Turn, awarded: int, goal: str = "") -> str:
    slowed = f"{turn.slowed} slowed down" if turn.slowed else "Both slowed down"
    if not turn.right and not race.done:
        return ""  # the card shows the right answer and its why, until Next
    typed = (race.answered - 1) in race.typed
    if turn.right and typed and race.typed[race.answered - 1].kind == "read":  # v4.13
        line = f"✓ {turn.why or 'Right!'} Boost! {slowed} 💨"  # Claude's line, or "In order!"
    elif typed and race.typed[race.answered - 1].kind == "read":  # a reading miss at the finish
        t = race.typed[race.answered - 1]
        line = _read_miss(t, turn, miss_opener(race, race.answered - 1))  # a worry: its words
    elif turn.right and typed:  # the word or number, with its parts or how it adds up
        line = f"✓ **{turn.answer}**" + (f": {turn.why}" if turn.why else "")
        line += f" Boost! {slowed} 💨"
    else:
        line = (
            f"Right answer: boost! {slowed} 💨"
            if turn.right
            else f"{miss_opener(race, race.answered - 1)} It's **{turn.answer}**. {turn.why}"
        )
    if race.done:
        line += f"\n\nYou finished {ORDINAL[place(race)]}! ⭐ +{awarded}"
        line += f"\n\n{goal}" if goal else ""
    return line


def games_tab(
    signin: SignIn,
    desk: RaceDesk | None,
    points: PointsStore,
    header_stars: gr.Markdown,
    garage: Garage,
    speech: Speech | None = None,
) -> tuple[gr.Tab, Callable[..., list[Any]], list[Any], list[gr.Button]]:
    """The Games tab: your car and the next goal, the race, then My cars and Showroom
    (between races only).

    Returns:
        The tab, a refresh for page load (no Claude call), the components it fills, and the
        finish's topic buttons, which open Chat (main.py wires them, since it owns the tabs).
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

    def covered_tile(c: Car) -> tuple[gr.Column, gr.HTML, gr.Button]:
        with gr.Column(elem_classes="lerni-tile", min_width=0, visible=False) as col:
            return col, gr.HTML(padding=False), gr.Button(elem_classes="lerni-buy")

    with gr.Tab("Games", id="games", visible=False) as tab:
        hero = gr.HTML(elem_id="lerni-hero")  # your car and the next goal, when not racing
        passage = gr.HTML(elem_id="lerni-passage", visible=False, padding=False)  # v4.13
        track = gr.HTML(elem_id="lerni-track", visible=False)  # once a race starts
        question = gr.Markdown(elem_classes="lerni-question")  # a tap reads it aloud (race.js)
        # the hidden reader: race.js presses it for a tap on the card, or a wrong answer's why
        speak = gr.Button(elem_id="lerni-read-go", elem_classes="lerni-hide")
        hear = gr.State("")  # what it reads: "question", "why", or nothing
        read_clip = gr.Textbox(
            elem_id="lerni-clip-read", elem_classes="lerni-hide", container=False
        )  # the clip for talk.js to play
        choices = [gr.Button(visible=False, elem_classes="lerni-choice") for _ in range(3)]
        talks = speech is not None
        # the bonus: typed or spoken, like Chat's dock (talk.js drives the "bonus" parts)
        with gr.Column(
            elem_id="lerni-dock-bonus",
            visible=False,
            elem_classes="lerni-dock lerni-voice" if talks else "lerni-dock",
        ) as dock:
            if talks:
                preview = gr.Markdown(elem_id="lerni-preview-bonus")  # what's heard so far
                gr.Button("🎤\nHold to talk", elem_id="lerni-talk-bonus", elem_classes="lerni-talk")
            with gr.Row(elem_classes="lerni-type"):
                answer_box = gr.Textbox(
                    show_label=False,
                    placeholder="Explain it in your own words…",
                    lines=1,
                    max_lines=4,
                    max_length=MAX_ANSWER,
                    container=False,
                    scale=4,
                    elem_id="lerni-question-bonus",
                )
                send = gr.Button(
                    "Send", variant="primary", scale=1, min_width=70, elem_id="lerni-send-bonus"
                )
            if talks:
                gr.HTML(
                    '<div class="lerni-mode" role="group" aria-label="Talk or type">'
                    '<button type="button" data-mode="talk">🎤 Talk</button>'
                    '<button type="button" data-mode="type">⌨️ Type</button></div>'
                )
                hide = {"elem_classes": "lerni-hide", "container": False}
                clip = gr.Textbox(elem_id="lerni-clip-bonus", **hide)
                partial = gr.Textbox(elem_id="lerni-partial-bonus", **hide)
                heard_btn = gr.Button(elem_id="lerni-heard-bonus", elem_classes="lerni-hide")
                peek = gr.Button(elem_id="lerni-peek-bonus", elem_classes="lerni-hide")
            skip = gr.Button("Skip", size="sm")
        # a typed question (v4.11): its picture, the answer field, and Check
        with gr.Column(
            elem_id="lerni-dock-typed", visible=False, elem_classes="lerni-dock"
        ) as tdock:
            drawing = gr.HTML(padding=False)  # a picture's blocks; empty for a word
            with gr.Row(elem_classes="lerni-type"):
                typed_box = gr.Textbox(
                    show_label=False,
                    lines=1,
                    max_lines=1,
                    max_length=TYPED_MAX,
                    container=False,
                    scale=4,
                    elem_id="lerni-typed",
                )  # race.js: no autocorrect
                check = gr.Button(
                    "Check", variant="primary", scale=1, min_width=80, elem_classes="lerni-check"
                )  # race.js counts it as a tap
        # a writing race (v4.14): the checklist, the paragraph, Check, and Done
        with gr.Column(
            elem_id="lerni-dock-write", visible=False, elem_classes="lerni-dock"
        ) as wdock:
            checklist = gr.HTML(padding=False)
            para_box = gr.Textbox(
                show_label=False,
                placeholder="Write your paragraph here…",
                lines=5,
                max_lines=10,
                max_length=MAX_PARAGRAPH,
                container=False,
                elem_id="lerni-paragraph",
            )  # race.js: no autocorrect, capitals, or spell check
            with gr.Row():
                para_check = gr.Button("Check", variant="primary", min_width=90)
                para_done = gr.Button("Done", min_width=90, visible=False)
        note = gr.Markdown(elem_id="lerni-note")
        # at the finish: up to two nearby ideas to talk about in Chat (v3.36)
        with gr.Column(visible=False, elem_classes="lerni-explore") as explore:
            gr.Markdown("Want to find out more?")
            with gr.Row():
                topic_btns = [
                    gr.Button(visible=False, elem_classes="lerni-topic") for _ in range(2)
                ]
        go = gr.Button("Race!", variant="primary", elem_classes="lerni-go")
        next_btn = gr.Button(
            "Next", variant="primary", elem_classes="lerni-go", visible=False, elem_id="lerni-next"
        )  # race.js holds it while the why is said
        shown = gr.State(("", 0))  # the race id and question number on screen
        # tiles are built once at startup, one per car in each list; each player sees theirs
        with gr.Column() as garage_box:  # out of sight while racing, so the race has the screen
            mine_title = gr.Markdown("### 🅿️ My cars")
            with gr.Row(elem_classes="lerni-tiles"):
                mine = {c.id: tile(c) for c in garage.cars}
            gr.Markdown("### 🛒 Showroom")
            with gr.Row(elem_classes="lerni-tiles"):
                shop = {c.id: shop_tile(c) for c in garage.cars}
            coming_title = gr.Markdown(visible=False)  # v4.17: covered cars and their day
            with gr.Row(elem_classes="lerni-tiles"):
                coming = {c.id: covered_tile(c) for c in garage.coming}

    outputs = [
        header_stars,
        hero,
        track,
        question,
        *choices,
        dock,
        answer_box,
        send,
        note,
        go,
        next_btn,
        shown,
        mine_title,
        *(x for pair in mine.values() for x in pair),
        *(x for parts in shop.values() for x in parts),
        coming_title,
        *(x for parts in coming.values() for x in parts),
        garage_box,
        hear,
        explore,
        *topic_btns,
        tdock,
        drawing,
        typed_box,
        passage,
        wdock,
        checklist,
        para_box,
        para_check,
        para_done,
    ]

    def garage_updates(p: Points | None) -> list[Any]:
        """The My cars title, each car's tile and button in both lists, then the covered
        cars: the next delivery's day on the car it would bring, and a ❤️ on each."""
        sold = garage.sold(p.cars, p.arrived) if p else []
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
                ups += [
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(value=f"Buy · {c.price:,} ⭐", interactive=True),
                ]
            else:
                ups += [
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(value=f"{c.price - p.balance:,} more ⭐", interactive=False),
                ]
        waiting = garage.waiting(p.cars, p.arrived) if p and p.delivery else []
        if not waiting:  # nothing to come, or before the first day is set
            return [*ups, gr.update(visible=False), *(
                x for _ in coming for x in (gr.update(visible=False), gr.update(), gr.update())
            )]
        try:
            when = arrival_day(date.fromisoformat(p.delivery), date.today())
        except ValueError:
            when = "soon"  # a broken day: settle sets a new one
        pick = next_pick(waiting, p.hearts)  # what the delivery would bring now
        ups.append(gr.update(
            value=f"### 🚚 Arriving {when}\nTap ❤️ on the cars you want. One comes each week.",
            visible=True,
        ))
        for c in garage.coming:
            if c not in waiting:  # arrived or owned: in the Showroom or My cars
                ups += [gr.update(visible=False), gr.update(), gr.update()]
                continue
            wanted = c.id in p.hearts
            ups += [
                gr.update(visible=True),
                covered_html(c, when if c is pick else ""),  # only the pick shows the day
                gr.update(value="💖 Wanted" if wanted else "❤️ Want it", interactive=True),
            ]
        return ups

    def screen(
        viewer: Viewer | None,
        race: Race | None,
        line: str,
        last: tuple[int, Turn] | None = None,
        typed: str = "",
        fresh: bool = False,
    ) -> list[Any]:
        """Every output, in order; ``last`` is the answer just given, for the waiting card, and
        ``typed`` what was just typed, to mark a missed word (never kept); ``fresh`` empties
        the paragraph field (a new race), which otherwise keeps its text for a revision."""
        writes = race is not None and race.paragraph is not None  # a writing race (v4.14)
        writing = writes and not race.done  # its field and buttons, until the finish
        pic, kind = None, ""  # a typed slot on screen: what to draw, and its kind
        p, came = settled(points, garage, viewer.username) if viewer else (None, None)
        if came is not None and not line:  # the delivery, said once, the first time it's seen
            line = f"🚚 The {came.name} just arrived in the Showroom!"
        driving = p.car if p else STARTER
        if race is None or race.done:
            ask, buttons = "", [gr.update(visible=False) for _ in choices]
            go_update = gr.update(visible=True, value="Race again!" if race else "Race!")
            ref, waiting, live = (race.id, race.answered) if race else ("", 0), False, False
            # a wrong last answer: its right answer and why are in the note
            why = (
                race is not None
                and last is not None
                and bool(last[1].answer)
                and not (last[1].right)
            )
            reads = "why" if why else ""
            typed_live = False
        else:
            ask, show = question_card(race, last, HEAR if talks and not writes else "", typed)
            # while the why shows, the hidden buttons don't get the next question yet
            buttons = (
                [gr.update(visible=True, value=c) for c in public(race)["choices"]]
                if show
                else [gr.update(visible=False) for _ in choices]
            )
            view = public(race)
            # a reading race's open answer (v4.13) is said or typed in the bonus's dock
            spoken = (
                view.get("typed") == "read" and (view.get("picture") or {}).get("kind") == "open"
            )
            live = (race.bonus_live or spoken) and not _why_first(race, last)  # the dock
            typed_live = "typed" in view and not spoken and not _why_first(race, last)
            if typed_live:
                pic, kind = view.get("picture"), view["typed"]
            go_update, ref, waiting = (
                gr.update(visible=False),
                (race.id, race.answered),
                not (show or live or typed_live or writing),
            )
            why = _why_first(race, last)
            reads = "why" if why else "question" if show or live or typed_live else ""
            reads = "" if writes else reads  # a paragraph's prompt is read, not heard
        mine = stars(points, viewer)
        topics = (
            desk.probes_after(viewer.username, race)  # only at the finish
            if desk is not None and viewer is not None and race is not None and race.done
            else []
        )
        return [
            gr.update(value=mine, visible=bool(mine)),
            gr.update(value=hero_html(garage, p), visible=race is None),
            gr.update(
                value=track_svg(race, driving, garage, reads if talks else ""),
                visible=race is not None,
            ),
            ask,
            *buttons,
            gr.update(visible=live),
            gr.update(value=""),
            gr.update(interactive=True),
            line,
            go_update,
            gr.update(visible=waiting),
            ref,
            *garage_updates(p),
            gr.update(visible=race is None or race.done),
            reads,
            gr.update(visible=bool(topics)),
            *(
                gr.update(visible=True, value=f"🔭 {topics[i]}")
                if i < len(topics)
                else gr.update(visible=False)
                for i in range(len(topic_btns))
            ),
            gr.update(visible=typed_live),
            picture_html(pic),
            gr.update(value="", placeholder=PLACEHOLDER.get(kind, "")),  # empty for each
            gr.update(
                value=passage_html(race.passage if race else None, opened=not writes),
                visible=bool(race and race.passage and not race.done),
            ),  # above the track
            gr.update(visible=writes),  # the checklist stays up at the finish
            checklist_html(race.graded if writes else None),
            gr.update(value="", visible=writing) if fresh else gr.update(visible=writing),
            gr.update(
                visible=writing,
                interactive=True,
                value="Check again" if writes and race.graded is not None else "Check",
            ),
            gr.update(visible=writing and race.graded is not None),  # Done, after a first try
        ]

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
        return screen(viewer, race, message, fresh=True)

    def recover(request: gr.Request) -> list[Any]:
        # after an error: the race as it stands, or the start; never "Lerni is reading…"
        oops = "Something went wrong. Tap Race! 🏁"
        try:
            viewer = viewer_of(request)
            race = desk.current(viewer.username) if desk and viewer else None
            return screen(viewer, race, "" if race else oops)
        except Exception:  # noqa: BLE001 - the screen failed too: just the Race button
            ups = [gr.update() for _ in outputs]
            for part, up in (
                (note, gr.update(value=oops)),
                (go, gr.update(visible=True)),
                (send, gr.update(interactive=True)),
            ):
                ups[next(n for n, c in enumerate(outputs) if c is part)] = up
            return ups

    def on_choice(i: int) -> Callable[..., list[Any]]:
        def handler(ref: tuple[str, int], request: gr.Request) -> list[Any]:
            try:  # anything odd: the race as it stands, never a stuck screen
                viewer = viewer_of(request)
                if desk is None or viewer is None:
                    return screen(viewer, None, "")
                race, turn, awarded = pick(desk, viewer, ref[0], ref[1], i)
                goal = goal_line(garage, points.get(viewer.username)) if race and race.done else ""
                shown = after_tap(race, ref, turn, awarded, goal)
                if shown is None:
                    return [gr.update() for _ in outputs]  # a repeat tap: nothing changes
                return screen(viewer, *shown, last=(ref[1], turn) if turn else None)
            except Exception:  # noqa: BLE001 - never show what went wrong inside
                return recover(request)

        return handler

    def on_bonus(text: str, ref: tuple[str, int], request: gr.Request, said: str = "") -> list[Any]:
        try:  # anything odd: the race as it stands, never a stuck screen
            # grade the answer once (it stays in memory), then show the grade until Next
            viewer = viewer_of(request)
            if desk is None or viewer is None:
                return screen(viewer, None, "")
            race, turn, awarded = desk.answer_bonus(
                viewer.username,
                ref[0],
                ref[1],
                text or "",
                supervised=viewer.role is Role.SUPERVISED,
            )
            if turn is None and race is not None and desk.grading(race.id):
                return [gr.update() for _ in outputs]  # the first answer is still being read
            if turn is None and race is not None and race.nudge:  # one more try (v4.13)
                return screen(viewer, race, (f"🎤 {said}\n\n" if said else "") + race.nudge)
            if turn is None:  # a double send, or the race ended
                return screen(viewer, race, "" if race else "That race ended. Tap Race! 🏁")
            line = (f"🎤 {said}\n\n" if said else "") + (f"⭐ +{awarded}" if awarded else "")
            return screen(viewer, race, line, last=(ref[1], turn))
        except Exception:  # noqa: BLE001 - never show what went wrong inside
            return recover(request)

    def on_typed(text: str, ref: tuple[str, int], request: gr.Request) -> list[Any]:
        try:  # anything odd: the race as it stands, never a stuck screen
            # checked by code on the server; the text is shown on screen once and never kept
            viewer = viewer_of(request)
            if desk is None or viewer is None:
                return screen(viewer, None, "")
            if not (text or "").strip():  # an empty Check never counts as a miss
                ups = [gr.update() for _ in outputs]  # the question stays; only the note
                ups[outputs.index(note)] = TYPE_FIRST
                return ups
            race, turn, awarded = desk.typed_answer(viewer.username, ref[0], ref[1], text)
            # the next car to save for, once the race is over
            goal = goal_line(garage, points.get(viewer.username)) if race and race.done else ""
            shown = after_tap(race, ref, turn, awarded, goal)
            if shown is None:
                return [gr.update() for _ in outputs]  # a double send: nothing changes
            return screen(viewer, *shown, last=(ref[1], turn) if turn else None, typed=text)
        except Exception:  # noqa: BLE001 - never show what went wrong inside
            return recover(request)

    def on_paragraph(
        text: str, ref: tuple[str, int], request: gr.Request, done: bool = False
    ) -> list[Any]:
        try:  # anything odd: the race as it stands, and the paragraph stays in its field
            # graded on the server; the text goes to Claude and the logs, never kept elsewhere
            viewer = viewer_of(request)
            if desk is None or viewer is None:
                return screen(viewer, None, "")
            race, graded, awarded = desk.paragraph_answer(
                viewer.username, ref[0], text or "", done=done
            )
            if graded is None and race is not None and desk.grading(race.id):
                return [gr.update() for _ in outputs]  # the first Check is still being read
            if graded is None:  # blank, a double send, or the race ended
                if race is not None and race.id == ref[0] and race.done:
                    return [gr.update() for _ in outputs]  # a second Done: the finish stays
                ended = race is None or race.id != ref[0]
                return screen(viewer, race, "That race ended. Tap Race! 🏁" if ended else
                              WRITE_FIRST)
            if not race.done:  # the first try: fix what's not yet, or Done
                return screen(viewer, race, "Fix what's not yet, then Check again. Or tap Done.")
            goal = goal_line(garage, points.get(viewer.username))
            line = f"You finished {ORDINAL[place(race)]}! ⭐ +{awarded}"
            return screen(viewer, race, line + (f"\n\n{goal}" if goal else ""))
        except Exception:  # noqa: BLE001 - never show what went wrong inside
            return recover(request)

    def on_next(request: gr.Request) -> list[Any]:
        try:  # anything odd: the race as it stands, never a stuck screen
            # the next question, after the right answer and its why (a dropped race: the start)
            viewer = viewer_of(request)
            if desk and viewer and desk.just_answered(viewer.username):
                return [gr.update() for _ in outputs]  # a double tap's second half: read the why
            race = desk.current(viewer.username) if desk and viewer else None
            ended = "" if race or viewer is None else "That race ended. Tap Race! 🏁"
            return screen(viewer, race, ended)
        except Exception:  # noqa: BLE001 - never show what went wrong inside
            return recover(request)

    def on_garage(car_id: str, wants: bool = False) -> Callable[..., list[Any]]:
        def handler(request: gr.Request) -> list[Any]:
            viewer = viewer_of(request)
            message = garage_tap(points, garage, viewer, car_id, wants=wants)
            race = desk.current(viewer.username) if desk is not None and viewer else None
            return screen(viewer, race, message)

        return handler

    def on_speak(ref: tuple[str, int], reads: str, request: gr.Request) -> Any:
        # what the card shows, spoken; a fresh value each time, so a second tap replays it
        viewer = viewer_of(request)
        if desk is None or viewer is None or not reads:
            return gr.update()
        audio = (
            desk.read_why(viewer.username, ref[0], ref[1] - 1)
            if reads == "why"
            else desk.read_aloud(viewer.username, ref[0], ref[1])
        )
        if not audio:  # an empty clip for a why: Next stops waiting for it
            return json.dumps([time.monotonic(), ""]) if reads == "why" else gr.update()
        return json.dumps([time.monotonic(), base64.b64encode(audio).decode()])

    # "multiple": a tap while an older reading is still being made isn't ignored
    speak.click(
        on_speak,
        [shown, hear],
        read_clip,
        concurrency_limit=MAX_AT_ONCE,
        trigger_mode="multiple",
        **PRIVATE,
    )
    read_clip.change(
        None,
        read_clip,
        None,  # one reading at a time: a new one replaces it
        js="(v) => { if (window.lerniRace?.wants() !== false) window.lerniTalk?.say(v); }",
    )  # not after Sound off or moving on
    tab.select(on_open, None, outputs, **PRIVATE)
    # Race hides while questions are written, so extra taps can't start more races
    # the note says why it waits; progress only on the hidden Race button, so no "processing"
    # over the hero, the card, and every garage car ("hidden" still shows it on HTML)
    go.click(
        lambda: [WAIT_LINE, *(gr.update(visible=False) for _ in range(3))],
        None,
        [note, go, garage_box, explore],
        queue=False,
        **PRIVATE,
    ).then(
        on_go, None, outputs, concurrency_limit=MAX_AT_ONCE, show_progress_on=[go], **PRIVATE
    )  # side by side
    for i, button in enumerate(choices):
        button.click(on_choice(i), shown, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    next_btn.click(on_next, None, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    for trigger in (check.click, typed_box.submit):  # Check, or Return on the keyboard
        trigger(on_typed, [typed_box, shown], outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    reading = (
        lambda: ["Lerni is reading your answer… ⭐", gr.update(interactive=False)],
        None,
        [note, send],
    )  # Send waits while Claude grades
    for trigger in (send.click, answer_box.submit):
        trigger(*reading, **PRIVATE).then(
            on_bonus, [answer_box, shown], outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE
        )

    marking = (
        lambda: ["Lerni is reading your paragraph… ✏️", gr.update(interactive=False)],
        None,
        [note, para_check],
    )  # Check waits while Claude grades
    para_check.click(*marking, **PRIVATE).then(
        on_paragraph, [para_box, shown], outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE
    )

    def on_para_done(ref: tuple[str, int], request: gr.Request) -> list[Any]:
        return on_paragraph("", ref, request, done=True)  # the first try's checklist stands

    para_done.click(on_para_done, [shown], outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)

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
            on_heard, [clip, shown], outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE
        )

        def on_peek(b64: str, request: gr.Request) -> str:
            viewer = viewer_of(request)  # what's heard so far, while the button is held
            return f"🎤 {talk_preview(speech, viewer, b64)}" if viewer else ""

        peek.click(on_peek, [partial], [preview], trigger_mode="always_last", **PRIVATE)
    for car_id, button in [
        *((i, t[-1]) for i, t in mine.items()),
        *((i, t[-1]) for i, t in shop.items()),
    ]:
        button.click(on_garage(car_id), None, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE)
    for car_id, (*_, button) in coming.items():  # a covered tile's ❤️ never buys
        button.click(
            on_garage(car_id, wants=True), None, outputs, concurrency_limit=MAX_AT_ONCE, **PRIVATE
        )
    return tab, refresh, outputs, topic_btns
