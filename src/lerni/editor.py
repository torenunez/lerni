"""Text input for Lerni - inline prompts and external editor integration."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

from .config import load_config

console = Console()

# Terminator to end multi-line input
END_MARKER = "/done"


def prompt_multiline(
    prompt_text: str,
    initial_content: str = "",
    hint: Optional[str] = None,
) -> str:
    """
    Prompt for multi-line input directly in terminal.

    User types content and enters '/done' on its own line to finish.
    Empty input (just /done) returns empty string.

    Args:
        prompt_text: Header text explaining what to enter.
        initial_content: Pre-populate with this text (shown for reference).
        hint: Optional hint shown below the prompt.

    Returns:
        The entered content, or empty string if nothing entered.
    """
    console.print(f"\n[bold cyan]{prompt_text}[/bold cyan]")
    if hint:
        console.print(f"[dim]{hint}[/dim]")
    console.print(f"[dim]Type your response. Enter [bold]{END_MARKER}[/bold] on a new line when done.[/dim]")

    if initial_content:
        console.print(f"\n[dim]Current content:[/dim]")
        for line in initial_content.split("\n")[:5]:  # Show first 5 lines
            console.print(f"[dim]  {line}[/dim]")
        if initial_content.count("\n") > 5:
            console.print(f"[dim]  ... ({initial_content.count(chr(10)) - 5} more lines)[/dim]")
        console.print()

    lines = []
    try:
        while True:
            line = console.input("[green]> [/green]")
            if line.strip().lower() == END_MARKER.lower():
                break
            lines.append(line)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Input cancelled.[/yellow]")
        return ""

    return "\n".join(lines).strip()


def prompt_single(
    prompt_text: str,
    default: str = "",
) -> str:
    """
    Prompt for single-line input.

    Args:
        prompt_text: The prompt to show.
        default: Default value if user just presses Enter.

    Returns:
        The entered text.
    """
    return Prompt.ask(f"[bold cyan]{prompt_text}[/bold cyan]", default=default)


def edit_text(
    initial_content: str = "",
    suffix: str = ".md",
    prompt_header: Optional[str] = None,
    use_editor: bool = False,
) -> str:
    """
    Get text input from user - inline prompt by default, or external editor.

    Args:
        initial_content: Pre-populate with this text.
        suffix: File extension for temp file (only used with editor).
        prompt_header: Text explaining what to enter.
        use_editor: If True, open external editor instead of inline prompt.

    Returns:
        Entered content, or empty string if aborted.
    """
    if use_editor:
        return _edit_with_external_editor(initial_content, suffix, prompt_header)

    # Extract a clean prompt from the header
    prompt_text = "Enter your response"
    hint = None

    if prompt_header:
        # Parse the header to get a clean prompt
        lines = prompt_header.strip().split("\n")
        # Find first non-comment line or use first comment as title
        for line in lines:
            clean = line.lstrip("#").strip()
            if clean:
                prompt_text = clean
                break
        # Get hint from remaining lines
        hints = []
        for line in lines[1:]:
            clean = line.lstrip("#").strip()
            if clean and not clean.startswith("Lines starting with"):
                hints.append(clean)
        if hints:
            hint = " ".join(hints[:2])  # First 2 hint lines

    return prompt_multiline(prompt_text, initial_content, hint)


def _edit_with_external_editor(
    initial_content: str = "",
    suffix: str = ".md",
    prompt_header: Optional[str] = None,
) -> str:
    """
    Open external editor for text input.

    Creates a temporary file, opens it in the user's editor, and returns
    the edited content with any header comments stripped.
    """
    editor = get_editor()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as f:
        if prompt_header:
            f.write(f"{prompt_header}\n\n")
        f.write(initial_content)
        temp_path = f.name

    try:
        # Open editor and wait for it to close
        subprocess.run([editor, temp_path], check=True)

        # Read the edited content
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Strip header comments (lines starting with #)
        lines = content.split("\n")
        result_lines = []
        in_header = True

        for line in lines:
            if in_header:
                # Skip comment lines at the start
                if line.startswith("#"):
                    continue
                # Skip empty lines after header
                if line.strip() == "":
                    continue
                in_header = False

            result_lines.append(line)

        return "\n".join(result_lines).strip()

    except subprocess.CalledProcessError:
        # Editor exited with error
        return ""

    except FileNotFoundError:
        # Editor not found
        raise RuntimeError(f"Editor not found: {editor}")

    finally:
        Path(temp_path).unlink(missing_ok=True)


def get_editor() -> str:
    """
    Get editor command in priority order: config > EDITOR > VISUAL > vim.

    Returns:
        Editor command string.
    """
    config = load_config()
    if config.editor:
        return config.editor
    return os.environ.get("EDITOR", os.environ.get("VISUAL", "vim"))


def edit_in_place(file_path: Path) -> bool:
    """
    Open an existing file in the editor.

    Args:
        file_path: Path to the file to edit.

    Returns:
        True if editor exited successfully, False otherwise.
    """
    editor = get_editor()

    try:
        subprocess.run([editor, str(file_path)], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        raise RuntimeError(f"Editor not found: {editor}")
