"""`lerni reading`: the educator's reading sources, from the shortlist Sheet saved as CSV
(v4.13). The sources stay in the private data folder, never in the repo."""

from collections import Counter
from pathlib import Path

import typer

from lerni.student.students import default_data_dir

reading_app = typer.Typer(help="Reading races: the educator's sources.")


@reading_app.command("import")
def import_cmd(
    csv_file: Path = typer.Argument(..., help="The shortlist Sheet, saved as CSV."),  # noqa: B008
    data: Path = typer.Option(  # noqa: B008
        None, "--data", help="The data folder (default: production's)."
    ),
) -> None:
    """Replace the reading sources with the CSV's ticked rows; prints counts only."""
    from lerni.student.reading import ReadingStore, import_sources

    folder = (data or default_data_dir()).expanduser().resolve()
    if not folder.is_dir():  # a typo never makes a new folder
        typer.echo(f"No such data folder: {folder}", err=True)
        raise typer.Exit(1)
    try:
        sources = import_sources(csv_file)
    except (OSError, UnicodeDecodeError) as exc:
        typer.echo(f"Couldn't read {csv_file} ({type(exc).__name__}).", err=True)
        raise typer.Exit(1) from None
    if not sources:  # an empty import never wipes the list
        typer.echo("No ticked rows with a kind and title: nothing changed.", err=True)
        raise typer.Exit(1)
    ReadingStore(folder).save_sources(sources)
    kinds = Counter(s.kind for s in sources)
    fetched = sum(s.fetch for s in sources)  # .gov pages read when writing
    typer.echo(f"Saved {len(sources)} sources: " + ", ".join(
        f"{n} {k}" for k, n in sorted(kinds.items())) + f"; {fetched} pages fetched when writing.")
