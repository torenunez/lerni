"""Pytest fixtures for Lerni tests."""

import tempfile
from pathlib import Path

import pytest

from lerni.db import init_db, get_connection
from lerni.models import Concept, Question, Answer


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        yield db_path


@pytest.fixture
def db_connection(temp_db):
    """Provide a database connection for testing."""
    with get_connection(temp_db) as conn:
        yield conn


@pytest.fixture
def sample_concept():
    """Create a sample concept for testing."""
    return Concept.create("Python Decorators", description="Function wrappers using @ syntax")


@pytest.fixture
def sample_question(sample_concept):
    """Create a sample question for testing."""
    return Question.create("Explain Python decorators", concept=sample_concept)


@pytest.fixture
def sample_answer(sample_question):
    """Create a sample answer with all fields populated."""
    return Answer.create(
        sample_question,
        raw_notes="Decorators are functions that modify other functions. They use the @ syntax.",
        simple_explanation="A decorator wraps a function to add extra behavior without changing the original function.",
        gaps_questions="How do decorators with arguments work? What about class decorators?",
        final_explanation="Decorators leverage Python's first-class functions and closures to wrap and modify callable behavior.",
        analogies_examples="Like gift wrapping - the gift (function) is unchanged but presented differently (with added behavior).",
    )
