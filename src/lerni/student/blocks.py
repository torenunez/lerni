"""Blocks (v4.11): picture questions toward multiplication, drawn and graded by code (spec 11).

A typed race question for a player with a goal in the Math area. One JSON file per player in
``<data root>/blocks/``: the level and the last few answers as right or wrong, numbers only
(rule 6). No Claude calls: code picks the sizes and works out the answer. Standard library only.
"""

from __future__ import annotations

import random
import re
import threading
from datetime import date
from pathlib import Path
from typing import Any

from lerni.student.interests import InterestMap, MapStore, mentions_set_aside
from lerni.student.jsonfiles import read_json, write_json_atomic
from lerni.student.race import Checked, Typed, interest_groups, note_answer
from lerni.student.students import check_username, default_data_dir

MAX_LEVEL = 6
SQUARE = ""  # no emoji matched: the page draws plain squares
DUE_UNTIL_TOP = 3  # counts as 3 items due until the top level, so blocks keep coming
DUE_AT_TOP = 1  # at the top level: a little practice still
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
    return int(t) if t.isdigit() and len(t) <= MAX_TYPED else None


class BlocksStore:
    """Everyone's blocks level and recent answers on disk, changed one at a time."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "blocks"
        self._lock = threading.Lock()  # one change at a time, so none is lost

    def _path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.json"  # a checked name: no ../ paths

    def get(self, username: str) -> dict[str, Any]:
        """The level (1-6) and recent answers; level 1 when missing or broken."""
        data = read_json(self._path(username)) or {}
        level = data.get("level", 1)
        return {
            "level": min(max(level, 1), MAX_LEVEL) if isinstance(level, int) else 1,
            "recent": [bool(x) for x in data.get("recent") or []],
        }

    def change(self, username: str, right: bool) -> None:
        """Note one answer; every 5, the level moves."""
        with self._lock:
            data = self.get(username)
            note_answer(data, right, MAX_LEVEL)
            write_json_atomic(self._path(username), {"schema": 1, **data})


class BlocksDesk:
    """Blocks as typed race questions (a ``TypedSource``)."""

    kind = "picture"

    def __init__(self, store: BlocksStore, maps: MapStore) -> None:
        self.store, self.maps = store, maps
        self.rng = random.Random()  # sizes and themes; tests may replace it

    def due(self, username: str, today: date) -> int | None:
        """Practice due: more until the top level; None without a Math goal."""
        if not has_math_goal(self.maps.get(username)):
            return None
        return DUE_UNTIL_TOP if self.store.get(username)["level"] < MAX_LEVEL else DUE_AT_TOP

    def item(self, username: str, today: date, avoid: set[str]) -> Typed | None:
        """A question at the player's level, themed by one of their interests."""
        m = self.maps.get(username)
        names = [name for name, _, _ in interest_groups(m)]  # general interests, none set aside
        matched = [n for n in names if emoji_for(n)]  # ones with an emoji first
        theme = self.rng.choice(matched or names) if names else ""
        level = self.store.get(username)["level"]
        for _ in range(5):  # a few tries for an answer not already in this race
            prompt, answer, draw, adds_up = question(
                level, self.rng, theme.capitalize(), emoji_for(theme)
            )
            if str(answer) not in avoid:
                break
        return Typed(
            self.kind,
            prompt,
            key=str(answer),
            label=f"blocks-{level}",
            picture={"kind": "blocks", **draw},
            note=adds_up,  # shown after the answer, never sent before
        )

    def check(self, username: str, item: Typed, text: str, today: date) -> Checked:
        """Right when the typed number is the answer; records it for the level."""
        right = typed_number(text) == int(item.key)  # "12 " is right; "twelve" isn't
        try:  # the level moves every 5 answers
            self.store.change(username, right)
        except OSError:
            pass  # a full disk: the race goes on, unrecorded
        return Checked(right, item.key, item.note)
