"""CLI entry point for Lerni."""

import typer
from rich.console import Console

from .db import init_db

# Create main app
app = typer.Typer(
    name="study",
    help="Lerni - Learn deeply, remember permanently",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Create concept subcommand group
concept_app = typer.Typer(
    help="Manage concepts in the knowledge graph",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main_callback():
    """Initialize database on first run."""
    init_db()


# Import and register commands after app is created to avoid circular imports
def register_commands():
    """Register all command modules."""
    from .commands import question, review, organize, notify

    # Question commands (at root level)
    app.command("new")(question.new_question)
    app.command("edit")(question.edit_question)
    app.command("snapshot")(question.snapshot_question)
    app.command("show")(question.show_question)
    app.command("history")(question.question_history)
    app.command("delete")(question.delete_question)

    # Review commands
    app.command("review")(review.review_cmd)
    app.command("skip")(review.skip_cmd)
    app.command("today")(review.today_cmd)

    # Organization commands
    app.command("list")(organize.list_cmd)
    app.command("search")(organize.search_cmd)
    app.command("assign")(organize.assign_cmd)
    app.command("meta")(organize.meta_cmd)

    # Concept commands (subgroup)
    concept_app.command("new")(organize.concept_new)
    concept_app.command("list")(organize.concept_list)
    concept_app.command("show")(organize.concept_show)
    concept_app.command("link")(organize.concept_link)
    concept_app.command("unlink")(organize.concept_unlink)
    concept_app.command("delete")(organize.concept_delete)
    app.add_typer(concept_app, name="concept")

    # Notification commands
    app.command("notify")(notify.notify_cmd)


# Register commands
register_commands()


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
