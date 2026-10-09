"""Run the student app on the home server."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_PASSCODE_ENV = "LERNI_EDUCATOR_PASSCODE"
MODEL_ENV = "LERNI_CLAUDE_MODEL"


class MissingPasscodeError(RuntimeError):
    """The environment variable that should hold the passcode is unset or empty."""


def resolve_passcode(env_var: str = DEFAULT_PASSCODE_ENV) -> str:
    """Read the educator passcode from an environment variable.

    The passcode is never read from a file or a command-line argument, so it
    can't end up in the repository or in shell history.

    Args:
        env_var: Name of the environment variable holding the passcode.

    Returns:
        The passcode.

    Raises:
        MissingPasscodeError: If the variable is unset or empty.

    Example:
        >>> os.environ["DEMO_PASSCODE"] = "s3cret"
        >>> resolve_passcode("DEMO_PASSCODE")
        's3cret'
    """
    value = os.environ.get(env_var, "")
    if not value:
        raise MissingPasscodeError(
            f"Set the educator passcode first: export {env_var}='...'"
        )
    return value


def _claude_drafter() -> Any:
    """Return the Claude Code drafter if the CLI is installed, else ``None``."""
    from lerni.student.adapters.claude_code import (
        DEFAULT_MODEL,
        ClaudeCodeDrafter,
        claude_cli_available,
    )

    if not claude_cli_available():
        return None
    return ClaudeCodeDrafter(model=os.environ.get(MODEL_ENV, DEFAULT_MODEL))


def serve(host: str, port: int, passcode_env: str = DEFAULT_PASSCODE_ENV) -> None:
    """Start the student app and block until it stops.

    Args:
        host: Address to bind. ``0.0.0.0`` lets the iPad and the educator's
            device reach it on the home network.
        port: Port to listen on.
        passcode_env: Name of the environment variable holding the passcode.

    Raises:
        MissingPasscodeError: If the passcode variable is unset or empty.
        ValueError: If the passcode is shorter than 8 characters.
    """
    passcode = resolve_passcode(passcode_env)

    import uvicorn

    from lerni.student.web.app import build_app

    drafter = _claude_drafter()
    app = build_app(passcode, drafter=drafter)
    print(f"Sign in:  http://<this-computer>:{port}/", flush=True)
    print("Educator: username 'educator' and the passcode. Students: their own.", flush=True)
    status = f"on ({drafter.model})" if drafter else "off (the claude CLI isn't installed)"
    print(f"Plan import with Claude: {status}", flush=True)
    print("Home network only. Press Ctrl-C to stop.", flush=True)
    # Gradio keeps each open page connected; without a time limit, Ctrl-C waits forever
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
        timeout_graceful_shutdown=3,
    )
