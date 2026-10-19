"""The `lerni service` commands: run the student app on its own, as macOS LaunchAgents."""

from pathlib import Path
from typing import Any

import typer
from rich.console import Console

console = Console()
service_app = typer.Typer(help="Run the student app on its own (macOS LaunchAgents).")
NAMES = ("prod", "dev")


def _check(name: str) -> str:
    if name not in NAMES:
        console.print("[red]The name is prod or dev.[/red]")
        raise typer.Exit(1)
    return name


def _plainly(fn: Any, *args: Any) -> Any:
    """Run a service call; say any problem in one red line instead of a traceback."""
    from lerni.student.service import ServiceError

    try:
        return fn(*args)
    except ServiceError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None


@service_app.command("install")
def install_cmd(
    name: str = typer.Argument(..., help="prod or dev."),
    cert: Path = typer.Option(..., help="HTTPS certificate (from mkcert)."),  # noqa: B008
    key: Path = typer.Option(..., help="The certificate's private key."),  # noqa: B008
    port: int = typer.Option(0, help="Default: 7860 for prod, 7861 for dev."),
    label: str | None = typer.Option(None, help="Default: none for prod, Development for dev."),
    data: Path | None = typer.Option(  # noqa: B008
        None, help="Data folder (LERNI_STUDENT_DATA); dev's default is ~/.lerni/student-dev."
    ),
) -> None:
    """Start this checkout's server now, at every login, and again after a crash."""
    from lerni.student.service import Server, install, log_path

    dev = _check(name) == "dev"
    for path in (cert, key):
        if not path.expanduser().is_file():
            console.print(f"[red]No such file: {path}[/red]")
            raise typer.Exit(1)
    if dev and data is None:
        data = Path.home() / ".lerni" / "student-dev"  # never production's data
    server = Server(name, port or (7861 if dev else 7860),
                    ("Development" if dev else "") if label is None else label,
                    data.expanduser().resolve() if data else None,
                    cert.expanduser().resolve(), key.expanduser().resolve())
    path = _plainly(install, server)
    console.print(f"Agent: {path}\nLog:   {log_path(Path.home(), name)}\nStarted.")


@service_app.command("restart")
def restart_cmd(name: str = typer.Argument(..., help="prod or dev.")) -> None:
    """Restart the server, on whatever code its checkout now holds."""
    from lerni.student.service import restart

    _plainly(restart, _check(name))
    console.print("Restarted.")


@service_app.command("stop")
def stop_cmd(name: str = typer.Argument(..., help="prod or dev.")) -> None:
    """Stop the server until the next install or login."""
    from lerni.student.service import stop

    stop(_check(name))
    console.print("Stopped.")


@service_app.command("uninstall")
def uninstall_cmd(name: str = typer.Argument(..., help="prod or dev.")) -> None:
    """Stop the server and remove its agent; nothing starts at login."""
    from lerni.student.service import uninstall

    uninstall(_check(name))
    console.print("Removed.")


@service_app.command("status")
def status_cmd(name: str = typer.Argument(None, help="prod or dev; both if left out.")) -> None:
    """Whether each server is running and answering."""
    from lerni.student.service import status

    for n in [_check(name)] if name else list(NAMES):
        console.print(status(n))
