"""Starting the server."""

import pytest

pytest.importorskip("gradio")


def test_ctrl_c_stops_the_server_without_waiting_for_open_pages(monkeypatch, tmp_path):
    # regression: uvicorn waited forever for Gradio's open page connections, so Ctrl-C hung
    import uvicorn

    from lerni.student.web import serve

    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: seen.update(kwargs))
    monkeypatch.setattr(serve, "_claude_tagger", lambda: None)
    monkeypatch.setattr(serve, "_claude_uploader", lambda: None)
    monkeypatch.setattr(serve, "_claude_chat", lambda: None)
    serve.serve("127.0.0.1", 0)
    assert 0 < seen["timeout_graceful_shutdown"] <= 5
