"""The garage: eight cars, cheapest first, the starter free, each drawn."""

from lerni.student.garage import CARS, car, car_card_svg, car_svg


def test_eight_cars_cheapest_first_and_each_draws():
    assert [c.price for c in CARS] == [0, 30, 60, 100, 150, 220, 300, 400]
    assert car("starter").price == 0 and len({c.id for c in CARS}) == 8
    for c in CARS:
        assert car_card_svg(c.id).startswith("<svg")
        assert 'data-lane="me"' in car_svg(c.id, 10, 5, "me")


def test_real_cars_load_from_a_private_file_with_prices_and_boosts(tmp_path):
    import json

    from lerni.student.garage import Garage, boost

    (tmp_path / "cars").mkdir()
    (tmp_path / "cars" / "fast.webp").write_bytes(b"RIFF")
    (tmp_path / "cars" / "quick.webp").write_bytes(b"RIFF")
    cars = [
        {"id": "fast", "name": "Fast car", "usd": 4_600_000, "zero_to_60": 2.0, "engine": "V16",
         "power_hp": 1775, "drive": "All-wheel", "note": "Limited", "picture": "fast.webp"},
        {"id": "quick", "name": "Quick car", "usd": 91_700, "zero_to_60": 3.4, "engine": "I6",
         "power_hp": 523, "drive": "All-wheel", "picture": "quick.webp"},
        {"id": "ghost", "name": "No picture", "usd": 100_000, "zero_to_60": 3.0,
         "picture": "ghost.webp"},  # its picture is missing: skipped alone
        {"id": "../x", "name": "Bad id", "usd": 1, "zero_to_60": 3.0, "picture": "quick.webp"},
    ]
    (tmp_path / "garage.json").write_text(json.dumps({"cars": cars}))
    garage = Garage(tmp_path)
    assert [c.id for c in garage.cars][:3] == ["starter", "quick", "fast"]  # cheapest first
    assert (garage.car("quick").price, garage.car("fast").price) == (37, 1840)
    assert boost(garage.car("starter")) == 1.0 and boost(garage.car("fast")) == 1.4
    assert round(boost(garage.car("quick")), 2) == 1.08
    assert garage.picture("fast") == tmp_path / "cars" / "fast.webp"
    assert garage.picture("starter") is None and garage.picture("../x") is None
    sold = [c.id for c in garage.sold(["starter", "rally"])]
    assert sold == ["starter", "quick", "fast", "rally"]
    (tmp_path / "garage.json").write_text("{not json")
    assert [c.id for c in Garage(tmp_path).sold(["starter"])] == ["starter"]  # cartoon garage
