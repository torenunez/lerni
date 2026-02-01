"""Notification commands for macOS reminders."""

import subprocess
import sys

import typer
from rich.console import Console

from ..config import load_config
from ..db import get_connection, QuestionRepository

console = Console()


def notify_cmd(
    setup: bool = typer.Option(False, "--setup", help="Show cron/launchd setup instructions"),
):
    """
    Send macOS notification with today's review summary.

    Shows a system notification if there are questions due for review.
    Use --setup to see instructions for daily automated reminders.
    """
    if setup:
        _show_setup_instructions()
        return

    # Check platform
    if sys.platform != "darwin":
        console.print("[yellow]Notifications are only supported on macOS.[/yellow]")
        raise typer.Exit(1)

    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        due_questions = question_repo.get_due()
        due_count = len(due_questions)

    if due_count == 0:
        console.print("[green]No questions due for review.[/green]")
        return

    # Build notification message
    title = "Lerni Review Reminder"
    if due_count == 1:
        message = f"1 question due: {due_questions[0].prompt[:30]}"
    else:
        message = f"{due_count} questions due for review"

    # Send macOS notification via osascript
    script = f'display notification "{message}" with title "{title}"'

    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
        )
        console.print(f"[green]Notification sent:[/green] {message}")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to send notification:[/red] {e}")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]osascript not found. Are you on macOS?[/red]")
        raise typer.Exit(1)


def _show_setup_instructions():
    """Print instructions for setting up daily notifications."""
    config = load_config()
    reminder_time = config.notifications.reminder_time

    # Parse time for cron format
    try:
        hour, minute = reminder_time.split(":")
    except ValueError:
        hour, minute = "9", "0"

    console.print("\n[bold]Daily Notification Setup[/bold]\n")

    # Get the path to the study command
    console.print("[bold cyan]Option 1: Crontab (simple)[/bold cyan]\n")
    console.print("Add this line to your crontab ([dim]crontab -e[/dim]):\n")
    console.print(
        f"[green]{minute} {hour} * * * ~/.lerni/.venv/bin/study notify 2>/dev/null[/green]"
    )
    console.print(
        "\n[dim]This runs at {reminder_time} daily. Adjust path if needed.[/dim]"
    )

    console.print("\n[bold cyan]Option 2: launchd (recommended for macOS)[/bold cyan]\n")
    console.print("Create [dim]~/Library/LaunchAgents/com.lerni.notify.plist[/dim]:\n")

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lerni.notify</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>~/.lerni/.venv/bin/study notify</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>StandardErrorPath</key>
    <string>/tmp/lerni-notify.err</string>
</dict>
</plist>"""

    console.print(f"[dim]{plist}[/dim]")

    console.print("\nThen load it with:")
    console.print(
        "[green]launchctl load ~/Library/LaunchAgents/com.lerni.notify.plist[/green]"
    )

    console.print(
        f"\n[dim]Current reminder time from config: {reminder_time}[/dim]"
    )
    console.print(
        "[dim]Edit ~/.lerni/config.toml to change the time.[/dim]"
    )
