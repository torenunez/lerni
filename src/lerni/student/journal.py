"""The map journal: every change to a map, so any one can be undone and a map rebuilt.

``<data root>/maps/<user>.events.jsonl``, one JSON line per change: its number, time,
who made it (``tagger``, ``person:<username>``, ``upload``, ``educator chat``, ``admin``),
and the before and after of only what changed. The first line is a ``baseline`` holding
the whole map, so replaying the journal gives today's map. Holds what maps hold (names,
notes people wrote, ids, dates), never message text. Works on map dicts, so it needs
nothing from ``interests.py``. Standard library only.
"""

from __future__ import annotations

import copy
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from lerni.student.students import check_username, default_data_dir

COUNTERS = frozenset({"edits", "next_id", "schema"})  # change with everything, never a conflict


class JournalError(ValueError):
    """A change can't be undone (a later one touched the same items) or isn't there."""


def _key(link: dict[str, Any]) -> str:
    return f"{link.get('a')}|{link.get('b')}|{link.get('kind')}"


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any] | None:
    """What changed between two map dicts; None when nothing did."""
    out: dict[str, Any] = {}
    was = {e["id"]: e for e in before.get("entries", [])}
    now = {e["id"]: e for e in after.get("entries", [])}
    entries = {i: [was.get(i), now.get(i)] for i in {*was, *now} if was.get(i) != now.get(i)}
    if entries:
        out["entries"] = entries
    if list(was) != list(now):
        out["entry_order"] = list(now)
    old = {_key(k): k for k in before.get("links", [])}
    new = {_key(k): k for k in after.get("links", [])}
    gone = [k for key, k in old.items() if new.get(key) != k]
    added = [k for key, k in new.items() if old.get(key) != k]
    if gone or added:
        out["links"] = {"removed": gone, "added": added}
    if list(old) != list(new):
        out["link_order"] = list(new)
    fields = {
        k: [before.get(k), after.get(k)]
        for k in {*before, *after} - {"entries", "links"}
        if before.get(k) != after.get(k)
    }
    if fields:
        out["fields"] = fields
    return out or None


def _touched(changes: dict[str, Any]) -> set[str]:
    # the items a change touched: entries, links, and fields that aren't counters
    links = changes.get("links", {})
    return (
        {f"entry:{i}" for i in changes.get("entries", {})}
        | {f"link:{_key(k)}" for k in [*links.get("removed", []), *links.get("added", [])]}
        | {f"field:{f}" for f in changes.get("fields", {}) if f not in COUNTERS}
    )


def _apply(m: dict[str, Any], changes: dict[str, Any]) -> None:
    """Replay one change forward onto a map dict."""
    entries = {e["id"]: e for e in m.get("entries", [])}
    for i, (_, after) in changes.get("entries", {}).items():
        if after is None:
            entries.pop(i, None)
        else:
            entries[i] = after
    order = changes.get("entry_order") or list(entries)
    m["entries"] = [entries[i] for i in order if i in entries] + [
        e for i, e in entries.items() if i not in order
    ]
    links = {_key(k): k for k in m.get("links", [])}
    for k in changes.get("links", {}).get("removed", []):
        links.pop(_key(k), None)
    for k in changes.get("links", {}).get("added", []):
        links[_key(k)] = k
    order = changes.get("link_order") or list(links)
    m["links"] = [links[k] for k in order if k in links] + [
        k for key, k in links.items() if key not in order
    ]
    for f, (_, after) in changes.get("fields", {}).items():
        m[f] = after


def replay(events: list[dict[str, Any]], upto: int | None = None) -> dict[str, Any]:
    """The map as it was after change ``upto`` (all of them by default).

    Raises:
        JournalError: The journal has no baseline to start from.
    """
    if not events or events[0].get("by") != "baseline":
        raise JournalError("This journal has no starting point.")
    m = copy.deepcopy(events[0]["map"])
    for e in events[1:]:
        if upto is not None and e["n"] > upto:
            break
        _apply(m, e.get("changes", {}))
    return m


def undo(current: dict[str, Any], events: list[dict[str, Any]], n: int) -> dict[str, Any]:
    """``current`` with change ``n`` reversed.

    Raises:
        JournalError: No such change, or a later change touched the same items.
    """
    event = next((e for e in events if e.get("n") == n and e.get("by") != "baseline"), None)
    if event is None:
        raise JournalError(f"There's no change {n} to undo.")
    changes, mine = event.get("changes", {}), _touched(event.get("changes", {}))
    later = [e["n"] for e in events if e.get("n", 0) > n and mine & _touched(e.get("changes", {}))]
    if later:
        raise JournalError(
            f"Later changes ({', '.join(map(str, later))}) touched the same items. "
            f"To return the whole map to before change {n}, rebuild it with --upto {n - 1}."
        )
    m = copy.deepcopy(current)
    entries = {e["id"]: e for e in m.get("entries", [])}
    order = [e["id"] for e in m.get("entries", [])]
    for i, (before, _) in changes.get("entries", {}).items():
        if before is None:
            entries.pop(i, None)
        else:
            if i not in entries:  # back in about the place it had
                was = next(
                    (k for k, x in enumerate(event.get("before_order", [])) if x == i), len(order)
                )
                order.insert(min(was, len(order)), i)
            entries[i] = before
    m["entries"] = [entries[i] for i in order if i in entries]
    links = [k for k in m.get("links", []) if k not in changes.get("links", {}).get("added", [])]
    for k in changes.get("links", {}).get("removed", []):  # back in their place by date
        if _key(k) not in {_key(x) for x in links}:
            at = next(
                (j for j, x in enumerate(links) if x.get("day", "") > k.get("day", "")), len(links)
            )
            links.insert(at, k)
    m["links"] = links
    for f, (before, _) in changes.get("fields", {}).items():
        if f not in COUNTERS:
            m[f] = before
    return m


def summary(event: dict[str, Any]) -> str:
    """One line about a change, names only: "+volcanoes ~Fractions -T-Rex, 2 links"."""
    if event.get("by") == "baseline":
        return f"the map as it was ({len(event.get('map', {}).get('entries', []))} items)"
    changes, parts = event.get("changes", {}), []
    for before, after in changes.get("entries", {}).values():
        sign = "+" if before is None else "-" if after is None else "~"
        parts.append(sign + str((after or before or {}).get("name", "?")))
    links = changes.get("links", {})
    count = len({_key(k) for k in [*links.get("removed", []), *links.get("added", [])]})
    parts += [f"{count} link{'s' if count != 1 else ''}"] if count else []
    parts += [f for f in changes.get("fields", {}) if f not in COUNTERS]
    return " ".join(parts) or "no visible change"


class MapJournal:
    """Every map's journal on disk, one line appended per change."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "maps"
        self._lock = threading.Lock()

    def path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.events.jsonl"

    def read(self, username: str) -> list[dict[str, Any]]:
        """Every change, oldest first; a broken line (a crash mid-write) is skipped."""
        try:
            lines = self.path(username).read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and isinstance(record.get("n"), int):
                out.append(record)
        return out

    def record(self, username: str, before: dict[str, Any], after: dict[str, Any], by: str) -> None:
        """Append what changed (a baseline first, for a journal that's just starting)."""
        changes = diff(before, after)
        if changes is None:
            return
        with self._lock:
            events = self.read(username)
            lines = []
            if not events:
                lines.append({"n": 1, "by": "baseline", "map": before})
            n = (events[-1]["n"] if events else len(lines)) + 1
            lines.append(
                {
                    "n": n,
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "by": by,
                    "changes": changes,
                    "before_order": [e["id"] for e in before.get("entries", [])],
                }
            )
            path = self.path(username)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                for line in lines:
                    handle.write(json.dumps(line, ensure_ascii=False) + "\n")
