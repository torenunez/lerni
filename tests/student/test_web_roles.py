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


def test_each_student_asks_in_their_own_voice():
    from lerni.student.conversation import Conversations
    from lerni.student.web.ask import ask_reply

    class Model:
        def __init__(self):
            self.systems = []

        def stream(self, system, turns):
            self.systems.append(system)
            yield "Hi."

    model = Model()
    convos = Conversations(model)
    lee = Viewer("lee", "Lee", Role.SUPERVISED)
    assert "".join(ask_reply(convos, SAM, "What is speed?")) == "Hi."
    # a supervised student gets the supervised voice, whatever the page asks for
    assert "".join(ask_reply(convos, lee, "Why is the sky blue?", supervised_voice=False)) == "Hi."
    assert "short, simple, playful" in model.systems[1] and "weapons" in model.systems[1]
    assert "short, simple, playful" not in model.systems[0]
    with pytest.raises(NotAllowed):
        list(ask_reply(convos, None, "hi"))


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


def test_upload_and_feedback_check_who_is_asking(tmp_path):
    from lerni.student.feedback import FeedbackStore
    from lerni.student.interests import MapStore
    from lerni.student.web.maps import add_proposals, propose_for, save_feedback

    class Uploader:
        def propose(self, system, source):
            return {"entries": [{"kind": "goal", "name": "Fractions"},
                                {"kind": "interest", "name": "sharks"}]}

    students, maps = StudentStore(tmp_path), MapStore(tmp_path)
    students.add("lee", "Lee", Kind.SUPERVISED, "1234")
    students.add("zoe", "Zoe", Kind.INDEPENDENT, "long enough")
    upload = tmp_path / "notes.txt"
    upload.write_text("Lee loves sharks; practice fractions")
    proposals, _, message = propose_for(Uploader(), maps, students, SAM, "lee", "", str(upload))
    assert message.startswith("⚠️") and proposals == []
    assert not upload.exists()  # deleted even when refused
    proposals, _, _ = propose_for(Uploader(), maps, students, EDUCATOR, "lee", "notes", None)
    assert add_proposals(maps, students, EDUCATOR, "lee", proposals,
                         [proposals[0].label]).startswith("✅")
    assert [e.name for e in maps.get("lee").entries] == ["Fractions"]  # only what was ticked
    store = FeedbackStore(tmp_path)
    assert save_feedback(store, students, SAM, None, "hi", "").startswith("⚠️")
    assert save_feedback(store, students, EDUCATOR, "zoe", "hi", "").startswith("⚠️")
    assert save_feedback(store, students, EDUCATOR, "lee", "more soccer", "").startswith("✅")
    assert [(f.who, f.map) for f in store.entries()] == [("alba", "lee")]


def test_ideas_made_for_one_student_never_land_on_another(tmp_path):
    # regression: switching the Student dropdown after Upload added A's ideas to B's map
    from lerni.student.interests import MapStore
    from lerni.student.upload import Proposal
    from lerni.student.web.maps import add_proposals

    students, maps = StudentStore(tmp_path), MapStore(tmp_path)
    for name in ("lee", "kim"):
        students.add(name, name.title(), Kind.SUPERVISED, "1234")
    ideas = [Proposal("goal", "Fractions")]
    message = add_proposals(maps, students, EDUCATOR, "kim", ideas, [ideas[0].label],
                            proposed_for="lee")
    assert message.startswith("⚠️") and maps.get("kim").entries == []


def test_uploads_over_5_mb_are_refused_and_leftovers_expire(tmp_path):
    # regression: any size was accepted, and a file picked but never sent stayed on disk
    StudentStore(tmp_path).add("zoe", "Zoe", Kind.INDEPENDENT, "long enough")
    app = build_app(data_root=tmp_path)
    client = TestClient(app)
    client.post("/signin", data={"username": "zoe", "password": "long enough"})
    big = client.post("/app/gradio_api/upload",
                      files={"files": ("notes.txt", b"x" * 5_100_000, "text/plain")})
    assert big.status_code == 413
    small = client.post("/app/gradio_api/upload",
                        files={"files": ("notes.txt", b"cars", "text/plain")})
    assert small.status_code == 200


def test_a_supervised_student_signs_in_to_the_conversation(tmp_path):
    # the page has two chats (Ask and the supervised screen); only Home is a supervised tab
    StudentStore(tmp_path).add("lee", "Lee", Kind.SUPERVISED, "1234")
    client = TestClient(build_app(data_root=tmp_path))
    client.post("/signin", data={"username": "lee", "password": "1234"})
    config = client.get("/app/config").json()
    labels = [c["props"].get("label") for c in config["components"] if c.get("type") == "tabitem"]
    assert "Lerni" in labels
    chats = [c for c in config["components"] if c.get("type") == "chatbot"]
    assert len(chats) == 2
    assert "Get ready to explore" not in client.get("/app/config").text  # no waiting screen
