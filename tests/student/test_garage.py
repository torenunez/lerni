"""The garage: eight cars, cheapest first, the starter free, each drawn."""

from lerni.student.garage import CARS, car, car_card_svg, car_svg


def test_eight_cars_cheapest_first_and_each_draws():
    assert [c.price for c in CARS] == [0, 30, 60, 100, 150, 220, 300, 400]
    assert car("starter").price == 0 and len({c.id for c in CARS}) == 8
    for c in CARS:
        assert car_card_svg(c.id).startswith("<svg")
        assert 'data-lane="me"' in car_svg(c.id, 10, 5, "me")
