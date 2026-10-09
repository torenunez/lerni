"""Tabs by role: educator actions refuse students, and the page config carries no user data."""

import pytest

pytest.importorskip("gradio")

from fastapi.testclient import TestClient  # noqa: E402

from lerni.student.signin import Role, Viewer  # noqa: E402
from lerni.student.students import Kind, StudentStore  # noqa: E402
from lerni.student.web.accounts import (  # noqa: E402
    NotAllowed,
    add_student,
    archive_student,
    reset_student,
    students_action,
)
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


def test_a_refused_action_shows_no_roster_and_educators_keep_their_own_account(tmp_path):
    students = StudentStore(tmp_path)
    add_student(students, EDUCATOR, "alba", "Alba", "independent", "long enough", True)
    # what the Students handlers return: a refusal and no roster (it was the whole roster)
    message, rows = students_action(students, SAM, archive_student, "alba")
    assert message.startswith("⚠️") and rows == []
    _, rows = students_action(students, EDUCATOR, reset_student, "alba", "long enough")
    assert rows[0][0] == "alba"
    with pytest.raises(NotAllowed):
        archive_student(students, EDUCATOR, "alba")


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
    # regression: a hidden tab stayed selected, so the educator saw an empty page
    from lerni.student.web.main import opening_tab, visible_tabs

    lee = Viewer("lee", "Lee", Role.SUPERVISED)
    assert visible_tabs(EDUCATOR) == ("ask", "mymap", "maps", "students", "account")
    assert visible_tabs(lee) == ("home",)  # the conversation arrives in step 9
    assert visible_tabs(SAM) == ("ask", "mymap", "account")
    assert (opening_tab(EDUCATOR), opening_tab(lee), opening_tab(SAM)) == ("ask", "home", "ask")


def test_sign_out_is_a_same_tab_button(tmp_path):
    # regression: a Markdown link opened Sign out in a new tab, leaving the old account on screen
    StudentStore(tmp_path).add("sam", "Sam", Kind.SUPERVISED, "1234")
    client = TestClient(build_app(data_root=tmp_path))
    client.post("/signin", data={"username": "sam", "password": "1234"})
    config = client.get("/app/config").json()
    buttons = [c["props"] for c in config["components"] if c.get("type") == "button"]
    assert any(b.get("link") == "/signout" and b.get("link_target") == "_self" for b in buttons)


def test_add_form_clears_after_a_save_and_educator_needs_independent():
    # regression: the form kept the last student, password and Educator tick included
    from lerni.student.web.accounts import add_form_after, educator_box_for

    cleared = add_form_after("✅ Added Sam (supervised).")
    assert [u.get("value") for u in cleared] == ["", "", "supervised", False, ""]
    assert all("value" not in u for u in add_form_after("⚠️ 'sam' is taken."))
    assert educator_box_for("supervised") == {"__type__": "update", "value": False,
                                              "interactive": False}
    assert educator_box_for("independent")["interactive"] is True


def test_only_independent_students_can_ask_lerni():
    from lerni.student.conversation import Conversations
    from lerni.student.web.ask import ask_reply

    class Model:
        def stream(self, system, turns):
            yield "Hi."

    convos = Conversations(Model())
    assert "".join(ask_reply(convos, SAM, "What is speed?")) == "Hi."
    with pytest.raises(NotAllowed):
        list(ask_reply(convos, Viewer("lee", "Lee", Role.SUPERVISED), "hi"))


def test_maps_reach_only_their_owner_or_an_educator_for_a_supervised_student(tmp_path):
    from lerni.student.interests import MapStore
    from lerni.student.web.maps import add_goal_to, map_owner

    students, maps = StudentStore(tmp_path), MapStore(tmp_path)
    students.add("lee", "Lee", Kind.SUPERVISED, "1234")
    students.add("zoe", "Zoe", Kind.INDEPENDENT, "long enough")
    assert map_owner(students, SAM, None) == "sam"  # My map
    assert map_owner(students, EDUCATOR, "lee") == "lee"  # Maps
    for viewer, requested in ((SAM, "lee"), (EDUCATOR, "zoe"), (EDUCATOR, "nobody"),
                              (Viewer("lee", "Lee", Role.SUPERVISED), None)):
        with pytest.raises(NotAllowed):
            map_owner(students, viewer, requested)
    assert add_goal_to(maps, students, SAM, "lee", "Fractions", "").startswith("⚠️")
    assert maps.get("lee").entries == []
    assert add_goal_to(maps, students, EDUCATOR, "lee", "Fractions", "").startswith("✅")


def test_cleared_fields_get_their_own_update():
    # regression: one shared update cleared only the first field (Gradio consumes its value),
    # so a reset left the new password in its box
    from lerni.student.web.accounts import cleared

    first, second = cleared(2, done=True)
    assert first is not second and first["value"] == second["value"] == ""


def test_a_redraw_keeps_the_entry_being_renamed():
    # regression: Maps' 30-second redraw reset the Rename/Remove pick, so Rename failed
    from lerni.student.interests import InterestMap, add_goal
    from lerni.student.web.maps import entry_update

    m = InterestMap()
    goal = add_goal(m, "Fractions")
    assert entry_update(m, goal.id)["value"] == goal.id
    assert entry_update(m, "gone")["value"] is None
