"""The usage meter (v4.12): what each Claude call cost, by feature, as numbers and labels only.

The calling code names its use with ``using("race-write")``; the adapter reads it with
``current_use`` when a call ends and adds one line to ``usage/<day>.jsonl``: the use, the
model, tokens, seconds, whether it failed, and the plan's window shares after it. Never a
username, a prompt, or a reply (rule 6). Standard library only.
"""

from __future__ import annotations

import contextvars
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from lerni.student.students import default_data_dir

KEEP_DAYS = 90  # usage lines kept this long, then deleted
_USE: contextvars.ContextVar[str] = contextvars.ContextVar("lerni_use", default="")


@contextmanager
def using(name: str) -> Iterator[None]:
    """Name the Claude calls made inside this block (``with using("race-write"):``)."""
    token = _USE.set(name)
    try:
        yield
    finally:
        _USE.reset(token)  # the name never leaks past the block


def current_use(default: str) -> str:
    """The use named by the nearest ``using``, or ``default`` (the adapter's own kind)."""
    return _USE.get() or default


class UsageLog:
    """Claude usage lines on disk, one file per day, appended one line at a time."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "usage"
        self._lock = threading.Lock()  # one line at a time, never interleaved

    def add(self, record: dict[str, Any], now: datetime | None = None) -> None:
        """Append one call's numbers to today's file (best effort: never fails a call)."""
        now = now or datetime.now()
        line = {"at": now.isoformat(timespec="seconds"), **record}  # to the second: enough
        try:
            with self._lock:
                self.root.mkdir(parents=True, exist_ok=True)  # made by the first call
                # one file per day, so old days are deleted whole
                with (self.root / f"{now.date().isoformat()}.jsonl").open(
                    "a", encoding="utf-8"
                ) as handle:
                    handle.write(json.dumps(line) + "\n")  # one call, one line
        except OSError:
            pass  # a full disk: the answer still comes

    def read(self, since: date, until: date | None = None) -> list[dict[str, Any]]:
        """Every line from ``since`` to ``until`` (today), oldest first; broken lines skipped."""
        out: list[dict[str, Any]] = []
        day, last = since, until or date.today()
        while day <= last:  # one file per day
            try:
                lines = (self.root / f"{day.isoformat()}.jsonl").read_text(encoding="utf-8")
            except OSError:
                lines = ""  # no calls that day
            for line in lines.splitlines():
                try:
                    record = json.loads(line)
                except ValueError:
                    continue  # a line cut short by a crash
                if isinstance(record, dict):  # anything else is skipped like a broken line
                    out.append(record)
            day += timedelta(days=1)  # the next day's file
        return out

    def prune(self, today: date | None = None) -> int:
        """Delete days older than 90; returns how many files went."""
        cutoff = (today or date.today()) - timedelta(days=KEEP_DAYS)  # older than this goes
        gone = 0  # files deleted
        for path in self.root.glob("*.jsonl") if self.root.is_dir() else []:
            try:
                if date.fromisoformat(path.stem) < cutoff:
                    path.unlink()
                    gone += 1
            except (ValueError, OSError):
                continue  # not a day's file, or already gone
        return gone


def by_feature(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each use's totals, most window movement first: calls, tokens, seconds, failures, and
    how far each window moved on its calls (a window's share since the call before)."""
    totals: dict[str, dict[str, Any]] = {}
    last: dict[str, tuple[float, int]] = {}  # window -> (share, resets at) at the call before
    for r in sorted(lines, key=lambda r: str(r.get("at", ""))):  # in time order
        t = totals.setdefault(  # a feature's first call starts its row at zero
            str(r.get("use") or "unknown"),
            {
                "use": str(r.get("use") or "unknown"),
                "calls": 0,
                "in": 0,
                "out": 0,
                "cached": 0,
                "cache_write": 0,
                "seconds": 0.0,
                "failed": 0,
                "five_hour": 0.0,
                "seven_day": 0.0,
            },
        )
        t["calls"] += 1
        for key in ("in", "out", "cached", "cache_write"):  # tokens: a missing count is 0
            t[key] += int(r.get(key) or 0)
        t["seconds"] += float(r.get("seconds") or 0)
        t["failed"] += bool(r.get("failed"))  # a call Claude answered with an error
        for window, field in (("five_hour", "five_hour"), ("seven_day", "seven_day")):
            now = r.get(window)  # [share, resets at], or missing when the CLI didn't say
            if not (isinstance(now, list) and len(now) == 2):
                continue
            share, resets = float(now[0]), int(now[1])
            before = last.get(window)
            # the first sighting is the baseline; a new window starts from 0; else the rise
            moved = 0.0 if before is None else share if before[1] != resets else share - before[0]
            t[field] += max(moved, 0.0)  # a window never moves back mid-way: no credit
            last[window] = (share, resets)  # the baseline for the next call
    return sorted(totals.values(), key=lambda t: (-t["five_hour"], -t["calls"]))


def usage_report(log: UsageLog, today: date | None = None) -> str:
    """"Claude use by feature" for today and the last 7 days, as plain text for ``lerni
    stats``; a line saying so when nothing was recorded."""
    today = today or date.today()
    parts = []  # one block per span: today, then the week
    for title, since in (("today", today), ("the last 7 days", today - timedelta(days=6))):
        rows = by_feature(log.read(since, today))
        if not rows:
            parts.append(f"Claude use by feature, {title}: nothing recorded yet.")
            continue
        lines = [f"Claude use by feature, {title} (5-hour and weekly: how far each window "
                 "moved on that feature's calls):",
                 f"  {'feature':<18}{'calls':>6}{'tokens in':>11}{'out':>8}{'secs':>7}"
                 f"{'failed':>7}{'5-hour':>8}{'weekly':>8}"]
        for t in rows:  # most 5-hour movement first; tokens in counts the cache too
            lines.append(f"  {t['use'][:17]:<18}{t['calls']:>6}{t['in'] + t['cached'] + t['cache_write']:>11,}"
                         f"{t['out']:>8,}{round(t['seconds']):>7}{t['failed']:>7}"
                         f"{t['five_hour']:>8.1%}{t['seven_day']:>8.1%}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
