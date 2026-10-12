"""Claude usage: warn educators early, pause Lerni before the limit, never use paid credits."""

from datetime import datetime, timedelta

from lerni.student.usage import Usage

NOW = datetime(2026, 10, 11, 17, 0)
LATER = int((NOW + timedelta(days=1)).timestamp())  # Mon 5:00 pm
SOON = int((NOW + timedelta(hours=3)).timestamp())


def test_a_high_week_warns_with_the_reset_time_and_a_full_one_pauses_until_then():
    usage = Usage()
    usage.record({"five_hour": (0.13, SOON), "seven_day": (0.88, LATER)}, overage=False)
    assert "88%" in usage.warning(NOW) and "Mon 5:00 pm" in usage.warning(NOW)
    assert usage.paused(NOW) == ""
    usage.record({"seven_day": (0.96, LATER)}, overage=False)
    assert "Mon 5:00 pm" in usage.paused(NOW)
    assert usage.paused(NOW + timedelta(days=2)) == ""  # the window reset


def test_paid_overage_pauses_lerni():
    usage = Usage()
    usage.record({"five_hour": (0.5, SOON), "seven_day": (0.5, LATER)}, overage=True)
    assert usage.paused(NOW) != ""
