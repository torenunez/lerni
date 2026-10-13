"""Points: won in a race or in Chat, spent on cars in the garage (spec 09).

One JSON file per person in ``<data root>/points/``: ids and numbers only, never
what anyone said. Each award or purchase has an id and applies once, so a double
tap, a refresh, or a late repeat never counts twice. Standard library only.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal, TypeVar

from lerni.student.jsonfiles import write_json_atomic
from lerni.student.students import check_username, default_data_dir

STARTER = "starter"  # every player starts with this car
CHAT_CAP = 30  # Chat points a day
RACES_PER_DAY = 10
KEEP_DAYS = 90  # awards are kept this long, only to spot repeats
T = TypeVar("T")


class PointsError(ValueError):
    """Something a player can't do: not enough points, a car they don't own, no races left."""


@dataclass
class Points:
    """One person's points, cars, and today's races."""

    balance: int = 0
    cars: list[str] = field(default_factory=lambda: [STARTER])
    car: str = STARTER  # the one they drive
    awards: list[dict[str, Any]] = field(default_factory=list)  # id, source, amount, day
    races: dict[str, Any] = field(default_factory=dict)  # day and count

    def races_today(self, today: date) -> int:
        """How many races they started today."""
        return int(self.races.get("count", 0)) if self.races.get("day") == today.isoformat() else 0


def _record(p: Points, award_id: str, source: str, amount: int, today: date) -> None:
    cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
    p.awards = [a for a in p.awards if a["day"] >= cutoff]  # old ones can't repeat anymore
    p.awards.append({"id": award_id, "source": source, "amount": amount, "day": today.isoformat()})


class PointsStore:
    """Everyone's points on disk, changed one at a time per person."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "points"
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.json"

    def _lock(self, username: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(username, threading.Lock())

    def get(self, username: str) -> Points:
        """Their points; a new player has none and the starter car."""
        path = self._path(username)
        if not path.exists():
            return Points()
        data = json.loads(path.read_text(encoding="utf-8"))
        return Points(int(data.get("balance", 0)), list(data.get("cars", [STARTER])),
                      str(data.get("car", STARTER)), list(data.get("awards", [])),
                      dict(data.get("races", {})))

    def _change(self, username: str, fn: Callable[[Points], T]) -> T:
        with self._lock(username):  # only the server writes points, so a thread lock is enough
            p = self.get(username)
            result = fn(p)
            write_json_atomic(self._path(username), {"schema": 1, **asdict(p)})
            return result

    def award(self, username: str, award_id: str, source: Literal["race", "chat"],
              amount: int, today: date | None = None) -> int:
        """Add points once per ``award_id``; Chat stops at the day's cap.

        Returns:
            The points added (0 for a repeat or a full day).
        """
        day = today or date.today()

        def apply(p: Points) -> int:
            if any(a["id"] == award_id for a in p.awards):
                return 0  # a double tap, a refresh, or a late repeat
            give = amount
            if source == "chat":
                so_far = sum(a["amount"] for a in p.awards
                             if a["source"] == "chat" and a["day"] == day.isoformat())
                give = min(amount, CHAT_CAP - so_far)
            if give <= 0:
                return 0
            _record(p, award_id, source, give, day)
            p.balance += give
            return give

        return self._change(username, apply)

    def buy(self, username: str, car_id: str, price: int, today: date | None = None) -> None:
        """Spend points on a car; it's theirs for good.

        Raises:
            PointsError: Already theirs, or not enough points (nothing changes).
        """

        def apply(p: Points) -> None:
            if car_id in p.cars:
                raise PointsError("That car is already yours.")
            if p.balance < price:
                raise PointsError(f"{price - p.balance:,} more ⭐ for that one.")
            _record(p, f"buy-{car_id}", "buy", -price, today or date.today())
            p.balance -= price
            p.cars.append(car_id)

        self._change(username, apply)

    def drive(self, username: str, car_id: str) -> None:
        """Race with a car they own.

        Raises:
            PointsError: Not theirs.
        """

        def apply(p: Points) -> None:
            if car_id not in p.cars:
                raise PointsError("Buy that car first.")
            p.car = car_id

        self._change(username, apply)

    def races_left(self, username: str, today: date | None = None) -> int:
        """Races they can still start today."""
        return RACES_PER_DAY - self.get(username).races_today(today or date.today())

    def start_race(self, username: str, today: date | None = None) -> None:
        """Count a race toward today's limit.

        Raises:
            PointsError: Today's races are used up.
        """
        day = today or date.today()

        def apply(p: Points) -> None:
            n = p.races_today(day)
            if n >= RACES_PER_DAY:
                raise PointsError("The track is closed for today 🌙 Come back tomorrow.")
            p.races = {"day": day.isoformat(), "count": n + 1}

        self._change(username, apply)
