"""The `lerni serve` command: run the student app on the home server."""

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def serve_cmd(
    host: str = typer.Option("0.0.0.0", help="Address to bind; 0.0.0.0 reaches the home network."),
    port: int = typer.Option(7860, help="Port to listen on."),
    cert: Path = typer.Option(  # noqa: B008 - typer reads options from defaults
        None, help="HTTPS certificate (from mkcert); needs --key."),
    key: Path = typer.Option(  # noqa: B008
        None, help="The certificate's private key; needs --cert."),
) -> None:
    """Run the student app: the sign-in page and the app with tabs by role."""
    try:
        from lerni.student.web.serve import serve
    except ImportError:
        console.print('[red]The student app needs Gradio: pip install -e ".[student]"[/red]')
        raise typer.Exit(1) from None
    try:
        serve(host=host, port=port, cert=cert, key=key)
    except ValueError as exc:  # a missing or unpaired HTTPS file
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None
