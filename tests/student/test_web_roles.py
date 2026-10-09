"""Tabs by role: educator actions refuse students, and the page config carries no user data."""

import pytest

pytest.importorskip("gradio")

from fastapi.testclient import TestClient  # noqa: E402

from lerni.student.signin import Role, Viewer  # noqa: E402
from lerni.student.students import Kind, StudentStore  # noqa: E402
from lerni.student.web.accounts import NotAllowed, add_student, archive_student  # noqa: E402
from lerni.student.web.app import build_app  # noqa: E402

EDUCATOR = Viewer("alba", "Alba", Role.INDEPENDENT, educator=True)
SAM = Viewer("sam", "Sam", Role.INDEPENDENT)


def test_students_can_not_manage_accounts(tmp_path):
    students = StudentStore(tmp_path)
    added = add_student(students, EDUCATOR, "sam", "Sam", "independent", "long enough", False)
    assert "Added" in added
    with pytest.raises(NotAllowed):
        add_student(students, SAM, "eve", "Eve", "independent", "long enough", False)
    with pytest.raises(NotAllowed):
        archive_student(students, None, "sam")  # an archived or unknown viewer resolves to None
    assert students.list_students()[0].username == "sam"


def test_page_config_carries_no_plans_or_usernames(tmp_path):
    students = StudentStore(tmp_path)
    students.add("sam", "Sam", Kind.SUPERVISED, "1234")
    students.add("zephyrine", "Zephyrine", Kind.INDEPENDENT, "long enough")
    client = TestClient(build_app(data_root=tmp_path))
    client.post("/signin", data={"username": "sam", "password": "1234"})
    config = client.get("/app/config").text  # Gradio adds the viewer's own username; fine
    for leaked in ("cars-", "sharks-", "zephyrine", "Zephyrine"):
        assert leaked not in config


def test_each_role_opens_on_a_tab_it_can_see():
    # regression: the hidden Learn tab stayed selected, so the educator saw an empty page
    from lerni.student.web.main import opening_tab, visible_tabs

    kid = Viewer("kid", "Kid", Role.SUPERVISED)
    everything = ("learn", "guide", "sessions", "plans", "students", "account")
    assert visible_tabs(EDUCATOR) == everything
    assert visible_tabs(kid) == ("learn",)
    assert visible_tabs(SAM) == ("learn", "guide", "account")
    openings = (opening_tab(EDUCATOR), opening_tab(kid), opening_tab(SAM))
    assert openings == ("guide", "learn", "learn")


def test_sign_out_is_a_same_tab_button(tmp_path):
    # regression: a Markdown link opened Sign out in a new tab, leaving the old account on screen
    StudentStore(tmp_path).add("sam", "Sam", Kind.SUPERVISED, "1234")
    client = TestClient(build_app(data_root=tmp_path))
    client.post("/signin", data={"username": "sam", "password": "1234"})
    config = client.get("/app/config").json()
    buttons = [c["props"] for c in config["components"] if c.get("type") == "button"]
    assert any(b.get("link") == "/signout" and b.get("link_target") == "_self" for b in buttons)
