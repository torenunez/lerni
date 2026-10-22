"""The map journal: every change to a map, so any one can be undone and a map rebuilt.

``<data root>/maps/<user>.events.jsonl``, one JSON line per change: its number, time,
who made it (``tagger``, ``person:<username>``, ``upload``, ``educator chat``, ``admin``),
the before and after of only what changed, and a hash of the map after it. A ``baseline``
line holds a whole map: the first line, and again whenever the map changed outside the
journal (a rollback, a failed write), so replaying from the latest baseline always gives
today's map. Holds what maps hold (names, notes people wrote, ids, dates), never message
text. Works on map dicts, so it needs nothing from ``interests.py``. Standard library only.
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from lerni.student.students import check_username, default_data_dir

COUNTERS = frozenset({"edits", "next_id", "schema"})  # change with everything, never a conflict
GROWS = ("days", "mentions", "aliases", "explained", "bounces")  # what talking about it adds
TAIL = 65536  # bytes read at a time from the end, to find the last line


class JournalError(ValueError):
    """A change can't be undone (a later one changed the same items) or isn't there."""


def _key(link: dict[str, Any]) -> str:
    return f"{link.get('a')}|{link.get('b')}|{link.get('kind')}"


def map_hash(m: dict[str, Any]) -> str:
    """A short fingerprint of a map dict, to tell whether it changed outside the journal."""
    return hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()[:16]


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any] | None:
    """What changed between two map dicts; None when nothing did."""
    out: dict[str, Any] = {}
    was = {e["id"]: e for e in before.get("entries", [])}
    now = {e["id"]: e for e in after.get("entries", [])}
    entries = {i: [was.get(i), now.get(i)] for i in now if was.get(i) != now.get(i)}
    entries.update({i: [e, None] for i, e in was.items() if i not in now})
    if entries:
        out["entries"] = entries
    if list(now) != [i for i in was if i in now]:  # an item added or moved: keep the order
        out["entry_order"] = list(now)
    old = {_key(k): k for k in before.get("links", [])}
    new = {_key(k): k for k in after.get("links", [])}
    gone = [k for key, k in old.items() if new.get(key) != k]
    added = [k for key, k in new.items() if old.get(key) != k]
    if gone or added:
        out["links"] = {"removed": gone, "added": added}
    # the order a replay gives anyway: unchanged links in place, changed ones at the end
    natural = [key for key in old if new.get(key) == old[key]] + [_key(k) for k in added]
    if list(new) != natural:
        out["link_order"] = list(new)
    fields = {
        k: [before.get(k), after.get(k)]
        for k in sorted({*before, *after} - {"entries", "links"})
        if before.get(k) != after.get(k)
    }
    if fields:
        out["fields"] = fields
    return out or None


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
        JournalError: No baseline at or before that point.
    """
    upto = events[-1]["n"] if upto is None and events else upto
    bases = [e for e in events if e.get("by") == "baseline" and e["n"] <= (upto or 0)]
    if not bases:
        raise JournalError("This journal has no starting point before that change.")
    m = copy.deepcopy(bases[-1]["map"])
    for e in events:
        if bases[-1]["n"] < e["n"] <= (upto or 0) and e.get("by") != "baseline":
            _apply(m, e.get("changes", {}))
    return m


def _grew(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    # an entry that was only talked about more: new days, mentions, names; nothing else moved
    if before is None or after is None:
        return False
    same = all(before.get(k) == after.get(k) for k in {*before, *after} - set(GROWS))
    lists = all(
        not Counter(before.get(k, [])) - Counter(after.get(k, [])) for k in GROWS if k != "mentions"
    )
    return same and lists and after.get("mentions", 0) >= before.get("mentions", 0)


def _link_grew(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    # a link that only came up on more days
    if before is None or after is None:
        return False
    same = all(before.get(k) == after.get(k) for k in {*before, *after} - {"day", "days"})
    return same and set(before.get("days", [])) <= set(after.get("days", []))


def _link_pairs(changes: dict[str, Any]) -> dict[str, list[Any]]:
    # each link key a change touched: [before, after] (None where it wasn't there)
    pairs: dict[str, list[Any]] = {}
    for k in changes.get("links", {}).get("removed", []):
        pairs.setdefault(_key(k), [None, None])[0] = k
    for k in changes.get("links", {}).get("added", []):
        pairs.setdefault(_key(k), [None, None])[1] = k
    return pairs


def _since(base: dict[str, Any], later: dict[str, Any], now: dict[str, Any]) -> dict[str, Any]:
    # ``base`` plus whatever ``now`` gained after ``later``: the growth since a change, kept
    out = copy.deepcopy(base)
    for k in GROWS:
        if k == "mentions":
            out[k] = base.get(k, 0) + max(0, now.get(k, 0) - later.get(k, 0))
            continue
        extra = list((Counter(now.get(k, [])) - Counter(later.get(k, []))).elements())
        merged = [
            *base.get(k, []),
            *(x for x in extra if k == "bounces" or x not in base.get(k, [])),
        ]
        out[k] = sorted(merged) if k in ("days", "explained", "bounces") else merged
    return out


def undo(current: dict[str, Any], events: list[dict[str, Any]], n: int) -> dict[str, Any]:
    """``current`` with change ``n`` reversed, keeping what only grew since (new days,
    mentions, names); the caller checks the result against the map's rules.

    Raises:
        JournalError: No such change, or a later change did more than grow the same items.
    """
    event = next((e for e in events if e.get("n") == n and e.get("by") != "baseline"), None)
    if event is None:
        raise JournalError(f"There's no change {n} to undo.")
    changes = event.get("changes", {})
    mine_links, mine_fields = _link_pairs(changes), set(changes.get("fields", {})) - COUNTERS
    blocked = []
    for e in events:
        if e.get("n", 0) <= n or e.get("by") == "baseline":
            continue
        later = e.get("changes", {})
        if (
            any(
                not _grew(*later["entries"][i])
                for i in changes.get("entries", {})
                if i in later.get("entries", {})
            )
            or any(not _link_grew(*p) for key, p in _link_pairs(later).items() if key in mine_links)
            or mine_fields & set(later.get("fields", {}))
        ):
            blocked.append(e["n"])
    if blocked:
        raise JournalError(
            f"Later changes ({', '.join(map(str, blocked))}) changed the same items. "
            f"To return the whole map to before change {n}, rebuild it with --upto {n - 1}."
        )
    m = copy.deepcopy(current)
    entries = {e["id"]: e for e in m.get("entries", [])}
    order = [e["id"] for e in m.get("entries", [])]
    for i, (before, after) in changes.get("entries", {}).items():
        if before is None:
            entries.pop(i, None)
            continue
        now = entries.get(i)
        if i not in entries:  # back in about the place it had
            was = event.get("before_order", [])
            order.insert(min(was.index(i) if i in was else len(order), len(order)), i)
        entries[i] = _since(before, after, now) if now is not None and after is not None else before
    m["entries"] = [entries[i] for i in order if i in entries]
    links = {_key(k): k for k in m.get("links", [])}
    kept = [k for k in m.get("links", [])]
    for key, (before, after) in mine_links.items():
        now = links.get(key)
        kept = [k for k in kept if _key(k) != key]
        if before is None:
            continue  # a link the change made goes
        if now is not None and after is not None:  # it came up on more days since: keep them
            days = sorted(
                {*before.get("days", []), *(set(now.get("days", [])) - set(after.get("days", [])))}
            )
            before = {**before, "days": days, "day": days[-1] if days else before.get("day")}
        at = next(
            (j for j, x in enumerate(kept) if x.get("day", "") > before.get("day", "")), len(kept)
        )
        kept.insert(at, before)  # back in its place by date
    m["links"] = kept
    for f, (before, _) in changes.get("fields", {}).items():
        if f not in COUNTERS:
            m[f] = before
    return m


def summary(event: dict[str, Any]) -> str:
    """One line about a change, names only: "+volcanoes ~Fractions -T-Rex 2 links"."""
    if event.get("by") == "baseline":
        return f"the map as it was ({len(event.get('map', {}).get('entries', []))} items)"
    changes, parts = event.get("changes", {}), []
    for before, after in changes.get("entries", {}).values():
        sign = "+" if before is None else "-" if after is None else "~"
        parts.append(sign + str((after or before or {}).get("name", "?")))
    count = len(_link_pairs(changes))
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

    def last(self, username: str) -> dict[str, Any] | None:
        """The newest whole line, read from the end of the file (a journal grows for good)."""
        try:
            handle = self.path(username).open("rb")
        except OSError:
            return None
        with handle:
            pos = handle.seek(0, 2)
            buf = b""
            while pos > 0:
                step = min(TAIL, pos)
                pos -= step
                handle.seek(pos)
                buf = handle.read(step) + buf
                lines = buf.split(b"\n")
                for raw in reversed(lines if pos == 0 else lines[1:]):  # [0] may be cut
                    try:
                        record = json.loads(raw)
                    except ValueError:
                        continue
                    if isinstance(record, dict) and isinstance(record.get("n"), int):
                        return record
        return None

    def record(self, username: str, before: dict[str, Any], after: dict[str, Any], by: str) -> None:
        """Append what changed; first a baseline, if the map changed outside the journal."""
        changes = diff(before, after)
        if changes is None:
            return
        with self._lock:
            last = self.last(username)
            n, lines = (last["n"] if last else 0), []
            if last is None or last.get("hash") != map_hash(before):  # new, or out of step
                n += 1
                lines.append({"n": n, "by": "baseline", "map": before, "hash": map_hash(before)})
            lines.append(
                {
                    "n": n + 1,
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "by": by,
                    "changes": changes,
                    "before_order": [e["id"] for e in before.get("entries", [])],
                    "hash": map_hash(after),
                }
            )
            path = self.path(username)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a+b") as handle:
                start = b""
                if handle.seek(0, 2) > 0:  # a cut-off last line never swallows this one
                    handle.seek(-1, 2)
                    start = b"" if handle.read(1) == b"\n" else b"\n"
                handle.write(
                    start
                    + b"".join(json.dumps(x, ensure_ascii=False).encode() + b"\n" for x in lines)
                )
