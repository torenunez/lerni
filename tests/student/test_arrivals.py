"""v4.17: new arrivals: covered cars, one a week, the student's ❤️ choosing which, and a
covered car never bought, even with the points for it."""

import json
from datetime import date

import pytest

from lerni.student.garage import Garage
from lerni.student.points import PointsStore
from lerni.student.signin import Role, Viewer
from lerni.student.web.games import delivery_chip, garage_tap, settled

pytestmark = pytest.mark.ci  # run on each PR by GitHub

WED, FRI, NEXT_FRI = date(2026, 11, 18), date(2026, 11, 20), date(2026, 11, 27)
SAM = Viewer("sam", "Sam", Role.SUPERVISED)


def garage_with_covered(tmp_path):
    """A car that's here, and two covered ones: a cheap one and a dearer one."""
    (tmp_path / "cars").mkdir()
    # (id, US price when new, covered): 40, 60, and 160 ⭐
    cars = [("here", 100_000, False), ("cheap", 150_000, True), ("dear", 400_000, True)]
    for name, _, _ in cars:
        (tmp_path / "cars" / f"{name}.webp").write_bytes(b"RIFF")  # a picture must exist
    entries = [{"id": n, "name": n.title(), "usd": usd, "zero_to_60": 3.0, "picture": f"{n}.webp",
                "coming": covered} for n, usd, covered in cars]
    (tmp_path / "garage.json").write_text(json.dumps({"cars": entries}))
    return Garage(tmp_path)


def test_a_hearted_car_arrives_on_friday_and_then_sells(tmp_path):
    garage, points = garage_with_covered(tmp_path), PointsStore(tmp_path)
    points.award("sam", "r1", "race", 400, WED)  # enough for any of them
    p, came = settled(points, garage, "sam", WED)  # first seen: the day is set, nothing comes
    assert came is None and p.delivery == FRI.isoformat()
    assert {c.id for c in garage.sold(p.cars, p.arrived)} >= {"here"}
    assert "cheap" not in {c.id for c in garage.sold(p.cars, p.arrived)}  # covered
    # a tap on a covered car hearts it; the dearer one now comes first
    assert "want" in garage_tap(points, garage, SAM, "dear", WED)
    assert "dear" in delivery_chip(garage, points.get("sam"), WED).lower()
    p, came = settled(points, garage, "sam", FRI)  # Friday: it arrives
    assert came.id == "dear" and p.arrived == {"dear": FRI.isoformat()}
    assert p.delivery == NEXT_FRI.isoformat() and not p.hearts  # here now, no longer a wish
    assert "yours" in garage_tap(points, garage, SAM, "dear", FRI)  # and now it sells
    # weeks away: only one car waits, the last, with no day after it
    p, came = settled(points, garage, "sam", date(2027, 1, 15))
    assert came.id == "cheap" and p.delivery == ""


def test_a_covered_car_is_never_bought_even_with_the_points(tmp_path):
    garage, points = garage_with_covered(tmp_path), PointsStore(tmp_path)
    points.award("sam", "r1", "race", 400, WED)
    settled(points, garage, "sam", WED)
    garage_tap(points, garage, SAM, "cheap", WED)  # straight to the handler, as an API call could
    p = points.get("sam")  # not bought, nothing spent, only wanted
    assert "cheap" not in p.cars and p.balance == 400 and p.hearts == ["cheap"]
    # regression (the v4.17 review): a ❤️ drawn Wednesday, tapped Friday as it arrives
    assert "arrived" in garage_tap(points, garage, SAM, "cheap", FRI, wants=True)
    p = points.get("sam")
    assert "cheap" in p.arrived and "cheap" not in p.cars and p.balance == 400
