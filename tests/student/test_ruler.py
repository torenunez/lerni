"""v4.11.2: ruler questions: every answer matches its drawing at one real scale, and typed
lengths are read exactly."""

import random
from fractions import Fraction

from lerni.student.ruler import CM_PER_INCH, MAX_LEVEL, RULER_CM, length_typed, question


def test_each_ruler_answer_matches_its_drawing():
    rng = random.Random(3)
    for level in range(1, MAX_LEVEL + 1):
        for _ in range(30):
            _, answer, draw, _, _ = question(level, rng, "🦕")
            bars = draw["bars"]
            assert all(0 <= b["start"] < b["end"] <= RULER_CM for b in bars)  # on the ruler
            cm = Fraction(bars[0]["end"]).limit_denominator(100) - int(bars[0]["start"])
            if level in (1, 3):  # centimeters: end minus start
                assert answer == cm
            elif level in (2, 4):  # inches: the same bar read on the other edge
                assert abs(answer * CM_PER_INCH - cm) < Fraction(1, 100)
            elif level == 5:  # converting: the nearest whole centimeter
                assert answer == round(cm)
            else:  # comparing: the longer bar, by real size
                longer = 1 if bars[0]["end"] > bars[1]["end"] else 2
                assert answer == longer and abs(bars[0]["end"] - bars[1]["end"]) >= 1


def test_typed_lengths_are_read_exactly():
    assert length_typed("1.5") == length_typed("1 1/2") == length_typed("1½") == Fraction(3, 2)
    assert length_typed("6 cm") == length_typed("6") == 6 and length_typed(".5") == Fraction(1, 2)
    for bad in ("1/0", "1.2.3", "abc", "²", "", "."):  # never a guess at what was meant
        assert length_typed(bad) is None
