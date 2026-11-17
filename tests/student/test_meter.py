"""v4.12: the usage meter: each Claude call leaves one line, named by its feature, with
numbers only; the report shares each window's movement out by feature."""

from datetime import date, datetime

import pytest
from claude_agent_sdk import ResultMessage

from lerni.student.adapters.claude_code import _note_limits
from lerni.student.meter import UsageLog, by_feature, usage_report, using
from lerni.student.usage import Usage

pytestmark = pytest.mark.ci  # run on each PR by GitHub (v4.12)


def test_a_call_leaves_one_numbers_only_line_named_by_its_feature(tmp_path):
    usage = Usage()
    usage.log = UsageLog(tmp_path)
    usage.record({"five_hour": (0.2, 2_000_000_000)}, overage=False)
    reply = ResultMessage(
        subtype="success", duration_ms=2500, duration_api_ms=2400, is_error=False, num_turns=1,
        session_id="s", usage={"input_tokens": 900, "output_tokens": 120,
                               "cache_read_input_tokens": 3000},
        result="zqx the secret reply", structured_output={"q": "zqx the secret question"})
    with using("race-write"):  # the feature names itself
        _note_limits(usage, reply, "small-model", "claude-haiku-5-5")
    _note_limits(usage, reply, "small-model", "claude-haiku-5-5")  # no name: the adapter's kind
    lines = usage.log.read(date.today())
    assert [r["use"] for r in lines] == ["race-write", "small-model"]
    assert lines[0]["in"] == 900 and lines[0]["cached"] == 3000 and lines[0]["seconds"] == 2.5
    assert lines[0]["five_hour"] == [0.2, 2_000_000_000]
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert not any(b"zqx" in p.read_bytes() for p in files)  # rule 6: never the text


def test_each_feature_gets_the_window_movement_of_its_own_calls(tmp_path):
    log = UsageLog(tmp_path)
    day = datetime(2026, 11, 17, 9)
    for minute, use, share in ((0, "chat-supervised", 0.10), (1, "race-write", 0.14),
                               (2, "chat-supervised", 0.15), (3, "race-write", 0.19)):
        log.add({"use": use, "in": 10, "out": 5, "seconds": 1,
                 "five_hour": [share, 99]}, now=day.replace(minute=minute))
    rows = {t["use"]: t for t in by_feature(log.read(day.date(), day.date()))}
    assert round(rows["race-write"]["five_hour"], 2) == 0.08  # 0.04 + 0.04
    assert round(rows["chat-supervised"]["five_hour"], 2) == 0.01  # the first is the baseline
    assert "race-write" in usage_report(log, day.date())
