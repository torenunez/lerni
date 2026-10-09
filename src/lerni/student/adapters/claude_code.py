"""Plan drafting through the Claude Code CLI on the home server (prototype only).

Uses the Claude account the CLI is logged into, so there's no API key to
store. Before anyone outside the household uses the app, replace this with an
API-key adapter; Anthropic doesn't allow offering claude.ai login to others.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    query,
)

from lerni.student.plan_import import (
    PLAN_SCHEMA,
    SYSTEM_PROMPT,
    DrafterUnavailable,
    DraftResult,
    ImportSource,
)

DEFAULT_MODEL = "claude-sonnet-5-5"
TIMEOUT_SECONDS = 120


def claude_cli_available() -> bool:
    """Return whether the `claude` CLI is installed on this machine."""
    return shutil.which("claude") is not None


class ClaudeCodeDrafter:
    """Propose a learning plan with one tightly limited Claude Code call."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model

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
            tools: list[str] = []
            pdf_path: Path | None = None
            if source.pdf is not None:
                pdf_path = Path(workdir) / "notes.pdf"
                pdf_path.write_bytes(source.pdf)
                tools = ["Read"]  # only to read this one PDF
                prompt += f"\n\nThe notes are also in the PDF at {pdf_path}."

            async def only_this_pdf(name: str, args: dict[str, Any], _ctx: Any) -> Any:
                if pdf_path and name == "Read" and Path(args.get("file_path", "")) == pdf_path:
                    return PermissionResultAllow()
                return PermissionResultDeny(message="Not allowed.")

            options = ClaudeAgentOptions(
                system_prompt=SYSTEM_PROMPT,
                model=self.model,
                tools=tools,
                setting_sources=[],  # no user or project settings, CLAUDE.md, or memory
                cwd=workdir,
                max_turns=3 if pdf_path else 1,
                output_format={"type": "json_schema", "schema": PLAN_SCHEMA},
                can_use_tool=only_this_pdf if pdf_path else None,
            )
            result: ResultMessage | None = None
            async for message in query(prompt=_prompt_stream(prompt), options=options):
                if isinstance(message, ResultMessage):
                    result = message
        if result is None or result.is_error or not isinstance(result.structured_output, dict):
            raise DrafterUnavailable("Claude didn't return a plan. Try shorter notes.")
        return DraftResult(proposal=result.structured_output)


async def _prompt_stream(text: str) -> Any:
    # can_use_tool needs streaming input, so the prompt is sent as one message
    yield {"type": "user", "message": {"role": "user", "content": text}}
