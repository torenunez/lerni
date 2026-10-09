"""Interest maps: people's edits, the cap, and saving."""

import pytest

from lerni.student.interests import (
    MAX_ENTRIES,
    InterestMap,
    MapError,
    MapStore,
    add_goal,
    remove,
    rename,
)


def test_goals_are_added_renamed_removed_and_saved(tmp_path):
    store = MapStore(tmp_path)
    goal = store.change("sam", lambda m: add_goal(m, "Fractions", "halves and quarters"))
    store.change("sam", lambda m: rename(m, goal.id, "Fractions and decimals"))
    m = store.get("sam")
    assert m.find("fractions and DECIMALS").notes == "halves and quarters"
    assert m.edits == 2  # every person's edit counts, so late tagger results can tell
    store.change("sam", lambda m: remove(m, goal.id))
    m = store.get("sam")
    assert m.entries == [] and m.removed == ["Fractions and decimals"]
    with pytest.raises(MapError):
        store.change("sam", lambda m: add_goal(m, "<b>bold</b>"))  # only plain names


def test_a_goal_takes_over_an_interest_and_a_full_map_says_so():
    m = InterestMap()
    m.entries.append(m.new_entry("Cars", "interest"))
    m.entries[0].days = ["2026-10-01"]
    goal = add_goal(m, "cars")  # one name, one entry: it keeps its days
    assert goal.kind == "goal" and goal.days == ["2026-10-01"] and len(m.entries) == 1
    for i in range(MAX_ENTRIES - 1):
        add_goal(m, f"Goal {i}")
    with pytest.raises(MapError):
        add_goal(m, "One too many")  # goals are never dropped to make room
