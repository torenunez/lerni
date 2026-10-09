"""The `lerni student` commands: the admin's way to add the first educator and to recover.

Everyday account changes happen in the app's Students tab. These run on the
home server, against the same accounts folder (``$LERNI_STUDENT_DATA`` or
``~/.lerni/student``). Passwords are typed at a hidden prompt, never as arguments.
"""

import typer
from rich.console import Console

from lerni.student.students import AccountError, Kind, StudentStore

student_app = typer.Typer(help="Manage student app accounts (first setup and recovery).",
                          no_args_is_help=True)
console = Console()


def _fail(exc: Exception) -> None:
    console.print(f"[red]{exc}[/red]")  # the reason only, never a password
    raise typer.Exit(1)


@student_app.command("add")
def add_cmd(
    username: str = typer.Argument(..., help="Lowercase letters, digits, or hyphens."),
    name: str = typer.Option(..., "--name", help="Display name (a nickname is fine)."),
    kind: str = typer.Option(..., "--kind", help="supervised or independent."),
    educator: bool = typer.Option(False, "--educator", help="May add students and plan."),
) -> None:
    """Add an account; the password is asked for at a hidden prompt."""
    # hidden and typed twice, so it never shows on screen or in shell history
    password = typer.prompt("Password", hide_input=True, confirmation_prompt=True)
    try:
        s = StudentStore().add(username, name, Kind(kind), password, educator=educator)
    except (AccountError, ValueError) as exc:
        _fail(exc)
    console.print(f"Added {s.username} ({s.kind.value}{', educator' if s.educator else ''}).")


@student_app.command("reset-password")
def reset_cmd(username: str = typer.Argument(...)) -> None:
    """Set a new password; every device signed in as this account is signed out."""
    password = typer.prompt("New password", hide_input=True, confirmation_prompt=True)  # hidden
    try:
        StudentStore().reset_password(username, password)
    except AccountError as exc:
        _fail(exc)
    console.print(f"New password set for {username}.")


@student_app.command("educator")
def educator_cmd(
    username: str = typer.Argument(...),
    off: bool = typer.Option(False, "--off", help="Take educator access away instead."),
) -> None:
    """Give an independent account educator access (or take it away with --off)."""
    try:
        StudentStore().set_educator(username, not off)
    except AccountError as exc:
        _fail(exc)
    console.print(f"{username} is {'no longer ' if off else ''}an educator.")


@student_app.command("list")
def list_cmd() -> None:
    """List accounts: usernames, kinds, and who is an educator."""
    for s in StudentStore().list_students():  # names and flags only, never password hashes
        flags = ", educator" if s.educator else ""
        flags += ", archived" if s.archived else ""
        console.print(f"{s.username}  {s.display_name}  ({s.kind.value}{flags})")
