"""Blocks (v4.11): picture questions toward multiplication, drawn and graded by code (spec 11).

A track of the picture questions in races (``pictures.py`` keeps its level), for a player
with a goal in the Math area. No Claude calls: code picks the sizes and works out the answer.
Standard library only.
"""

from __future__ import annotations

import random
import re
from typing import Any

from lerni.student.interests import InterestMap, mentions_set_aside

MAX_LEVEL = 6
SQUARE = ""  # no emoji matched: the page draws plain squares
MAX_TYPED = 6  # characters of an answer read; a number is never longer
SIZES = {  # level -> (rows from-to, columns from-to)
    1: ((2, 3), (2, 4)),  # up to 12, to count one by one
    2: ((2, 4), (2, 5)),
    3: ((2, 4), (2, 5)),
    4: ((2, 5), (2, 5)),
    5: ((2, 5), (2, 5)),
    6: ((3, 6), (3, 6)),  # up to 6 × 6
}
EMOJI = {  # a word in an interest's name -> the emoji drawn as blocks; squares otherwise
    "dinosaur": "🦕",
    "dino": "🦕",
    "rex": "🦖",
    "lego": "🧱",
    "brick": "🧱",
    "car": "🏎️",
    "racing": "🏎️",
    "truck": "🚚",
    "train": "🚂",
    "plane": "✈️",
    "rocket": "🚀",
    "space": "🚀",
    "planet": "🪐",
    "shark": "🦈",
    "fish": "🐟",
    "whale": "🐳",
    "ocean": "🐳",
    "dog": "🐶",
    "puppy": "🐶",
    "cat": "🐱",
    "horse": "🐴",
    "bird": "🐦",
    "butterfly": "🦋",
    "bug": "🐞",
    "insect": "🐞",
    "snake": "🐍",
    "frog": "🐸",
    "soccer": "⚽",
    "football": "🏈",
    "basketball": "🏀",
    "baseball": "⚾",
    "music": "🎵",
    "piano": "🎹",
    "guitar": "🎸",
    "art": "🎨",
    "drawing": "🎨",
    "robot": "🤖",
    "pizza": "🍕",
    "apple": "🍎",
    "flower": "🌸",
    "tree": "🌳",
    "volcano": "🌋",
    "moon": "🌙",
    "minecraft": "⛏️",
}
_WORD = re.compile(r"[a-z]+")


def emoji_for(name: str) -> str:
    """The emoji for an interest's name ("Dinosaurs" -> 🦕), or "" when none fits."""
    for word in _WORD.findall(name.casefold()):
        # "dinosaurs" and "dinosaur" both match; "cars" too
        for w in (word, word.removesuffix("s"), word.removesuffix("es")):
            if w in EMOJI:
                return EMOJI[w]
    return SQUARE


def has_math_goal(m: InterestMap) -> bool:
    """Whether a goal on the map is in the Math area (nothing set aside)."""
    return any(
        e.kind == "goal" and e.area.casefold() == "math" and not mentions_set_aside(m, e.name)
        for e in m.entries
    )


def question(
    level: int, rng: random.Random, theme: str = "", emoji: str = SQUARE
) -> tuple[str, int, dict[str, Any], str]:
    """One blocks question at ``level``: (prompt, answer, what to draw, how it adds up).

    Example:
        >>> question(2, random.Random(1), "Dinosaurs")[0]
        'Dinosaurs: 2 rows of 2. How many in all?'
    """
    (r0, r1), (c0, c1) = SIZES[min(max(level, 1), MAX_LEVEL)]  # a hand-edited level clamped
    rows, cols = rng.randint(r0, r1), rng.randint(c0, c1)  # sizes drawn within the level
    total, name = rows * cols, f"{theme}: " if theme else ""  # the label leads the prompt
    draw: dict[str, Any] = {"rows": rows, "cols": cols, "emoji": emoji, "empty": False}
    adds_up = f"{rows} rows of {cols} is {total}."  # shown after the answer
    kind = level if level < MAX_LEVEL else rng.choice((4, 5))  # the top level mixes 4 and 5
    if kind == 1:  # count them one by one
        return f"{name}How many are there? Count them all.", total, draw, adds_up
    if kind == 2:  # rows and how many in each
        return f"{name}{rows} rows of {cols}. How many in all?", total, draw, adds_up
    if kind == 3:  # turned sideways: the same total
        draw.update(rows=cols, cols=rows)
        return (
            f"{name}Turn {rows} rows of {cols} sideways: now it's {cols} rows of {rows}. "
            "How many in all?",
            total,
            draw,
            f"Turned sideways, it's still {total}.",
        )
    if kind == 4:  # the multiplication itself, with the picture
        return f"{name}{rows} × {cols} = ?", total, draw, f"{rows} × {cols} = {total}."
    draw.update(cols=0, total=total, empty=True)  # the pile, and empty rows to share it into
    return (
        f"{name}{total} in {rows} equal rows. How many in each row?",
        cols,
        draw,
        f"{total} in {rows} rows is {cols} in each.",
    )


def typed_number(text: str) -> int | None:
    """The whole number typed ("12", " 12 "), or None for anything else."""
    t = "".join(text[: MAX_TYPED + 4].split())  # spaces anywhere don't count
    return int(t) if t.isascii() and t.isdigit() and len(t) <= MAX_TYPED else None  # not "²"
