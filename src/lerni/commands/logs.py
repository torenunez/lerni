"""`lerni logs`: the admin reads recent conversations (a year is kept), to check the maps."""

import json

import typer
from rich.console import Console

from lerni.student.logs import ConversationLog
from lerni.student.students import AccountError

console = Console()


def logs_cmd(
    username: str = typer.Argument(None, help="Only this student (default: everyone)."),
    days: int = typer.Option(7, "--days", min=1, help="How many days back (a year is kept)."),
) -> None:
    """Show each kept exchange: when, who, the question, the answer, and what the tagger did."""
    try:
        records = ConversationLog().read(username, days=days)
    except AccountError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None
    if not records:
        console.print(f"No conversations in the last {days} days.")
    for r in records:
        console.print(f"[bold]{r.get('time', '')} · {r['username']}[/bold]", markup=True)
        console.print(f"  Q: {r.get('question', '')}", markup=False)
        console.print(f"  A: {r.get('answer', '')}", markup=False)
        console.print(f"  map: {json.dumps(r.get('tags'), ensure_ascii=False)}", markup=False)
