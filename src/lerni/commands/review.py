"""Review management commands."""

from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from ..config import load_config
from ..db import get_connection, QuestionRepository, AnswerRepository, ReviewRepository, ConceptRepository
from ..editor import edit_text
from ..models import Review, Question
from ..sm2 import calculate_sm2, format_interval, GRADE_DESCRIPTIONS

console = Console()


def review_cmd(
    question_id: Optional[str] = typer.Argument(
        None, help="Specific question to review (optional)"
    ),
    editor: bool = typer.Option(
        False, "--editor", "-e", help="Use external editor instead of inline prompts"
    ),
):
    """
    Start a review session.

    Without arguments, reviews all questions due today in sequence.
    With a question ID, reviews only that specific question.

    During review, you'll see the question prompt and attempt to explain
    from memory. Rate your recall on the SM-2 scale (0-5).
    """
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)

        if question_id:
            question = question_repo.get_by_id(question_id)
            if not question:
                console.print(f"[red]Question not found: {question_id}[/red]")
                raise typer.Exit(1)
            questions = [question]
        else:
            questions = question_repo.get_due()

        if not questions:
            console.print("[green]No questions due for review![/green]")
            console.print("[dim]Use 'study today' to see upcoming reviews.[/dim]")
            return

        console.print(f"\n[bold]Review Session[/bold] - {len(questions)} question(s) due\n")

        for i, question in enumerate(questions, 1):
            console.print(f"\n[bold cyan]── Question {i}/{len(questions)} ──[/bold cyan]")
            _review_single_question(conn, question, use_editor=editor)

            if i < len(questions):
                if not typer.confirm("\nContinue to next question?", default=True):
                    console.print("[dim]Session paused. Run 'study review' to continue.[/dim]")
                    break

        console.print("\n[green bold]Review session complete![/green bold]")


def _review_single_question(conn, question: Question, use_editor: bool = False):
    """
    Interactive review for a single question using 2-stage recall flow.

    Stage 1: Show question + metadata, user attempts explanation from scratch
    Stage 2: If couldn't recall, show previous answer and identify gaps
    """
    question_repo = QuestionRepository(conn)
    answer_repo = AnswerRepository(conn)
    review_repo = ReviewRepository(conn)
    concept_repo = ConceptRepository(conn)

    answer = answer_repo.get_latest_for_question(question.id)
    if not answer:
        console.print(f"[yellow]No answer for this question[/yellow]")
        return

    # Display question metadata (but NOT the answer)
    console.print()

    # Show concept if attached
    if question.concept_id:
        concept = concept_repo.get_by_id(question.concept_id)
        if concept:
            console.print(f"[dim]Concept: {concept.name}[/dim]")

    if question.difficulty:
        console.print(f"[dim]Difficulty: {question.difficulty}/5[/dim]")

    console.print(f"[dim]EF: {question.schedule_state.easiness_factor:.2f} | Interval: {question.schedule_state.interval} days | Reps: {question.schedule_state.repetitions}[/dim]")

    console.print()

    # Show the question prominently
    console.print(Panel(question.prompt, title="Question", border_style="bold yellow"))

    console.print("\n[bold cyan]Stage 1: Explain from memory[/bold cyan]")
    console.print("[dim]Try to answer this question from scratch without seeing your previous answer.[/dim]\n")

    # User attempts explanation from scratch
    attempted_explanation = edit_text(
        prompt_header=f"# Question: {question.prompt}\n#\n# Write your explanation from memory.\n# Don't worry if it's incomplete - just write what you remember.\n# Lines starting with # will be removed.",
        use_editor=use_editor,
    )

    # Ask if they could recall
    recalled = Confirm.ask("\n[bold]Were you able to explain from memory?[/bold]", default=True)

    if recalled:
        # They recalled - grade 3-5
        console.print("\n[green]Great! Now grade your recall quality.[/green]")
        console.print("[dim]Consider: Was it complete? Accurate? Did you hesitate?[/dim]\n")

        for grade in [3, 4, 5]:
            style = "green" if grade == 5 else "cyan"
            console.print(f"  [{style}]{grade}[/{style}]: {GRADE_DESCRIPTIONS[grade]}")

        grade = IntPrompt.ask("\nYour grade", choices=["3", "4", "5"])
        gaps = None

    else:
        # Couldn't recall - show previous answer, grade 0-2
        console.print("\n[bold cyan]Stage 2: Review your previous answer[/bold cyan]")
        console.print("[dim]Here's what you wrote before. Identify what you forgot.[/dim]\n")

        # Show previous explanation
        content = answer.simple_explanation or answer.raw_notes
        console.print(Panel(content, title="Your Previous Explanation", border_style="blue"))

        if answer.analogies_examples:
            console.print(
                Panel(answer.analogies_examples, title="Analogies", border_style="magenta")
            )

        # Ask them to identify gaps
        console.print("\n[dim]What did you forget or get wrong?[/dim]")
        gaps = Prompt.ask("Gaps identified", default="")

        console.print("\n[yellow]Grade your recall (0-2 since you needed to see the answer).[/yellow]\n")

        for grade in [0, 1, 2]:
            style = "red" if grade == 0 else "yellow"
            console.print(f"  [{style}]{grade}[/{style}]: {GRADE_DESCRIPTIONS[grade]}")

        grade = IntPrompt.ask("\nYour grade", choices=["0", "1", "2"])

    # Calculate next review using SM-2
    result = calculate_sm2(
        grade=grade,
        easiness_factor=question.schedule_state.easiness_factor,
        interval=question.schedule_state.interval,
        repetitions=question.schedule_state.repetitions,
    )

    # Update question schedule
    question.schedule_state.easiness_factor = result.easiness_factor
    question.schedule_state.interval = result.interval
    question.schedule_state.repetitions = result.repetitions
    question.next_review_at = result.next_review
    question_repo.update(question)

    # Create review record with attempted explanation
    review = Review.create(question, answer)
    review_repo.create(review)
    review_repo.complete(
        review.id,
        grade=grade,
        attempted_explanation=attempted_explanation if attempted_explanation else None,
        recalled_from_memory=recalled,
        gaps=gaps if gaps else None,
    )

    # Show result
    interval_str = format_interval(result.interval)
    if grade >= 3:
        console.print(f"\n[green]Next review in {interval_str}[/green]")
    else:
        console.print(f"\n[yellow]Needs more practice. Review again in {interval_str}[/yellow]")


def skip_cmd(
    question_id: str = typer.Argument(..., help="Question ID to skip"),
):
    """
    Skip review and reschedule for tomorrow.

    Use this when you can't review a question right now but don't
    want it to affect your SM-2 score.
    """
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        answer_repo = AnswerRepository(conn)
        review_repo = ReviewRepository(conn)

        question = question_repo.get_by_id(question_id)
        if not question:
            console.print(f"[red]Question not found: {question_id}[/red]")
            raise typer.Exit(1)

        # Reschedule for tomorrow
        question.next_review_at = datetime.now() + timedelta(days=1)
        question_repo.update(question)

        # Create skipped review record
        answer = answer_repo.get_latest_for_question(question.id)
        if answer:
            review = Review.create(question, answer)
            review_repo.create(review)
            review_repo.skip(review.id)

        console.print(f"[yellow]Skipped:[/yellow] {question.prompt[:50]}...")
        console.print(f"[dim]Rescheduled for tomorrow.[/dim]")


def today_cmd():
    """
    Show daily review summary.

    Lists questions due today and upcoming reviews for the next 7 days.
    """
    config = load_config()
    lookahead = config.review.lookahead_days

    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        concept_repo = ConceptRepository(conn)

        due_today = question_repo.get_due()
        upcoming = question_repo.get_due_in_days(lookahead)

        # Today's reviews
        console.print("\n[bold]Today's Reviews[/bold]\n")

        if due_today:
            table = Table(show_header=True)
            table.add_column("Question", style="cyan", no_wrap=True)
            table.add_column("Concept", style="dim")
            table.add_column("EF", justify="right", style="dim")
            table.add_column("Interval", justify="right", style="dim")

            for question in due_today:
                concept_name = ""
                if question.concept_id:
                    concept = concept_repo.get_by_id(question.concept_id)
                    concept_name = concept.name if concept else ""

                table.add_row(
                    question.prompt[:35] + ("..." if len(question.prompt) > 35 else ""),
                    concept_name[:15],
                    f"{question.schedule_state.easiness_factor:.2f}",
                    f"{question.schedule_state.interval}d",
                )

            console.print(table)
            console.print(f"\n[bold green]{len(due_today)}[/bold green] question(s) due for review")
            console.print("[dim]Run 'study review' to start.[/dim]")
        else:
            console.print("[green]All caught up! No reviews due today.[/green]")

        # Upcoming reviews
        if upcoming:
            console.print(f"\n[bold]Upcoming ({lookahead} days)[/bold]\n")

            table = Table(show_header=True)
            table.add_column("Question", style="cyan", no_wrap=True)
            table.add_column("Due", justify="right", style="yellow")

            for question in upcoming[:10]:  # Show max 10
                if question.next_review_at:
                    days_until = (question.next_review_at.date() - datetime.now().date()).days
                    due_str = f"in {days_until} day{'s' if days_until != 1 else ''}"
                else:
                    due_str = "unknown"

                table.add_row(
                    question.prompt[:40] + ("..." if len(question.prompt) > 40 else ""),
                    due_str,
                )

            console.print(table)

            if len(upcoming) > 10:
                console.print(f"[dim]...and {len(upcoming) - 10} more[/dim]")
        else:
            console.print(f"\n[dim]No reviews scheduled in the next {lookahead} days.[/dim]")

        # Summary stats
        all_questions = question_repo.list_all()
        console.print(f"\n[dim]Total questions: {len(all_questions)}[/dim]")
