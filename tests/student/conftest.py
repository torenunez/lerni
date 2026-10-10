"""Shared fixtures for student app tests: every test gets its own data folder."""

import pytest


@pytest.fixture(autouse=True)
def isolated_student_data(tmp_path, monkeypatch):
    """Point the student app's data folder at a temp dir, so no test writes to ~/.lerni."""
    monkeypatch.setenv("LERNI_STUDENT_DATA", str(tmp_path / "student-data"))
