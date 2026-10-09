"""The `lerni serve` command: run the student app on the home server."""

import typer
from rich.console import Console

console = Console()


def serve_cmd(
    host: str = typer.Option("0.0.0.0", help="Address to bind; 0.0.0.0 reaches the home network."),
    port: int = typer.Option(7860, help="Port to listen on."),
) -> None:
    """Run the student app: the sign-in page and the app with tabs by role."""
    try:
        from lerni.student.web.serve import serve
    except ImportError:
        console.print('[red]The student app needs Gradio: pip install -e ".[student]"[/red]')
        raise typer.Exit(1) from None
    serve(host=host, port=port)
