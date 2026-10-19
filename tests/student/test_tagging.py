"""The map keeper: tags each exchange in the background, logs it, and never undoes a person."""

from datetime import date, timedelta

from lerni.student.interests import MapStore, add_goal, rename
from lerni.student.logs import ConversationLog
from lerni.student.tagging import Exchange, MapKeeper

TODAY = date(2026, 10, 10)


class FakeTagger:
    def __init__(self, answer, during=None):
        self.answer, self.during, self.prompts = answer, during, []

    def tag(self, system, prompt):
        self.prompts.append(prompt)
        if self.during:
            self.during()  # a person edits the map while the call is out
        return self.answer


def keeper(tmp_path, tagger):
    maps, log = MapStore(tmp_path), ConversationLog(tmp_path, today=lambda: TODAY)
    return maps, log, MapKeeper(maps, tagger, log, run=lambda f: f(), today=lambda: TODAY)


def exchange(question, stopped=False, current=True):
    return Exchange("sam", "", question, "Answer.", stopped, lambda: current)


def test_an_exchange_grows_the_map_and_is_logged(tmp_path):
    maps, log, k = keeper(tmp_path, FakeTagger({"new_interests": ["cars"]}))
    k.after(exchange("I love cars"))
    assert maps.get("sam").find("cars").days == ["2026-10-10"]
    assert "cars" in k.context("sam")
    [record] = log.read("sam")
    assert record["question"] == "I love cars" and record["tags"]["new_interests"] == ["cars"]
    k.after(exchange("Tell me about trains", stopped=True))  # stopped: logged, not tagged
    assert log.read("sam")[-1]["tags"] == "stopped" and maps.get("sam").find("trains") is None
    assert "sam" not in k.tagger.prompts[0]  # never the username


def test_a_late_result_never_undoes_a_person_or_a_new_conversation(tmp_path):
    maps = MapStore(tmp_path)
    goal = maps.change("sam", lambda m: add_goal(m, "Fractions"))
    renamed = lambda: maps.change("sam", lambda m: rename(m, goal.id, "Halves"))  # noqa: E731
    _, log, k = keeper(tmp_path, FakeTagger({"new_interests": ["cars"]}, during=renamed))
    k.after(exchange("I love cars"))
    assert maps.get("sam").find("cars") is None and log.read("sam")[-1]["tags"] == "stale"
    _, _, k = keeper(tmp_path, FakeTagger({"new_interests": ["cars"]}))
    k.after(exchange("I love cars", current=False))  # New conversation came meanwhile
    assert maps.get("sam").find("cars") is None


def test_logs_older_than_7_days_are_deleted(tmp_path):
    log = ConversationLog(tmp_path, today=lambda: TODAY)
    folder = tmp_path / "logs" / "sam"
    folder.mkdir(parents=True)
    for age in (6, 7):
        (folder / f"{(TODAY - timedelta(days=age)).isoformat()}.jsonl").write_text("{}\n")
    log.purge()
    assert sorted(p.stem for p in folder.iterdir()) == ["2026-10-04"]


def test_a_real_answer_earns_stars_once_and_never_when_skipped_stopped_or_cleared(tmp_path):
    from lerni.student.points import CHAT_CAP, PointsStore

    points, tags = PointsStore(tmp_path), {"answered": "right"}
    k = MapKeeper(MapStore(tmp_path), FakeTagger(tags), None, run=lambda f: f(),
                  today=lambda: TODAY, points=points)
    ex = Exchange("sam", "What makes it speed up?", "the engine pushes", "Yes!", False,
                  lambda: True)
    k.after(ex)
    k.after(ex)  # tagged again: the same exchange awards once
    assert points.get("sam").balance == 3
    tags["answered"] = "tried"
    k.after(exchange("maybe the wheels"))
    assert points.get("sam").balance == 4
    tags["answered"] = "right"
    for skip, stopped, current in (("scary", False, True), (None, True, True),
                                   (None, False, False)):
        tags["skip"] = skip
        k.after(exchange("an answer", stopped=stopped, current=current))
    assert points.get("sam").balance == 4  # skipped, stopped, or New conversation: nothing
    tags["skip"] = None
    for _ in range(20):
        k.after(exchange("an answer"))
    assert points.get("sam").balance == CHAT_CAP  # Chat stops at the day's cap


def test_only_players_earn_stars_and_the_watch_outlasts_the_tagger(tmp_path):
    # regression: an independent student earned stars they could never see or spend
    from lerni.student.adapters.claude_code import TAG_TIMEOUT_SECONDS
    from lerni.student.conversation import system_prompt
    from lerni.student.points import PointsStore
    from lerni.student.web.main import WATCH_TICKS

    points = PointsStore(tmp_path)
    k = MapKeeper(MapStore(tmp_path), FakeTagger({"answered": "right"}), None,
                  run=lambda f: f(), today=lambda: TODAY, points=points,
                  earns=lambda username: username == "sam")
    k.after(exchange("the engine pushes"))
    k.after(Exchange("ivy", "", "the engine pushes", "Yes!", False, lambda: True))
    assert (points.get("sam").balance, points.get("ivy").balance) == (3, 0)
    assert "⭐" in system_prompt("", "supervised") and "⭐" not in system_prompt("", "independent")
    # regression: the header stopped looking for "+3" before a slow tagger finished
    assert WATCH_TICKS * 2 > TAG_TIMEOUT_SECONDS
