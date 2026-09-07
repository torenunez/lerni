"""Immutable lesson domain for Explore.

Every type here is frozen and slotted. Nothing carries a provider, model,
credential, prompt, database id, or graph relationship, and nothing carries raw
child text. Lesson order is authored data (``Lesson.sequence``), never derived
from a concept graph.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


class ReviewScope(StrEnum):
    SCIENCE = "science"
    CHILD_CONTENT = "child_content"
    VISUAL_ACCESSIBILITY = "visual_accessibility"
    PARENT_APPROVAL = "parent_approval"


class StepKind(StrEnum):
    INTRO = "intro"
    TEACH = "teach"


class LessonPhase(StrEnum):
    INTRO = "intro"
    TEACH = "teach"
    CHECK = "check"
    HINT = "hint"
    COMPLETE = "complete"


class LessonAction(StrEnum):
    CONTINUE = "continue"
    SUBMIT_CHOICE = "submit_choice"
    RESTART = "restart"


class CompletionKind(StrEnum):
    CORRECT = "correct"
    ANSWER_REVEALED = "answer_revealed"


class TransitionOutcome(StrEnum):
    ADVANCED = "advanced"
    HINT_SHOWN = "hint_shown"
    COMPLETED_CORRECT = "completed_correct"
    COMPLETED_REVEALED = "completed_revealed"
    RESTARTED = "restarted"


@dataclass(frozen=True, slots=True)
class ReviewAttestation:
    id: str
    scope: ReviewScope
    reviewer_role: str
    reviewed_on: date
    evidence_ref: str | None
    reviewed_payload_sha256: str


@dataclass(frozen=True, slots=True)
class ReviewMetadata:
    status: ApprovalStatus
    attestations: tuple[ReviewAttestation, ...]


@dataclass(frozen=True, slots=True)
class SourceReference:
    id: str
    title: str
    publisher: str
    url: str
    retrieved_on: date


@dataclass(frozen=True, slots=True)
class GroundedFact:
    id: str
    canonical_text: str
    child_text: str
    source_ids: tuple[str, ...]
    allowed_numbers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GroundingBundle:
    scope: str
    fallback_text: str
    redirect_text: str
    facts: tuple[GroundedFact, ...]
    sources: tuple[SourceReference, ...]


@dataclass(frozen=True, slots=True)
class AssetRef:
    resource_name: str
    media_type: str
    alt_text: str
    sha256: str | None


@dataclass(frozen=True, slots=True)
class LessonStep:
    id: str
    kind: StepKind
    heading: str
    body: str
    visual: AssetRef | None
    fact_ids: tuple[str, ...]
    scope_terms: frozenset[str]


@dataclass(frozen=True, slots=True)
class CheckChoice:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class RetrievalCheck:
    id: str
    prompt: str
    choices: tuple[CheckChoice, ...]
    correct_choice_id: str
    hints: tuple[str, ...]
    success_text: str
    reveal_text: str
    fact_ids: tuple[str, ...]
    scope_terms: frozenset[str]
    allowed_short_replies: frozenset[str]


@dataclass(frozen=True, slots=True)
class Lesson:
    schema_version: int
    id: str
    content_version: int
    title: str
    locale: str
    audience: str
    max_turns: int
    review: ReviewMetadata
    sequence: tuple[str, ...]
    steps: tuple[LessonStep, ...]
    check: RetrievalCheck
    grounding: GroundingBundle


@dataclass(frozen=True, slots=True)
class LessonPackageIdentity:
    lesson_id: str
    content_version: int
    package_sha256: str
    lesson_payload_sha256: str


@dataclass(frozen=True, slots=True)
class LessonState:
    lesson_id: str
    lesson_content_version: int
    phase: LessonPhase
    step_index: int | None
    attempts: int
    hint_index: int | None
    completion: CompletionKind | None


@dataclass(frozen=True, slots=True)
class LessonEvent:
    action: LessonAction
    choice_id: str | None = None


@dataclass(frozen=True, slots=True)
class ChoiceView:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class LessonSnapshot:
    lesson_id: str
    lesson_content_version: int
    title: str
    phase: LessonPhase
    step_id: str | None
    heading: str
    body: str
    visual: AssetRef | None
    choices: tuple[ChoiceView, ...]
    hint_text: str | None
    completion: CompletionKind | None
    can_continue: bool
    can_submit_choice: bool
    can_restart: bool


@dataclass(frozen=True, slots=True)
class LessonTransition:
    before: LessonState
    event: LessonEvent
    after: LessonState
    outcome: TransitionOutcome


@dataclass(frozen=True, slots=True)
class LessonContext:
    grounding: GroundingBundle
    scope_terms: frozenset[str]
    allowed_short_replies: frozenset[str]
    redirect_text: str


class LessonError(Exception):
    pass


class LessonContentError(LessonError, ValueError):
    pass


class LessonNotFoundError(LessonError):
    pass


class LessonNotApprovedError(LessonError):
    pass


class InvalidLessonStateError(LessonError, ValueError):
    pass


class InvalidTransitionError(LessonError, ValueError):
    pass


class UnknownChoiceError(LessonError, ValueError):
    pass


def context_for_snapshot(lesson: Lesson, snapshot: LessonSnapshot) -> LessonContext:
    """Resolve the grounding actually bound to the child's current position.

    Tutor code must never receive the lesson-wide fact set when only a subset is
    on screen. During ``INTRO``/``TEACH`` the bound facts are the current step's;
    from ``CHECK`` onward they are the retrieval check's.

    Raises:
        LessonContentError: the snapshot names a step this lesson does not have,
            or a bound fact id that the grounding bundle does not define.
    """
    if snapshot.phase in (LessonPhase.INTRO, LessonPhase.TEACH):
        step = next((s for s in lesson.steps if s.id == snapshot.step_id), None)
        if step is None:
            raise LessonContentError(
                f"{lesson.id}: snapshot references unknown step {snapshot.step_id!r}"
            )
        fact_ids = step.fact_ids
        scope_terms = step.scope_terms
        allowed_short_replies: frozenset[str] = frozenset()
    else:
        fact_ids = lesson.check.fact_ids
        scope_terms = lesson.check.scope_terms
        allowed_short_replies = lesson.check.allowed_short_replies

    by_id = {fact.id: fact for fact in lesson.grounding.facts}
    missing = [fact_id for fact_id in fact_ids if fact_id not in by_id]
    if missing:
        raise LessonContentError(
            f"{lesson.id}: bound facts not defined in grounding: {sorted(missing)}"
        )

    bound = tuple(by_id[fact_id] for fact_id in fact_ids)

    # Keep only the sources those facts cite, in the lesson's declared order.
    cited = {source_id for fact in bound for source_id in fact.source_ids}
    unknown = cited - {source.id for source in lesson.grounding.sources}
    if unknown:
        raise LessonContentError(
            f"{lesson.id}: bound facts cite unknown sources: {sorted(unknown)}"
        )
    sources = tuple(s for s in lesson.grounding.sources if s.id in cited)

    return LessonContext(
        grounding=GroundingBundle(
            scope=lesson.grounding.scope,
            fallback_text=lesson.grounding.fallback_text,
            redirect_text=lesson.grounding.redirect_text,
            facts=bound,
            sources=sources,
        ),
        scope_terms=scope_terms,
        allowed_short_replies=allowed_short_replies,
        redirect_text=lesson.grounding.redirect_text,
    )
