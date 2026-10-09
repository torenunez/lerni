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
