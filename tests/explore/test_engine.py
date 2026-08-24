"""Deterministic lesson engine tests.

Two properties matter most and are asserted repeatedly: no tutor-shaped input
can advance state, and a rejected transition leaves the caller's state exactly
as it was.
"""

import dataclasses

import pytest

from lerni.explore.domain import (
    CompletionKind,
    InvalidLessonStateError,
    InvalidTransitionError,
    LessonAction,
    LessonEvent,
    LessonPhase,
    LessonState,
    TransitionOutcome,
    UnknownChoiceError,
)
from lerni.explore.engine import DeterministicLessonEngine

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


def test_initial_state_points_to_intro(start, valid_lesson):
    assert start.phase is LessonPhase.INTRO
    assert start.step_index == 0
    assert start.attempts == 0
    assert start.hint_index is None
    assert start.completion is None
    assert start.lesson_id == valid_lesson.id


def test_continue_moves_intro_to_teach(engine, valid_lesson, start):
    result = engine.transition(valid_lesson, start, CONTINUE)
    assert result.after.phase is LessonPhase.TEACH
    assert result.after.step_index == 1
    assert result.outcome is TransitionOutcome.ADVANCED


def test_final_teach_continue_enters_check(at_check):
    assert at_check.phase is LessonPhase.CHECK
    assert at_check.step_index is None


def test_correct_first_choice_completes_correct(engine, valid_lesson, at_check):
    result = engine.transition(valid_lesson, at_check, submit("car-a"))
    assert result.outcome is TransitionOutcome.COMPLETED_CORRECT
    assert result.after.phase is LessonPhase.COMPLETE
    assert result.after.completion is CompletionKind.CORRECT
    assert result.after.attempts == 1


def test_first_wrong_choice_shows_first_hint(engine, valid_lesson, at_check):
    result = engine.transition(valid_lesson, at_check, submit("car-b"))
    assert result.outcome is TransitionOutcome.HINT_SHOWN
    assert result.after.phase is LessonPhase.HINT
    assert result.after.hint_index == 0


def test_second_wrong_choice_shows_second_hint(engine, valid_lesson, at_check):
    state = engine.transition(valid_lesson, at_check, submit("car-b")).after
    result = engine.transition(valid_lesson, state, submit("same"))
    assert result.after.hint_index == 1
    assert result.outcome is TransitionOutcome.HINT_SHOWN


def test_wrong_after_final_hint_reveals_without_penalty_loop(engine, valid_lesson, at_check):
    state = at_check
    for choice in ("car-b", "same", "car-b"):
        result = engine.transition(valid_lesson, state, submit(choice))
        state = result.after
    assert result.outcome is TransitionOutcome.COMPLETED_REVEALED
    assert state.completion is CompletionKind.ANSWER_REVEALED
    assert state.attempts == 3


def test_correct_after_hint_completes_correct(engine, valid_lesson, at_check):
    state = engine.transition(valid_lesson, at_check, submit("car-b")).after
    result = engine.transition(valid_lesson, state, submit("car-a"))
    assert result.after.completion is CompletionKind.CORRECT
    assert result.after.attempts == 2


def test_attempts_increment_once_per_submission(engine, valid_lesson, at_check):
    state = at_check
    assert state.attempts == 0
    state = engine.transition(valid_lesson, state, submit("car-b")).after
    assert state.attempts == 1
    state = engine.transition(valid_lesson, state, submit("car-b")).after
    assert state.attempts == 2


def test_continue_does_not_increment_attempts(engine, valid_lesson, start):
    state = engine.transition(valid_lesson, start, CONTINUE).after
    assert state.attempts == 0


def test_restart_from_every_phase_returns_initial(engine, valid_lesson, start, at_check):
    hint = engine.transition(valid_lesson, at_check, submit("car-b")).after
    done = engine.transition(valid_lesson, at_check, submit("car-a")).after
    teach = engine.transition(valid_lesson, start, CONTINUE).after
    for state in (start, teach, at_check, hint, done):
        assert engine.transition(valid_lesson, state, RESTART).after == start


def test_unknown_choice_raises_without_mutating_input_state(engine, valid_lesson, at_check):
    before = dataclasses.replace(at_check)
    with pytest.raises(UnknownChoiceError):
        engine.transition(valid_lesson, at_check, submit("no-such-choice"))
    assert at_check == before


def test_submit_during_intro_is_rejected(engine, valid_lesson, start):
    with pytest.raises(InvalidTransitionError):
        engine.transition(valid_lesson, start, submit("car-a"))
    assert start.phase is LessonPhase.INTRO


def test_continue_during_check_is_rejected(engine, valid_lesson, at_check):
    with pytest.raises(InvalidTransitionError):
        engine.transition(valid_lesson, at_check, CONTINUE)


def test_continue_after_complete_is_rejected(engine, valid_lesson, at_check):
    done = engine.transition(valid_lesson, at_check, submit("car-a")).after
    with pytest.raises(InvalidTransitionError):
        engine.transition(valid_lesson, done, CONTINUE)
    with pytest.raises(InvalidTransitionError):
        engine.transition(valid_lesson, done, submit("car-a"))


def test_submit_without_choice_is_rejected(engine, valid_lesson, at_check):
    with pytest.raises(InvalidTransitionError):
        engine.transition(valid_lesson, at_check, LessonEvent(action=LessonAction.SUBMIT_CHOICE))


def test_continue_with_choice_is_rejected(engine, valid_lesson, start):
    bad = LessonEvent(action=LessonAction.CONTINUE, choice_id="car-a")
    with pytest.raises(InvalidTransitionError):
        engine.transition(valid_lesson, start, bad)


def test_mismatched_lesson_version_raises(engine, valid_lesson, start):
    bad = dataclasses.replace(start, lesson_content_version=99)
    with pytest.raises(InvalidLessonStateError):
        engine.transition(valid_lesson, bad, CONTINUE)


def test_state_from_another_lesson_raises(engine, valid_lesson, start):
    bad = dataclasses.replace(start, lesson_id="some-other-lesson")
    with pytest.raises(InvalidLessonStateError):
        engine.transition(valid_lesson, bad, CONTINUE)


def test_impossible_state_combinations_raise(engine, valid_lesson, start, at_check):
    impossible = [
        dataclasses.replace(start, step_index=99),
        dataclasses.replace(start, hint_index=0),
        dataclasses.replace(start, completion=CompletionKind.CORRECT),
        dataclasses.replace(at_check, step_index=0),
        dataclasses.replace(at_check, phase=LessonPhase.HINT, hint_index=None),
        dataclasses.replace(at_check, phase=LessonPhase.HINT, hint_index=99),
        dataclasses.replace(at_check, phase=LessonPhase.COMPLETE, completion=None),
        dataclasses.replace(start, attempts=-1),
    ]
    for state in impossible:
        with pytest.raises(InvalidLessonStateError):
            engine.transition(valid_lesson, state, CONTINUE)


def test_tutor_like_text_has_no_engine_event(engine, valid_lesson, at_check):
    # There is no action a model could emit. LessonAction is a closed enum, and
    # free text is not one of its members.
    assert {a.value for a in LessonAction} == {"continue", "submit_choice", "restart"}
    with pytest.raises(ValueError):
        LessonAction("Great question! Let's move on.")


def test_replay_is_deterministic(engine, valid_lesson, start):
    def run():
        state = start
        outcomes = []
        for event in (CONTINUE, CONTINUE, submit("car-b"), submit("same"), submit("car-a")):
            result = engine.transition(valid_lesson, state, event)
            state = result.after
            outcomes.append(result.outcome)
        return state, outcomes

    assert run() == run()


# --- snapshots -----------------------------------------------------------


def test_snapshot_never_exposes_answer_key(engine, valid_lesson, start, at_check):
    hint = engine.transition(valid_lesson, at_check, submit("car-b")).after
    correct = engine.transition(valid_lesson, at_check, submit("car-a")).after
    revealed = at_check
    for choice in ("car-b", "same", "car-b"):
        revealed = engine.transition(valid_lesson, revealed, submit(choice)).after

    for state in (start, at_check, hint, correct, revealed):
        snapshot = engine.snapshot(valid_lesson, state)
        assert not hasattr(snapshot, "correct_choice_id")
        rendered = " ".join(
            filter(None, [snapshot.heading, snapshot.body, snapshot.hint_text or ""])
        )
        assert valid_lesson.grounding.scope not in rendered
        for source in valid_lesson.grounding.sources:
            assert source.url not in rendered


def test_check_snapshot_shows_choices_but_no_hint(engine, valid_lesson, at_check):
    snapshot = engine.snapshot(valid_lesson, at_check)
    assert snapshot.phase is LessonPhase.CHECK
    assert [c.id for c in snapshot.choices] == ["car-a", "car-b", "same"]
    assert snapshot.hint_text is None
    assert snapshot.can_submit_choice and not snapshot.can_continue


def test_hint_snapshot_shows_the_current_hint(engine, valid_lesson, at_check):
    state = engine.transition(valid_lesson, at_check, submit("car-b")).after
    snapshot = engine.snapshot(valid_lesson, state)
    assert snapshot.hint_text == valid_lesson.check.hints[0]
    assert snapshot.choices


def test_completion_snapshots_use_the_authored_text(engine, valid_lesson, at_check):
    correct = engine.transition(valid_lesson, at_check, submit("car-a")).after
    assert engine.snapshot(valid_lesson, correct).body == valid_lesson.check.success_text

    revealed = at_check
    for choice in ("car-b", "same", "car-b"):
        revealed = engine.transition(valid_lesson, revealed, submit(choice)).after
    assert engine.snapshot(valid_lesson, revealed).body == valid_lesson.check.reveal_text


def test_intro_snapshot_carries_the_authored_step_and_visual(engine, valid_lesson, start):
    snapshot = engine.snapshot(valid_lesson, start)
    step = valid_lesson.steps[0]
    assert snapshot.step_id == step.id
    assert snapshot.heading == step.heading
    assert snapshot.body == step.body
    assert snapshot.visual == step.visual
    assert snapshot.choices == ()
    assert snapshot.can_continue and not snapshot.can_submit_choice


def test_restart_is_always_offered(engine, valid_lesson, start, at_check):
    for state in (start, at_check):
        assert engine.snapshot(valid_lesson, state).can_restart
