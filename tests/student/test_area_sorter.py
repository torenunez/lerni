"""Lerni sorts goals with no area into subject areas by itself; a person can move one (v3.37)."""

from lerni.student.area_sorter import AreaSorter
from lerni.student.interests import MapStore, add_goal, set_area


class FakeWriter:
    """Answers with fixed areas, and counts its calls."""

    def __init__(self, picks=None, fail=False):
        self.picks, self.fail, self.calls = picks or {}, fail, []

    def write(self, system, prompt, schema, timeout):
        self.calls.append(prompt)
        if self.fail:
            raise RuntimeError("resting")
        return {"areas": [{"goal": g, "area": a} for g, a in self.picks.items()]}


def _map(tmp_path):
    maps = MapStore(tmp_path)

    def seed(m):
        set_area(m, add_goal(m, "Fractions").id, "Math")  # a person's area stays
        add_goal(m, "Note values")
        add_goal(m, "Taekwondo tenets")

    maps.change("sam", seed, by="person:ann")
    return maps


def test_goals_with_no_area_are_sorted_once_as_lerni(tmp_path):
    maps = _map(tmp_path)
    writer = FakeWriter({"Note values": "music", "Taekwondo tenets": "Taekwondo",
                         "Fractions": "Science", "Not a goal": "Math"})
    sorter = AreaSorter(writer, maps)
    assert sorter.sort("sam") == 2
    got = {e.name: e.area for e in maps.get("sam").entries}
    assert got == {"Fractions": "Math", "Note values": "Music", "Taekwondo tenets": "Taekwondo"}
    assert "Math" in writer.calls[0] and "Fractions" in writer.calls[0]  # how it's sorted so far
    assert maps.journal.read("sam")[-1]["by"] == "lerni"  # one change, undone like any other
    assert sorter.sort("sam") == 0 and len(writer.calls) == 1  # nothing left: no call


def test_a_failed_sort_keeps_the_save_and_waits_before_trying_again(tmp_path):
    maps = _map(tmp_path)
    writer = FakeWriter(fail=True)
    sorter = AreaSorter(writer, maps)
    now = [0.0]
    sorter.clock = lambda: now[0]
    maps.after_change = sorter.sort  # as the app wires it
    maps.change("sam", lambda m: add_goal(m, "Energy"), by="person:ann")  # the save still lands
    maps.change("sam", lambda m: add_goal(m, "Equation"), by="person:ann")
    m = maps.get("sam")
    assert m.find("Energy").area == "" and m.find("Equation").area == ""
    assert len(writer.calls) == 1  # resting or no answer: no call on every save
    now[0] += 601
    writer.fail, writer.picks = False, {"Energy": "Science"}
    maps.change("sam", lambda m: add_goal(m, "Volcanoes"), by="person:ann")
    assert len(writer.calls) == 2 and maps.get("sam").find("Energy").area == "Science"


def test_review_regressions_other_is_a_choice_a_sort_isnt_a_persons_edit(tmp_path):
    from lerni.student.interests import by_area

    maps = _map(tmp_path)
    edits = maps.get("sam").edits
    writer = FakeWriter({"Note values": "Music"})
    sorter = AreaSorter(writer, maps)
    sorter.sort("sam")
    m = maps.get("sam")
    assert m.edits == edits  # an in-flight tagger update isn't dropped for a sort
    maps.change("sam", lambda m: set_area(m, m.find("Note values").id, "other"))
    sorter.sort("sam")  # a person's Other stays Other: Lerni leaves it
    m = maps.get("sam")
    assert m.find("Note values").area == "Other"
    goals = [e for e in m.entries if e.kind == "goal"]
    assert [a for a, _ in by_area(goals)] == ["Math", "Other"]  # one Other heading
    assert sorted(e.name for e in dict(by_area(goals))["Other"]) == [
        "Note values", "Taekwondo tenets"]
