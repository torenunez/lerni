"""Walking skeleton: the student screen is open; the educator view needs the passcode.

Runs in-process with FastAPI's test client; nothing goes over the network.
"""

import os

import pytest

pytest.importorskip("gradio")

from fastapi.testclient import TestClient  # noqa: E402

from lerni.student.web.app import build_app, passcode_checker  # noqa: E402
from lerni.student.web.serve import MissingPasscodeError, resolve_passcode  # noqa: E402

PASSCODE = "test-passcode"


@pytest.fixture
def client():
    return TestClient(build_app(PASSCODE))


def login(client, password):
    return client.post("/educator/login", data={"username": "educator", "password": password})


def test_student_screen_needs_no_login(client):
    assert client.get("/").status_code == 200
    config = client.get("/config")
    assert config.status_code == 200
    assert "Waiting for your educator" in config.text


@pytest.mark.parametrize("path", ["/educator/config", "/educator/gradio_api/info"])
def test_educator_routes_refuse_without_passcode(client, path):
    assert client.get(path).status_code == 401


def test_wrong_passcode_is_refused(client):
    assert login(client, "guess").status_code == 400
    assert client.get("/educator/config").status_code == 401


def test_right_passcode_opens_the_educator_view(client):
    assert login(client, PASSCODE).status_code == 200
    config = client.get("/educator/config")
    assert config.status_code == 200
    assert "No approved activities yet" in config.text


@pytest.mark.parametrize("path", ["/openapi.json", "/educator/openapi.json", "/docs"])
def test_no_api_schema_or_docs_pages(client, path):
    assert client.get(path).status_code == 404


def test_analytics_are_off():
    assert os.environ["GRADIO_ANALYTICS_ENABLED"] == "False"


def test_checker_needs_both_username_and_passcode():
    check = passcode_checker(PASSCODE)
    assert check("educator", PASSCODE)
    assert not check("educator", "guess")
    assert not check("student", PASSCODE)


def test_empty_passcode_is_rejected():
    with pytest.raises(ValueError):
        build_app("")


@pytest.mark.parametrize("value", [None, ""])
def test_serve_refuses_without_a_passcode(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("LERNI_TEST_PASSCODE", raising=False)
    else:
        monkeypatch.setenv("LERNI_TEST_PASSCODE", value)
    with pytest.raises(MissingPasscodeError):
        resolve_passcode("LERNI_TEST_PASSCODE")
