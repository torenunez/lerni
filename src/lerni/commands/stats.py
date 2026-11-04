"""`lerni stats`: how the students are doing, from a read-only SQLite copy of their data."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import typer

from lerni.student.students import default_data_dir


def _fail(message: str) -> typer.Exit:
    typer.secho(message, fg=typer.colors.RED, err=True)
    return typer.Exit(1)


def stats_cmd(username: str = typer.Argument("", help="One student's report."),
              weeks: int = typer.Option(4, "--weeks", min=1, help="Weeks to look back."),
              everything: bool = typer.Option(False, "--all", help="Every week there is."),
              sql: str = typer.Option("", "--sql", help="Run one read-only query instead."),
              data: Path = typer.Option(  # noqa: B008
                  None, "--data", help="The data folder (default: production's).")) -> None:
    """Rebuild the stats copy, then show every student, one student, or a query's rows."""
    from lerni.student.stats import build, monday, overview, query, report

    folder = (data or default_data_dir()).expanduser().resolve()
    if not folder.is_dir():  # a typo never makes a new folder
        raise _fail(f"No such data folder: {folder}")
    try:
        built = build(folder)
    except (OSError, sqlite3.Error) as exc:
        raise _fail(f"Couldn't build the stats copy: {exc}") from None
    if sql:
        try:
            columns, rows = query(built.path, sql)
        except (sqlite3.Error, sqlite3.Warning) as exc:
            raise _fail(f"Query refused: {exc}") from None
        for row in [columns, *rows]:  # tab-separated, so it pipes into other tools
            typer.echo("\t".join("" if cell is None else str(cell) for cell in row))
        return
    # whole weeks, this one included, so each week's row is a full count
    start = "" if everything else (
        monday(date.today()) - timedelta(weeks=weeks - 1)).isoformat()
    if username:
        if not query(built.path, "SELECT 1 FROM students WHERE username = ?", (username,))[1]:
            raise _fail(f"No student {username}.")
        window = "all time" if everything else "this week" if weeks == 1 \
            else f"last {weeks} weeks"
        typer.echo(report(built.path, username, start, window))
    else:
        typer.echo(overview(built.path, start))
    if built.skipped:
        typer.echo(f"\nCut-off lines or broken files skipped: {built.skipped}")
