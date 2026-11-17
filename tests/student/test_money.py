"""v4.11.1: money questions: every answer matches its drawing in whole cents, coins keep their
real sizes, and typed amounts are read exactly."""

import random

from lerni.student.money import COIN_MM, COIN_PX, COINS, MAX_LEVEL, cents_typed, listing, question


def test_each_money_answer_matches_its_drawing_in_cents():
    rng = random.Random(11)
    for level in range(1, MAX_LEVEL + 1):
        for _ in range(30):
            _, cents, draw, _, dollars = question(level, rng, "🦕")
            held = sum(COINS[c] for c in draw["coins"]) + 100 * sum(draw["bills"])
            if draw["price"]:  # making change: the bill paid, less the price
                assert cents == 100 * draw["bills"][0] - draw["price"] > 0
            else:
                assert cents == held
            assert dollars is (level >= 4)  # dollars from bills on; cents before
            if level == 5:  # regression (review): never "$1 and 100¢"
                assert sum(COINS[c] for c in draw["coins"]) < 100
    # the coins keep their real sizes: the dime smallest, the quarter largest
    order = sorted(COIN_PX, key=COIN_PX.get)
    assert order == sorted(COIN_MM, key=COIN_MM.get) == ["dime", "penny", "nickel", "quarter"]


def test_typed_amounts_are_read_exactly():
    assert cents_typed("$1.35", dollars=True) == cents_typed(" 1.35 ", dollars=True) == 135
    assert cents_typed("7", dollars=True) == cents_typed("7.00", dollars=True) == 700
    assert cents_typed("35¢", dollars=False) == cents_typed("35", dollars=False) == 35
    for bad in ("1.3.5", "1.234", "abc", "²", "", "$", "."):  # never a guess at what was meant
        assert cents_typed(bad, dollars=True) is None
    assert cents_typed("0.10", dollars=True) + cents_typed("0.20", dollars=True) == 30
    # regression (review): change under a dollar, and one decimal digit, read as meant
    assert [cents_typed(t, dollars=True) for t in (".65", "65¢", "1.5", "3.")] == [65, 65, 150, 300]
    assert listing(["a quarter", "a dime"]) == "a quarter and a dime"  # no comma for two
