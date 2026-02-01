"""Organization commands for listing, searching, and managing concepts/questions."""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.tree import Tree

from ..db import (
    get_connection,
    QuestionRepository,
    ConceptRepository,
    ConceptEdgeRepository,
)
from ..models import Concept, ConceptEdge, RelationshipType

console = Console()


# ============================================================================
# Question commands
# ============================================================================


def list_cmd(
    concept: Optional[str] = typer.Option(None, "--concept", "-c", help="Filter by concept"),
    due: bool = typer.Option(False, "--due", help="Only show questions due for review"),
    uncategorized: bool = typer.Option(False, "--inbox", "-i", help="Show uncategorized questions"),
):
    """
    List all questions with optional filters.

    Use --concept to filter by concept name/ID.
    Use --due to show only questions that need review.
    Use --inbox to show uncategorized questions.
    """
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        concept_repo = ConceptRepository(conn)

        concept_id = None
        if concept:
            c = concept_repo.get_by_id(concept) or concept_repo.get_by_name(concept)
            if c:
                concept_id = c.id
            else:
                console.print(f"[yellow]Concept not found: {concept}[/yellow]")
                return

        if uncategorized:
            questions = question_repo.get_uncategorized()
        else:
            questions = question_repo.list_all(concept_id=concept_id, due_only=due)

        if not questions:
            console.print("[dim]No questions found.[/dim]")
            if concept or due:
                console.print("[dim]Try removing filters.[/dim]")
            return

        table = Table(show_header=True)
        table.add_column("ID", style="dim", no_wrap=True, max_width=8)
        table.add_column("Question", style="cyan")
        table.add_column("Concept", style="blue")
        table.add_column("Next Review", justify="right", style="yellow")
        table.add_column("EF", justify="right", style="dim")

        for question in questions:
            short_id = str(question.id)[:8]

            # Get concept name
            concept_name = ""
            if question.concept_id:
                c = concept_repo.get_by_id(question.concept_id)
                concept_name = c.name if c else ""

            # Format next review
            if question.next_review_at:
                from datetime import datetime

                days = (question.next_review_at.date() - datetime.now().date()).days
                if days < 0:
                    review_str = f"[red]{abs(days)}d overdue[/red]"
                elif days == 0:
                    review_str = "[yellow]Today[/yellow]"
                else:
                    review_str = f"in {days}d"
            else:
                review_str = "-"

            table.add_row(
                short_id,
                question.prompt[:40] + ("..." if len(question.prompt) > 40 else ""),
                concept_name[:15],
                review_str,
                f"{question.schedule_state.easiness_factor:.1f}",
            )

        console.print(table)
        console.print(f"\n[dim]{len(questions)} question(s)[/dim]")


def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
):
    """
    Search questions by prompt text.

    Performs case-insensitive substring matching.
    """
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        concept_repo = ConceptRepository(conn)
        questions = question_repo.search(query)

        if not questions:
            console.print(f"[dim]No questions matching '{query}'[/dim]")
            return

        console.print(f"\n[bold]Search results for:[/bold] {query}\n")

        table = Table(show_header=True)
        table.add_column("ID", style="dim", no_wrap=True, max_width=8)
        table.add_column("Question", style="cyan")
        table.add_column("Concept", style="blue")

        for question in questions:
            concept_name = ""
            if question.concept_id:
                c = concept_repo.get_by_id(question.concept_id)
                concept_name = c.name if c else ""

            table.add_row(
                str(question.id)[:8],
                question.prompt[:50] + ("..." if len(question.prompt) > 50 else ""),
                concept_name,
            )

        console.print(table)
        console.print(f"\n[dim]{len(questions)} result(s)[/dim]")


def assign_cmd(
    question_id: str = typer.Argument(..., help="Question ID"),
    concept_name: str = typer.Argument(..., help="Concept name or ID"),
):
    """
    Assign a question to a concept.

    If the concept doesn't exist, offers to create it.
    """
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)
        concept_repo = ConceptRepository(conn)

        question = question_repo.get_by_id(question_id)
        if not question:
            console.print(f"[red]Question not found: {question_id}[/red]")
            raise typer.Exit(1)

        # Find or create concept
        concept = concept_repo.get_by_id(concept_name) or concept_repo.get_by_name(concept_name)
        if not concept:
            if Confirm.ask(f"Concept '{concept_name}' not found. Create it?", default=True):
                concept = Concept.create(concept_name)
                concept_repo.create(concept)
                console.print(f"[green]Created concept: {concept.name}[/green]")
            else:
                console.print("[dim]Cancelled.[/dim]")
                return

        question.concept_id = concept.id
        question_repo.update(question)
        console.print(f"[green]Assigned to concept:[/green] {concept.name}")


def meta_cmd(
    question_id: str = typer.Argument(..., help="Question ID"),
    difficulty: Optional[int] = typer.Option(
        None, "--difficulty", help="Difficulty 1-5", min=1, max=5
    ),
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Add source reference (URL or citation)"
    ),
):
    """
    Update question metadata.

    Set difficulty or add source references.
    Use 'study assign' to change the concept.
    """
    with get_connection() as conn:
        question_repo = QuestionRepository(conn)

        question = question_repo.get_by_id(question_id)
        if not question:
            console.print(f"[red]Question not found: {question_id}[/red]")
            raise typer.Exit(1)

        updated = False

        if difficulty is not None:
            question.difficulty = difficulty
            updated = True

        if source is not None:
            if source not in question.source_refs:
                question.source_refs.append(source)
            updated = True

        if updated:
            question_repo.update(question)
            console.print(f"[green]Updated metadata[/green]")

            console.print(f"\n[dim]Difficulty:[/dim] {question.difficulty or 'not set'}")
            if question.source_refs:
                console.print(f"[dim]Sources:[/dim]")
                for ref in question.source_refs:
                    console.print(f"  - {ref}")
        else:
            console.print("[yellow]No changes specified.[/yellow]")
            console.print("[dim]Use --difficulty or --source to update.[/dim]")


# ============================================================================
# Concept commands
# ============================================================================


def concept_new(
    name: str = typer.Argument(..., help="Concept name"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description"),
    alias: Optional[str] = typer.Option(None, "--alias", "-a", help="Comma-separated aliases"),
    parent: Optional[str] = typer.Option(None, "--parent", "-p", help="Parent concept name/ID"),
):
    """
    Create a new concept in the knowledge graph.

    Concepts organize questions into a semantic hierarchy.
    """
    with get_connection() as conn:
        concept_repo = ConceptRepository(conn)
        edge_repo = ConceptEdgeRepository(conn)

        # Check if concept already exists
        existing = concept_repo.get_by_name(name)
        if existing:
            console.print(f"[yellow]Concept already exists: {name}[/yellow]")
            return

        aliases = [a.strip() for a in alias.split(",")] if alias else []
        concept = Concept.create(name, description=description, aliases=aliases)
        concept_repo.create(concept)

        console.print(f"[green]Created concept:[/green] {concept.name}")

        # Add parent relationship if specified
        if parent:
            parent_concept = concept_repo.get_by_id(parent) or concept_repo.get_by_name(parent)
            if parent_concept:
                edge = ConceptEdge.create(concept, parent_concept, RelationshipType.PARENT)
                edge_repo.create(edge)
                console.print(f"[dim]Parent: {parent_concept.name}[/dim]")
            else:
                console.print(f"[yellow]Parent concept not found: {parent}[/yellow]")


def concept_list():
    """
    List all concepts.

    Shows concepts organized as a tree when possible.
    """
    with get_connection() as conn:
        concept_repo = ConceptRepository(conn)
        edge_repo = ConceptEdgeRepository(conn)

        concepts = concept_repo.list_all()

        if not concepts:
            console.print("[dim]No concepts found.[/dim]")
            console.print("[dim]Create one with 'study concept new \"Name\"'[/dim]")
            return

        # Build tree structure
        roots = concept_repo.list_roots()

        if roots:
            console.print("\n[bold]Concept Tree[/bold]\n")

            for root in roots:
                tree = Tree(f"[bold cyan]{root.name}[/bold cyan]")
                _build_concept_tree(tree, root, edge_repo, concept_repo)
                console.print(tree)
                console.print()

        # Show orphans (concepts with parents that weren't found in roots)
        shown_ids = set()
        for root in roots:
            shown_ids.add(root.id)
            _collect_descendant_ids(root, edge_repo, shown_ids)

        orphans = [c for c in concepts if c.id not in shown_ids]
        if orphans:
            console.print("[dim]Uncategorized concepts:[/dim]")
            for c in orphans:
                console.print(f"  - {c.name}")

        console.print(f"\n[dim]{len(concepts)} concept(s) total[/dim]")


def _build_concept_tree(tree: Tree, concept: Concept, edge_repo, concept_repo, depth=0):
    """Recursively build concept tree."""
    if depth > 10:  # Prevent infinite loops
        return

    children = edge_repo.get_children(concept.id)
    for child in children:
        child_tree = tree.add(f"[cyan]{child.name}[/cyan]")
        _build_concept_tree(child_tree, child, edge_repo, concept_repo, depth + 1)


def _collect_descendant_ids(concept: Concept, edge_repo, ids: set):
    """Collect all descendant IDs."""
    children = edge_repo.get_children(concept.id)
    for child in children:
        ids.add(child.id)
        _collect_descendant_ids(child, edge_repo, ids)


def concept_show(
    concept_name: str = typer.Argument(..., help="Concept name or ID"),
):
    """
    Show concept details and relationships.

    Displays the concept's description, aliases, parents, children,
    prerequisites, related concepts, and associated questions.
    """
    with get_connection() as conn:
        concept_repo = ConceptRepository(conn)
        edge_repo = ConceptEdgeRepository(conn)
        question_repo = QuestionRepository(conn)

        concept = concept_repo.get_by_id(concept_name) or concept_repo.get_by_name(concept_name)
        if not concept:
            console.print(f"[red]Concept not found: {concept_name}[/red]")
            raise typer.Exit(1)

        console.print(f"\n[bold cyan]{concept.name}[/bold cyan]")
        console.print(f"[dim]ID: {concept.id}[/dim]")

        if concept.description:
            console.print(f"\n{concept.description}")

        if concept.aliases:
            console.print(f"\n[dim]Aliases: {', '.join(concept.aliases)}[/dim]")

        # Relationships
        parents = edge_repo.get_parents(concept.id)
        children = edge_repo.get_children(concept.id)
        prerequisites = edge_repo.get_prerequisites(concept.id)
        related = edge_repo.get_related(concept.id)

        if parents:
            console.print(f"\n[bold]Parents:[/bold] {', '.join(p.name for p in parents)}")
        if children:
            console.print(f"[bold]Children:[/bold] {', '.join(c.name for c in children)}")
        if prerequisites:
            console.print(f"[bold]Prerequisites:[/bold] {', '.join(p.name for p in prerequisites)}")
        if related:
            console.print(f"[bold]Related:[/bold] {', '.join(r.name for r in related)}")

        # Questions
        questions = question_repo.get_for_concept(concept.id)
        if questions:
            console.print(f"\n[bold]Questions ({len(questions)}):[/bold]")
            for q in questions[:5]:
                console.print(f"  - {q.prompt[:50]}...")
            if len(questions) > 5:
                console.print(f"  [dim]...and {len(questions) - 5} more[/dim]")
        else:
            console.print("\n[dim]No questions attached to this concept.[/dim]")


def concept_link(
    concept1: str = typer.Argument(..., help="First concept name/ID"),
    concept2: str = typer.Argument(..., help="Second concept name/ID"),
    rel_type: str = typer.Option(
        "parent",
        "--type",
        "-t",
        help="Relationship type: parent, prerequisite, or related",
    ),
):
    """
    Create a relationship between two concepts.

    Types:
    - parent: concept1 is a child of concept2 (concept1 → concept2)
    - prerequisite: concept2 is a prerequisite for concept1
    - related: bidirectional association
    """
    try:
        relationship = RelationshipType(rel_type)
    except ValueError:
        console.print(f"[red]Invalid relationship type: {rel_type}[/red]")
        console.print("[dim]Use: parent, prerequisite, or related[/dim]")
        raise typer.Exit(1)

    with get_connection() as conn:
        concept_repo = ConceptRepository(conn)
        edge_repo = ConceptEdgeRepository(conn)

        c1 = concept_repo.get_by_id(concept1) or concept_repo.get_by_name(concept1)
        c2 = concept_repo.get_by_id(concept2) or concept_repo.get_by_name(concept2)

        if not c1:
            console.print(f"[red]Concept not found: {concept1}[/red]")
            raise typer.Exit(1)
        if not c2:
            console.print(f"[red]Concept not found: {concept2}[/red]")
            raise typer.Exit(1)

        edge = ConceptEdge.create(c1, c2, relationship)
        try:
            edge_repo.create(edge)
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                console.print("[yellow]This relationship already exists.[/yellow]")
                return
            raise

        if relationship == RelationshipType.PARENT:
            console.print(f"[green]Linked:[/green] {c1.name} → {c2.name} (parent)")
        elif relationship == RelationshipType.PREREQUISITE:
            console.print(f"[green]Linked:[/green] {c2.name} is prerequisite for {c1.name}")
        else:
            console.print(f"[green]Linked:[/green] {c1.name} ↔ {c2.name} (related)")


def concept_unlink(
    concept1: str = typer.Argument(..., help="First concept name/ID"),
    concept2: str = typer.Argument(..., help="Second concept name/ID"),
    rel_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Specific relationship type to remove (default: all)",
    ),
):
    """
    Remove relationship between two concepts.

    Without --type, removes all relationships between the concepts.
    """
    with get_connection() as conn:
        concept_repo = ConceptRepository(conn)
        edge_repo = ConceptEdgeRepository(conn)

        c1 = concept_repo.get_by_id(concept1) or concept_repo.get_by_name(concept1)
        c2 = concept_repo.get_by_id(concept2) or concept_repo.get_by_name(concept2)

        if not c1:
            console.print(f"[red]Concept not found: {concept1}[/red]")
            raise typer.Exit(1)
        if not c2:
            console.print(f"[red]Concept not found: {concept2}[/red]")
            raise typer.Exit(1)

        removed = False

        if rel_type:
            try:
                relationship = RelationshipType(rel_type)
                if edge_repo.delete(c1.id, c2.id, relationship):
                    removed = True
                if edge_repo.delete(c2.id, c1.id, relationship):
                    removed = True
            except ValueError:
                console.print(f"[red]Invalid relationship type: {rel_type}[/red]")
                raise typer.Exit(1)
        else:
            # Remove all relationships in both directions
            for rt in RelationshipType:
                if edge_repo.delete(c1.id, c2.id, rt):
                    removed = True
                if edge_repo.delete(c2.id, c1.id, rt):
                    removed = True

        if removed:
            console.print(f"[green]Unlinked:[/green] {c1.name} and {c2.name}")
        else:
            console.print("[yellow]No relationship found between these concepts.[/yellow]")


def concept_delete(
    concept_name: str = typer.Argument(..., help="Concept name or ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """
    Delete a concept.

    Questions assigned to this concept will become uncategorized.
    """
    with get_connection() as conn:
        concept_repo = ConceptRepository(conn)
        question_repo = QuestionRepository(conn)

        concept = concept_repo.get_by_id(concept_name) or concept_repo.get_by_name(concept_name)
        if not concept:
            console.print(f"[red]Concept not found: {concept_name}[/red]")
            raise typer.Exit(1)

        questions = question_repo.get_for_concept(concept.id)

        if not force:
            msg = f"Delete concept '{concept.name}'?"
            if questions:
                msg += f" ({len(questions)} question(s) will become uncategorized)"
            if not Confirm.ask(msg, default=False):
                console.print("[dim]Cancelled.[/dim]")
                return

        concept_repo.delete(concept.id)
        console.print(f"[green]Deleted concept:[/green] {concept.name}")
