"""`lerni race`: a batch of race questions for the admin to rate, and the ratings read back
into the checked bank (v4.5). Prints numbers only; question text goes only to ``--out``."""

import json
import os
from datetime import date
from pathlib import Path

import typer
from rich.console import Console

from lerni.student.students import AccountError, Kind, StudentStore, default_data_dir

console = Console()
race_app = typer.Typer(help="Rate race questions in bulk: write a batch, read the ratings back.")


def _fail(message: str) -> None:
    console.print(f"[red]{message}[/red]", markup=True)
    raise typer.Exit(1) from None


@race_app.command("batch")
def batch_cmd(
    user: str = typer.Option(..., "--user", help="Whose map to write from."),
    out: Path = typer.Option(..., "--out", help="The JSON file to write (private)."),  # noqa: B008
    per_goal: int = typer.Option(
        8, "--per-goal", min=1, max=20, help="Questions wanted on each goal."
    ),
    data: Path = typer.Option(  # noqa: B008
        None, "--data", help="The data folder (default: production's)."
    ),
) -> None:
    """Write about --per-goal checked questions on each goal, on a copy of the data."""
    from lerni.student.batch import write_batch
    from lerni.student.web.serve import _claude_quizzer, _embedder

    root = data or default_data_dir()
    try:
        student = StudentStore(root).get(user)
    except AccountError as exc:
        _fail(str(exc))
    quizzer = _claude_quizzer()
    if quizzer is None:
        _fail("Claude Code isn't installed here.")
    embedder, _ = _embedder()
    rows = write_batch(
        root,
        user,
        quizzer,
        supervised=student.kind == Kind.SUPERVISED,
        today=date.today(),
        per_goal=per_goal,
        checker=quizzer,
        embedder=embedder,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # private from the start
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"rows": rows}, handle, ensure_ascii=False, indent=2)
    goals = {r["goal"] for r in rows}
    console.print(f"Wrote {len(rows)} questions on {len(goals)} goals to {out}.", markup=False)


@race_app.command("labels")
def labels_cmd(
    file: Path = typer.Argument(..., help="The rated rows, as JSON."),  # noqa: B008
    user: str = typer.Option(..., "--user", help="Whose bank to add to."),
    data: Path = typer.Option(  # noqa: B008
        None, "--data", help="The data folder (default: production's)."
    ),
) -> None:
    """Add the rated rows to the checked bank; prints how many were kept and skipped."""
    from lerni.student.bank import BankStore
    from lerni.student.interests import MapStore

    root = data or default_data_dir()
    try:
        StudentStore(root).get(user)
        loaded = json.loads(file.read_text(encoding="utf-8"))
    except AccountError as exc:
        _fail(str(exc))
    except (OSError, ValueError) as exc:
        _fail(f"Couldn't read the file ({type(exc).__name__}).")
    rows = loaded.get("rows") if isinstance(loaded, dict) else loaded
    if not isinstance(rows, list):
        _fail("The file needs a list of rows.")
    kept, skipped = BankStore(root).add_labels(
        user, [r for r in rows if isinstance(r, dict)], MapStore(root).get(user), date.today()
    )
    console.print(f"Banked {kept} rated questions; skipped {skipped} (goal gone or incomplete).")
