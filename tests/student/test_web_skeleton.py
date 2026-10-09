"""Walking skeleton: the student screen is open; the educator view needs the passcode.

Runs in-process with FastAPI's test client; nothing goes over the network.
"""


import pytest

pytest.importorskip("gradio")

from fastapi.testclient import TestClient  # noqa: E402

from lerni.student.web.app import build_app  # noqa: E402

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




def test_right_passcode_opens_the_educator_view(client):
    assert login(client, PASSCODE).status_code == 200
    config = client.get("/educator/config")
    assert config.status_code == 200
    assert "No approved activities yet" in config.text
