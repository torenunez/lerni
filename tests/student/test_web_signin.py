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


def test_the_cookie_is_secure_only_over_https(tmp_path):
    StudentStore(tmp_path).add("sam", "Sam", Kind.INDEPENDENT, "long enough")
    for base, secure in (("https://lerni.test", True), ("http://lerni.test", False)):
        client = TestClient(build_app(data_root=tmp_path), base_url=base, follow_redirects=False)
        response = client.post("/signin", data={"username": "sam", "password": "long enough"})
        assert ("secure" in response.headers["set-cookie"].lower()) is secure


def test_a_development_server_says_so_and_production_does_not(tmp_path):
    # two environments look alike; the label keeps them apart at a glance
    StudentStore(tmp_path).add("sam", "Sam", Kind.INDEPENDENT, "long enough")
    dev = TestClient(build_app(data_root=tmp_path, label="Development"))
    assert "Development" in dev.get("/signin").text
    dev.post("/signin", data={"username": "sam", "password": "long enough"})
    assert "Development" in dev.get("/app/config").text
    prod = TestClient(build_app(data_root=tmp_path))
    assert "Development" not in prod.get("/signin").text


def test_the_sign_in_page_says_which_version_is_running(tmp_path):
    # regression: an old server looked like a bug, with no way to tell from the iPad
    from lerni.student.web.serve import running_version

    version = running_version()
    assert version and "@" in version  # e.g. "main @ e152c46, 2026-10-10" in a checkout
    client = TestClient(build_app(data_root=tmp_path, version=version))
    assert version in client.get("/signin").text


def test_a_development_server_keeps_its_own_sign_in(tmp_path):
    # same host, another port: its cookie mustn't replace production's
    StudentStore(tmp_path).add("sam", "Sam", Kind.INDEPENDENT, "long enough")
    client = TestClient(build_app(data_root=tmp_path, label="Development"),
                        base_url="https://lerni.test", follow_redirects=False)
    response = client.post("/signin", data={"username": "sam", "password": "long enough"})
    assert response.headers["set-cookie"].startswith("lerni_session_development=")
    assert client.get("/").headers["location"] == "/app/"
