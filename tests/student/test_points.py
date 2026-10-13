"""Points: each award once, the Chat cap, buying and driving, and the day's races."""

from datetime import date, timedelta

import pytest

from lerni.student.points import CHAT_CAP, RACES_PER_DAY, PointsError, PointsStore

DAY = date(2026, 10, 13)


def test_an_award_counts_once_and_chat_stops_at_its_cap(tmp_path):
    store = PointsStore(tmp_path)
    assert store.award("sam", "race-1", "race", 13, DAY) == 13
    assert store.award("sam", "race-1", "race", 13, DAY) == 0  # a double tap or a refresh
    for n in range(CHAT_CAP):
        store.award("sam", f"chat-{n}", "chat", 3, DAY)
    assert store.get("sam").balance == 13 + CHAT_CAP
    assert store.award("sam", "chat-next-day", "chat", 3, DAY + timedelta(days=1)) == 3


def test_buying_charges_once_never_below_zero_and_only_owned_cars_drive(tmp_path):
    store = PointsStore(tmp_path)
    store.award("sam", "race-1", "race", 40, DAY)
    with pytest.raises(PointsError):
        store.buy("sam", "muscle", 60, DAY)  # 20 short: nothing changes
    with pytest.raises(PointsError):
        store.drive("sam", "rally")  # not theirs yet
    store.buy("sam", "rally", 30, DAY)
    with pytest.raises(PointsError):
        store.buy("sam", "rally", 30, DAY)  # a double tap charges once
    store.drive("sam", "rally")
    p = store.get("sam")
    assert (p.balance, p.cars, p.car) == (10, ["starter", "rally"], "rally")


def test_ten_races_a_day_then_tomorrow(tmp_path):
    store = PointsStore(tmp_path)
    for _ in range(RACES_PER_DAY):
        store.start_race("sam", DAY)
    assert store.races_left("sam", DAY) == 0
    with pytest.raises(PointsError, match="tomorrow"):
        store.start_race("sam", DAY)
    assert store.races_left("sam", DAY + timedelta(days=1)) == RACES_PER_DAY
