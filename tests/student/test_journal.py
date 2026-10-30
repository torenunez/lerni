"""The map journal: every change can be undone exactly, and a map rebuilt from its journal."""

import json
from datetime import date

import pytest

from lerni.student.interests import (
    InterestMap,
    MapStore,
    _to_dict,
    add_goal,
    apply_tags,
    parse_tags,
    set_notes,
)
from lerni.student.journal import JournalError, MapJournal, replay


def test_a_bad_merge_can_be_undone_and_the_map_rebuilt(tmp_path):
    m = InterestMap()
    goal = add_goal(m, "Fractions")
    for name in ("T-Rex", "Tyrannosaurus", "lava"):
        m.entries.append(m.new_entry(name, "interest"))
    apply_tags(m, parse_tags({"related": [["T-Rex", "lava"]]}), "x", date(2026, 10, 1))
    apply_tags(m, parse_tags({"about": ["Tyrannosaurus"]}), "x", date(2026, 10, 2))
    (tmp_path / "maps").mkdir()
    (tmp_path / "maps" / "sam.json").write_text(json.dumps(_to_dict(m)))  # from before journals
    store, journal = MapStore(tmp_path), MapJournal(tmp_path)

    # the tagger merges two items, then a person edits something else
    store.change("sam", lambda m: apply_tags(m, parse_tags(
        {"same_as": [["T-Rex", "Tyrannosaurus"]]}), "a T-Rex!", date(2026, 10, 3)), by="tagger")
    store.change("sam", lambda m: set_notes(m, goal.id, "halves"), by="person:ann")
    assert [e["by"] for e in journal.read("sam")] == ["baseline", "tagger", "person:ann"]
    assert len([e for e in store.get("sam").entries if e.kind == "interest"]) == 2  # merged

    # undoing the merge brings both items back with their history, and keeps the later edit
    store.undo("sam", 2)
    after = store.get("sam")
    trex, lava = after.find("T-Rex"), after.find("lava")
    assert trex is not None and trex.name == "T-Rex" and after.find("Tyrannosaurus") is not trex
    assert any({k.a, k.b} == {trex.id, lava.id} for k in after.links)  # its link came back
    assert after.get(goal.id).notes == "halves"
    assert journal.read("sam")[-1]["by"] == "admin"

    # an undo never silently wipes a newer change to the same items
    with pytest.raises(JournalError):
        store.undo("sam", 2)

    # the journal alone rebuilds today's map
    assert replay(journal.read("sam")) == _to_dict(store.get("sam"))


def test_review_regressions_undo_is_smart_and_safe_and_the_journal_stays_true(tmp_path):
    from lerni.student.interests import add_interest, not_the_same, remove, rename

    store, journal = MapStore(tmp_path), MapJournal(tmp_path)
    tag = lambda tags, text, day: lambda m: apply_tags(m, parse_tags(tags), text, day)  # noqa: E731
    d = [date(2026, 10, day) for day in range(1, 8)]

    # a merge undone days later: the kept item kept being talked about, and keeps those days
    store.change("sam", tag({"new_interests": ["T-Rex", "Tyrannosaurus"]}, "T-Rex, Tyrannosaurus",
                            d[0]), by="tagger")
    store.change("sam", tag({"same_as": [["T-Rex", "Tyrannosaurus"]]}, "a T-Rex!", d[1]),
                 by="tagger")
    merge = journal.read("sam")[-1]["n"]
    store.change("sam", tag({"about": ["Tyrannosaurus"]}, "x", d[3]), by="tagger")
    store.undo("sam", merge)
    m = store.get("sam")
    assert m.find("T-Rex").name == "T-Rex" and "2026-10-04" in m.find("Tyrannosaurus").days

    # an undo that would break the map's rules (two items with one name) is refused
    store.change("sam", lambda m: add_interest(m, "dinos"), by="person:ann")
    store.change("sam", lambda m: rename(m, m.find("dinos").id, "volcanoes"), by="person:ann")
    renamed = journal.read("sam")[-1]["n"]
    store.change("sam", lambda m: add_interest(m, "dinos"), by="person:ann")
    with pytest.raises(JournalError):
        store.undo("sam", renamed)

    # rewinding never reuses an id, and every undo counts as an edit (a stale tagger result waits)
    edits, next_id = store.get("sam").edits, store.get("sam").next_id
    store.rebuild("sam", upto=2)
    assert store.get("sam").next_id >= next_id and store.get("sam").edits > edits

    # a link mentioned again moves to the end without the whole list order in its line
    store.change("sam", tag({"new_interests": ["cars", "lava"], "related": [["cars", "lava"]]},
                            "cars and lava", d[4]), by="tagger")
    store.change("sam", tag({"related": [["cars", "lava"]]}, "x", d[5]), by="tagger")
    assert "link_order" not in journal.read("sam")[-1]["changes"]

    # a change made outside the journal (a rollback) starts a new baseline, so it stays true
    raw = json.loads((tmp_path / "maps" / "sam.json").read_text())
    raw["entries"][0]["mentions"] += 5
    (tmp_path / "maps" / "sam.json").write_text(json.dumps(raw))
    store.change("sam", tag({"about": ["cars"]}, "x", d[6]), by="tagger")
    assert store.rebuild("sam")

    # a name a person split off survives its near-name being removed, and the journal agrees
    store.change("sam", lambda m: add_interest(m, "shark"), by="person:ann")
    store.change("sam", tag({"about": ["sharks"]}, "sharks!", d[6]), by="tagger")  # another name
    store.change("sam", lambda m: not_the_same(m, m.find("shark").id, "sharks"), by="person:ann")
    store.change("sam", tag({"new_interests": ["sharks"]}, "sharks", d[6]), by="tagger")
    store.change("sam", lambda m: remove(m, m.find("shark").id), by="person:ann")
    assert store.get("sam").find("sharks") is not None and store.rebuild("sam")


def test_undo_stops_at_a_map_replaced_since(tmp_path):
    store, journal = MapStore(tmp_path), MapJournal(tmp_path)
    goal = store.change("sam", lambda m: add_goal(m, "Fractions"), by="person:ann")
    store.change("sam", lambda m: set_notes(m, goal.id, "halves"), by="person:ann")  # change 3
    path = tmp_path / "maps" / "sam.json"  # a restore puts other notes back
    saved = json.loads(path.read_text())
    saved["entries"][0]["notes"] = "quarters"
    path.write_text(json.dumps(saved))
    store.change("sam", lambda m: add_goal(m, "Saturn"), by="person:ann")  # a baseline, then 5
    assert journal.read("sam")[-2]["by"] == "baseline"
    with pytest.raises(JournalError, match="replaced"):  # never writes "" over "quarters"
        store.undo("sam", 3)
    assert store.get("sam").get(goal.id).notes == "quarters"
    store.rebuild("sam", upto=2)  # going back before it still works
    assert store.get("sam").get(goal.id).notes == ""
