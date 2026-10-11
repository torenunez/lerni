"""Claude usage: warn educators well before a limit, and pause Lerni just before it.

The model adapter reports each window's share used and its reset time after
every call; Lerni never uses paid extra usage, so overage pauses it too.
Standard library only, and nothing about who asked or what was said.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

WARN_AT = {"five_hour": 0.80}  # per window; the weekly ones warn at WEEK_WARN
WEEK_WARN = 0.75
PAUSE_AT = 0.95  # leaves a little room for the admin's own Claude use
OVERAGE_PAUSE = timedelta(hours=5)  # if overage comes with no reset time


def _when(at: datetime) -> str:
    """Like "Mon 6:00 pm"."""
    return f"{at:%a} {at.hour % 12 or 12}:{at:%M} {'am' if at.hour < 12 else 'pm'}"


def _name(window: str) -> str:
    """How a window is said on screen."""
    return "the 5-hour limit" if window == "five_hour" else "this week's limit"


class Usage:
    """The latest usage the adapter saw, shared by every call."""

    def __init__(self) -> None:
        self._windows: dict[str, tuple[float, datetime]] = {}
        self._overage_until: datetime | None = None
        self._lock = threading.Lock()

    def record(self, windows: dict[str, tuple[float, int]], overage: bool) -> None:
        """Note each window's share used (0–1) and reset time (Unix seconds)."""
        with self._lock:
            for name, (used, resets_at) in windows.items():
                self._windows[name] = (used, datetime.fromtimestamp(resets_at))
            if overage:  # paid credits: stop until the windows reset
                resets = [at for _, at in self._windows.values() if at > datetime.now()]
                self._overage_until = max(resets, default=datetime.now() + OVERAGE_PAUSE)

    def warning(self, now: datetime | None = None) -> str:
        """A line for educators when a window is getting full; "" otherwise."""
        now = now or datetime.now()
        with self._lock:
            high = [
                (used, name, at)
                for name, (used, at) in self._windows.items()
                if at > now and used >= WARN_AT.get(name, WEEK_WARN)
            ]
        if not high:
            return ""
        used, name, at = max(high)
        return (
            f"⚠️ Claude has used {used:.0%} of {_name(name)}; it resets {_when(at)}. "
            f"Lerni rests at {PAUSE_AT:.0%}."
        )

    def paused(self, now: datetime | None = None) -> str:
        """Why Lerni is resting and until when; "" while it may call Claude."""
        now = now or datetime.now()
        with self._lock:
            until = [at for used, at in self._windows.values() if used >= PAUSE_AT and at > now]
            if self._overage_until and self._overage_until > now:
                until.append(self._overage_until)
        return f"Lerni is resting until {_when(max(until))}. 😴" if until else ""
