"""Tabs by role: educator actions refuse students, and the page config carries no user data."""

import pytest

pytest.importorskip("gradio")

from fastapi.testclient import TestClient  # noqa: E402

from lerni.student.signin import Role, Viewer  # noqa: E402
from lerni.student.students import Kind, StudentStore  # noqa: E402
from lerni.student.web.accounts import NotAllowed, add_student, archive_student  # noqa: E402
from lerni.student.web.app import build_app  # noqa: E402

EDUCATOR = Viewer("educator", "Educator", Role.EDUCATOR)
SAM = Viewer("sam", "Sam", Role.INDEPENDENT)


def test_students_can_not_manage_accounts(tmp_path):
    students = StudentStore(tmp_path)
    assert "Added" in add_student(students, EDUCATOR, "sam", "Sam", "independent", "long enough")
    with pytest.raises(NotAllowed):
        add_student(students, SAM, "eve", "Eve", "independent", "long enough")
    with pytest.raises(NotAllowed):
        archive_student(students, None, "sam")  # an archived or unknown viewer resolves to None
    assert students.list_students()[0].username == "sam"


def test_page_config_carries_no_plans_or_usernames(tmp_path):
    students = StudentStore(tmp_path)
    students.add("sam", "Sam", Kind.SUPERVISED, "1234")
    students.add("zephyrine", "Zephyrine", Kind.INDEPENDENT, "long enough")
    client = TestClient(build_app("test-passcode", data_root=tmp_path))
    client.post("/signin", data={"username": "sam", "password": "1234"})
    config = client.get("/app/config").text  # Gradio adds the viewer's own username; fine
    for leaked in ("cars-", "sharks-", "zephyrine", "Zephyrine"):
        assert leaked not in config


def test_each_role_opens_on_a_tab_it_can_see():
    # regression: the hidden Learn tab stayed selected, so the educator saw an empty page
    from lerni.student.web.main import visible_tabs

    assert visible_tabs(Role.EDUCATOR) == ("guide", "sessions", "plans", "students")
    assert visible_tabs(Role.SUPERVISED) == ("learn",)
    assert visible_tabs(Role.INDEPENDENT) == ("learn", "guide", "account")
