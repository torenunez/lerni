"""The garage: eight cars, cheapest first, the starter free, each drawn."""

import json

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


def test_a_huge_or_endless_number_skips_that_car_only_and_prices_round_to_tens(tmp_path):
    import json

    from lerni.student.garage import Garage

    # regression: one car priced at infinity stopped the server starting
    (tmp_path / "cars").mkdir()
    (tmp_path / "cars" / "a.webp").write_bytes(b"RIFF")
    car = {"id": "a", "name": "A", "usd": 91_700, "zero_to_60": 3.5, "picture": "a.webp"}
    text = json.dumps({"cars": [car, {**car, "id": "b", "usd": 1e400},
                                {**car, "id": "c", "zero_to_60": float("inf")},
                                {**car, "id": "d", "usd": 5_000}]})
    (tmp_path / "garage.json").write_text(text)
    garage = Garage(tmp_path)
    assert [(c.id, c.price) for c in garage.cars if c.picture] == [("d", 10), ("a", 40)]


def test_cards_say_speed_in_bolts_price_in_family_cars_and_the_next_car_to_save_for(tmp_path):
    from lerni.student.garage import Garage, bolts, family_cars, next_goal

    garage = Garage(tmp_path)  # no file: the cartoon garage
    assert bolts(garage.car("starter")) == 1
    assert family_cars(0) == "" and family_cars(60_000) == "about the price of a family car"
    assert family_cars(4_600_000) == "as much as 92 family cars 🚗"
    car, line = next_goal(garage.sold(["starter"]), ["starter"], 0)
    assert car is None and line == "Every car is yours! 🏆"  # only the starter is sold
    (tmp_path / "cars").mkdir()
    (tmp_path / "cars" / "a.webp").write_bytes(b"RIFF")
    fast = {"id": "fast", "name": "Fast", "usd": 1_000_000, "zero_to_60": 2.0, "picture": "a.webp"}
    slow = {**fast, "id": "slow", "name": "Slow", "usd": 100_000, "zero_to_60": 3.5}
    (tmp_path / "garage.json").write_text(json.dumps({"cars": [fast, slow]}))
    garage = Garage(tmp_path)
    assert (bolts(garage.car("slow")), bolts(garage.car("fast"))) == (2, 5)
    sold = garage.sold(["starter"])
    assert next_goal(sold, ["starter"], 0)[1] == "Slow · ⭐ 0 / 40 · about 4 races"
    assert next_goal(sold, ["starter"], 50)[1] == "Fast · ⭐ 50 / 400 · about 27 races"
    assert next_goal(sold, ["starter"], 500)[1] == "You can get the Fast now!"
