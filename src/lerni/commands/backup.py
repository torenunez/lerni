"""`lerni backup`: copy Lerni's data folder now, or every night at 03:00, or put a copy
back."""

import os
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console

from lerni.student.students import default_data_dir

console = Console()
backup_app = typer.Typer(help="Copies of Lerni's data folder: tonight's, the newest 30 kept.")


def _backups(data: Path | None = None) -> Path:
    return (data or default_data_dir()).parent / "backups"  # ~/.lerni/backups, beside the data


def _data(data: Path | None) -> Path:
    from lerni.student.jsonfiles import private

    os.umask(0o077)  # anything written from here on is this account's only
    folder = (data or default_data_dir()).expanduser().resolve()
    if data and not folder.is_dir():  # a typo never makes a new folder
        console.print(f"[red]No such data folder: {folder}[/red]")
        raise typer.Exit(1)
    private(folder)
    return folder


@backup_app.command("run")
def run_cmd(to: Path = typer.Option(  # noqa: B008
                None, "--to", help="Also copy it here (an external drive)."),
            keep: int = typer.Option(30, "--keep", min=1, help="Nightly copies kept."),
            data: Path = typer.Option(  # noqa: B008
                None, "--data", help="The data folder to copy (default: production's).")) -> None:
    """Copy the data folder to ~/.lerni/backups/<its name>/nightly-<today>/ (and --to)."""
    from lerni.student.backup import run

    data = _data(data)
    for place in [_backups(data), *([to] if to else [])]:
        try:
            console.print(f"Copied to {run(data, place, date.today(), keep)}")
        except OSError as exc:
            console.print(f"[red]Couldn't copy to {place}: {exc}[/red]")
            raise typer.Exit(1) from None


@backup_app.command("install")
def install_cmd(data: Path = typer.Option(  # noqa: B008
                    None, "--data", help="The data folder to copy (default: production's)."),
                ) -> None:
    """Run `lerni backup run` every night at 03:00, as a LaunchAgent."""
    from lerni.student.backup import install
    from lerni.student.service import ServiceError

    lerni = Path(sys.executable).parent / "lerni"  # this checkout's own venv
    checkout = Path(__file__).resolve().parents[3]
    try:
        install(lerni, checkout, (data or default_data_dir()).expanduser().resolve())
    except ServiceError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None
    console.print("Installed: a copy every night at 03:00, the newest 30 kept.")


@backup_app.command("status")
def status_cmd() -> None:
    """Whether the nightly copy is set up, and the newest copy."""
    from lerni.student.backup import status

    console.print(status(_backups(), default_data_dir()))


@backup_app.command("restore")
def restore_cmd(name: str = typer.Argument(
                    "", help="The copy to put back (nightly-YYYY-MM-DD, or its path)."),
                data: Path = typer.Option(  # noqa: B008
                    None, "--data", help="The data folder to replace (default: production's)."),
                yes: bool = typer.Option(False, "--yes", help="Don't ask first.")) -> None:
    """Put a whole nightly copy back, keeping the folder it replaces; restarts its server."""
    from lerni.student.backup import NIGHTLY, BackupError, restore
    from lerni.student.service import ServiceError, wait_until_up

    data = _data(data)
    copies = _backups(data) / data.name

    def describe(folder: Path) -> str:
        count = lambda sub: len(list((folder / sub).glob("*.json")))  # noqa: E731
        return f"{count('students')} accounts, {count('maps')} maps"

    if not name:
        nights = sorted((p for p in copies.glob("nightly-*") if NIGHTLY.match(p.name)),
                        reverse=True) if copies.is_dir() else []
        console.print(f"Copies of {data}, newest first:" if nights else f"No copies of {data}.")
        for p in nights:
            console.print(f"  {p.name}   {describe(p)}")
        if nights:
            flag = f" --data {data}" if data.name != "student" else ""  # development's, say
            console.print(f"Restore one: lerni backup restore {nights[0].name}{flag}")
        return
    copy = Path(name).expanduser() if "/" in name else copies / name
    if not yes:
        console.print(f"This puts {data} back to {copy.name} ({describe(copy)}).\n"
                      "Everything since then is set aside, not deleted. Its server restarts; "
                      "open conversations end.")
        if not typer.confirm("Restore?"):
            raise typer.Exit(1)
    try:
        kept, server = restore(data, copy)
    except BackupError as exc:  # says itself whether anything changed
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None
    except (ServiceError, OSError) as exc:
        console.print(f"[red]Couldn't restore, nothing changed: {exc}[/red]")
        raise typer.Exit(1) from None
    console.print(f"Restored {copy.name}.\nThe folder it replaced: {kept}")
    if server:
        try:
            wait_until_up(server, Path.home())
            console.print(f"{server} is running again.")
        except ServiceError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from None
