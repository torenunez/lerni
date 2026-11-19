"""When Lerni's background jobs run (v4.16): every job time in one place, in the home
server's local time. The admin reference has the same table.

Changing a time is one edit and a restart; the nightly copy's time is written into its
LaunchAgent, so it also needs ``lerni backup install`` again. Standard library only.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

NIGHT_HOUR = 2  # the night job: purge, bridges, the morning plan, the day's questions
NIGHT_TRIES = 9  # 02:00, then every half hour until 06:00 while something failed
RETRY_SECONDS = 30 * 60  # between the night job's tries
WAIT_SECONDS = 15 * 60  # each try waits this long at most for its writes
COPY_AT = {"Hour": 3, "Minute": 0}  # the nightly copy and stats rebuild, after the night job
ARRIVAL_WEEKDAY = 4  # new cars arrive on Fridays (Monday is 0; v4.17)


def seconds_until(hour: int, now: datetime) -> float:
    """Seconds from ``now`` to the next ``hour`` o'clock, today or tomorrow."""
    at = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    return ((at if at > now else at + timedelta(days=1)) - now).total_seconds()


def next_delivery(today: date) -> date:
    """The first delivery day after ``today`` (never today itself: a day shown is a day ahead)."""
    return today + timedelta(days=(ARRIVAL_WEEKDAY - today.weekday() - 1) % 7 + 1)
