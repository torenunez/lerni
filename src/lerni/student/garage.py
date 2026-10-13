"""The garage: cartoon cars drawn in code, each with a price in points (spec 09).

Every car faces right at the same scale with its wheels on one line, so any car
can race in any lane. No images, licenses, or downloads. A private garage file
for real cars comes later.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

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
BASE_0_60, MAX_BOOST = 4.0, 1.4  # a 4-second car gets no boost; none gets more than ×1.4
_ID = re.compile(r"^[a-z0-9-]{1,40}$")
_PICTURE = re.compile(r"^[a-z0-9-]{1,40}\.(webp|png)$")


def boost(c: Car) -> float:
    """How far a right answer's gas pushes this car: √(4.0 s ÷ its 0–60), ×1.0 to ×1.4."""
    if c.zero_to_60 <= 0:
        return 1.0  # cartoon cars
    return min(MAX_BOOST, max(1.0, math.sqrt(BASE_0_60 / c.zero_to_60)))


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
                    round(usd / PRICE_PER_STAR),
                    "#000",
                    "",
                    usd,
                    float(item["zero_to_60"]),
                    str(item.get("engine", "")),
                    int(item.get("power_hp", 0)),
                    str(item.get("drive", "")),
                    str(item.get("note", "")),
                    picture,
                )
            except (KeyError, TypeError, ValueError):
                continue  # a bad entry is skipped alone
            if (
                _ID.fullmatch(c.id)
                and _PICTURE.fullmatch(picture)
                and usd > 0
                and c.zero_to_60 > 0
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

    def sold(self, owned: list[str]) -> list[Car]:
        """What this player's garage lists: the starter, real cars, and cartoon cars they own."""
        return [c for c in self.cars if c.id == "starter" or c.id in self._real or c.id in owned]

    def svg(self, car_id: str, x: float, y: float, lane: str) -> str:
        """A car on the track: a real car's picture, or a cartoon drawing."""
        if car_id not in self._real:
            return car_svg(car_id if car_id in _BY_ID else "starter", x, y, lane)
        return (
            f'<g transform="translate({x:.0f} {y:.0f})"><g class="lerni-racer" data-lane="{lane}" '
            f'data-x="{x:.0f}"><image href="/cars/{car_id}" x="-6" y="0" width="72" height="26" '
            'preserveAspectRatio="xMidYMax meet"/></g></g>'
        )
