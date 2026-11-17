"""Rulers (v4.11.2): measure an object on a two-sided ruler, in centimeters and inches (spec 11).

A track of the picture questions in races, beside blocks and money. Centimeters run along the
top edge and inches along the bottom, at one real scale, so the link between them is seen
every time. Lengths are exact fractions in code (half inches without floats). Standard
library only.
"""

from __future__ import annotations

import random
import re
from fractions import Fraction
from typing import Any

MAX_LEVEL = 6
RULER_CM = 12  # the ruler's length: 0 to 12 cm on top, about 4¾ inches below
CM_PER_INCH = Fraction(254, 100)  # exactly 2.54
LINK = "An inch is about 2½ cm."  # said after inches, converting, and comparing
_UNITS = re.compile(r"(centimeters?|cm|inch(es)?|in)$")  # "6 cm" or "2 inches" still reads
_DECIMAL = re.compile(r"(\d{0,3})(?:\.(\d{0,2}))?")  # "6", "1.5", ".5", "2."
_MIXED = re.compile(r"(?:(\d{1,3}) +)?(\d{1,2})/(\d{1,2})")  # "1 1/2", "1/2"


def say_length(length: Fraction, unit: str = "") -> str:
    """A length as the screen shows it: "6", "1½", "½"; with ``unit``, "6 cm" or "1½ in"."""
    whole, half = int(length), length - int(length)  # every length here is in halves
    text = (str(whole) if whole or not half else "") + ("½" if half else "")
    return f"{text} {unit}".strip()


def length_typed(text: str) -> Fraction | None:
    """A typed length, exactly: "1.5", "1 1/2", "1½", "2", or "6 cm"; None for anything else.

    Example:
        >>> length_typed("1 1/2") == length_typed("1.5") == Fraction(3, 2)
        True
    """
    t = " ".join(text.strip()[:20].lower().replace("½", " 1/2").split())  # "1½" is "1 1/2"
    t = _UNITS.sub("", t).strip()  # the unit is optional
    if not t.isascii() or not t:  # only plain digits: never "²"
        return None
    if m := _DECIMAL.fullmatch(t):
        if not (m.group(1) or m.group(2)):
            return None  # "." alone
        return int(m.group(1) or 0) + Fraction(int(m.group(2) or 0), 10 ** len(m.group(2) or ""))
    if (m := _MIXED.fullmatch(t)) and int(m.group(3)):  # never "1/0"
        return int(m.group(1) or 0) + Fraction(int(m.group(2)), int(m.group(3)))
    return None


def _bar(start_cm: Fraction, end_cm: Fraction, emoji: str, label: str = "") -> dict[str, Any]:
    # one object above the ruler, in centimeters from its 0 (floats only for drawing)
    return {"start": float(start_cm), "end": float(end_cm), "emoji": emoji, "label": label}


def question(
    level: int, rng: random.Random, emoji: str = ""
) -> tuple[str, Fraction, dict[str, Any], str, str]:
    """One ruler question at ``level``: (prompt, answer, what to draw, how to read it, the
    answer as shown).

    Example:
        >>> question(1, random.Random(4))[:2]
        ('How many centimeters long is it?', Fraction(5, 1))
    """
    kind = min(max(level, 1), MAX_LEVEL)  # a hand-edited level clamped
    thing = emoji or "✏️"  # a pencil when no interest has an emoji
    draw: dict[str, Any] = {"kind": "ruler", "bars": []}
    if kind == 1:  # the centimeter edge, from 0
        cm = Fraction(rng.randint(2, RULER_CM))
        draw["bars"] = [_bar(Fraction(0), cm, thing)]
        return (
            "How many centimeters long is it?",
            cm,
            draw,
            f"It ends at {cm} on the centimeter edge.",
            say_length(cm, "cm"),
        )
    if kind == 2:  # the inch edge, from 0
        inches = Fraction(rng.randint(1, 4))
        draw["bars"] = [_bar(Fraction(0), inches * CM_PER_INCH, thing)]
        return (
            "How many inches long is it?",
            inches,
            draw,
            f"It ends at {inches} on the inch edge. {LINK}",
            say_length(inches, "in"),
        )
    if kind == 3:  # not starting at 0: the length is end minus start
        start = Fraction(rng.randint(1, 5))
        cm = Fraction(rng.randint(2, RULER_CM - int(start)))
        draw["bars"] = [_bar(start, start + cm, thing)]
        return (
            "How many centimeters long is it?",
            cm,
            draw,
            f"It starts at {start} and ends at {start + cm}: {cm} cm.",
            say_length(cm, "cm"),
        )
    if kind == 4:  # half inches: 1½, 2½, ...
        inches = Fraction(rng.randint(1, 4)) + Fraction(1, 2)  # 4½ in is 11.4 cm: it fits
        draw["bars"] = [_bar(Fraction(0), inches * CM_PER_INCH, thing)]
        return (
            "How many inches long is it? A half is 0.5",
            inches,
            draw,
            f"It ends halfway past {int(inches)} on the inch edge. {LINK}",
            say_length(inches, "in"),
        )
    if kind == 5:  # converting: read the same object on the other edge
        inches = Fraction(rng.randint(3, 8), 2)  # 1½ to 4 inches; none lands on a .5 tie
        exact = inches * CM_PER_INCH  # 3 in is 7.62 cm
        cm = Fraction(round(exact))  # the nearest whole centimeter: 8
        other = int(exact) if cm > exact else int(exact) + 1  # the other side of it: 7
        draw["bars"] = [_bar(Fraction(0), exact, thing)]
        return (
            f"It's {say_length(inches)} inches long. How many centimeters, to the nearest one?",
            cm,
            draw,
            f"{say_length(inches)} in is {float(exact):.2f} cm, nearer {cm} than {other}.",
            say_length(cm, "cm"),
        )
    while True:  # comparing on the ruler alone: one in centimeters, one in inches
        cm, inches = rng.randint(2, RULER_CM - 1), rng.randint(1, 4)
        if abs(cm - inches * CM_PER_INCH) >= 1:  # at least 1 cm apart
            break
    first = cm > inches * CM_PER_INCH  # which is longer, by real size
    answer = Fraction(1 if first else 2)  # no bars: he finds both on the ruler's two edges
    unit = "inch" if inches == 1 else "inches"
    longer = f"{cm} cm" if first else f"{inches} {unit}"
    return (
        f"Which is longer: {cm} cm or {inches} {unit}? Find both on the ruler. "
        f"Type 1 for {cm} cm or 2 for {inches} {unit}",
        answer,
        draw,
        f"{longer} is longer. {LINK}",
        str(int(answer)),
    )
