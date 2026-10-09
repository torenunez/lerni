"""The Claude Code adapters run isolated: no tools, no settings, and no saved transcripts."""

import pytest

pytest.importorskip("claude_agent_sdk")

from lerni.student.adapters.claude_code import (  # noqa: E402
    ClaudeCodeChat,
    ClaudeCodeDrafter,
    ClaudeCodeTagger,
    ClaudeCodeUploader,
)


@pytest.mark.parametrize("options", [
    ClaudeCodeDrafter().options("/tmp/x"),
    ClaudeCodeChat().options("Be brief.", "/tmp/x"),
    ClaudeCodeTagger().options("Tag it.", "/tmp/x"),
    ClaudeCodeUploader().options("Sort it.", "/tmp/x"),
])
def test_claude_calls_keep_nothing_and_reach_nothing(options):
    assert options.tools == []
    assert options.setting_sources == []
    assert "no-session-persistence" in options.extra_args  # no transcripts on the server
    assert options.strict_mcp_config  # no MCP servers from the admin's setup


def test_the_tagger_has_a_turn_for_its_json():
    # regression: with one turn, every structured answer ended in "maximum number of turns"
    assert ClaudeCodeTagger().options("Tag it.", "/tmp/x").max_turns >= 2


def test_the_uploader_has_a_turn_for_its_json():
    # same lesson as the tagger: a structured answer needs its own turn
    assert ClaudeCodeUploader().options("Sort it.", "/tmp/x").max_turns >= 2
