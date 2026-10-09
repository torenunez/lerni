"""Deterministic lesson engine tests.

Two properties matter most and are asserted repeatedly: no tutor-shaped input
can advance state, and a rejected transition leaves the caller's state exactly
as it was.
"""


import pytest

from lerni.student.domain import (
    CompletionKind,
    LessonAction,
    LessonEvent,
    LessonPhase,
    LessonState,
    TransitionOutcome,
)
from lerni.student.engine import DeterministicLessonEngine

CONTINUE = LessonEvent(action=LessonAction.CONTINUE)
RESTART = LessonEvent(action=LessonAction.RESTART)


def submit(choice_id: str) -> LessonEvent:
    return LessonEvent(action=LessonAction.SUBMIT_CHOICE, choice_id=choice_id)


@pytest.fixture
def engine() -> DeterministicLessonEngine:
    return DeterministicLessonEngine()


@pytest.fixture
def start(engine, valid_lesson) -> LessonState:
    return engine.initial_state(valid_lesson)


@pytest.fixture
def at_check(engine, valid_lesson, start) -> LessonState:
    state = engine.transition(valid_lesson, start, CONTINUE).after
    return engine.transition(valid_lesson, state, CONTINUE).after








def test_correct_first_choice_completes_correct(engine, valid_lesson, at_check):
    result = engine.transition(valid_lesson, at_check, submit("car-a"))
    assert result.outcome is TransitionOutcome.COMPLETED_CORRECT
    assert result.after.phase is LessonPhase.COMPLETE
    assert result.after.completion is CompletionKind.CORRECT
    assert result.after.attempts == 1






def test_wrong_after_final_hint_reveals_without_penalty_loop(engine, valid_lesson, at_check):
    state = at_check
    for choice in ("car-b", "same", "car-b"):
        result = engine.transition(valid_lesson, state, submit(choice))
        state = result.after
    assert result.outcome is TransitionOutcome.COMPLETED_REVEALED
    assert state.completion is CompletionKind.ANSWER_REVEALED
    assert state.attempts == 3
































# --- snapshots -----------------------------------------------------------
