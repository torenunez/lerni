"""External editor integration for Lerni."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .config import load_config


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


def edit_text(
    initial_content: str = "",
    suffix: str = ".md",
    prompt_header: Optional[str] = None,
) -> str:
    """
    Open external editor for text input.

    Creates a temporary file, opens it in the user's editor, and returns
    the edited content with any header comments stripped.

    Args:
        initial_content: Pre-populate editor with this text.
        suffix: File extension for temp file (affects syntax highlighting).
        prompt_header: Optional comment header explaining what to enter.
            Lines starting with # in the header area will be stripped.

    Returns:
        Edited content with header stripped, or empty string if aborted.

    Example:
        >>> content = edit_text(
        ...     initial_content="",
        ...     prompt_header="# Enter your notes below. Lines starting with # will be removed."
        ... )
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
