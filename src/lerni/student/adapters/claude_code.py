"""Claude through the Claude Code CLI on the home server (prototype only).

Two uses: drafting a plan from rough notes, and Ask Lerni's conversation.

Uses the Claude account the CLI is logged into, so there's no API key to
store. Before anyone outside the household uses the app, replace this with an
API-key adapter; Anthropic doesn't allow offering claude.ai login to others.
"""

from __future__ import annotations

import asyncio
import queue
import shutil
import tempfile
import threading
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    StreamEvent,
    query,
)

from lerni.student.conversation import ConversationUnavailable, Turn
from lerni.student.plan_import import (
    PLAN_SCHEMA,
    SYSTEM_PROMPT,
    DrafterUnavailable,
    DraftResult,
    ImportSource,
)

DEFAULT_MODEL = "claude-sonnet-5-5"
TIMEOUT_SECONDS = 120
CHAT_TIMEOUT_SECONDS = 60


def _isolated() -> dict[str, Any]:
    """Every call: no settings, CLAUDE.md, memory, or MCP servers, and no transcript saved."""
    return {
        "setting_sources": [],
        "strict_mcp_config": True,  # ignore MCP servers configured for the admin
        "extra_args": {"no-session-persistence": None},  # a fresh dict per call
    }


def claude_cli_available() -> bool:
    """Return whether the `claude` CLI is installed on this machine."""
    return shutil.which("claude") is not None


class ClaudeCodeDrafter:
    """Propose a learning plan with one tightly limited Claude Code call."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model

    def options(
        self, workdir: str, pdf_path: Path | None = None, can_use_tool: Any = None
    ) -> Any:
        """The call's options: no tools (except reading one uploaded PDF), nothing kept."""
        return ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            model=self.model,
            tools=["Read"] if pdf_path else [],  # only to read this one PDF
            cwd=workdir,
            max_turns=3 if pdf_path else 1,
            output_format={"type": "json_schema", "schema": PLAN_SCHEMA},
            can_use_tool=can_use_tool,
            **_isolated(),
        )

    def draft(self, source: ImportSource) -> DraftResult:
        """Send the notes to Claude and return its structured proposal.

        Raises:
            DrafterUnavailable: Claude didn't run or returned no plan.
        """
        try:
            return asyncio.run(asyncio.wait_for(self._draft(source), TIMEOUT_SECONDS))
        except DrafterUnavailable:
            raise
        except Exception as exc:  # never echo the notes in errors
            raise DrafterUnavailable("Claude didn't respond. Try again in a moment.") from exc

    async def _draft(self, source: ImportSource) -> DraftResult:
        # empty working folder: no project files or settings in reach
        with tempfile.TemporaryDirectory(prefix="lerni-import-") as workdir:
            prompt = "Structure these notes into a learning plan.\n\n" + source.text
            pdf_path: Path | None = None
            if source.pdf is not None:
                pdf_path = Path(workdir) / "notes.pdf"
                pdf_path.write_bytes(source.pdf)
                prompt += f"\n\nThe notes are also in the PDF at {pdf_path}."

            async def only_this_pdf(name: str, args: dict[str, Any], _ctx: Any) -> Any:
                if pdf_path and name == "Read" and Path(args.get("file_path", "")) == pdf_path:
                    return PermissionResultAllow()
                return PermissionResultDeny(message="Not allowed.")

            options = self.options(workdir, pdf_path, only_this_pdf if pdf_path else None)
            result: ResultMessage | None = None
            async for message in query(prompt=_prompt_stream(prompt), options=options):
                if isinstance(message, ResultMessage):
                    result = message
        if result is None or result.is_error or not isinstance(result.structured_output, dict):
            raise DrafterUnavailable("Claude didn't return a plan. Try shorter notes.")
        return DraftResult(proposal=result.structured_output)


class ClaudeCodeChat:
    """Answer Ask Lerni conversations, streaming the reply as it's written."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model

    def options(self, system: str, workdir: str) -> Any:
        """The call's options: no tools, one turn, partial text as it arrives, nothing kept."""
        return ClaudeAgentOptions(
            system_prompt=system,
            model=self.model,
            tools=[],
            cwd=workdir,
            max_turns=1,
            include_partial_messages=True,
            **_isolated(),
        )

    def stream(self, system: str, turns: Sequence[Turn]) -> Iterator[str]:
        """Yield the reply a piece at a time.

        Raises:
            ConversationUnavailable: Claude didn't answer in time or at all.
        """
        pieces: queue.Queue[str | BaseException | None] = queue.Queue()

        def run() -> None:
            # the SDK is async; run it on its own thread and hand pieces over
            try:
                reply = self._reply(system, turns, pieces)
                asyncio.run(asyncio.wait_for(reply, CHAT_TIMEOUT_SECONDS))
            except BaseException as exc:  # noqa: BLE001 - passed to the reader below
                pieces.put(exc)
            finally:
                pieces.put(None)

        threading.Thread(target=run, daemon=True).start()
        sent = False
        while (piece := pieces.get()) is not None:
            if isinstance(piece, BaseException):
                raise ConversationUnavailable("Claude didn't answer. Try again in a moment.")
            sent = True
            yield piece
        if not sent:
            raise ConversationUnavailable("Claude didn't answer. Try again in a moment.")

    async def _reply(
        self, system: str, turns: Sequence[Turn], pieces: queue.Queue[Any]
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="lerni-ask-") as workdir:
            options = self.options(system, workdir)
            async for message in query(prompt=_transcript(turns), options=options):
                if isinstance(message, ResultMessage) and message.is_error:
                    raise ConversationUnavailable("Claude didn't finish.")  # don't save it as done
                if not isinstance(message, StreamEvent):
                    continue
                # only the text as it's written; the final message repeats it
                event, delta = message.event, message.event.get("delta", {})
                if event.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                    pieces.put(delta.get("text", ""))


def _transcript(turns: Sequence[Turn]) -> str:
    """The conversation so far as one message; the last turn is the new question."""
    *earlier, latest = turns
    lines = [f"{'Them' if t.role == 'user' else 'You'}: {t.text}" for t in earlier]
    head = "Conversation so far:\n" + "\n".join(lines) + "\n\n" if lines else ""
    return head + "Their new question:\n" + latest.text


async def _prompt_stream(text: str) -> Any:
    # can_use_tool needs streaming input, so the prompt is sent as one message
    yield {"type": "user", "message": {"role": "user", "content": text}}
