"""The Claude Code adapters run isolated: no tools, no settings, and no saved transcripts."""

import pytest

pytest.importorskip("claude_agent_sdk")

from lerni.student.adapters.claude_code import ClaudeCodeChat, ClaudeCodeDrafter  # noqa: E402


@pytest.mark.parametrize("options", [
    ClaudeCodeDrafter().options("/tmp/x"),
    ClaudeCodeChat().options("Be brief.", "/tmp/x"),
])
def test_claude_calls_keep_nothing_and_reach_nothing(options):
    assert options.tools == []
    assert options.setting_sources == []
    assert "no-session-persistence" in options.extra_args  # no transcripts on the server
