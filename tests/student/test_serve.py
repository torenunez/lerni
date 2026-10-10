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


def test_https_needs_both_files_and_passes_them_to_uvicorn(monkeypatch, tmp_path, capsys):
    import uvicorn

    from lerni.student.web import serve

    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: seen.update(kwargs))
    for name in ("_claude_tagger", "_claude_uploader", "_claude_chat"):
        monkeypatch.setattr(serve, name, lambda: None)
    cert, key = tmp_path / "home.pem", tmp_path / "home-key.pem"
    with pytest.raises(ValueError):
        serve.serve("127.0.0.1", 0, cert=cert)  # a key is needed too
    with pytest.raises(ValueError):
        serve.serve("127.0.0.1", 0, cert=cert, key=key)  # files that don't exist
    cert.write_text("cert")
    key.write_text("key")
    serve.serve("127.0.0.1", 0, cert=cert, key=key)
    assert seen["ssl_certfile"] == str(cert) and seen["ssl_keyfile"] == str(key)
    assert "https://" in capsys.readouterr().out
