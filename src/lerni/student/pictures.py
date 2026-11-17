"""Picture questions in races (v4.11; tracks since v4.11.1): blocks, money, and rulers, drawn
and graded by code (spec 11).

One source for the picture kind, with a track for each: a race's picture slot goes to the
track that needs it most. One JSON file per player in ``<data root>/pictures/``: each track's
level and last few answers as right or wrong, numbers only (rule 6). A v4.11 ``blocks/`` file
is read as the blocks track until the first answer here. Standard library only.
"""

from __future__ import annotations

import random
import threading
from datetime import date
from fractions import Fraction
from pathlib import Path
from typing import Any

from lerni.student import blocks, money, ruler
from lerni.student.interests import MapStore
from lerni.student.jsonfiles import read_json, write_json_atomic
from lerni.student.race import (
    NO_HISTORY_NEED,
    RECENT,
    Checked,
    Typed,
    interest_groups,
    note_answer,
)
from lerni.student.students import check_username, default_data_dir

TRACKS = ("blocks", "money", "ruler")  # the picture kind's tracks
MAX_LEVEL = 6  # both tracks run 1 to 6
DUE_UNTIL_TOP = 3  # counts as 3 items due while a track is below the top, so pictures come
DUE_AT_TOP = 1  # every track at the top: a little practice still
CLIMB_NEED = 0.1  # a track below the top level needs a little more than one at the top
WAIT_NEED = 0.1  # each picture question a track sits out adds this to its need


def _track(raw: Any) -> dict[str, Any]:
    # one track's numbers, with a hand edit or a missing field made safe
    raw = raw if isinstance(raw, dict) else {}
    level = raw.get("level", 1)
    return {
        "level": min(max(level, 1), MAX_LEVEL) if isinstance(level, int) else 1,
        "recent": [bool(x) for x in raw.get("recent") or []],  # since the level last moved
        "history": [bool(x) for x in raw.get("history") or []][-RECENT:],  # for its need
        "waited": int(raw.get("waited") or 0),  # picture questions since it was last asked
    }


class PicturesStore:
    """Everyone's picture tracks on disk, changed one at a time."""

    def __init__(self, root: Path | None = None) -> None:
        self.base = root or default_data_dir()
        self.root = self.base / "pictures"
        self._lock = threading.Lock()  # one change at a time, so none is lost

    def _path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.json"  # a checked name: no ../ paths

    def get(self, username: str) -> dict[str, dict[str, Any]]:
        """Each track's level, recent answers, history, and last time asked."""
        data = read_json(self._path(username))
        if data is None:  # none yet: a v4.11 blocks file carries its level over
            old = read_json(self.base / "blocks" / f"{check_username(username)}.json") or {}
            data = {"tracks": {"blocks": old}}
        tracks = data.get("tracks") if isinstance(data.get("tracks"), dict) else {}
        return {name: _track(tracks.get(name)) for name in TRACKS}

    def change(self, username: str, track: str, right: bool) -> None:
        """Note one answer on ``track``; every 5, its level moves."""
        with self._lock:
            tracks = self.get(username)
            t = tracks[track]
            note_answer(t, right, MAX_LEVEL)  # the level, every 5 answers
            t["history"] = (t["history"] + [right])[-RECENT:]  # the last 10, for its need
            write_json_atomic(self._path(username), {"schema": 1, "tracks": tracks})

    def asked(self, username: str, track: str) -> None:
        """Note that ``track`` was asked: the others have waited one more question."""
        with self._lock:
            tracks = self.get(username)
            for name, t in tracks.items():  # the one asked starts over; the rest wait longer
                t["waited"] = 0 if name == track else t["waited"] + 1
            write_json_atomic(self._path(username), {"schema": 1, "tracks": tracks})


def track_need(t: dict[str, Any]) -> float:
    """How much a track needs practice: its recent miss rate, a little more below the top, and
    a little for each picture question it sat out, so a track done well still comes back."""
    history = t["history"]
    rate = history.count(False) / len(history) if history else NO_HISTORY_NEED
    climb = CLIMB_NEED if t["level"] < MAX_LEVEL else 0.0
    return rate + climb + WAIT_NEED * t["waited"]


class PicturesDesk:
    """Picture questions as typed race questions (a ``TypedSource``)."""

    kind = "picture"

    def __init__(self, store: PicturesStore, maps: MapStore) -> None:
        self.store, self.maps = store, maps
        self.rng = random.Random()  # sizes, coins, and themes; tests may replace it

    def due(self, username: str, today: date) -> int | None:
        """Practice due: more while a track is below the top; None without a Math goal."""
        if not blocks.has_math_goal(self.maps.get(username)):
            return None
        tracks = self.store.get(username)
        return DUE_UNTIL_TOP if any(t["level"] < MAX_LEVEL for t in tracks.values()) else DUE_AT_TOP

    def item(self, username: str, today: date, avoid: set[str]) -> Typed | None:
        """A question from the neediest track at its level, themed by an interest."""
        tracks = self.store.get(username)
        # the neediest track; a tie goes to the one that has waited longest
        name = max(TRACKS, key=lambda n: (track_need(tracks[n]), tracks[n]["waited"]))
        level = tracks[name]["level"]
        names = [n for n, _, _ in interest_groups(self.maps.get(username))]  # nothing set aside
        matched = [n for n in names if blocks.emoji_for(n)]  # ones with an emoji first
        theme = self.rng.choice(matched or names) if names else ""
        emoji = blocks.emoji_for(theme)  # "" for squares, or a toy for money
        try:  # so the other track wins the next tie
            self.store.asked(username, name)
        except OSError:
            pass  # a full disk: the question still comes
        if name == "ruler":  # its key an exact fraction ("3/2"); shown as "1½ in"
            prompt, length, draw, adds_up, shown = ruler.question(level, self.rng, emoji)
            return Typed(self.kind, prompt, key=str(length), label=f"ruler-{level}",
                         picture=draw, note=adds_up, answer=shown)
        if name == "money":  # its key in whole cents; shown as "$1.35" or "35¢"
            prompt, cents, draw, adds_up, dollars = money.question(level, self.rng, emoji)
            return Typed(
                self.kind,
                prompt,
                key=str(cents),
                label=f"money-{level}",
                picture=draw,
                note=adds_up,  # the note stays here until answered
                answer=money.say_cents(cents, dollars),
            )
        for _ in range(5):  # a few tries for an answer not already in this race
            prompt, answer, draw, adds_up = blocks.question(
                level, self.rng, theme.capitalize(), emoji
            )
            if str(answer) not in avoid:
                break
        return Typed(
            self.kind,
            prompt,
            key=str(answer),
            label=f"blocks-{level}",
            picture={"kind": "blocks", **draw},  # what the page draws: never the answer
            note=adds_up,  # how it adds up, after the answer
        )

    def check(self, username: str, item: Typed, text: str, today: date) -> Checked:
        """Right when the typed amount is the answer; records it on its track."""
        track = item.label.split("-")[0]  # "money-3" -> "money"
        if track == "money":  # amounts in whole cents: "1.35" and "$1.35" are both 135
            dollars = item.answer.startswith("$")
            right = money.cents_typed(text, dollars) == int(item.key)
        elif track == "ruler":  # exact: "1.5" and "1 1/2" are both 3/2
            right = ruler.length_typed(text) == Fraction(item.key)
        else:
            right = blocks.typed_number(text) == int(item.key)  # "12 " is right
        try:  # the level moves every 5 answers
            self.store.change(username, track if track in TRACKS else "blocks", right)
        except OSError:
            pass  # a full disk: the race goes on, unrecorded
        return Checked(right, item.answer or item.key, item.note)
