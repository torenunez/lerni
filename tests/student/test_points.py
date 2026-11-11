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


def test_review_a_broken_points_file_is_moved_aside_and_an_unreadable_one_kept(tmp_path):
    # outside review (2026-11-10): a cut-off file broke every Games action
    store = PointsStore(tmp_path)
    store.award("sam", "r1", "race", 5, DAY)
    path = store._path("sam")
    path.write_text('{"balance": 5, "ca')  # half a file
    assert store.get("sam").balance == 0  # Games still opens
    assert list(path.parent.glob("sam.broken-*.json"))  # kept for the admin
    store.award("sam", "r2", "race", 3, DAY)
    path.chmod(0)  # unreadable: never overwritten with an empty one
    try:
        with pytest.raises(OSError):
            store.award("sam", "r3", "race", 3, DAY)
    finally:
        path.chmod(0o600)
    assert store.get("sam").balance == 3
