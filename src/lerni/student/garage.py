"""The garage: cartoon cars drawn in code, each with a price in points (spec 09).

Every car faces right at the same scale with its wheels on one line, so any car
can race in any lane. No images, licenses, or downloads. A private garage file
for real cars comes later.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Car:
    """One car: what it's called, what it costs, and its shape (an SVG path in a 60×24 box)."""

    id: str
    name: str
    price: int
    color: str
    body: str


CARS = (
    Car("starter", "Starter hatchback", 0, "#1D9E75",
        "M4 18 L4 10 Q6 6 14 6 L30 4 Q38 4 42 10 L56 12 Q58 14 58 18 Z"),
    Car("rally", "Rally car", 30, "#378ADD",
        "M2 18 L4 11 L18 10 L26 4 L40 4 L46 10 L58 12 L58 18 Z M2 9 L8 9 L8 11 L2 11 Z"),
    Car("muscle", "Muscle car", 60, "#D85A30",
        "M2 18 L2 12 L20 11 L28 5 L42 5 L48 11 L58 12 L58 18 Z"),
    Car("truck", "Race truck", 100, "#BA7517",
        "M2 18 L2 6 L22 6 L22 2 L40 2 L44 8 L58 9 L58 18 Z"),
    Car("super", "Supercar", 150, "#E24B4A",
        "M2 18 L4 13 L22 11 L32 6 L44 7 L58 13 L58 18 Z"),
    Car("hyper", "Hypercar", 220, "#534AB7",
        "M2 18 L2 14 L18 12 L30 6 L42 6 L56 13 L58 18 Z M4 14 L6 8 L9 8 L8 14 Z"),
    Car("formula", "Formula racer", 300, "#993556",
        "M0 16 L10 14 L24 14 L28 8 L34 8 L36 13 L56 14 L60 16 L56 18 L4 18 Z "
        "M0 8 L8 8 L8 14 L0 14 Z"),
    Car("rocket", "Rocket car", 400, "#185FA5",
        "M2 18 L2 12 L44 10 L58 14 L44 18 Z M2 13 L-8 15 L2 17 Z"),
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
    return (f'<path d="{c.body}" fill="{color}"/>'
            '<circle cx="14" cy="20" r="5" fill="#2C2C2A"/>'
            '<circle cx="46" cy="20" r="5" fill="#2C2C2A"/>')


def car_svg(car_id: str, x: float, y: float, lane: str, color: str | None = None) -> str:
    """One car on the track; race.js glides the inner group when ``x`` changes."""
    c = car(car_id)
    return (f'<g transform="translate({x:.0f} {y:.0f})"><g class="lerni-racer" data-lane="{lane}" '
            f'data-x="{x:.0f}">{_drawing(c, color or c.color)}</g></g>')


def car_card_svg(car_id: str) -> str:
    """A small picture of the car for the garage list."""
    c = car(car_id)
    return (f'<svg viewBox="-10 0 72 26" width="72" height="26" role="img" '
            f'aria-label="{c.name}">{_drawing(c, c.color)}</svg>')
