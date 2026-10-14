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
        {"id": "fast", "name": "Fast car", "usd": 5_000_000, "zero_to_60": 2.0, "engine": "V12",
         "power_hp": 1500, "drive": "All-wheel", "note": "Limited", "picture": "fast.webp"},
        {"id": "quick", "name": "Quick car", "usd": 100_000, "zero_to_60": 3.5, "engine": "I6",
         "power_hp": 523, "drive": "All-wheel", "picture": "quick.webp"},
        {"id": "ghost", "name": "No picture", "usd": 100_000, "zero_to_60": 3.0,
         "picture": "ghost.webp"},  # its picture is missing: skipped alone
        {"id": "../x", "name": "Bad id", "usd": 1, "zero_to_60": 3.0, "picture": "quick.webp"},
    ]
    (tmp_path / "garage.json").write_text(json.dumps({"cars": cars}))
    garage = Garage(tmp_path)
    assert [c.id for c in garage.cars][:3] == ["starter", "quick", "fast"]  # cheapest first
    assert (garage.car("quick").price, garage.car("fast").price) == (40, 2000)
    assert boost(garage.car("starter")) == 1.0 and boost(garage.car("fast")) == 1.4
    assert round(boost(garage.car("quick")), 2) == 1.07
    assert garage.picture("fast") == tmp_path / "cars" / "fast.webp"
    assert garage.picture("starter") is None and garage.picture("../x") is None
    sold = [c.id for c in garage.sold(["starter", "rally"])]
    assert sold == ["starter", "quick", "fast", "rally"]
    (tmp_path / "garage.json").write_text("{not json")
    assert [c.id for c in Garage(tmp_path).sold(["starter"])] == ["starter"]  # cartoon garage


def test_a_repeated_id_in_the_garage_file_is_skipped(tmp_path):
    import json

    from lerni.student.garage import Garage

    (tmp_path / "cars").mkdir()
    (tmp_path / "cars" / "a.webp").write_bytes(b"RIFF")
    car = {"id": "a", "name": "A", "usd": 100_000, "zero_to_60": 3.5, "picture": "a.webp"}
    (tmp_path / "garage.json").write_text(json.dumps({"cars": [car, {**car, "name": "Copy"}]}))
    ids = [c.id for c in Garage(tmp_path).cars]
    assert len(ids) == len(set(ids))  # regression: a copied entry misaligned every button
