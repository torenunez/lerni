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
