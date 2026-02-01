"""Question management commands."""

from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from ..db import get_connection, QuestionRepository, AnswerRepository, ConceptRepository
from ..editor import edit_text
from ..models import Question, Answer

console = Console()


def new_question(
    quick: bool = typer.Option(
        False, "--quick", "-q", help="Quick capture (step 1 only)"
    ),
    concept: Optional[str] = typer.Option(
        None, "--concept", "-c", help="Concept name or ID to attach question to"
    ),
    step: Optional[int] = typer.Option(
        None, "--step", "-s", help="Start at specific step (1-4)", min=1, max=4
    ),
    editor: bool = typer.Option(
        False, "--editor", "-e", help="Use external editor instead of inline prompts"
    ),
):
    """
    Create a new question using the Feynman workflow.

    First, you'll write the question that tests understanding of a concept.
    Then the full flow guides you through 4 steps:

    1. Raw notes - dump everything you know
    2. Simple explanation - explain like teaching a beginner
    3. Gaps & questions - identify what you don't understand
    4. Final explanation + analogies - refined understanding

    Use --quick to capture only raw notes (step 1).
    Use --concept to attach to an existing concept.
    """
    console.print("\n[bold]Creating new question[/bold]\n")

    # First: Define the question (required)
    console.print("[bold cyan]Question[/bold cyan]")
    console.print("[dim]Write a question that tests understanding of a concept.[/dim]")
    console.print("[dim]This question will be shown during review (without your answer).[/dim]\n")
    prompt = edit_text(
        prompt_header="# Question\n# Write a question that tests understanding of a concept.\n# Example: 'What are Python decorators and how do they work?'\n# This will be shown during review - your answer will be hidden.\n# Lines starting with # will be removed.",
        use_editor=editor,
    )

    if not prompt:
        console.print("[red]Aborted: Question is required.[/red]")
        raise typer.Exit(1)

    # Find or create concept if specified
    concept_obj = None
    with get_connection() as conn:
        if concept:
            concept_repo = ConceptRepository(conn)
            # Try by ID first, then by name
            concept_obj = concept_repo.get_by_id(concept)
            if not concept_obj:
                concept_obj = concept_repo.get_by_name(concept)
            if not concept_obj:
                # Offer to create
                if Confirm.ask(f"Concept '{concept}' not found. Create it?", default=True):
                    from ..models import Concept
                    concept_obj = Concept.create(concept)
                    concept_repo.create(concept_obj)
                    console.print(f"[green]Created concept: {concept_obj.name}[/green]")

    start_step = step if step else 1

    # Step 1: Raw notes (always required)
    if start_step <= 1:
        console.print("\n[dim]Step 1/4:[/dim] [bold]Raw Notes[/bold]")
        console.print("[dim]Dump everything you know about this topic.[/dim]\n")
        raw_notes = edit_text(
            prompt_header="# Step 1: Raw Notes\n# Write everything you know about this topic.\n# Don't worry about organization - just dump your knowledge.\n# Lines starting with # will be removed.",
            use_editor=editor,
        )

        if not raw_notes:
            console.print("[red]Aborted: No content entered.[/red]")
            raise typer.Exit(1)
    else:
        raw_notes = ""

    if quick:
        # Quick mode: save with only raw notes
        question_id = _save_question(prompt, raw_notes=raw_notes, concept=concept_obj)
        console.print(f"\n[green]Question created (quick mode).[/green]")
        console.print(f"[dim]ID: {question_id}[/dim]")
        return

    # Step 2: Simple explanation
    simple_explanation = None
    if start_step <= 2:
        console.print("\n[dim]Step 2/4:[/dim] [bold]Simple Explanation[/bold]")
        console.print(
            "[dim]Explain this as if teaching a complete beginner.[/dim]\n"
        )
        simple_explanation = edit_text(
            prompt_header="# Step 2: Simple Explanation\n# Explain this topic as if teaching someone who knows nothing about it.\n# Use simple words, avoid jargon.\n# Lines starting with # will be removed.",
            use_editor=editor,
        )

    # Step 3: Gaps and questions
    gaps_questions = None
    if start_step <= 3:
        console.print("\n[dim]Step 3/4:[/dim] [bold]Gaps & Questions[/bold]")
        console.print(
            "[dim]What parts are unclear? What questions do you still have?[/dim]\n"
        )
        gaps_questions = edit_text(
            prompt_header="# Step 3: Gaps & Questions\n# Identify what you struggled to explain.\n# What questions remain? What needs more research?\n# Lines starting with # will be removed.",
            use_editor=editor,
        )

    # Step 4: Final explanation
    console.print("\n[dim]Step 4/4:[/dim] [bold]Final Explanation[/bold]")
    console.print(
        "[dim]Write your refined explanation incorporating what you learned.[/dim]\n"
    )
    final_explanation = edit_text(
        prompt_header="# Step 4: Final Explanation\n# Write your refined explanation incorporating what you learned from identifying gaps.\n# Lines starting with # will be removed.",
        use_editor=editor,
    )

    # Bonus: Analogies
    console.print("\n[dim]Bonus:[/dim] [bold]Analogies & Examples[/bold]")
    console.print("[dim]Provide real-world analogies or concrete examples.[/dim]\n")
    analogies_examples = edit_text(
        prompt_header="# Analogies & Examples\n# Provide real-world analogies or concrete examples that illustrate the concept.\n# Lines starting with # will be removed.",
        use_editor=editor,
    )

    question_id = _save_question(
        prompt,
        concept=concept_obj,
        raw_notes=raw_notes,
        simple_explanation=simple_explanation or None,
        gaps_questions=gaps_questions or None,
        final_explanation=final_explanation or None,
        analogies_examples=analogies_examples or None,
    )

    console.print(f"\n[green bold]Question created successfully![/green bold]")
    console.print(f"[dim]ID: {question_id}[/dim]")


def _save_question(prompt: str, concept=None, **answer_fields) -> UUID:
    """Save question and initial answer to database."""
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        answer_repo = AnswerRepository(conn)

        question = Question.create(prompt, concept=concept)
        answer = Answer.create(question, **answer_fields)
        question.current_answer_id = answer.id

        question_repo.create(question)
        answer_repo.create(answer)

        return question.id


def edit_question(
    question_id: str = typer.Argument(..., help="Question ID (partial match supported)"),
    editor: bool = typer.Option(
        False, "--editor", "-e", help="Use external editor instead of inline prompts"
    ),
):
    """
    Edit question content (minor changes, no new version).

    Opens the current answer in your editor. Changes are saved
    to the existing answer without creating a new snapshot.

    Use 'study snapshot' to create a new version instead.
    """
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        answer_repo = AnswerRepository(conn)

        question = question_repo.get_by_id(question_id)
        if not question:
            console.print(f"[red]Question not found: {question_id}[/red]")
            raise typer.Exit(1)

        answer = answer_repo.get_latest_for_question(question.id)
        if not answer:
            console.print(f"[red]No answer found for question[/red]")
            raise typer.Exit(1)

        console.print(f"\n[bold]Editing:[/bold] {question.prompt[:50]}...\n")

        # Edit each field
        console.print("[dim]Editing raw notes...[/dim]")
        new_raw = edit_text(
            initial_content=answer.raw_notes,
            prompt_header="# Raw Notes\n# Edit your raw notes below.\n# Lines starting with # will be removed.",
            use_editor=editor,
        )
        if new_raw:
            answer.raw_notes = new_raw

        if answer.simple_explanation or Confirm.ask(
            "Add simple explanation?", default=False
        ):
            console.print("[dim]Editing simple explanation...[/dim]")
            new_simple = edit_text(
                initial_content=answer.simple_explanation or "",
                prompt_header="# Simple Explanation\n# Lines starting with # will be removed.",
                use_editor=editor,
            )
            answer.simple_explanation = new_simple or answer.simple_explanation

        if answer.gaps_questions or Confirm.ask(
            "Add gaps/questions?", default=False
        ):
            console.print("[dim]Editing gaps/questions...[/dim]")
            new_gaps = edit_text(
                initial_content=answer.gaps_questions or "",
                prompt_header="# Gaps & Questions\n# Lines starting with # will be removed.",
                use_editor=editor,
            )
            answer.gaps_questions = new_gaps or answer.gaps_questions

        if answer.final_explanation or Confirm.ask(
            "Add final explanation?", default=False
        ):
            console.print("[dim]Editing final explanation...[/dim]")
            new_final = edit_text(
                initial_content=answer.final_explanation or "",
                prompt_header="# Final Explanation\n# Lines starting with # will be removed.",
                use_editor=editor,
            )
            answer.final_explanation = new_final or answer.final_explanation

        if answer.analogies_examples or Confirm.ask(
            "Add analogies/examples?", default=False
        ):
            console.print("[dim]Editing analogies/examples...[/dim]")
            new_analogies = edit_text(
                initial_content=answer.analogies_examples or "",
                prompt_header="# Analogies & Examples\n# Lines starting with # will be removed.",
                use_editor=editor,
            )
            answer.analogies_examples = new_analogies or answer.analogies_examples

        answer_repo.update(answer)
        console.print("\n[green]Question updated.[/green]")


def snapshot_question(
    question_id: str = typer.Argument(..., help="Question ID"),
    editor: bool = typer.Option(
        False, "--editor", "-e", help="Use external editor instead of inline prompts"
    ),
):
    """
    Create a new answer snapshot (meaningful revision).

    Opens a fresh editor with the current content. The new answer
    is saved as an immutable snapshot, preserving history.
    """
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        answer_repo = AnswerRepository(conn)

        question = question_repo.get_by_id(question_id)
        if not question:
            console.print(f"[red]Question not found: {question_id}[/red]")
            raise typer.Exit(1)

        current = answer_repo.get_latest_for_question(question.id)

        console.print(f"\n[bold]Creating snapshot for:[/bold] {question.prompt[:50]}...\n")

        # Create new answer with current content as starting point
        raw_notes = edit_text(
            initial_content=current.raw_notes if current else "",
            prompt_header="# Raw Notes (new snapshot)\n# Lines starting with # will be removed.",
            use_editor=editor,
        )

        if not raw_notes:
            console.print("[red]Aborted: No content entered.[/red]")
            raise typer.Exit(1)

        simple = edit_text(
            initial_content=current.simple_explanation if current else "",
            prompt_header="# Simple Explanation\n# Lines starting with # will be removed.",
            use_editor=editor,
        )

        gaps = edit_text(
            initial_content=current.gaps_questions if current else "",
            prompt_header="# Gaps & Questions\n# Lines starting with # will be removed.",
            use_editor=editor,
        )

        final = edit_text(
            initial_content=current.final_explanation if current else "",
            prompt_header="# Final Explanation\n# Lines starting with # will be removed.",
            use_editor=editor,
        )

        analogies = edit_text(
            initial_content=current.analogies_examples if current else "",
            prompt_header="# Analogies & Examples\n# Lines starting with # will be removed.",
            use_editor=editor,
        )

        new_answer = Answer.create(
            question,
            raw_notes=raw_notes,
            simple_explanation=simple or None,
            gaps_questions=gaps or None,
            final_explanation=final or None,
            analogies_examples=analogies or None,
        )

        answer_repo.create(new_answer)
        question.current_answer_id = new_answer.id
        question_repo.update(question)

        answers = answer_repo.get_for_question(question.id)
        console.print(
            f"\n[green]Snapshot created.[/green] Version {len(answers)}"
        )


def show_question(
    question_id: str = typer.Argument(..., help="Question ID"),
):
    """Display question content and metadata."""
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        answer_repo = AnswerRepository(conn)
        concept_repo = ConceptRepository(conn)

        question = question_repo.get_by_id(question_id)
        if not question:
            console.print(f"[red]Question not found: {question_id}[/red]")
            raise typer.Exit(1)

        answer = answer_repo.get_latest_for_question(question.id)

        # Header
        console.print(f"\n[dim]ID: {question.id}[/dim]")
        console.print(f"[dim]Created: {question.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]")

        if question.next_review_at:
            console.print(
                f"[dim]Next review: {question.next_review_at.strftime('%Y-%m-%d')}[/dim]"
            )

        # Concept
        if question.concept_id:
            concept = concept_repo.get_by_id(question.concept_id)
            if concept:
                console.print(f"[dim]Concept: {concept.name}[/dim]")

        if question.difficulty:
            console.print(f"[dim]Difficulty: {question.difficulty}/5[/dim]")

        console.print()

        # Question prompt
        console.print(Panel(question.prompt, title="Question", border_style="bold yellow"))

        if answer:
            # Raw notes
            console.print(Panel(answer.raw_notes, title="Raw Notes", border_style="blue"))

            if answer.simple_explanation:
                console.print(
                    Panel(
                        answer.simple_explanation,
                        title="Simple Explanation",
                        border_style="green",
                    )
                )

            if answer.gaps_questions:
                console.print(
                    Panel(
                        answer.gaps_questions,
                        title="Gaps & Questions",
                        border_style="yellow",
                    )
                )

            if answer.final_explanation:
                console.print(
                    Panel(
                        answer.final_explanation,
                        title="Final Explanation",
                        border_style="cyan",
                    )
                )

            if answer.analogies_examples:
                console.print(
                    Panel(
                        answer.analogies_examples,
                        title="Analogies & Examples",
                        border_style="magenta",
                    )
                )
        else:
            console.print("[yellow]No answer versions found.[/yellow]")


def question_history(
    question_id: str = typer.Argument(..., help="Question ID"),
):
    """Show answer history for a question."""
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        answer_repo = AnswerRepository(conn)

        question = question_repo.get_by_id(question_id)
        if not question:
            console.print(f"[red]Question not found: {question_id}[/red]")
            raise typer.Exit(1)

        answers = answer_repo.get_for_question(question.id)

        console.print(f"\n[bold]Answer history:[/bold] {question.prompt[:50]}...\n")

        if not answers:
            console.print("[yellow]No answers found.[/yellow]")
            return

        table = Table()
        table.add_column("Version", style="cyan")
        table.add_column("Created", style="dim")
        table.add_column("Fields", style="green")

        for i, a in enumerate(reversed(answers), 1):
            fields = []
            if a.raw_notes:
                fields.append("raw")
            if a.simple_explanation:
                fields.append("simple")
            if a.gaps_questions:
                fields.append("gaps")
            if a.final_explanation:
                fields.append("final")
            if a.analogies_examples:
                fields.append("analogies")

            is_current = a.id == question.current_answer_id
            version_label = f"v{i}" + (" (current)" if is_current else "")

            table.add_row(
                version_label,
                a.created_at.strftime("%Y-%m-%d %H:%M"),
                ", ".join(fields),
            )

        console.print(table)


def delete_question(
    question_id: str = typer.Argument(..., help="Question ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a question and all its answers."""
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)

        question = question_repo.get_by_id(question_id)
        if not question:
            console.print(f"[red]Question not found: {question_id}[/red]")
            raise typer.Exit(1)

        if not force:
            if not Confirm.ask(
                f"Delete question '[bold]{question.prompt[:50]}...[/bold]' and all its answers?",
                default=False,
            ):
                console.print("[dim]Cancelled.[/dim]")
                raise typer.Exit(0)

        question_repo.delete(question.id)
        console.print(f"[green]Deleted question[/green]")
