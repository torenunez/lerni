"""`lerni feedback`: the admin reads educators' feedback, groups it, and closes it.

Nothing here changes the app or a map; the admin makes changes by hand.
"""

import typer
from rich.console import Console

from lerni.student.feedback import FeedbackError, FeedbackStore, themes

feedback_app = typer.Typer(help="Read and close educators' feedback.",
                           invoke_without_command=True)
console = Console()


@feedback_app.callback()
def list_cmd(
    ctx: typer.Context,
    summary: bool = typer.Option(False, "--summary", help="Ask Claude to group open entries."),
) -> None:
    """List open feedback (or group it into themes with --summary)."""
    if ctx.invoked_subcommand is not None:
        return
    entries = FeedbackStore().entries(open_only=True)
    if not entries:
        console.print("No open feedback.")
        return
    for f in entries:
        about = f" · about {f.map}" if f.map else ""
        console.print(f"[bold]{f.number}. {f.day} · {f.who}{about}[/bold]")
        console.print(f"  {f.text}", markup=False)
        if f.summary:
            console.print(f"  Claude: {f.summary}", markup=False)
    if summary:
        from lerni.student.adapters.claude_code import ClaudeCodeChat, claude_cli_available

        if not claude_cli_available():
            console.print("[red]The claude CLI isn't installed here.[/red]")
            raise typer.Exit(1)
        console.print("\n[bold]Themes[/bold]")
        console.print(themes(ClaudeCodeChat(), entries), markup=False)


@feedback_app.command("done")
def done_cmd(number: int = typer.Argument(..., help="The entry's number.")) -> None:
    """Mark one entry handled."""
    try:
        FeedbackStore().mark_done(number)
    except FeedbackError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None
    console.print(f"Feedback {number} marked handled.")
