"""Run the student app on the home server."""

from __future__ import annotations

import os
from typing import Any

MODEL_ENV = "LERNI_CLAUDE_MODEL"


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


def _claude_chat() -> Any:
    """Return the Claude Code chat model for Ask Lerni if the CLI is installed, else ``None``."""
    from lerni.student.adapters.claude_code import (
        DEFAULT_MODEL,
        ClaudeCodeChat,
        claude_cli_available,
    )

    if not claude_cli_available():
        return None
    return ClaudeCodeChat(model=os.environ.get(MODEL_ENV, DEFAULT_MODEL))


def serve(host: str, port: int) -> None:
    """Start the student app and block until it stops.

    Args:
        host: Address to bind. ``0.0.0.0`` lets the iPad and other devices on
            the home network reach it.
        port: Port to listen on.
    """
    import uvicorn

    from lerni.student.students import StudentStore
    from lerni.student.web.app import build_app

    drafter = _claude_drafter()
    app = build_app(drafter=drafter, chat_model=_claude_chat())
    print(f"Sign in:  http://<this-computer>:{port}/", flush=True)
    if not any(s.educator for s in StudentStore().list_students()):
        print("No educator yet: lerni student add USERNAME --name NAME "
              "--kind independent --educator", flush=True)
    status = f"on ({drafter.model})" if drafter else "off (the claude CLI isn't installed)"
    print(f"Plan import and Ask Lerni with Claude: {status}", flush=True)
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
