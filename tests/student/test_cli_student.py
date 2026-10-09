"""The admin's `lerni student` commands, for the first educator account and recovery."""

from typer.testing import CliRunner

from lerni.cli import app
from lerni.student.students import StudentStore


def test_admin_adds_the_first_educator_from_the_terminal():
    result = CliRunner().invoke(
        app,
        ["student", "add", "alba", "--name", "Alba", "--kind", "independent", "--educator"],
        input="long enough\nlong enough\n",
    )
    assert result.exit_code == 0, result.output
    assert StudentStore().get("alba").educator


def test_logs_shows_the_last_exchanges():
    from lerni.student.logs import ConversationLog

    ConversationLog().write("sam", {"question": "I love cars", "answer": "Vroom!",
                                    "tags": {"new_interests": ["cars"]}})
    result = CliRunner().invoke(app, ["logs", "sam"])
    assert result.exit_code == 0, result.output
    assert "I love cars" in result.output and "new_interests" in result.output
