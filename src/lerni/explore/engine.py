"""The deterministic lesson state machine.

The application owns progression. A tutor can phrase an explanation, but it
cannot select content, inspect an answer, or advance state — there is no engine
event a model can emit. Every transition here comes from an explicit
:class:`~lerni.explore.domain.LessonEvent` raised by a UI control.

The engine is stateless and pure: the same lesson, state, and event always
produce the same result, and rejected transitions never mutate the state passed
in. That is what makes a session replayable and a telemetry record trustworthy.
"""

from lerni.explore.domain import (
    ChoiceView,
    CompletionKind,
    InvalidLessonStateError,
    InvalidTransitionError,
    Lesson,
    LessonAction,
    LessonEvent,
    LessonPhase,
    LessonSnapshot,
    LessonState,
    LessonTransition,
    StepKind,
    TransitionOutcome,
    UnknownChoiceError,
)

__all__ = ["DeterministicLessonEngine"]


class DeterministicLessonEngine:
    """Stateless driver for a lesson's intro/teach/check/hint/complete flow."""

    def initial_state(self, lesson: Lesson) -> LessonState:
        """Return the state a fresh session starts in."""
        return LessonState(
            lesson_id=lesson.id,
            lesson_content_version=lesson.content_version,
            phase=LessonPhase.INTRO,
            step_index=0,
            attempts=0,
            hint_index=None,
            completion=None,
        )

    # --- validation ------------------------------------------------------

    def _validate(self, lesson: Lesson, state: LessonState) -> None:
        """Reject any state that cannot have been produced by this engine.

        Raises:
            InvalidLessonStateError: The state belongs to another lesson or
                content version, or its fields are mutually impossible.
        """
        if state.lesson_id != lesson.id:
            raise InvalidLessonStateError(
                f"state belongs to lesson {state.lesson_id!r}, not {lesson.id!r}"
            )
        if state.lesson_content_version != lesson.content_version:
            raise InvalidLessonStateError(
                f"state is for content version {state.lesson_content_version}, "
                f"lesson is version {lesson.content_version}"
            )
        if state.attempts < 0:
            raise InvalidLessonStateError("attempts cannot be negative")

        phase = state.phase
        if phase in (LessonPhase.INTRO, LessonPhase.TEACH):
            if state.step_index is None or not 0 <= state.step_index < len(lesson.steps):
                raise InvalidLessonStateError(f"{phase.value}: step_index out of range")
            expected = StepKind.INTRO if phase is LessonPhase.INTRO else StepKind.TEACH
            if lesson.steps[state.step_index].kind is not expected:
                raise InvalidLessonStateError(
                    f"{phase.value}: step {state.step_index} is not a {expected.value} step"
                )
            if state.hint_index is not None or state.completion is not None:
                raise InvalidLessonStateError(f"{phase.value}: cannot carry hint or completion")
        elif phase is LessonPhase.CHECK:
            if state.step_index is not None or state.hint_index is not None:
                raise InvalidLessonStateError("check: cannot carry step or hint index")
            if state.completion is not None:
                raise InvalidLessonStateError("check: cannot carry completion")
        elif phase is LessonPhase.HINT:
            if state.step_index is not None or state.completion is not None:
                raise InvalidLessonStateError("hint: cannot carry step index or completion")
            if state.hint_index is None or not 0 <= state.hint_index < len(lesson.check.hints):
                raise InvalidLessonStateError("hint: hint_index out of range")
        elif phase is LessonPhase.COMPLETE:
            if state.completion is None:
                raise InvalidLessonStateError("complete: completion is required")
            if state.step_index is not None:
                raise InvalidLessonStateError("complete: cannot carry step index")

    # --- transitions -----------------------------------------------------

    def transition(
        self, lesson: Lesson, state: LessonState, event: LessonEvent
    ) -> LessonTransition:
        """Apply ``event`` to ``state``.

        Args:
            lesson: The lesson being taught.
            state: The current state, which is never mutated.
            event: The action the child took.

        Returns:
            The before state, the event, the after state, and what happened.

        Raises:
            InvalidLessonStateError: ``state`` is not valid for ``lesson``.
            InvalidTransitionError: The action is not legal in this phase, or
                the event's choice payload does not match its action.
            UnknownChoiceError: The submitted choice is not one this check offers.
        """
        self._validate(lesson, state)

        if event.action is LessonAction.SUBMIT_CHOICE:
            if event.choice_id is None:
                raise InvalidTransitionError("submit_choice requires a choice_id")
        elif event.choice_id is not None:
            raise InvalidTransitionError(f"{event.action.value} must not carry a choice_id")

        if event.action is LessonAction.RESTART:
            return LessonTransition(
                before=state,
                event=event,
                after=self.initial_state(lesson),
                outcome=TransitionOutcome.RESTARTED,
            )

        if event.action is LessonAction.CONTINUE:
            return self._continue(lesson, state, event)
        return self._submit(lesson, state, event)

    def _continue(
        self, lesson: Lesson, state: LessonState, event: LessonEvent
    ) -> LessonTransition:
        if state.phase not in (LessonPhase.INTRO, LessonPhase.TEACH):
            raise InvalidTransitionError(f"continue is not available during {state.phase.value}")

        assert state.step_index is not None  # guaranteed by _validate
        next_index = state.step_index + 1
        if next_index < len(lesson.steps):
            after = LessonState(
                lesson_id=state.lesson_id,
                lesson_content_version=state.lesson_content_version,
                phase=LessonPhase.TEACH,
                step_index=next_index,
                attempts=state.attempts,
                hint_index=None,
                completion=None,
            )
        else:
            after = LessonState(
                lesson_id=state.lesson_id,
                lesson_content_version=state.lesson_content_version,
                phase=LessonPhase.CHECK,
                step_index=None,
                attempts=state.attempts,
                hint_index=None,
                completion=None,
            )
        return LessonTransition(
            before=state, event=event, after=after, outcome=TransitionOutcome.ADVANCED
        )

    def _submit(self, lesson: Lesson, state: LessonState, event: LessonEvent) -> LessonTransition:
        if state.phase not in (LessonPhase.CHECK, LessonPhase.HINT):
            raise InvalidTransitionError(
                f"submit_choice is not available during {state.phase.value}"
            )
        if event.choice_id not in {choice.id for choice in lesson.check.choices}:
            raise UnknownChoiceError(f"{event.choice_id!r} is not a choice on this check")

        attempts = state.attempts + 1

        def completed(kind: CompletionKind, outcome: TransitionOutcome) -> LessonTransition:
            return LessonTransition(
                before=state,
                event=event,
                after=LessonState(
                    lesson_id=state.lesson_id,
                    lesson_content_version=state.lesson_content_version,
                    phase=LessonPhase.COMPLETE,
                    step_index=None,
                    attempts=attempts,
                    hint_index=state.hint_index,
                    completion=kind,
                ),
                outcome=outcome,
            )

        if event.choice_id == lesson.check.correct_choice_id:
            return completed(CompletionKind.CORRECT, TransitionOutcome.COMPLETED_CORRECT)

        next_hint = 0 if state.phase is LessonPhase.CHECK else (state.hint_index or 0) + 1
        if next_hint >= len(lesson.check.hints):
            # Out of hints. Reveal rather than loop — a child should not be
            # trapped repeating a question they cannot answer.
            return completed(
                CompletionKind.ANSWER_REVEALED, TransitionOutcome.COMPLETED_REVEALED
            )

        return LessonTransition(
            before=state,
            event=event,
            after=LessonState(
                lesson_id=state.lesson_id,
                lesson_content_version=state.lesson_content_version,
                phase=LessonPhase.HINT,
                step_index=None,
                attempts=attempts,
                hint_index=next_hint,
                completion=None,
            ),
            outcome=TransitionOutcome.HINT_SHOWN,
        )

    # --- presentation ----------------------------------------------------

    def snapshot(self, lesson: Lesson, state: LessonState) -> LessonSnapshot:
        """Return exactly what the child may see in ``state``.

        The answer key, grounding internals, review metadata, and source URLs
        are all absent by construction — :class:`LessonSnapshot` has no field
        that could carry them.
        """
        self._validate(lesson, state)
        check = lesson.check
        choices = tuple(ChoiceView(id=c.id, label=c.label) for c in check.choices)

        if state.phase in (LessonPhase.INTRO, LessonPhase.TEACH):
            assert state.step_index is not None
            step = lesson.steps[state.step_index]
            return self._snapshot(
                lesson,
                state,
                step_id=step.id,
                heading=step.heading,
                body=step.body,
                visual=step.visual,
                choices=(),
                hint_text=None,
                can_continue=True,
                can_submit_choice=False,
            )

        if state.phase is LessonPhase.CHECK:
            return self._snapshot(
                lesson,
                state,
                step_id=None,
                heading=check.prompt,
                body="",
                visual=None,
                choices=choices,
                hint_text=None,
                can_continue=False,
                can_submit_choice=True,
            )

        if state.phase is LessonPhase.HINT:
            assert state.hint_index is not None
            return self._snapshot(
                lesson,
                state,
                step_id=None,
                heading=check.prompt,
                body="",
                visual=None,
                choices=choices,
                hint_text=check.hints[state.hint_index],
                can_continue=False,
                can_submit_choice=True,
            )

        body = (
            check.success_text
            if state.completion is CompletionKind.CORRECT
            else check.reveal_text
        )
        return self._snapshot(
            lesson,
            state,
            step_id=None,
            heading=check.prompt,
            body=body,
            visual=None,
            choices=(),
            hint_text=None,
            can_continue=False,
            can_submit_choice=False,
        )

    def _snapshot(
        self,
        lesson: Lesson,
        state: LessonState,
        *,
        step_id: str | None,
        heading: str,
        body: str,
        visual: object,
        choices: tuple[ChoiceView, ...],
        hint_text: str | None,
        can_continue: bool,
        can_submit_choice: bool,
    ) -> LessonSnapshot:
        return LessonSnapshot(
            lesson_id=lesson.id,
            lesson_content_version=lesson.content_version,
            title=lesson.title,
            phase=state.phase,
            step_id=step_id,
            heading=heading,
            body=body,
            visual=visual,  # type: ignore[arg-type]
            choices=choices,
            hint_text=hint_text,
            completion=state.completion,
            can_continue=can_continue,
            can_submit_choice=can_submit_choice,
            can_restart=True,
        )
