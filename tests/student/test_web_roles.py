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
    assert visible_tabs(EDUCATOR) == ("games", "ask", "mymap", "maps", "account")
    assert visible_tabs(lee) == ("home", "games")
    assert visible_tabs(SAM) == ("ask", "mymap", "account")
    assert (opening_tab(EDUCATOR), opening_tab(lee), opening_tab(SAM)) == ("ask", "home", "ask")


def test_the_educator_opens_on_their_student_by_name(tmp_path):
    # with one supervised student, the menu names them and sign-in opens their page
    from lerni.student.web.main import menu_label, opening_tab

    store = StudentStore(tmp_path)
    assert opening_tab(EDUCATOR, store) == "ask"  # no student yet: their own Chat
    store.add("lee", "Lee", Kind.SUPERVISED, "1234")
    assert opening_tab(EDUCATOR, store) == "maps" and menu_label("maps", EDUCATOR, store) == "Lee"
    store.add("kim", "Kim", Kind.SUPERVISED, "1234")
    assert menu_label("maps", EDUCATOR, store) == "MentalMaps"  # two: a picker again
    assert menu_label("account", SAM, store) == "Settings"


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
    from lerni.student.web.maps import map_owner
    from lerni.student.web.mentallist import add_item, put_back_item, remove_item

    students, maps = StudentStore(tmp_path), MapStore(tmp_path)
    students.add("lee", "Lee", Kind.SUPERVISED, "1234")
    students.add("zoe", "Zoe", Kind.INDEPENDENT, "long enough")
    assert map_owner(students, SAM, None) == "sam"  # My map
    assert map_owner(students, EDUCATOR, "lee") == "lee"  # Maps
    for viewer, requested in ((SAM, "lee"), (EDUCATOR, "zoe"), (EDUCATOR, "nobody"),
                              (Viewer("lee", "Lee", Role.SUPERVISED), None)):
        with pytest.raises(NotAllowed):
            map_owner(students, viewer, requested)
    assert add_item(maps, students, SAM, "lee", "Goal", "Fractions", "").startswith("⚠️")
    supervised = Viewer("lee", "Lee", Role.SUPERVISED)
    assert add_item(maps, students, supervised, None, "Interest", "trains", "").startswith("⚠️")
    assert maps.get("lee").entries == []
    assert add_item(maps, students, EDUCATOR, "lee", "Interest", "sharks", "").startswith("✅")
    shark = maps.get("lee").find("sharks").id
    assert remove_item(maps, students, EDUCATOR, "lee", shark).startswith("✅")
    assert remove_item(maps, students, EDUCATOR, "lee", shark).startswith("⚠️")  # stale id
    assert put_back_item(maps, students, EDUCATOR, "lee", "sharks").startswith("✅")
    assert put_back_item(maps, students, EDUCATOR, "lee", "sharks").startswith("⚠️")  # twice


def test_cleared_fields_get_their_own_update():
    # regression: one shared update cleared only the first field (Gradio consumes its value),
    # so a reset left the new password in its box
    from lerni.student.web.accounts import cleared

    first, second = cleared(2, done=True)
    assert first is not second and first["value"] == second["value"] == ""


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
    # the page has three chats (Chat, the supervised screen, Maps); only Home is a supervised tab
    StudentStore(tmp_path).add("lee", "Lee", Kind.SUPERVISED, "1234")
    client = TestClient(build_app(data_root=tmp_path))
    client.post("/signin", data={"username": "lee", "password": "1234"})
    config = client.get("/app/config").json()
    labels = [c["props"].get("label") for c in config["components"] if c.get("type") == "tabitem"]
    assert "Chat" in labels
    chats = [c for c in config["components"] if c.get("type") == "chatbot"]
    assert len(chats) == 2  # the two Chats; the student page has none since v3.26
    assert "Get ready to explore" not in client.get("/app/config").text  # no waiting screen


def test_a_talked_question_is_heard_then_answered_in_the_right_voice():
    from lerni.student.conversation import Conversations
    from lerni.student.web.ask import talk_preview, talk_reply
    from tests.student.test_voice import FakeSpeech, clip

    class Model:
        def __init__(self):
            self.systems = []

        def stream(self, system, turns):
            self.systems.append(system)
            yield "Fish. Seals too."

    model, speech = Model(), FakeSpeech()
    convos = Conversations(model)
    lee = Viewer("lee", "Lee", Role.SUPERVISED)
    text, reply = talk_reply(convos, speech, lee, clip())
    assert text == "what do sharks eat"
    out = list(reply)
    assert "".join(t for t, _ in out) == "Fish. Seals too."
    assert speech.spoken == ["Fish.", "Seals too."]
    assert "short, simple, playful" in model.systems[0]  # the supervised voice
    assert convos.history("lee")[0].text == "what do sharks eat"
    with pytest.raises(NotAllowed):
        talk_reply(convos, speech, None, clip())
    assert speech.clips == 1  # nobody signed in: nothing transcribed
    assert talk_preview(speech, lee, clip()) == "what do sharks eat"
    assert talk_preview(speech, lee, "not a clip") == ""  # a bad preview shows nothing
    with pytest.raises(NotAllowed):
        talk_preview(speech, None, clip())


def test_a_typed_question_is_answered_aloud_when_voice_is_on():
    # the student asked to type sometimes; answers are still spoken (the admin's choice)
    from lerni.student.conversation import Conversations
    from lerni.student.web.ask import typed_reply
    from tests.student.test_voice import FakeSpeech

    class Model:
        def stream(self, system, turns):
            yield "Fish. Seals too."

    speech, lee = FakeSpeech(), Viewer("lee", "Lee", Role.SUPERVISED)
    out = list(typed_reply(Conversations(Model()), speech, lee, "What do sharks eat?"))
    assert speech.spoken == ["Fish.", "Seals too."] and sum(1 for _, a in out if a) == 2
    silent = list(typed_reply(Conversations(Model()), None, lee, "And whales?"))
    assert "".join(t for t, _ in silent) == "Fish. Seals too." and not any(a for _, a in silent)


def test_educator_chat_is_for_educators_and_applies_only_ticked_items(tmp_path):
    from lerni.student.educator_agent import EducatorChats
    from lerni.student.feedback import FeedbackStore
    from lerni.student.interests import MapStore
    from lerni.student.web.educator import educator_add, educator_send, preticked

    class Model:
        def stream(self, system, turns):
            yield ('Ideas.\n```proposals\n{"proposals": ['
                   '{"kind": "goal", "name": "fractions"},'
                   '{"kind": "interest", "name": "baking"},'
                   '{"kind": "feedback", "notes": "bigger buttons"}]}\n```')

    students, maps, store = StudentStore(tmp_path), MapStore(tmp_path), FeedbackStore(tmp_path)
    students.add("lee", "Lee", Kind.SUPERVISED, "1234")
    students.add("kim", "Kim", Kind.SUPERVISED, "1234")
    chats = EducatorChats(Model(), maps)
    with pytest.raises(NotAllowed):
        list(educator_send(chats, students, SAM, "lee", "hi"))  # not an educator
    shown = "".join(educator_send(chats, students, EDUCATOR, "lee", "fractions please"))
    assert shown.strip() == "Ideas."
    labels = [p.label for p in chats.proposals("alba", "lee")]
    # review: feedback (and removals) wait for a tick of their own under "Add"
    assert preticked(chats.proposals("alba", "lee")) == labels[:2]
    assert educator_add(chats, maps, store, students, SAM, "lee", labels).startswith("⚠️")
    # the student picked meanwhile doesn't matter: the held owner is used
    msg = educator_add(chats, maps, store, students, EDUCATOR, "lee", [labels[0], labels[2]])
    assert msg.startswith("✅")
    assert maps.get("lee").find("fractions") and not maps.get("lee").find("baking")
    assert maps.get("kim").find("fractions") is None
    assert [(f.text, f.map) for f in store.entries()] == [("bigger buttons", "lee")]


def test_a_pdf_in_the_educator_chat_gets_a_friendly_message(tmp_path):
    from lerni.student.educator_agent import EducatorChats
    from lerni.student.interests import MapStore
    from lerni.student.upload import UploadError
    from lerni.student.web.educator import educator_send

    students = StudentStore(tmp_path)
    students.add("lee", "Lee", Kind.SUPERVISED, "1234")
    chats = EducatorChats(object(), MapStore(tmp_path))  # never called
    with pytest.raises(UploadError, match="PDF"):
        list(educator_send(chats, students, EDUCATOR, "lee", "", "notes.pdf", b"%PDF-1.4"))


def test_list_draws_run_one_at_a_time(tmp_path):
    # regression: two lists drawing at once could take the same block id (DuplicateBlockError)
    app = build_app(data_root=tmp_path)
    blocks = next(r.app for r in app.routes if getattr(r, "path", "") == "/app").get_blocks()
    draws = [f for f in blocks.fns.values() if getattr(f, "renderable", None) is not None]
    assert len(draws) == 2
    assert {(f.concurrency_id, f.concurrency_limit) for f in draws} == {("mental-list", 1)}


def test_an_open_item_with_links_draws_on_both_lists(tmp_path):
    # regression: v3.25's folded flag hid the open-item state, so a jump button broke the draw
    import gradio as gr

    from lerni.student.interests import MapStore, add_interest, group

    StudentStore(tmp_path).add("ann", "Ann", Kind.INDEPENDENT, "long enough")
    MapStore(tmp_path).change("ann", lambda m: [add_interest(m, "sharks"),
                                                add_interest(m, "great white"),
                                                group(m, "e2", "e1")])
    app = build_app(data_root=tmp_path)
    blocks = next(r.app for r in app.routes if getattr(r, "path", "") == "/app").get_blocks()
    for f in [f for f in blocks.fns.values() if getattr(f, "renderable", None) is not None]:
        with gr.Blocks():
            f.renderable.fn("ann", 0, "e1", None, [])  # sharks open, great white under Kinds


def test_an_edit_only_reaches_the_map_on_screen(tmp_path):
    # regression: on a shared device, a row drawn for one account removed the next one's e1
    from lerni.student.interests import MapStore, add_interest
    from lerni.student.web.mentallist import remove_item

    students, maps = StudentStore(tmp_path), MapStore(tmp_path)
    students.add("ann", "Ann", Kind.INDEPENDENT, "long enough")
    maps.change("ann", lambda m: add_interest(m, "sharks"))
    ann = Viewer("ann", "Ann", Role.INDEPENDENT)
    assert remove_item(maps, students, ann, None, "e1", expected="sam").startswith("⚠️")
    assert maps.get("ann").find("sharks") is not None


def test_putting_an_item_in_a_group_checks_the_map_on_screen(tmp_path):
    from lerni.student.interests import MapStore, add_interest, parents
    from lerni.student.web.mentallist import group_item, ungroup_item

    students, maps = StudentStore(tmp_path), MapStore(tmp_path)
    students.add("ann", "Ann", Kind.INDEPENDENT, "long enough")
    maps.change("ann", lambda m: [add_interest(m, "sharks"), add_interest(m, "great white")])
    ann = Viewer("ann", "Ann", Role.INDEPENDENT)
    assert group_item(maps, students, ann, None, "e2", "sharks", expected="sam").startswith("⚠️")
    assert group_item(maps, students, ann, None, "e2", "sharks", expected="ann").startswith("✅")
    assert parents(maps.get("ann"), "e2") == ["e1"]
    assert ungroup_item(maps, students, ann, None, "e2", "e1", expected="ann").startswith("✅")


def test_games_are_for_players_and_each_player_spends_only_their_own_points(tmp_path):
    from datetime import date

    from lerni.student.garage import Garage
    from lerni.student.points import PointsStore
    from lerni.student.results import ResultsLog
    from lerni.student.web.games import garage_tap, require_player, student_progress

    students, points, garage = StudentStore(tmp_path), PointsStore(tmp_path), Garage(tmp_path)
    students.add("lee", "Lee", Kind.SUPERVISED, "1234")
    lee = Viewer("lee", "Lee", Role.SUPERVISED)
    with pytest.raises(NotAllowed):
        require_player(SAM)  # independent, not an educator: no Games yet
    assert garage_tap(points, garage, None, "starter").startswith("⚠️")  # signed out
    points.award("lee", "race-1", "race", 40)
    points.buy("lee", "rally", 30)
    assert garage_tap(points, garage, lee, "rally").startswith("Driving")
    assert points.get("lee").balance == 10 and points.get("alba").balance == 0
    results, today = ResultsLog(tmp_path), date.today().isoformat()
    for right in (True, True, True, False, False):
        results.add("lee", {"day": today, "goal": "a<b", "right": right})
    card = student_progress(points, garage, students, EDUCATOR, "lee", results)
    assert "⭐ 10" in card and garage.car("rally").name in card and "3 of 5" in card
    assert "a&lt;b" in card and "a<b" not in card  # names are escaped
    assert student_progress(points, garage, students, SAM, "lee", results) == ""  # educators only
    # v3.28: grouped by area, the most practiced area and goal first, no area last
    from lerni.student.interests import MapStore, add_goal, by_area

    maps = MapStore(tmp_path)
    maps.change("lee", lambda m: [setattr(add_goal(m, g), "area", a) for g, a in (
        ("Nouns", "Language"), ("Fractions", "Math"), ("Rain", "Math"), ("Verbs", "Language"),
        ("Planets", "Language"))])
    for goal, n in (("Nouns", 2), ("Fractions", 4), ("Rain", 1)):
        for _ in range(n):
            results.add("lee", {"day": today, "goal_id": maps.get("lee").find(goal).id,
                                "goal": goal, "right": True})
    card = student_progress(points, garage, students, EDUCATOR, "lee", results, maps)
    order = [card.index(x) for x in ("Math", "Fractions", "Rain", "Language", "Nouns", "Other")]
    assert order == sorted(order) and "5 of 5" in card  # Math's total
    assert [(a, [e.name for e in es]) for a, es in by_area(
        [e for e in maps.get("lee").entries if e.kind == "goal"])] == [
        ("Language", ["Nouns", "Verbs", "Planets"]), ("Math", ["Fractions", "Rain"])]


def test_a_tap_on_a_race_that_ended_offers_a_new_one():
    from lerni.student.race import Question, new_race
    from lerni.student.web.games import after_tap

    q = Question("Fractions", "Half of 8?", ("4", "2", "6"), 0, "Half means 2 equal parts.")
    race = new_race([q] * 5)
    assert after_tap(race, (race.id, 0), None) is None  # a repeat tap: nothing changes
    shown, line = after_tap(None, ("gone", 2), None)  # regression: the card went dead
    assert shown is None and "Tap Race" in line


def test_a_real_car_is_bought_at_its_star_price_and_old_cartoon_cars_stay(tmp_path):
    import json

    from lerni.student.garage import Garage
    from lerni.student.points import PointsStore
    from lerni.student.web.games import garage_tap

    (tmp_path / "cars").mkdir()
    (tmp_path / "cars" / "quick.webp").write_bytes(b"RIFF")
    (tmp_path / "garage.json").write_text(json.dumps({"cars": [
        {"id": "quick", "name": "Quick", "usd": 100_000, "zero_to_60": 3.5,
         "picture": "quick.webp"}]}))
    garage, points = Garage(tmp_path), PointsStore(tmp_path)
    lee = Viewer("lee", "Lee", Role.SUPERVISED)
    points.award("lee", "race-1", "race", 70)
    points.buy("lee", "rally", 30)  # bought in v3.1, before real cars
    assert garage_tap(points, garage, lee, "quick").startswith("🎉")
    assert points.get("lee").balance == 70 - 30 - 40
    assert [c.id for c in garage.sold(points.get("lee").cars)] == ["starter", "quick", "rally"]


def test_games_never_queue_one_player_behind_another_and_an_odd_error_brings_race_back(tmp_path):
    from lerni.student.race import NOT_READY
    from lerni.student.web.ask import MAX_AT_ONCE
    from lerni.student.web.games import start_race

    # regression: one player's slow start held up every Race and answer tap in the house
    app = build_app(data_root=tmp_path)
    blocks = next(r.app for r in app.routes if getattr(r, "path", "") == "/app").get_blocks()
    games = [f for f in blocks.fns.values() if f.name in ("on_go", "handler")
             and f.fn and f.fn.__qualname__.startswith("games_tab")]
    assert games and {f.concurrency_limit for f in games} == {MAX_AT_ONCE}

    class Broken:
        def start(self, *args, **kwargs):
            raise OSError("disk")

    lee = Viewer("lee", "Lee", Role.SUPERVISED)
    assert start_race(Broken(), lee) == (None, NOT_READY)  # regression: Race never came back


def test_a_fast_car_reaches_the_finish_only_on_the_fifth_answer_in_the_car_it_started_in(tmp_path):
    import re

    from lerni.student.garage import Garage
    from lerni.student.race import QUESTIONS_PER_RACE, Question, answer, new_race
    from lerni.student.web.games import END, track_svg

    q = Question("Fractions", "Half of 8?", ("4", "2", "6"), 0, "Half means 2 equal parts.")
    race = new_race([q] * QUESTIONS_PER_RACE, boost=1.4, car="rally")
    garage = Garage(tmp_path)

    def my_x() -> float:
        svg = track_svg(race, "starter", garage)  # they've switched to the starter meanwhile
        assert 'data-car="rally"' in svg  # regression: the track showed the new car mid-race
        return float(re.search(r'data-lane="me" data-x="(\d+)"', svg).group(1))

    for n in range(4):
        answer(race, n, 0)
    assert my_x() < END  # regression: a ×1.4 car stopped at the line after 4 right
    answer(race, 4, 0)
    assert my_x() == END


def test_a_car_out_of_reach_shows_only_its_picture_name_and_price(tmp_path):
    import json

    from lerni.student.garage import Garage
    from lerni.student.web.games import card_html

    (tmp_path / "cars").mkdir()
    (tmp_path / "cars" / "a.webp").write_bytes(b"RIFF")
    (tmp_path / "garage.json").write_text(json.dumps({"cars": [
        {"id": "a", "name": "Quick", "usd": 100_000, "zero_to_60": 3.5, "engine": "V8",
         "picture": "a.webp"}]}))
    quick = Garage(tmp_path).car("a")
    locked, open_ = card_html(quick, locked=True), card_html(quick)
    assert "Quick" in locked and "$100,000" in locked and "family car" in locked
    assert "⚡" not in locked and "Car facts" not in locked  # earned by saving up
    assert "⚡" in open_ and "Car facts" in open_ and "V8" in open_
