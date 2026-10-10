"""Run the student app on the home server."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

MODEL_ENV = "LERNI_CLAUDE_MODEL"
TAGGER_ENV = "LERNI_TAGGER_MODEL"


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


def _claude_tagger() -> Any:
    """Return the Claude Code tagger if the CLI is installed, else ``None``."""
    from lerni.student.adapters.claude_code import (
        DEFAULT_TAGGER_MODEL,
        ClaudeCodeTagger,
        claude_cli_available,
    )

    if not claude_cli_available():
        return None
    return ClaudeCodeTagger(model=os.environ.get(TAGGER_ENV, DEFAULT_TAGGER_MODEL))


def _claude_uploader() -> Any:
    """Return the Claude Code uploader if the CLI is installed, else ``None``."""
    from lerni.student.adapters.claude_code import (
        DEFAULT_MODEL,
        ClaudeCodeUploader,
        claude_cli_available,
    )

    if not claude_cli_available():
        return None
    return ClaudeCodeUploader(model=os.environ.get(MODEL_ENV, DEFAULT_MODEL))


def running_version() -> str:
    """Which code is running: ``"<branch> @ <commit>, <date>"``, or the package version."""
    import subprocess
    from importlib import metadata

    here = Path(__file__).resolve().parent
    try:
        # the checkout this code runs from, as git sees it
        out = subprocess.run(
            ["git", "-C", str(here), "log", "-1", "--format=%h %cs"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.split()
        branch = subprocess.run(
            ["git", "-C", str(here), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
        return f"{branch} @ {out[0]}, {out[1]}"
    except (OSError, subprocess.SubprocessError, IndexError):
        return f"version @ {metadata.version('lerni')}"  # installed without git


def serve(
    host: str, port: int, cert: Path | None = None, key: Path | None = None, label: str = ""
) -> None:
    """Start the student app and block until it stops.

    Args:
        host: Address to bind. ``0.0.0.0`` lets the iPad and other devices on
            the home network reach it.
        port: Port to listen on.
        cert: The HTTPS certificate (from mkcert); with ``key``, serves HTTPS.
        key: The certificate's private key.
        label: Shown on every page (e.g. "Development"); empty for production.

    Raises:
        ValueError: Only one of ``cert`` and ``key``, or a file that doesn't exist.
    """
    # check the HTTPS files before anything starts
    if (cert is None) != (key is None):
        raise ValueError("HTTPS needs both --cert and --key.")
    for path in (cert, key):
        if path is not None and not path.is_file():
            raise ValueError(f"No such file: {path}")
    scheme = "https" if cert else "http"

    import uvicorn

    from lerni.student.students import StudentStore
    from lerni.student.web.app import build_app

    chat, tagger = _claude_chat(), _claude_tagger()
    version = running_version()
    app = build_app(
        chat_model=chat, tagger=tagger, uploader=_claude_uploader(), label=label, version=version
    )
    print(f"Running:  {version}", flush=True)
    print(f"Sign in:  {scheme}://<this-computer>:{port}/", flush=True)
    if not any(s.educator for s in StudentStore().list_students()):
        print("No educator yet: lerni student add USERNAME --name NAME "
              "--kind independent --educator", flush=True)
    status = (f"on ({chat.model}; the map with {tagger.model})" if chat
              else "off (the claude CLI isn't installed)")
    print(f"Ask Lerni, the interest map, and Upload with Claude: {status}", flush=True)
    print("Conversation logs (7 days): lerni logs", flush=True)
    print("Home network only. Press Ctrl-C to stop.", flush=True)
    # Gradio keeps each open page connected; without a time limit, Ctrl-C waits forever
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
        timeout_graceful_shutdown=3,
        ssl_certfile=str(cert) if cert else None,  # HTTPS when both files are given
        ssl_keyfile=str(key) if key else None,
    )
