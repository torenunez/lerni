"""The one app: signed-out visits go to the sign-in form; a cookie opens the app."""

import pytest

pytest.importorskip("gradio")

from fastapi.testclient import TestClient  # noqa: E402

from lerni.student.students import Kind, StudentStore  # noqa: E402
from lerni.student.web.app import build_app  # noqa: E402


@pytest.fixture
def client(tmp_path):
    StudentStore(tmp_path).add("sam", "Sam", Kind.SUPERVISED, "1234")
    return TestClient(build_app(data_root=tmp_path), follow_redirects=False)


def sign_in(client, username, password):
    return client.post("/signin", data={"username": username, "password": password})


def test_signed_out_visits_go_to_the_sign_in_form(client):
    assert client.get("/app/").headers["location"] == "/signin"
    form = client.get("/signin").text
    assert 'autocomplete="current-password"' in form and "<form" in form
    assert client.get("/app/config").status_code == 401


def test_a_right_password_opens_the_app_and_sign_out_ends_it(client):
    assert sign_in(client, "sam", "nope").status_code == 401
    response = sign_in(client, "sam", "1234")
    assert response.status_code == 303 and response.headers["location"] == "/app/"
    assert client.get("/app/config").status_code == 200
    client.get("/signout")
    assert client.get("/app/config").status_code == 401


def test_first_start_says_how_to_add_the_first_account(tmp_path):
    client = TestClient(build_app(data_root=tmp_path))
    assert "lerni student add" in client.get("/signin").text
