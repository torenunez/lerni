"""`lerni backup`: copy Lerni's data folder now, or every night at 03:00."""

import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console

from lerni.student.students import default_data_dir

console = Console()
backup_app = typer.Typer(help="Copies of Lerni's data folder: tonight's, the newest 30 kept.")


def _backups() -> Path:
    return default_data_dir().parent / "backups"  # ~/.lerni/backups, beside the data


@backup_app.command("run")
def run_cmd(to: Path = typer.Option(  # noqa: B008
                None, "--to", help="Also copy it here (an external drive)."),
            keep: int = typer.Option(30, "--keep", min=1, help="Nightly copies kept.")) -> None:
    """Copy the data folder to ~/.lerni/backups/<its name>/nightly-<today>/ (and --to)."""
    from lerni.student.backup import run

    data = default_data_dir()
    for place in [_backups(), *([to] if to else [])]:
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
