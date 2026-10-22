"""`lerni map`: the admin reads a map's change journal, undoes one change, or rebuilds a map.

Works on the data folder the student app uses (``LERNI_STUDENT_DATA``, or ``~/.lerni/student``),
safely while the server runs: both take the same per-map lock.
"""

import typer
from rich.console import Console

from lerni.student.interests import MapStore
from lerni.student.journal import JournalError, summary
from lerni.student.students import AccountError

console = Console()
map_app = typer.Typer(help="A map's change journal: read it, undo a change, or rebuild a map.")


def _fail(exc: Exception) -> None:
    console.print(f"[red]{exc}[/red]", markup=True)
    raise typer.Exit(1) from None


@map_app.command("log")
def log_cmd(username: str = typer.Argument(..., help="Whose map."),
            last: int = typer.Option(20, "--last", min=1, help="How many changes to show."),
            ) -> None:
    """Each change: its number, when, who made it, and what (names only)."""
    try:
        events = MapStore().journal.read(username)
    except AccountError as exc:
        _fail(exc)
    if not events:
        console.print("No changes journaled yet (the journal starts at the next change).")
    for e in events[-last:]:
        console.print(f"{e['n']:>4}  {e.get('time', ''):19}  {e.get('by', ''):<16} {summary(e)}",
                      markup=False)


@map_app.command("undo")
def undo_cmd(username: str = typer.Argument(..., help="Whose map."),
             n: int = typer.Argument(..., help="The change to undo (from lerni map log).")) -> None:
    """Reverse one change, as a new change (so the undo can be undone too)."""
    try:
        MapStore().undo(username, n)
    except (AccountError, JournalError) as exc:
        _fail(exc)
    console.print(f"Undid change {n}. The server shows it at the next redraw.")


@map_app.command("rebuild")
def rebuild_cmd(username: str = typer.Argument(..., help="Whose map."),
                upto: int = typer.Option(None, "--upto", help="Return the map to just after this "
                                         "change (a new change; undo it to go forward again).")
                ) -> None:
    """Check that the journal alone gives today's map, or return the map to an earlier point."""
    try:
        same = MapStore().rebuild(username, upto)
    except (AccountError, JournalError) as exc:
        _fail(exc)
    if upto is not None:
        console.print(f"The map is back as it was after change {upto}.")
    elif same:
        console.print("The journal rebuilds today's map exactly.")
    else:
        console.print("[yellow]The journal doesn't match today's map (a change made by an "
                      "older version, or a cut-off line); nothing was written.[/yellow]")
