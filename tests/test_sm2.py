"""Tests for SM-2 spaced repetition algorithm."""



from lerni.sm2 import (
    DEFAULT_EASINESS_FACTOR,
    calculate_sm2,
)


class TestCalculateSM2:
    """Test SM-2 algorithm calculations."""












    def test_long_sequence_increases_interval(self):
        """Simulating multiple successful reviews should grow interval."""
        ef = DEFAULT_EASINESS_FACTOR
        interval = 0
        reps = 0

        intervals = []
        for _ in range(10):
            result = calculate_sm2(
                grade=4,
                easiness_factor=ef,
                interval=interval,
                repetitions=reps,
            )
            intervals.append(result.interval)
            ef = result.easiness_factor
            interval = result.interval
            reps = result.repetitions

        # Intervals should generally increase
        assert intervals[-1] > intervals[0]
        # After 10 reviews with grade 4, interval should be substantial
        assert intervals[-1] > 30
