"""Data models for Lerni."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
import json


class ReviewStatus(Enum):
    """Status of a review session."""

    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class RelationshipType(Enum):
    """Type of relationship between concepts."""

    PARENT = "parent"  # child → parent ("belongs to")
    PREREQUISITE = "prerequisite"  # concept → prerequisite ("requires understanding of")
    RELATED = "related"  # bidirectional association


@dataclass
class ScheduleState:
    """SM-2 algorithm state for spaced repetition scheduling."""

    easiness_factor: float = 2.5
    interval: int = 0  # days
    repetitions: int = 0

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "ScheduleState":
        """Deserialize from JSON string."""
        return cls(**json.loads(data))


@dataclass
class Concept:
    """
    Node in the knowledge graph.

    Concepts form a DAG (Directed Acyclic Graph) with typed relationships.
    Can be broad ("Python", "Math") or specific ("Decorators", "Derivatives").
    """

    id: UUID
    name: str  # Canonical name, unique
    aliases: list[str]  # For fuzzy matching ["python", "python programming"]
    description: Optional[str]
    created_at: datetime

    @classmethod
    def create(cls, name: str, description: Optional[str] = None, aliases: Optional[list[str]] = None) -> "Concept":
        """
        Factory method for new concepts.

        Args:
            name: Canonical name (e.g., "Python", "Decorators").
            description: Optional description of the concept.
            aliases: Optional list of alternative names for fuzzy matching.

        Returns:
            A new Concept instance.
        """
        return cls(
            id=uuid4(),
            name=name,
            aliases=aliases or [],
            description=description,
            created_at=datetime.now(),
        )


@dataclass
class ConceptEdge:
    """
    Typed relationship between two concepts.

    Relationships:
    - parent: child → parent ("Decorators" belongs to "Python")
    - prerequisite: concept → prerequisite ("Decorators" requires "Closures")
    - related: bidirectional association
    """

    from_concept_id: UUID
    to_concept_id: UUID
    relationship: RelationshipType

    @classmethod
    def create(cls, from_concept: "Concept", to_concept: "Concept", relationship: RelationshipType) -> "ConceptEdge":
        """
        Factory method for new concept edges.

        Args:
            from_concept: Source concept.
            to_concept: Target concept.
            relationship: Type of relationship.

        Returns:
            A new ConceptEdge instance.
        """
        return cls(
            from_concept_id=from_concept.id,
            to_concept_id=to_concept.id,
            relationship=relationship,
        )


@dataclass
class Question:
    """
    A study card attached to a concept.

    Each question tests understanding of a specific concept.
    One concept can have multiple questions testing different aspects.
    """

    id: UUID
    concept_id: Optional[UUID]  # FK to Concept (nullable for inbox/uncategorized)
    prompt: str  # The question text shown during review
    current_answer_id: Optional[UUID]
    next_review_at: Optional[datetime]
    schedule_state: ScheduleState
    difficulty: Optional[int]  # 1-5
    source_refs: list[str]  # URLs, books, etc.
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, prompt: str, concept: Optional[Concept] = None, difficulty: Optional[int] = None) -> "Question":
        """
        Factory method for new questions.

        Args:
            prompt: The question text.
            concept: Optional concept this question tests.
            difficulty: Optional difficulty rating (1-5).

        Returns:
            A new Question instance with default values.
        """
        now = datetime.now()
        return cls(
            id=uuid4(),
            concept_id=concept.id if concept else None,
            prompt=prompt,
            current_answer_id=None,
            next_review_at=now,  # Due immediately for first review
            schedule_state=ScheduleState(),
            difficulty=difficulty,
            source_refs=[],
            created_at=now,
            updated_at=now,
        )


@dataclass
class Answer:
    """
    Versioned content for a question (Feynman workflow output).

    Each answer captures the 4-step Feynman technique:
    - Step 1: raw_notes - dump everything you know
    - Step 2: simple_explanation - explain like teaching a beginner
    - Step 3: gaps_questions - identify what you don't understand
    - Step 4: final_explanation + analogies_examples - refined understanding

    Answers are immutable snapshots.
    """

    id: UUID
    question_id: UUID
    raw_notes: str  # Step 1 (required)
    simple_explanation: Optional[str]  # Step 2
    gaps_questions: Optional[str]  # Step 3
    final_explanation: Optional[str]  # Step 4
    analogies_examples: Optional[str]  # Step 4 bonus
    created_at: datetime

    @classmethod
    def create(
        cls,
        question: Question,
        raw_notes: str,
        simple_explanation: Optional[str] = None,
        gaps_questions: Optional[str] = None,
        final_explanation: Optional[str] = None,
        analogies_examples: Optional[str] = None,
    ) -> "Answer":
        """
        Factory method for new answers.

        Args:
            question: The parent Question.
            raw_notes: Step 1 content (required).
            simple_explanation: Step 2 content.
            gaps_questions: Step 3 content.
            final_explanation: Step 4 content.
            analogies_examples: Step 4 bonus content.

        Returns:
            A new Answer instance.
        """
        return cls(
            id=uuid4(),
            question_id=question.id,
            raw_notes=raw_notes,
            simple_explanation=simple_explanation,
            gaps_questions=gaps_questions,
            final_explanation=final_explanation,
            analogies_examples=analogies_examples,
            created_at=datetime.now(),
        )


@dataclass
class Review:
    """Review session record."""

    id: UUID
    question_id: UUID
    answer_id: UUID
    scheduled_for: datetime
    completed_at: Optional[datetime]
    status: ReviewStatus
    self_grade: Optional[int]  # 0-5 SM-2 scale
    attempted_explanation: Optional[str]  # What user wrote from scratch during review
    recalled_from_memory: Optional[bool]  # True if user could explain without seeing answer
    gaps_identified: Optional[str]
    notes: Optional[str]
    ai_session_id: Optional[UUID]  # NULL for Phase 1

    @classmethod
    def create(cls, question: Question, answer: Answer) -> "Review":
        """
        Factory method for creating a pending review.

        Args:
            question: The Question being reviewed.
            answer: The Answer to review.

        Returns:
            A new Review instance with pending status.
        """
        return cls(
            id=uuid4(),
            question_id=question.id,
            answer_id=answer.id,
            scheduled_for=question.next_review_at or datetime.now(),
            completed_at=None,
            status=ReviewStatus.PENDING,
            self_grade=None,
            attempted_explanation=None,
            recalled_from_memory=None,
            gaps_identified=None,
            notes=None,
            ai_session_id=None,
        )
