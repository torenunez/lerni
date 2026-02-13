"""
Database layer for Lerni.

Provides SQLite schema management, connection handling, and repository classes
for CRUD operations on Concept, Question, Answer, and Review entities.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional
from uuid import UUID

from .models import (
    Answer,
    Concept,
    ConceptEdge,
    Question,
    RelationshipType,
    Review,
    ReviewStatus,
    ScheduleState,
)

# Schema version for migrations
SCHEMA_VERSION = 3

SCHEMA_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Concepts (knowledge graph nodes)
CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    aliases TEXT NOT NULL,  -- JSON array
    description TEXT,
    created_at TEXT NOT NULL
);

-- Concept edges (DAG relationships)
CREATE TABLE IF NOT EXISTS concept_edges (
    from_concept_id TEXT NOT NULL,
    to_concept_id TEXT NOT NULL,
    relationship TEXT NOT NULL,  -- 'parent', 'prerequisite', 'related'
    PRIMARY KEY (from_concept_id, to_concept_id, relationship),
    FOREIGN KEY (from_concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (to_concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    CHECK (from_concept_id != to_concept_id)
);

-- Questions (study cards)
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    concept_id TEXT,  -- nullable for inbox/uncategorized
    prompt TEXT NOT NULL,
    current_answer_id TEXT,
    next_review_at TEXT,
    schedule_state TEXT NOT NULL,  -- JSON
    difficulty INTEGER,
    source_refs TEXT NOT NULL,  -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE SET NULL
);

-- Answers (versioned Feynman content)
CREATE TABLE IF NOT EXISTS answers (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    raw_notes TEXT NOT NULL,
    simple_explanation TEXT,
    gaps_questions TEXT,
    final_explanation TEXT,
    analogies_examples TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- Review sessions
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    answer_id TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    self_grade INTEGER,
    attempted_explanation TEXT,
    recalled_from_memory INTEGER,
    gaps_identified TEXT,
    notes TEXT,
    ai_session_id TEXT,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (answer_id) REFERENCES answers(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_questions_next_review ON questions(next_review_at);
CREATE INDEX IF NOT EXISTS idx_questions_concept ON questions(concept_id);
CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
CREATE INDEX IF NOT EXISTS idx_reviews_question ON reviews(question_id);
CREATE INDEX IF NOT EXISTS idx_answers_question ON answers(question_id);
CREATE INDEX IF NOT EXISTS idx_concept_edges_from ON concept_edges(from_concept_id);
CREATE INDEX IF NOT EXISTS idx_concept_edges_to ON concept_edges(to_concept_id);
"""

# Migration from v2 to v3 (complete schema restructure)
MIGRATION_V2_TO_V3 = """
-- Create new concepts table
CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    aliases TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);

-- Create concept edges table
CREATE TABLE IF NOT EXISTS concept_edges (
    from_concept_id TEXT NOT NULL,
    to_concept_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    PRIMARY KEY (from_concept_id, to_concept_id, relationship),
    FOREIGN KEY (from_concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (to_concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    CHECK (from_concept_id != to_concept_id)
);

-- Create new questions table from topics
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    concept_id TEXT,
    prompt TEXT NOT NULL,
    current_answer_id TEXT,
    next_review_at TEXT,
    schedule_state TEXT NOT NULL,
    difficulty INTEGER,
    source_refs TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE SET NULL
);

-- Migrate data from topics to questions
INSERT INTO questions (id, concept_id, prompt, current_answer_id, next_review_at,
                       schedule_state, difficulty, source_refs, created_at, updated_at)
SELECT id, NULL, question, current_version_id, next_review_at,
       schedule_state, json_extract(metadata, '$.difficulty'),
       COALESCE(json_extract(metadata, '$.source_refs'), '[]'),
       created_at, updated_at
FROM topics;

-- Create new answers table from topic_versions
CREATE TABLE IF NOT EXISTS answers (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    raw_notes TEXT NOT NULL,
    simple_explanation TEXT,
    gaps_questions TEXT,
    final_explanation TEXT,
    analogies_examples TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- Migrate data from topic_versions to answers
INSERT INTO answers (id, question_id, raw_notes, simple_explanation, gaps_questions,
                     final_explanation, analogies_examples, created_at)
SELECT id, topic_id, raw_notes, simple_explanation, gaps_questions,
       final_explanation, analogies_examples, created_at
FROM topic_versions;

-- Create new reviews table
CREATE TABLE IF NOT EXISTS reviews_new (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    answer_id TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    self_grade INTEGER,
    attempted_explanation TEXT,
    recalled_from_memory INTEGER,
    gaps_identified TEXT,
    notes TEXT,
    ai_session_id TEXT,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (answer_id) REFERENCES answers(id)
);

-- Migrate reviews data
INSERT INTO reviews_new (id, question_id, answer_id, scheduled_for, completed_at,
                         status, self_grade, attempted_explanation, recalled_from_memory,
                         gaps_identified, notes, ai_session_id)
SELECT id, topic_id, version_id, scheduled_for, completed_at,
       status, self_grade, attempted_explanation, recalled_from_memory,
       gaps_identified, notes, ai_session_id
FROM reviews;

-- Drop old tables
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS topic_versions;
DROP TABLE IF EXISTS topics;

-- Rename new reviews table
ALTER TABLE reviews_new RENAME TO reviews;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_questions_next_review ON questions(next_review_at);
CREATE INDEX IF NOT EXISTS idx_questions_concept ON questions(concept_id);
CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
CREATE INDEX IF NOT EXISTS idx_reviews_question ON reviews(question_id);
CREATE INDEX IF NOT EXISTS idx_answers_question ON answers(question_id);
CREATE INDEX IF NOT EXISTS idx_concept_edges_from ON concept_edges(from_concept_id);
CREATE INDEX IF NOT EXISTS idx_concept_edges_to ON concept_edges(to_concept_id);
"""


def get_db_path() -> Path:
    """Get database path (~/.lerni/lerni.db)."""
    from .config import get_lerni_dir

    return get_lerni_dir() / "lerni.db"


@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    """
    Context manager for database connection.

    Args:
        db_path: Optional path to database file. Defaults to ~/.lerni/lerni.db.

    Yields:
        sqlite3.Connection with row_factory set to sqlite3.Row.
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """
    Initialize database schema.

    Creates tables if they don't exist, runs migrations, and sets schema version.

    Args:
        db_path: Optional path to database file.
    """
    with get_connection(db_path) as conn:
        # Check if this is a fresh database
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        is_fresh = cursor.fetchone() is None

        if is_fresh:
            # Fresh database - create all tables
            conn.executescript(SCHEMA_SQL)
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
            )
        else:
            # Existing database - check for migrations
            cursor = conn.execute("SELECT version FROM schema_version")
            row = cursor.fetchone()
            current_version = row[0] if row else 0

            if current_version < 3:
                # Run migration from v2 to v3
                conn.executescript(MIGRATION_V2_TO_V3)
                conn.execute("UPDATE schema_version SET version = ?", (3,))


class ConceptRepository:
    """Data access for Concept entities."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, concept: Concept) -> None:
        """Insert new concept."""
        self.conn.execute(
            """INSERT INTO concepts (id, name, aliases, description, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                str(concept.id),
                concept.name,
                json.dumps(concept.aliases),
                concept.description,
                concept.created_at.isoformat(),
            ),
        )

    def get_by_id(self, concept_id: UUID | str) -> Optional[Concept]:
        """Fetch concept by ID (supports prefix match)."""
        id_str = str(concept_id)
        cursor = self.conn.execute(
            "SELECT * FROM concepts WHERE id = ?", (id_str,)
        )
        row = cursor.fetchone()

        if row is None and len(id_str) < 36:
            cursor = self.conn.execute(
                "SELECT * FROM concepts WHERE id LIKE ?", (f"{id_str}%",)
            )
            rows = cursor.fetchall()
            if len(rows) == 1:
                row = rows[0]
            elif len(rows) > 1:
                raise ValueError(f"Ambiguous concept ID prefix: {id_str}")

        if row is None:
            return None
        return self._row_to_concept(row)

    def get_by_name(self, name: str) -> Optional[Concept]:
        """Fetch concept by exact name (case-insensitive)."""
        cursor = self.conn.execute(
            "SELECT * FROM concepts WHERE LOWER(name) = LOWER(?)", (name,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_concept(row)

    def find_by_alias(self, alias: str) -> list[Concept]:
        """Find concepts matching an alias (case-insensitive)."""
        cursor = self.conn.execute(
            """SELECT * FROM concepts
               WHERE LOWER(name) = LOWER(?)
                  OR EXISTS (
                      SELECT 1 FROM json_each(aliases)
                      WHERE LOWER(value) = LOWER(?)
                  )""",
            (alias, alias),
        )
        return [self._row_to_concept(row) for row in cursor.fetchall()]

    def search(self, query: str) -> list[Concept]:
        """Search concepts by name or alias (substring match)."""
        pattern = f"%{query}%"
        cursor = self.conn.execute(
            """SELECT * FROM concepts
               WHERE name LIKE ?
                  OR EXISTS (
                      SELECT 1 FROM json_each(aliases)
                      WHERE value LIKE ?
                  )
               ORDER BY name""",
            (pattern, pattern),
        )
        return [self._row_to_concept(row) for row in cursor.fetchall()]

    def list_all(self) -> list[Concept]:
        """List all concepts ordered by name."""
        cursor = self.conn.execute("SELECT * FROM concepts ORDER BY name")
        return [self._row_to_concept(row) for row in cursor.fetchall()]

    def list_roots(self) -> list[Concept]:
        """List concepts with no parents."""
        cursor = self.conn.execute(
            """SELECT c.* FROM concepts c
               WHERE NOT EXISTS (
                   SELECT 1 FROM concept_edges e
                   WHERE e.from_concept_id = c.id AND e.relationship = 'parent'
               )
               ORDER BY c.name"""
        )
        return [self._row_to_concept(row) for row in cursor.fetchall()]

    def update(self, concept: Concept) -> None:
        """Update concept."""
        self.conn.execute(
            """UPDATE concepts SET name = ?, aliases = ?, description = ?
               WHERE id = ?""",
            (
                concept.name,
                json.dumps(concept.aliases),
                concept.description,
                str(concept.id),
            ),
        )

    def delete(self, concept_id: UUID | str) -> bool:
        """Delete concept (cascades to edges)."""
        cursor = self.conn.execute(
            "DELETE FROM concepts WHERE id = ?", (str(concept_id),)
        )
        return cursor.rowcount > 0

    def _row_to_concept(self, row: sqlite3.Row) -> Concept:
        """Convert database row to Concept object."""
        return Concept(
            id=UUID(row["id"]),
            name=row["name"],
            aliases=json.loads(row["aliases"]),
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class ConceptEdgeRepository:
    """Data access for ConceptEdge entities."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, edge: ConceptEdge) -> None:
        """Insert new concept edge."""
        self.conn.execute(
            """INSERT INTO concept_edges (from_concept_id, to_concept_id, relationship)
               VALUES (?, ?, ?)""",
            (
                str(edge.from_concept_id),
                str(edge.to_concept_id),
                edge.relationship.value,
            ),
        )

    def delete(
        self,
        from_concept_id: UUID | str,
        to_concept_id: UUID | str,
        relationship: RelationshipType,
    ) -> bool:
        """Delete a specific edge."""
        cursor = self.conn.execute(
            """DELETE FROM concept_edges
               WHERE from_concept_id = ? AND to_concept_id = ? AND relationship = ?""",
            (str(from_concept_id), str(to_concept_id), relationship.value),
        )
        return cursor.rowcount > 0

    def get_parents(self, concept_id: UUID | str) -> list[Concept]:
        """Get parent concepts (via 'parent' relationship)."""
        cursor = self.conn.execute(
            """SELECT c.* FROM concepts c
               JOIN concept_edges e ON c.id = e.to_concept_id
               WHERE e.from_concept_id = ? AND e.relationship = 'parent'
               ORDER BY c.name""",
            (str(concept_id),),
        )
        return [ConceptRepository(self.conn)._row_to_concept(row) for row in cursor.fetchall()]

    def get_children(self, concept_id: UUID | str) -> list[Concept]:
        """Get child concepts."""
        cursor = self.conn.execute(
            """SELECT c.* FROM concepts c
               JOIN concept_edges e ON c.id = e.from_concept_id
               WHERE e.to_concept_id = ? AND e.relationship = 'parent'
               ORDER BY c.name""",
            (str(concept_id),),
        )
        return [ConceptRepository(self.conn)._row_to_concept(row) for row in cursor.fetchall()]

    def get_prerequisites(self, concept_id: UUID | str) -> list[Concept]:
        """Get prerequisite concepts."""
        cursor = self.conn.execute(
            """SELECT c.* FROM concepts c
               JOIN concept_edges e ON c.id = e.to_concept_id
               WHERE e.from_concept_id = ? AND e.relationship = 'prerequisite'
               ORDER BY c.name""",
            (str(concept_id),),
        )
        return [ConceptRepository(self.conn)._row_to_concept(row) for row in cursor.fetchall()]

    def get_related(self, concept_id: UUID | str) -> list[Concept]:
        """Get related concepts (bidirectional)."""
        cursor = self.conn.execute(
            """SELECT c.* FROM concepts c
               JOIN concept_edges e ON (c.id = e.to_concept_id OR c.id = e.from_concept_id)
               WHERE (e.from_concept_id = ? OR e.to_concept_id = ?)
                 AND e.relationship = 'related'
                 AND c.id != ?
               ORDER BY c.name""",
            (str(concept_id), str(concept_id), str(concept_id)),
        )
        return [ConceptRepository(self.conn)._row_to_concept(row) for row in cursor.fetchall()]

    def get_all_edges_for_concept(self, concept_id: UUID | str) -> list[ConceptEdge]:
        """Get all edges involving a concept."""
        cursor = self.conn.execute(
            """SELECT * FROM concept_edges
               WHERE from_concept_id = ? OR to_concept_id = ?""",
            (str(concept_id), str(concept_id)),
        )
        return [self._row_to_edge(row) for row in cursor.fetchall()]

    def _row_to_edge(self, row: sqlite3.Row) -> ConceptEdge:
        """Convert database row to ConceptEdge object."""
        return ConceptEdge(
            from_concept_id=UUID(row["from_concept_id"]),
            to_concept_id=UUID(row["to_concept_id"]),
            relationship=RelationshipType(row["relationship"]),
        )


class QuestionRepository:
    """Data access for Question entities."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, question: Question) -> None:
        """Insert new question."""
        self.conn.execute(
            """INSERT INTO questions
               (id, concept_id, prompt, current_answer_id, next_review_at,
                schedule_state, difficulty, source_refs, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(question.id),
                str(question.concept_id) if question.concept_id else None,
                question.prompt,
                str(question.current_answer_id) if question.current_answer_id else None,
                question.next_review_at.isoformat() if question.next_review_at else None,
                question.schedule_state.to_json(),
                question.difficulty,
                json.dumps(question.source_refs),
                question.created_at.isoformat(),
                question.updated_at.isoformat(),
            ),
        )

    def get_by_id(self, question_id: UUID | str) -> Optional[Question]:
        """Fetch question by ID (supports prefix match)."""
        id_str = str(question_id)
        cursor = self.conn.execute(
            "SELECT * FROM questions WHERE id = ?", (id_str,)
        )
        row = cursor.fetchone()

        if row is None and len(id_str) < 36:
            cursor = self.conn.execute(
                "SELECT * FROM questions WHERE id LIKE ?", (f"{id_str}%",)
            )
            rows = cursor.fetchall()
            if len(rows) == 1:
                row = rows[0]
            elif len(rows) > 1:
                raise ValueError(f"Ambiguous question ID prefix: {id_str}")

        if row is None:
            return None
        return self._row_to_question(row)

    def get_due(self, as_of: Optional[datetime] = None) -> list[Question]:
        """Fetch questions due for review."""
        if as_of is None:
            as_of = datetime.now()

        cursor = self.conn.execute(
            """SELECT * FROM questions
               WHERE next_review_at IS NOT NULL AND next_review_at <= ?
               ORDER BY next_review_at""",
            (as_of.isoformat(),),
        )
        return [self._row_to_question(row) for row in cursor.fetchall()]

    def get_due_in_days(self, days: int, as_of: Optional[datetime] = None) -> list[Question]:
        """Fetch questions due within the next N days."""
        if as_of is None:
            as_of = datetime.now()

        end_date = as_of + timedelta(days=days)

        cursor = self.conn.execute(
            """SELECT * FROM questions
               WHERE next_review_at IS NOT NULL
                 AND next_review_at > ?
                 AND next_review_at <= ?
               ORDER BY next_review_at""",
            (as_of.isoformat(), end_date.isoformat()),
        )
        return [self._row_to_question(row) for row in cursor.fetchall()]

    def get_for_concept(self, concept_id: UUID | str) -> list[Question]:
        """Get all questions for a concept."""
        cursor = self.conn.execute(
            """SELECT * FROM questions WHERE concept_id = ? ORDER BY created_at DESC""",
            (str(concept_id),),
        )
        return [self._row_to_question(row) for row in cursor.fetchall()]

    def get_uncategorized(self) -> list[Question]:
        """Get questions not assigned to any concept."""
        cursor = self.conn.execute(
            "SELECT * FROM questions WHERE concept_id IS NULL ORDER BY created_at DESC"
        )
        return [self._row_to_question(row) for row in cursor.fetchall()]

    def update(self, question: Question) -> None:
        """Update existing question."""
        question.updated_at = datetime.now()
        self.conn.execute(
            """UPDATE questions SET
               concept_id = ?,
               prompt = ?,
               current_answer_id = ?,
               next_review_at = ?,
               schedule_state = ?,
               difficulty = ?,
               source_refs = ?,
               updated_at = ?
               WHERE id = ?""",
            (
                str(question.concept_id) if question.concept_id else None,
                question.prompt,
                str(question.current_answer_id) if question.current_answer_id else None,
                question.next_review_at.isoformat() if question.next_review_at else None,
                question.schedule_state.to_json(),
                question.difficulty,
                json.dumps(question.source_refs),
                question.updated_at.isoformat(),
                str(question.id),
            ),
        )

    def delete(self, question_id: UUID | str) -> bool:
        """Delete question (cascades to answers/reviews)."""
        cursor = self.conn.execute(
            "DELETE FROM questions WHERE id = ?", (str(question_id),)
        )
        return cursor.rowcount > 0

    def list_all(
        self,
        concept_id: Optional[UUID | str] = None,
        due_only: bool = False,
    ) -> list[Question]:
        """List questions with optional filters."""
        query = "SELECT * FROM questions WHERE 1=1"
        params: list = []

        if due_only:
            query += " AND next_review_at IS NOT NULL AND next_review_at <= ?"
            params.append(datetime.now().isoformat())

        if concept_id:
            query += " AND concept_id = ?"
            params.append(str(concept_id))

        query += " ORDER BY updated_at DESC"

        cursor = self.conn.execute(query, params)
        return [self._row_to_question(row) for row in cursor.fetchall()]

    def search(self, query: str) -> list[Question]:
        """Search questions by prompt."""
        cursor = self.conn.execute(
            "SELECT * FROM questions WHERE prompt LIKE ? ORDER BY updated_at DESC",
            (f"%{query}%",),
        )
        return [self._row_to_question(row) for row in cursor.fetchall()]

    def _row_to_question(self, row: sqlite3.Row) -> Question:
        """Convert database row to Question object."""
        return Question(
            id=UUID(row["id"]),
            concept_id=UUID(row["concept_id"]) if row["concept_id"] else None,
            prompt=row["prompt"],
            current_answer_id=UUID(row["current_answer_id"]) if row["current_answer_id"] else None,
            next_review_at=datetime.fromisoformat(row["next_review_at"]) if row["next_review_at"] else None,
            schedule_state=ScheduleState.from_json(row["schedule_state"]),
            difficulty=row["difficulty"],
            source_refs=json.loads(row["source_refs"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class AnswerRepository:
    """Data access for Answer entities."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, answer: Answer) -> None:
        """Insert new answer."""
        self.conn.execute(
            """INSERT INTO answers
               (id, question_id, raw_notes, simple_explanation, gaps_questions,
                final_explanation, analogies_examples, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(answer.id),
                str(answer.question_id),
                answer.raw_notes,
                answer.simple_explanation,
                answer.gaps_questions,
                answer.final_explanation,
                answer.analogies_examples,
                answer.created_at.isoformat(),
            ),
        )

    def get_by_id(self, answer_id: UUID | str) -> Optional[Answer]:
        """Fetch answer by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM answers WHERE id = ?", (str(answer_id),)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_answer(row)

    def get_for_question(self, question_id: UUID | str) -> list[Answer]:
        """Get all answers for a question (newest first)."""
        cursor = self.conn.execute(
            """SELECT * FROM answers
               WHERE question_id = ?
               ORDER BY created_at DESC""",
            (str(question_id),),
        )
        return [self._row_to_answer(row) for row in cursor.fetchall()]

    def get_latest_for_question(self, question_id: UUID | str) -> Optional[Answer]:
        """Get the most recent answer for a question."""
        cursor = self.conn.execute(
            """SELECT * FROM answers
               WHERE question_id = ?
               ORDER BY created_at DESC
               LIMIT 1""",
            (str(question_id),),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_answer(row)

    def update(self, answer: Answer) -> None:
        """Update answer content."""
        self.conn.execute(
            """UPDATE answers SET
               raw_notes = ?,
               simple_explanation = ?,
               gaps_questions = ?,
               final_explanation = ?,
               analogies_examples = ?
               WHERE id = ?""",
            (
                answer.raw_notes,
                answer.simple_explanation,
                answer.gaps_questions,
                answer.final_explanation,
                answer.analogies_examples,
                str(answer.id),
            ),
        )

    def _row_to_answer(self, row: sqlite3.Row) -> Answer:
        """Convert database row to Answer object."""
        return Answer(
            id=UUID(row["id"]),
            question_id=UUID(row["question_id"]),
            raw_notes=row["raw_notes"],
            simple_explanation=row["simple_explanation"],
            gaps_questions=row["gaps_questions"],
            final_explanation=row["final_explanation"],
            analogies_examples=row["analogies_examples"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class ReviewRepository:
    """Data access for Review entities."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, review: Review) -> None:
        """Insert new review."""
        self.conn.execute(
            """INSERT INTO reviews
               (id, question_id, answer_id, scheduled_for, completed_at,
                status, self_grade, attempted_explanation, recalled_from_memory,
                gaps_identified, notes, ai_session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(review.id),
                str(review.question_id),
                str(review.answer_id),
                review.scheduled_for.isoformat(),
                review.completed_at.isoformat() if review.completed_at else None,
                review.status.value,
                review.self_grade,
                review.attempted_explanation,
                1 if review.recalled_from_memory else (0 if review.recalled_from_memory is False else None),
                review.gaps_identified,
                review.notes,
                str(review.ai_session_id) if review.ai_session_id else None,
            ),
        )

    def get_by_id(self, review_id: UUID | str) -> Optional[Review]:
        """Fetch review by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM reviews WHERE id = ?", (str(review_id),)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_review(row)

    def get_for_question(self, question_id: UUID | str) -> list[Review]:
        """Get all reviews for a question (newest first)."""
        cursor = self.conn.execute(
            """SELECT * FROM reviews
               WHERE question_id = ?
               ORDER BY scheduled_for DESC""",
            (str(question_id),),
        )
        return [self._row_to_review(row) for row in cursor.fetchall()]

    def get_pending_for_question(self, question_id: UUID | str) -> Optional[Review]:
        """Get pending review for a question if one exists."""
        cursor = self.conn.execute(
            """SELECT * FROM reviews
               WHERE question_id = ? AND status = ?
               ORDER BY scheduled_for DESC
               LIMIT 1""",
            (str(question_id), ReviewStatus.PENDING.value),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_review(row)

    def complete(
        self,
        review_id: UUID | str,
        grade: int,
        attempted_explanation: Optional[str] = None,
        recalled_from_memory: Optional[bool] = None,
        gaps: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Mark review as completed with grade and explanation details."""
        self.conn.execute(
            """UPDATE reviews SET
               completed_at = ?,
               status = ?,
               self_grade = ?,
               attempted_explanation = ?,
               recalled_from_memory = ?,
               gaps_identified = ?,
               notes = ?
               WHERE id = ?""",
            (
                datetime.now().isoformat(),
                ReviewStatus.COMPLETED.value,
                grade,
                attempted_explanation,
                1 if recalled_from_memory else (0 if recalled_from_memory is False else None),
                gaps,
                notes,
                str(review_id),
            ),
        )

    def skip(self, review_id: UUID | str) -> None:
        """Mark review as skipped."""
        self.conn.execute(
            """UPDATE reviews SET
               completed_at = ?,
               status = ?
               WHERE id = ?""",
            (
                datetime.now().isoformat(),
                ReviewStatus.SKIPPED.value,
                str(review_id),
            ),
        )

    def _row_to_review(self, row: sqlite3.Row) -> Review:
        """Convert database row to Review object."""
        recalled = row["recalled_from_memory"]
        return Review(
            id=UUID(row["id"]),
            question_id=UUID(row["question_id"]),
            answer_id=UUID(row["answer_id"]),
            scheduled_for=datetime.fromisoformat(row["scheduled_for"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            status=ReviewStatus(row["status"]),
            self_grade=row["self_grade"],
            attempted_explanation=row["attempted_explanation"],
            recalled_from_memory=bool(recalled) if recalled is not None else None,
            gaps_identified=row["gaps_identified"],
            notes=row["notes"],
            ai_session_id=UUID(row["ai_session_id"]) if row["ai_session_id"] else None,
        )
