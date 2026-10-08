"""The deprecated ``study`` alias warns, then runs the same app."""

import lerni.cli as cli


def test_study_alias_warns_and_runs_app(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "app", lambda: calls.append("ran"))
    cli.study_alias()
    assert calls == ["ran"]
    assert "deprecated" in capsys.readouterr().err
