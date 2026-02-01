"""Tests for SM-2 spaced repetition algorithm."""

from datetime import datetime, timedelta

import pytest

from lerni.sm2 import (
    DEFAULT_EASINESS_FACTOR,
    MIN_EASINESS_FACTOR,
    calculate_sm2,
    format_interval,
    grade_description,
)


class TestCalculateSM2:
    """Test SM-2 algorithm calculations."""

    def test_initial_state_grade_5(self):
        """Perfect recall on first review should give 1-day interval."""
        result = calculate_sm2(
            grade=5,
            easiness_factor=DEFAULT_EASINESS_FACTOR,
            interval=0,
            repetitions=0,
        )
        assert result.interval == 1
        assert result.repetitions == 1
        # Grade 5: EF increases by 0.1
        assert result.easiness_factor == pytest.approx(2.6, rel=1e-2)

    def test_initial_state_grade_4(self):
        """Good recall on first review."""
        result = calculate_sm2(
            grade=4,
            easiness_factor=DEFAULT_EASINESS_FACTOR,
            interval=0,
            repetitions=0,
        )
        assert result.interval == 1
        assert result.repetitions == 1
        # Grade 4: EF unchanged
        assert result.easiness_factor == pytest.approx(2.5, rel=1e-2)

    def test_second_review_grade_4(self):
        """Second successful review should give 6-day interval."""
        result = calculate_sm2(
            grade=4,
            easiness_factor=2.5,
            interval=1,
            repetitions=1,
        )
        assert result.interval == 6
        assert result.repetitions == 2

    def test_third_review_uses_ef_multiplier(self):
        """Third+ reviews multiply interval by EF."""
        result = calculate_sm2(
            grade=4,
            easiness_factor=2.5,
            interval=6,
            repetitions=2,
        )
        # 6 * 2.5 = 15
        assert result.interval == 15
        assert result.repetitions == 3

    def test_grade_below_3_resets_to_beginning(self):
        """Grades 0-2 should reset repetitions and interval."""
        for grade in [0, 1, 2]:
            result = calculate_sm2(
                grade=grade,
                easiness_factor=2.5,
                interval=15,
                repetitions=5,
            )
            assert result.repetitions == 0, f"Grade {grade} should reset repetitions"
            assert result.interval == 1, f"Grade {grade} should reset interval to 1"

    def test_ef_minimum_enforced(self):
        """Easiness factor should never go below 1.3."""
        # Multiple failures should push EF down but not below 1.3
        result = calculate_sm2(
            grade=0,
            easiness_factor=MIN_EASINESS_FACTOR,
            interval=1,
            repetitions=0,
        )
        assert result.easiness_factor >= MIN_EASINESS_FACTOR

    def test_ef_increases_for_grade_5(self):
        """Grade 5 should increase EF."""
        result = calculate_sm2(
            grade=5,
            easiness_factor=2.5,
            interval=6,
            repetitions=2,
        )
        assert result.easiness_factor > 2.5

    def test_ef_decreases_for_grade_3(self):
        """Grade 3 should slightly decrease EF."""
        result = calculate_sm2(
            grade=3,
            easiness_factor=2.5,
            interval=6,
            repetitions=2,
        )
        assert result.easiness_factor < 2.5

    @pytest.mark.parametrize(
        "grade,expected_ef_delta",
        [
            (5, 0.1),
            (4, 0.0),
            (3, -0.14),
            (2, -0.32),
            (1, -0.54),
            (0, -0.8),
        ],
    )
    def test_ef_adjustment_formula(self, grade, expected_ef_delta):
        """Verify EF adjustment matches SM-2 formula."""
        result = calculate_sm2(
            grade=grade,
            easiness_factor=2.5,
            interval=1,
            repetitions=1,
        )
        expected_ef = max(MIN_EASINESS_FACTOR, 2.5 + expected_ef_delta)
        assert result.easiness_factor == pytest.approx(expected_ef, rel=1e-2)

    def test_next_review_date_calculated(self):
        """Next review date should be interval days from review date."""
        review_date = datetime(2025, 1, 1, 12, 0, 0)
        result = calculate_sm2(
            grade=4,
            easiness_factor=2.5,
            interval=6,
            repetitions=2,
            review_date=review_date,
        )
        expected_next = review_date + timedelta(days=result.interval)
        assert result.next_review == expected_next

    def test_invalid_grade_raises_error(self):
        """Grades outside 0-5 should raise ValueError."""
        with pytest.raises(ValueError, match="Grade must be between 0 and 5"):
            calculate_sm2(grade=6)

        with pytest.raises(ValueError, match="Grade must be between 0 and 5"):
            calculate_sm2(grade=-1)

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


class TestGradeDescription:
    """Test grade description helper."""

    @pytest.mark.parametrize(
        "grade,expected",
        [
            (0, "Complete blackout"),
            (1, "Incorrect, but recognized answer"),
            (2, "Incorrect, but easy to recall"),
            (3, "Correct with serious difficulty"),
            (4, "Correct with hesitation"),
            (5, "Perfect response"),
        ],
    )
    def test_valid_grades(self, grade, expected):
        """Each grade should have a description."""
        assert grade_description(grade) == expected

    def test_invalid_grade(self):
        """Invalid grades should return 'Unknown grade'."""
        assert grade_description(99) == "Unknown grade"


class TestFormatInterval:
    """Test interval formatting helper."""

    @pytest.mark.parametrize(
        "days,expected",
        [
            (1, "1 day"),
            (2, "2 days"),
            (6, "6 days"),
            (7, "1 week"),
            (14, "2 weeks"),
            (21, "3 weeks"),
            (30, "1 month"),
            (60, "2 months"),
            (90, "3 months"),
            (365, "1 year"),
            (730, "2 years"),
        ],
    )
    def test_interval_formatting(self, days, expected):
        """Intervals should be formatted in human-readable form."""
        assert format_interval(days) == expected
