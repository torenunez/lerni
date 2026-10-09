"""Interest maps: what each student loves, the goals people set, and the bridges between.

One JSON file per student in ``<data root>/maps/``. Interests grow from the
conversation; goals and their notes come only from a person. See
``plans/specs/04-interest-map.md``. Standard library only.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeVar

from lerni.student.jsonfiles import write_json_atomic
from lerni.student.students import check_username, default_data_dir

SCHEMA = 1
MAX_ENTRIES = 60
MAX_NAME = 40
MAX_NOTES = 200
FADE_DAYS = 30  # not discussed for this long: drawn faded
# letters (any language) and digits, with spaces, hyphens, and apostrophes between
NAME_RE = re.compile(r"^[^\W_](?:[^\W_]|[' -])*$")

Kind = Literal["interest", "goal"]
T = TypeVar("T")


class MapError(ValueError):
    """A person's edit can't be made (bad name, taken, unknown entry, or a full map)."""


@dataclass
class Entry:
    """One interest or goal on a map."""

    id: str
    name: str
    kind: Kind
    notes: str = ""  # goals only
    days: list[str] = field(default_factory=list)  # ISO dates it came up, sorted
    mentions: int = 0
    # goals only: dates Lerni thinks they explained it back, and dates they bounced off a bridge
    explained: list[str] = field(default_factory=list)
    bounces: list[str] = field(default_factory=list)


@dataclass
class Link:
    """Two entries that came up together (``related``) or a bridge from an interest to a goal."""

    a: str
    b: str
    kind: Literal["related", "bridge"]
    day: str


@dataclass
class InterestMap:
    """A student's whole map."""

    entries: list[Entry] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)  # names a person removed; never re-added
    edits: int = 0  # bumped by every person's edit
    next_id: int = 1

    def find(self, name: str) -> Entry | None:
        """The entry with this name, ignoring case, or None."""
        key = name.strip().casefold()
        return next((e for e in self.entries if e.name.casefold() == key), None)

    def get(self, entry_id: str) -> Entry:
        """The entry with this id.

        Raises:
            MapError: No such entry.
        """
        entry = next((e for e in self.entries if e.id == entry_id), None)
        if entry is None:
            raise MapError("That's no longer on the map.")
        return entry

    def new_entry(self, name: str, kind: Kind, notes: str = "") -> Entry:
        """A new entry with the next id (not yet added)."""
        entry = Entry(id=f"e{self.next_id}", name=name, kind=kind, notes=notes)
        self.next_id += 1
        return entry

    def is_removed(self, name: str) -> bool:
        """Whether a person removed this name."""
        return name.casefold() in {r.casefold() for r in self.removed}


def check_name(name: str) -> str:
    """Return ``name`` tidied (single spaces) if it's a plain name of 1–40 characters.

    Raises:
        MapError: Empty, too long, or other characters.

    Example:
        >>> check_name("  monster   trucks ")
        'monster trucks'
    """
    name = " ".join((name or "").split())
    if not name or len(name) > MAX_NAME or not NAME_RE.fullmatch(name):
        raise MapError(f"Use up to {MAX_NAME} letters, digits, spaces, hyphens, or apostrophes.")
    return name


def _check_notes(notes: str) -> str:
    notes = " ".join((notes or "").split())
    if len(notes) > MAX_NOTES:
        raise MapError(f"Keep notes under {MAX_NOTES} characters.")
    return notes


def make_room(m: InterestMap) -> bool:
    """Make room for one more entry, dropping the least-seen, oldest interest if full.

    Returns:
        False if the map is full of goals (nothing the server may drop).
    """
    if len(m.entries) < MAX_ENTRIES:
        return True
    interests = [e for e in m.entries if e.kind == "interest"]
    if not interests:
        return False
    # fewest days first, then the longest ago
    drop = min(interests, key=lambda e: (len(e.days), e.days[-1] if e.days else ""))
    _forget(m, drop.id)
    return True


def _forget(m: InterestMap, entry_id: str) -> None:
    m.entries = [e for e in m.entries if e.id != entry_id]
    m.links = [k for k in m.links if entry_id not in (k.a, k.b)]


def _unremove(m: InterestMap, name: str) -> None:
    m.removed = [r for r in m.removed if r.casefold() != name.casefold()]


def add_goal(m: InterestMap, name: str, notes: str = "") -> Entry:
    """A person adds a goal; an interest with the same name becomes that goal.

    Raises:
        MapError: A bad name or notes, an existing goal, or a map full of goals.
    """
    name, notes = check_name(name), _check_notes(notes)
    existing = m.find(name)
    if existing is not None and existing.kind == "goal":
        raise MapError(f"{existing.name} is already a goal.")
    _unremove(m, name)  # a person may bring back what they removed
    if existing is not None:
        existing.kind, existing.notes = "goal", notes  # keeps its days
        entry = existing
    else:
        if not make_room(m):
            raise MapError("This map is full; remove something first.")
        entry = m.new_entry(name, "goal", notes)
        m.entries.append(entry)
    m.edits += 1
    return entry


def rename(m: InterestMap, entry_id: str, name: str) -> Entry:
    """A person renames an interest or a goal; links keep pointing at it.

    Raises:
        MapError: Unknown entry, a bad name, or a name already on the map.
    """
    entry, name = m.get(entry_id), check_name(name)
    other = m.find(name)
    if other is not None and other.id != entry_id:
        raise MapError(f"{other.name} is already on the map.")
    entry.name = name
    m.edits += 1
    return entry


def remove(m: InterestMap, entry_id: str) -> None:
    """A person removes an entry for good: only its name is kept, so it's never re-added.

    Raises:
        MapError: Unknown entry.
    """
    entry = m.get(entry_id)
    _forget(m, entry_id)
    if not m.is_removed(entry.name):
        m.removed.append(entry.name)
    m.edits += 1


def _to_dict(m: InterestMap) -> dict[str, Any]:
    return {"schema": SCHEMA, **asdict(m)}


def _from_dict(data: dict[str, Any]) -> InterestMap:
    entries = [Entry(**e) for e in data.get("entries", [])]
    links = [Link(**k) for k in data.get("links", [])]
    return InterestMap(entries, links, list(data.get("removed", [])),
                       int(data.get("edits", 0)), int(data.get("next_id", 1)))


class MapStore:
    """Every student's map on disk, changed one at a time per student."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "maps"
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _path(self, username: str) -> Path:
        # canonical usernames only, so a name can never point outside the folder
        return self.root / f"{check_username(username)}.json"

    def _lock(self, username: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(username, threading.Lock())

    def get(self, username: str) -> InterestMap:
        """``username``'s map; an empty one if they have none yet."""
        path = self._path(username)
        if not path.is_file():
            return InterestMap()
        return _from_dict(json.loads(path.read_text(encoding="utf-8")))

    def change(self, username: str, fn: Callable[[InterestMap], T]) -> T:
        """Read, change, and save ``username``'s map with no other change in between."""
        with self._lock(username):  # only the server writes maps, so a thread lock is enough
            m = self.get(username)
            result = fn(m)
            write_json_atomic(self._path(username), _to_dict(m))
            return result
