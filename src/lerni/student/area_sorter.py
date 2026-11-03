"""Lerni sorts goals with no area into subject areas by itself (v3.37).

Areas only organize the list and the progress card; a person moves a goal with Area and Move,
and each sort is one journal line `lerni map undo` reverses. Goals themselves stay rule 5.
"""

from __future__ import annotations

import threading
from typing import Any

from lerni.student.interests import (
    MAX_NOTES,
    Entry,
    InterestMap,
    MapError,
    MapStore,
    areas,
    check_name,
    set_area,
)
from lerni.student.race import Checker

AREA_TIMEOUT_SECONDS = 20  # a save waits for it, so short; a goal left unsorted shows in Other

AREA_SYSTEM = """You sort a learner's goals into subject areas for their educator's list.
- Give each goal under "Goals to sort" exactly one area.
- Use an area from "Areas to choose from" when one fits, the way the "Already sorted" goals \
were sorted.
- Only when none fits, make a new short area (one or two words, Title Case), and put goals \
that belong together in the same new area.
- Answer only about the goals you were asked to sort, spelled exactly as given."""

AREA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"areas": {"type": "array", "items": {
        "type": "object",
        "properties": {"goal": {"type": "string"}, "area": {"type": "string"}},
        "required": ["goal", "area"],
    }}},
    "required": ["areas"],
}


def area_input(m: InterestMap, todo: list[Entry]) -> str:
    """The prompt: how the map's goals are sorted so far, the areas, and the goals to sort."""
    def line(e: Entry) -> str:
        return f"- {e.name}" + (f" (notes: {e.notes[:MAX_NOTES]})" if e.notes else "")

    done = [f"- {e.name}: {e.area}" for e in m.entries if e.kind == "goal" and e.area]
    return "\n".join(["Already sorted:", *(done or ["(none yet)"]),
                      f"Areas to choose from: {', '.join(areas(m))}",
                      "Goals to sort:", *(line(e) for e in todo)])


def parse_areas(raw: dict[str, Any], todo: list[Entry]) -> dict[str, str]:
    """Goal id → area, for the asked goals only, each area a plain name."""
    ids = {e.name.casefold(): e.id for e in todo}
    picks: dict[str, str] = {}
    for item in raw.get("areas") or []:
        if not isinstance(item, dict):
            continue
        goal_id = ids.get(str(item.get("goal", "")).strip().casefold())
        try:
            area = check_name(str(item.get("area", "")))
        except MapError:
            continue  # an odd area: that goal stays in Other
        if goal_id and area.casefold() != "other":
            picks.setdefault(goal_id, area)
    return picks


class AreaSorter:
    """Gives each goal with no area one, with one small-model call per sort."""

    def __init__(self, writer: Checker, maps: MapStore) -> None:
        self.writer, self.maps = writer, maps
        self._guard = threading.Lock()
        self._busy: set[tuple[str, str]] = set()  # goals being sorted now
        self._tried: set[tuple[str, str]] = set()  # goals Claude couldn't sort: not again

    def sort(self, username: str) -> int:
        """Sort ``username``'s goals with no area; returns how many got one. Never raises."""
        m = self.maps.get(username)
        with self._guard:
            todo = [e for e in m.entries if e.kind == "goal" and not e.area
                    and (username, e.id) not in self._busy | self._tried]
            keys = {(username, e.id) for e in todo}
            self._busy |= keys
        if not todo:
            return 0
        picks: dict[str, str] = {}
        try:
            raw = self.writer.write(AREA_SYSTEM, area_input(m, todo), AREA_SCHEMA,
                                    AREA_TIMEOUT_SECONDS)
            picks = parse_areas(raw, todo)

            def apply(m: InterestMap) -> int:
                n = 0
                for goal_id, area in picks.items():
                    try:
                        e = m.get(goal_id)
                    except MapError:
                        continue  # removed meanwhile
                    if e.kind == "goal" and not e.area:  # a person's area always wins
                        set_area(m, goal_id, area)
                        n += 1
                return n

            return self.maps.change(username, apply, by="lerni") if picks else 0
        except Exception:  # noqa: BLE001 - resting or no answer: those goals wait in Other
            return 0
        finally:
            with self._guard:
                self._busy -= keys
                self._tried |= {(username, i) for _, i in keys if i not in picks}
