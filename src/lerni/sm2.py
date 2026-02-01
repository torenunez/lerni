"""
SM-2 Spaced Repetition Algorithm.

Implementation of the SM-2 algorithm by Piotr Wozniak, used in SuperMemo 2.
This module provides pure functions for calculating review schedules.

Grade Scale (0-5):
    0: Complete blackout - no recall at all
    1: Incorrect, but recognized answer when shown
    2: Incorrect, but answer seemed easy to recall
    3: Correct with serious difficulty
    4: Correct with hesitation
    5: Perfect response - immediate recall

Algorithm:
    1. Update easiness factor (EF):
       EF' = EF + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
       EF' = max(1.3, EF')  # Minimum EF is 1.3

    2. Calculate next interval:
       If grade < 3: reset repetitions to 0, interval = 1 day
       Else:
         If repetitions == 0: interval = 1 day
         If repetitions == 1: interval = 6 days
         Else: interval = previous_interval * EF

    3. Increment repetitions (if grade >= 3)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

# Grade descriptions for user interface
GRADE_DESCRIPTIONS: dict[int, str] = {
    0: "Complete blackout",
    1: "Incorrect, but recognized answer",
    2: "Incorrect, but easy to recall",
    3: "Correct with serious difficulty",
    4: "Correct with hesitation",
    5: "Perfect response",
}

# Default SM-2 parameters
DEFAULT_EASINESS_FACTOR = 2.5
MIN_EASINESS_FACTOR = 1.3


@dataclass
class SM2Result:
    """Result of SM-2 calculation."""

    easiness_factor: float
    interval: int  # days
    repetitions: int
    next_review: datetime


def calculate_sm2(
    grade: int,
    easiness_factor: float = DEFAULT_EASINESS_FACTOR,
    interval: int = 0,
    repetitions: int = 0,
    review_date: datetime | None = None,
) -> SM2Result:
    """
    Calculate next SM-2 state based on self-grade.

    Args:
        grade: Self-assessment grade (0-5).
        easiness_factor: Current EF (min 1.3, default 2.5).
        interval: Current interval in days.
        repetitions: Number of successful repetitions.
        review_date: Date of review (defaults to now).

    Returns:
        SM2Result with updated state and next review date.

    Raises:
        ValueError: If grade is not in range 0-5.

    Examples:
        >>> result = calculate_sm2(grade=5, easiness_factor=2.5, interval=0, repetitions=0)
        >>> result.interval
        1
        >>> result.repetitions
        1

        >>> result = calculate_sm2(grade=4, easiness_factor=2.5, interval=6, repetitions=2)
        >>> result.interval
        15

        >>> result = calculate_sm2(grade=2, easiness_factor=2.5, interval=6, repetitions=2)
        >>> result.interval
        1
        >>> result.repetitions
        0
    """
    if not 0 <= grade <= 5:
        raise ValueError(f"Grade must be between 0 and 5, got {grade}")

    if review_date is None:
        review_date = datetime.now()

    # Update easiness factor using SM-2 formula
    new_ef = easiness_factor + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    new_ef = max(MIN_EASINESS_FACTOR, new_ef)

    # Calculate interval and repetitions based on grade
    if grade < 3:
        # Failed recall - reset to beginning
        new_repetitions = 0
        new_interval = 1
    else:
        # Successful recall - advance schedule
        new_repetitions = repetitions + 1
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * new_ef)

    next_review = review_date + timedelta(days=new_interval)

    return SM2Result(
        easiness_factor=new_ef,
        interval=new_interval,
        repetitions=new_repetitions,
        next_review=next_review,
    )


def grade_description(grade: int) -> str:
    """
    Return human-readable description of SM-2 grade.

    Args:
        grade: SM-2 grade (0-5).

    Returns:
        Description string for the grade.

    Example:
        >>> grade_description(5)
        'Perfect response'
        >>> grade_description(0)
        'Complete blackout'
    """
    return GRADE_DESCRIPTIONS.get(grade, "Unknown grade")


def format_interval(days: int) -> str:
    """
    Format interval in human-readable form.

    Args:
        days: Number of days.

    Returns:
        Human-readable string (e.g., "1 day", "2 weeks", "3 months").

    Examples:
        >>> format_interval(1)
        '1 day'
        >>> format_interval(7)
        '1 week'
        >>> format_interval(30)
        '1 month'
    """
    if days == 1:
        return "1 day"
    elif days < 7:
        return f"{days} days"
    elif days < 14:
        return "1 week"
    elif days < 30:
        weeks = days // 7
        return f"{weeks} weeks"
    elif days < 60:
        return "1 month"
    elif days < 365:
        months = days // 30
        return f"{months} months"
    else:
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''}"
