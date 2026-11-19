"""The garage: cartoon cars drawn in code, and real cars from a private file (spec 09).

Every car faces right at the same scale with its wheels on one line, so any car
can race in any lane. Real cars' pictures and facts live only on the home server.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lerni.student.schedule import next_delivery
from lerni.student.students import default_data_dir


@dataclass(frozen=True)
class Car:
    """One car: what it's called, what it costs, and its shape (an SVG path in a 60×24 box)."""

    id: str
    name: str
    price: int
    color: str
    body: str
    usd: int = 0  # real cars: price in dollars
    zero_to_60: float = 0.0  # seconds; 0 for cartoon cars
    engine: str = ""
    power_hp: int = 0
    drive: str = ""
    note: str = ""  # e.g. "Limited to 250 cars"
    picture: str = ""  # a file in <data>/cars/
    coming: bool = False  # covered until its delivery day (v4.17)


CARS = (
    Car(
        "starter",
        "Starter hatchback",
        0,
        "#1D9E75",
        "M4 18 L4 10 Q6 6 14 6 L30 4 Q38 4 42 10 L56 12 Q58 14 58 18 Z",
    ),
    Car(
        "rally",
        "Rally car",
        30,
        "#378ADD",
        "M2 18 L4 11 L18 10 L26 4 L40 4 L46 10 L58 12 L58 18 Z M2 9 L8 9 L8 11 L2 11 Z",
    ),
    Car(
        "muscle",
        "Muscle car",
        60,
        "#D85A30",
        "M2 18 L2 12 L20 11 L28 5 L42 5 L48 11 L58 12 L58 18 Z",
    ),
    Car("truck", "Race truck", 100, "#BA7517", "M2 18 L2 6 L22 6 L22 2 L40 2 L44 8 L58 9 L58 18 Z"),
    Car("super", "Supercar", 150, "#E24B4A", "M2 18 L4 13 L22 11 L32 6 L44 7 L58 13 L58 18 Z"),
    Car(
        "hyper",
        "Hypercar",
        220,
        "#534AB7",
        "M2 18 L2 14 L18 12 L30 6 L42 6 L56 13 L58 18 Z M4 14 L6 8 L9 8 L8 14 Z",
    ),
    Car(
        "formula",
        "Formula racer",
        300,
        "#993556",
        "M0 16 L10 14 L24 14 L28 8 L34 8 L36 13 L56 14 L60 16 L56 18 L4 18 Z "
        "M0 8 L8 8 L8 14 L0 14 Z",
    ),
    Car(
        "rocket",
        "Rocket car",
        400,
        "#185FA5",
        "M2 18 L2 12 L44 10 L58 14 L44 18 Z M2 13 L-8 15 L2 17 Z",
    ),
)
_BY_ID = {c.id: c for c in CARS}


def car(car_id: str) -> Car:
    """The car with this id.

    Raises:
        KeyError: No such car.
    """
    return _BY_ID[car_id]


def _drawing(c: Car, color: str) -> str:
    # the body, then two wheels on the same line for every car
    return (
        f'<path d="{c.body}" fill="{color}"/>'
        '<circle cx="14" cy="20" r="5" fill="#2C2C2A"/>'
        '<circle cx="46" cy="20" r="5" fill="#2C2C2A"/>'
    )


def car_svg(car_id: str, x: float, y: float, lane: str, color: str | None = None) -> str:
    """One car on the track; race.js glides the inner group when ``x`` changes."""
    c = car(car_id)
    return (
        f'<g transform="translate({x:.0f} {y:.0f})"><g class="lerni-racer" data-lane="{lane}" '
        f'data-x="{x:.0f}">{_drawing(c, color or c.color)}</g></g>'
    )


def car_card_svg(car_id: str) -> str:
    """A small picture of the car for the garage list."""
    c = car(car_id)
    return (
        f'<svg viewBox="-10 0 72 26" width="72" height="26" role="img" '
        f'aria-label="{c.name}">{_drawing(c, c.color)}</svg>'
    )


PRICE_PER_STAR = 2500  # dollars per ⭐
PRICE_STEP = 10  # prices round to tens of ⭐
MAX_USD = 1_000_000_000  # no real car costs more
BASE_0_60, MAX_BOOST = 4.0, 1.4  # a 4-second car gets no boost; none gets more than ×1.4
_ID = re.compile(r"^[a-z0-9-]{1,40}$")
_PICTURE = re.compile(r"^[a-z0-9-]{1,40}\.(webp|png)$")


def boost(c: Car) -> float:
    """How far a right answer's gas pushes this car: √(4.0 s ÷ its 0–60), ×1.0 to ×1.4."""
    if c.zero_to_60 <= 0:
        return 1.0  # cartoon cars
    return min(MAX_BOOST, max(1.0, math.sqrt(BASE_0_60 / c.zero_to_60)))


FAMILY_CAR_USD = 50_000  # about what a new family car costs
STARS_PER_RACE = 13  # about what a race earns, for "about N races"
MAX_IN_REACH = 4  # cars whose facts race questions may use


def bolts(c: Car) -> int:
    """How fast a car feels, as 1 to 5 ⚡, from its gas boost."""
    return 1 + round((boost(c) - 1) / (MAX_BOOST - 1) * 4)


def family_cars(usd: int) -> str:
    """A price anyone can picture; "" for a car with no price in dollars."""
    if usd <= 0:
        return ""
    if usd < FAMILY_CAR_USD * 1.5:
        return "about the price of a family car"
    return f"as much as {round(usd / FAMILY_CAR_USD):,} family cars 🚗"


def next_goal(cars: Sequence[Car], owned: Collection[str], balance: int) -> tuple[Car | None, str]:
    """The car to save for next, and the line that says how far off it is."""
    wanted = sorted((c for c in cars if c.id not in owned), key=lambda c: c.price)
    if not wanted:
        return None, "Every car is yours! 🏆"
    later = [c for c in wanted if c.price > balance]
    if not later:
        return wanted[-1], f"You can get the {wanted[-1].name} now!"
    goal = later[0]
    races = math.ceil((goal.price - balance) / STARS_PER_RACE)
    plural = "" if races == 1 else "s"
    return goal, f"{goal.name} · ⭐ {balance:,} / {goal.price:,} · about {races} race{plural}"


def next_pick(waiting: Sequence[Car], hearts: Collection[str]) -> Car:
    """The car that comes next: the cheapest one hearted, or the cheapest when none is
    (so an affordable car keeps coming). ``waiting`` is never empty."""
    wanted = [c for c in waiting if c.id in hearts] or list(waiting)
    return min(wanted, key=lambda c: (c.price, c.id))  # id breaks a tie the same way each time


def arrival_day(day: date, today: date) -> str:
    """When a delivery comes, in words: "today", "tomorrow", a weekday, or a date."""
    days = (day - today).days
    if days <= 0:
        return "today"  # due: it arrives the next time Games opens
    if days == 1:
        return "tomorrow"
    return f"{day:%A}" if days <= 7 else f"{day:%b} {day.day}"  # "Friday", or "Nov 28"


class Garage:
    """The cartoon cars in code, plus real cars from the home server's private garage file."""

    def __init__(self, root: Path | None = None) -> None:
        self.folder = (root or default_data_dir()) / "cars"
        real = sorted(
            self._load((root or default_data_dir()) / "garage.json"), key=lambda c: c.price
        )
        self.cars = (CARS[0], *real, *CARS[1:])  # starter, real cars cheapest first, other cartoons
        self._by_id = {c.id: c for c in self.cars}
        self._real = {c.id for c in real}
        self.coming = tuple(c for c in real if c.coming)  # covered cars, cheapest first

    def _load(self, path: Path) -> list[Car]:
        try:
            items = json.loads(path.read_text(encoding="utf-8")).get("cars", [])
        except (OSError, ValueError, AttributeError):
            return []  # no file, or a broken one: the cartoon garage
        cars = []
        for item in items if isinstance(items, list) else []:
            try:
                usd, picture = int(item["usd"]), str(item["picture"])
                c = Car(
                    str(item["id"]),
                    str(item["name"]),
                    max(PRICE_STEP, round(usd / PRICE_PER_STAR / PRICE_STEP) * PRICE_STEP),
                    "#000",
                    "",
                    usd,
                    float(item["zero_to_60"]),
                    str(item.get("engine", "")),
                    int(item.get("power_hp", 0)),
                    str(item.get("drive", "")),
                    str(item.get("note", "")),
                    picture,
                    item.get("coming") is True,  # only a real true covers it
                )
            except (KeyError, TypeError, ValueError, OverflowError):
                continue  # a bad entry is skipped alone
            if (
                _ID.fullmatch(c.id)
                and _PICTURE.fullmatch(picture)
                and 0 < usd <= MAX_USD
                and 0 < c.zero_to_60
                and math.isfinite(c.zero_to_60)
                and c.id not in _BY_ID
                and c.id not in {x.id for x in cars}  # no repeats
                and (self.folder / picture).is_file()
            ):
                cars.append(c)
        return cars

    def car(self, car_id: str) -> Car:
        """The car with this id.

        Raises:
            KeyError: No such car.
        """
        return self._by_id[car_id]

    def picture(self, car_id: str) -> Path | None:
        """A real car's picture on disk; None for anything else (never a path from a request)."""
        c = self._by_id.get(car_id)
        return self.folder / c.picture if c is not None and c.id in self._real else None

    def here(self, c: Car, owned: Collection[str], arrived: Collection[str]) -> bool:
        """A real car is here unless it's covered and hasn't arrived for this player."""
        return c.id in self._real and (not c.coming or c.id in arrived or c.id in owned)

    def sold(self, owned: Collection[str], arrived: Collection[str] = ()) -> list[Car]:
        """What this player's garage lists: the starter, real cars that are here, and cartoon
        cars they own. Without ``arrived``, no covered car is sold (the safe default)."""
        return [c for c in self.cars
                if c.id == "starter" or self.here(c, owned, arrived) or c.id in owned]

    def in_reach(
        self, owned: Collection[str], balance: int, arrived: Collection[str] = ()
    ) -> list[Car]:
        """Real cars here that they own or can afford (the Showroom shows these facts),
        fastest first."""
        near = [c for c in self.cars  # a covered car's facts wait for its delivery
                if self.here(c, owned, arrived) and (c.id in owned or c.price <= balance)]
        return sorted(near, key=lambda c: c.zero_to_60)[:MAX_IN_REACH]

    def waiting(self, owned: Collection[str], arrived: Collection[str]) -> list[Car]:
        """Covered cars still to come for this player, cheapest first."""
        return [c for c in self.coming if c.id not in arrived and c.id not in owned]

    def deliver(
        self, owned: Collection[str], hearts: Collection[str], arrived: Collection[str],
        delivery: str, today: date,
    ) -> tuple[str | None, str]:
        """The car arriving now (or None) and the next delivery day ("" with none to come).

        A delivery day, once set, never moves; on or after it, one car comes (``next_pick``),
        and the next day is the first delivery day after today, so weeks away don't pile up.
        """
        waiting = self.waiting(owned, arrived)
        if not waiting:
            return None, ""  # nothing to come: no day shown
        if not delivery:
            return None, next_delivery(today).isoformat()  # first seen: the next Friday
        try:
            due = date.fromisoformat(delivery)
        except ValueError:
            return None, next_delivery(today).isoformat()  # a broken day starts again
        if due > today:
            return None, delivery  # still on its way
        car = next_pick(waiting, hearts)
        later = len(waiting) > 1  # another to come after this one
        return car.id, next_delivery(today).isoformat() if later else ""

    def rivals(
        self, owned: Collection[str], driving: str, balance: int, arrived: Collection[str] = ()
    ) -> tuple[Car | None, Car | None]:
        """The fast and slow lanes' cars; None where a bot drives instead.

        Fast: the car they save for, or with every car theirs, their fastest other one.
        Slow: their fastest owned car no faster than the one they drive.
        """
        mine = [c for c in self.sold(owned) if c.id in owned and c.id != driving]
        mine.sort(key=boost, reverse=True)
        fast, _ = next_goal(self.sold(owned, arrived), owned, balance)
        if fast is None and mine:
            fast = mine[0]
        try:
            limit = boost(self.car(driving))
        except KeyError:
            limit = 1.0  # a car gone from the garage file drives like the starter
        slow = next((c for c in mine if boost(c) <= limit and c is not fast), None)
        return fast, slow

    def svg(self, car_id: str, x: float, y: float, lane: str) -> str:
        """A car on the track: a real car's picture, or a cartoon drawing."""
        if car_id not in self._real:
            return car_svg(car_id if car_id in _BY_ID else "starter", x, y, lane)
        return (
            f'<g transform="translate({x:.0f} {y:.0f})"><g class="lerni-racer" data-lane="{lane}" '
            f'data-x="{x:.0f}"><image href="/cars/{car_id}" x="-6" y="0" width="72" height="26" '
            'preserveAspectRatio="xMidYMax meet"/></g></g>'
        )
