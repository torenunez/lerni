"""The deprecated ``study`` alias warns, then runs the same app."""

import lerni.cli as cli


def test_study_alias_warns_and_runs_app(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "app", lambda **kw: calls.append(kw))
    cli.study_alias()
    assert calls == [{"prog_name": "lerni"}]
    assert "deprecated" in capsys.readouterr().err
