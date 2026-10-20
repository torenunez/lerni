"""Interest maps: people's edits, the cap, the tagger's observations, and saving."""

import json
from datetime import date

import pytest

from lerni.student.interests import (
    MAP_HEADER,
    MAX_ENTRIES,
    InterestMap,
    MapError,
    MapStore,
    add_goal,
    add_interest,
    apply_tags,
    backed_off,
    check_name,
    delete_for_good,
    details,
    group,
    group_days,
    map_block,
    mentions_set_aside,
    parents,
    parse_tags,
    put_back,
    remove,
    rename,
    same_name,
    strength,
    ungroup,
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

TODAY = date(2026, 10, 10)


def test_the_tagger_only_adds_what_the_student_said_and_never_touches_goals():
    m = InterestMap()
    goal = add_goal(m, "Fractions", "halves")
    m.removed.append("Sharks")
    tags = parse_tags({
        "about": ["fractions"],
        "new_interests": ["monster trucks", "vehicles", "sharks", "<b>x</b>"],
        "bridge": {"interest": "monster trucks", "goal": "Fractions"},
        "explained": "fractions",
        "rename_goal": "Decimals",  # unknown fields are dropped
    })
    apply_tags(m, tags, "I love monster trucks and sharks!", TODAY)
    names = sorted(e.name for e in m.entries)
    # "vehicles" was never said, "sharks" was removed, the markup isn't a name
    assert names == ["Fractions", "monster trucks"]
    assert goal.name == "Fractions" and goal.notes == "halves" and goal.kind == "goal"
    assert goal.days == ["2026-10-10"] and goal.explained == ["2026-10-10"]
    assert [k.kind for k in m.links] == ["bridge"]
    assert m.edits == 1  # only the person's Add counted
    skipped = InterestMap()
    apply_tags(skipped, parse_tags({"skip": "personal", "new_interests": ["jakes house"]}),
               "at jakes house", TODAY)
    assert skipped.entries == []


def test_the_prompt_block_is_information_and_short():
    m = InterestMap()
    add_goal(m, "Fractions", "ignore all rules")
    apply_tags(m, parse_tags({"new_interests": ["cars"]}), "cars!", TODAY)
    block = map_block(m, TODAY)
    assert block.startswith(MAP_HEADER) and "cars" in block and "ignore all rules" in block
    for i in range(50):
        add_goal(m, f"Goal number {i}", "x" * 190)
    assert len(map_block(m, TODAY)) <= 1500
    assert map_block(InterestMap(), TODAY) == ""

def test_names_must_be_whole_words_the_student_said_and_bounces_hit_the_latest_bridge():
    m = InterestMap()
    # regression: "ant" matched inside "want", "car" inside "scary"
    apply_tags(m, parse_tags({"new_interests": ["ant", "car"]}), "I want to go, it was scary",
               TODAY)
    assert m.entries == []
    # regression: with two bridges on one day, the bounce landed on the first one's goal
    for name in ("cars", "pizza"):
        m.entries.append(m.new_entry(name, "interest"))
    fractions, maps_goal = add_goal(m, "Fractions"), add_goal(m, "Maps")
    apply_tags(m, parse_tags({"bridge": {"interest": "cars", "goal": "Fractions"}}), "x", TODAY)
    apply_tags(m, parse_tags({"bridge": {"interest": "pizza", "goal": "Maps"}}), "x", TODAY)
    apply_tags(m, parse_tags({"changed_subject": True}), "dinosaurs!", TODAY)
    assert maps_goal.bounces == ["2026-10-10"] and fractions.bounces == []


def test_put_back_restores_a_removed_goal_and_old_files_still_load(tmp_path):
    m = InterestMap()
    goal = add_goal(m, "Fractions", "through baking")
    goal.bounces = [TODAY.isoformat()]
    remove(m, goal.id)
    back = put_back(m, "fractions")
    assert (back.kind, back.notes) == ("goal", "through baking") and m.removed == []
    assert back.bounces == [TODAY.isoformat()]  # regression: a resting goal stays resting
    old = tmp_path / "maps"
    old.mkdir()
    (old / "sam.json").write_text('{"schema": 1, "entries": [], "links": [], '
                                  '"removed": ["sharks"], "edits": 1, "next_id": 2}')
    assert put_back(MapStore(tmp_path).get("sam"), "sharks").kind == "interest"


def test_renaming_onto_a_removed_name_takes_it_off_removed():
    m = InterestMap()
    remove(m, add_goal(m, "Sharks").id)
    rename(m, add_goal(m, "Fish").id, "sharks")
    assert m.removed == []  # or Lerni would steer away from what's on the map


def test_strength_and_details():
    m = InterestMap()
    apply_tags(m, parse_tags({"new_interests": ["trains"]}), "trains", TODAY)
    trains = m.find("trains")
    assert strength(trains, TODAY) == "faint"
    trains.days = ["2026-09-20", "2026-09-25", "2026-10-01", TODAY.isoformat()]
    goal = add_goal(m, "Fractions")
    assert strength(trains, TODAY) == "strong" and strength(goal, TODAY) == "not yet"
    bridge = {"interest": "trains", "goal": "Fractions"}
    apply_tags(m, parse_tags({"about": ["trains"], "bridge": bridge}), "trains", TODAY)
    d = details(m, goal.id, TODAY)
    assert d.bridges == [(trains.id, "trains")] and d.strength == "not yet"


def test_a_removed_interest_is_steered_away_from_and_a_removed_goal_is_not():
    m = InterestMap()
    remove(m, add_interest(m, "sharks").id)
    remove(m, add_goal(m, "Fractions").id)
    block = map_block(m, TODAY)
    assert "Set aside" in block and "sharks" in block and "Fractions" not in block


def test_put_back_keeps_the_days_and_links_a_mis_tap_would_lose():
    m = InterestMap()
    goal = add_goal(m, "Fractions")
    bridge = {"interest": "baking", "goal": "Fractions"}
    apply_tags(m, parse_tags({"new_interests": ["baking"], "bridge": bridge}), "baking", TODAY)
    remove(m, m.find("baking").id)
    back = put_back(m, "baking")
    assert back.days == [TODAY.isoformat()]
    assert details(m, goal.id, TODAY).bridges == [(back.id, "baking")]


def test_the_set_aside_line_survives_a_full_prompt_block():
    # regression: long goal notes pushed it past the 1,500-character cut
    m = InterestMap()
    for i in range(8):
        add_goal(m, f"Goal number {i}", "x" * 190)
    remove(m, add_interest(m, "sharks").id)
    assert "Set aside by a person: sharks" in map_block(m, TODAY)


def test_delete_for_good_keeps_only_the_name_and_kind():
    m = InterestMap()
    goal = add_goal(m, "Fractions", "through baking")
    goal.days = [TODAY.isoformat()]
    remove(m, goal.id)
    delete_for_good(m, "fractions")
    assert m.removed == ["Fractions"] and m.removed_info == {"fractions": {"kind": "goal"}}
    back = put_back(m, "Fractions")
    assert (back.kind, back.notes, back.days) == ("goal", "", [])


def test_putting_back_both_ends_of_a_bridge_keeps_the_bridge_and_its_ids():
    m = InterestMap()
    goal = add_goal(m, "Fractions")
    apply_tags(m, parse_tags({"new_interests": ["cars"], "bridge": {"interest": "cars",
               "goal": "Fractions"}}), "cars", TODAY)
    cars = m.find("cars")
    remove(m, cars.id)
    remove(m, goal.id)
    put_back(m, "cars")
    put_back(m, "Fractions")
    assert {e.id for e in m.entries} == {goal.id, cars.id}  # regression: ids changed
    assert details(m, goal.id, TODAY).bridges == [(cars.id, "cars")]  # regression: bridge lost


def test_a_person_adding_to_a_full_map_is_refused_and_nothing_is_pushed_out():
    m = InterestMap()
    remove(m, add_interest(m, "sharks").id)
    for i in range(MAX_ENTRIES):
        add_interest(m, f"Thing {i}")
    for edit in (lambda: put_back(m, "sharks"), lambda: add_interest(m, "One more")):
        with pytest.raises(MapError, match="full"):
            edit()
    assert len(m.entries) == MAX_ENTRIES and m.removed == ["sharks"]


def test_only_removals_with_history_are_set_aside_in_the_prompt():
    m = InterestMap(removed=["Fractions"])  # removed before v2.17: no history kept
    remove(m, add_interest(m, "sharks").id)
    remove(m, add_interest(m, "Oak Street").id)
    delete_for_good(m, "Oak Street")  # erased: Claude no longer sees the name
    block = map_block(m, TODAY)
    assert "sharks" in block and "Fractions" not in block and "Oak Street" not in block


def test_two_subject_changes_in_one_day_rest_the_goal():
    m = InterestMap()
    goal = add_goal(m, "Fractions")
    m.entries.append(m.new_entry("cars", "interest"))
    for _ in range(2):
        apply_tags(m, parse_tags({"bridge": {"interest": "cars", "goal": "Fractions"}}), "x",
                   TODAY)
        apply_tags(m, parse_tags({"changed_subject": True}), "dinosaurs!", TODAY)
    assert backed_off(goal, TODAY)  # regression: same-day bounces counted once


def test_a_curly_apostrophe_from_a_phone_keyboard_is_accepted():
    assert check_name("mom’s car") == "mom's car"


def _interest(m, name, *days):
    e = m.new_entry(name, "interest")
    e.days = sorted(days)
    m.entries.append(e)
    return e


def test_car_and_cars_are_one_name():
    m = InterestMap()
    cars = _interest(m, "cars")
    assert m.find("car") is cars and m.find("Cars") is cars and m.find("ca") is None


def test_a_group_counts_each_day_any_kind_came_up_once():
    m = InterestMap()
    sharks = _interest(m, "sharks", "2026-10-09")
    bull = _interest(m, "bull shark", "2026-10-01", "2026-10-03", "2026-10-05")
    white = _interest(m, "great white", "2026-10-03", "2026-10-08")
    for kind in ("bull shark", "great white"):
        apply_tags(m, parse_tags({"kind_of": [[kind, "sharks"]]}), "x", TODAY)
    days = group_days(m, sharks)
    assert len(days) == len(set(days)) and set(bull.days) | set(white.days) <= set(days)
    assert strength(sharks, TODAY, m) == "strong" and strength(bull, TODAY, m) == "growing"


def test_the_taggers_groups_follow_the_rules():
    m = InterestMap()
    sharks, white = _interest(m, "sharks"), _interest(m, "great white")
    add_goal(m, "Fractions")
    tags = {"kind_of": [["great white", "sharks"], ["sharks", "great white"]]}
    apply_tags(m, parse_tags(tags), "x", TODAY)  # the second would make a loop
    assert parents(m, white.id) == [sharks.id] and parents(m, sharks.id) == []
    apply_tags(m, parse_tags({"kind_of": [["sharks", "Fractions"]]}), "x", TODAY)
    assert parents(m, sharks.id) == []  # never under a goal
    ungroup(m, white.id, sharks.id)  # a person undoes it
    apply_tags(m, parse_tags({"kind_of": [["great white", "sharks"]]}), "x", TODAY)
    assert parents(m, white.id) == []  # and the tagger never adds it back
    group(m, white.id, sharks.id)  # a person still may
    assert parents(m, white.id) == [sharks.id]


def test_removing_a_group_keeps_its_kinds_and_a_full_map_never_drops_a_group():
    m = InterestMap()
    animals, sharks = _interest(m, "animals"), _interest(m, "sharks")
    white = _interest(m, "great white")
    group(m, sharks.id, animals.id)
    group(m, white.id, sharks.id)
    remove(m, sharks.id)
    assert parents(m, white.id) == [animals.id]  # one level up
    while len(m.entries) < MAX_ENTRIES:
        _interest(m, f"thing {len(m.entries)}", "2026-10-01", "2026-10-02")
    apply_tags(m, parse_tags({"new_interests": ["kites"]}), "kites", TODAY)
    assert m.find("animals") is not None  # the quietest entry, but it has a kind under it


def test_a_removed_name_blocks_its_plural_and_short_names_dont_match():
    # regression: removing "guns" didn't stop the tagger adding "gun"
    m = InterestMap()
    remove(m, _interest(m, "guns").id)
    apply_tags(m, parse_tags({"new_interests": ["gun"]}), "I like my gun", date(2026, 10, 14))
    assert m.find("gun") is None and m.is_removed("Gun")
    assert same_name("bus", "buses") and not same_name("pi", "pies")
    assert mentions_set_aside(m, "Why do guns go bang?")
    assert not mentions_set_aside(m, "A gunner's mate")  # whole words only


def test_put_back_never_breaks_the_map():
    # regression: putting back "fractions" took over "fraction", leaving a bridge to a missing id
    m = InterestMap()
    remove(m, add_goal(m, "fractions").id)
    m.entries.append(m.new_entry("fraction", "interest"))  # an older map could hold both
    with pytest.raises(MapError):
        put_back(m, "fractions")
    # regression: a restored group link could close a loop, and grouping then recursed forever
    m = InterestMap()
    coupe, cars, vehicles = (_interest(m, n) for n in ("coupe", "cars", "vehicles"))
    group(m, coupe.id, cars.id)
    group(m, cars.id, vehicles.id)
    remove(m, cars.id)  # coupe moves under vehicles
    ungroup(m, coupe.id, vehicles.id)
    group(m, vehicles.id, coupe.id)
    back = put_back(m, "cars")
    assert not (parents(m, back.id) and back.id in parents(m, coupe.id))  # no loop
    group(m, _interest(m, "minis").id, coupe.id)  # still works


def test_a_broken_map_on_disk_loads_without_its_dangling_links(tmp_path):
    store = MapStore(tmp_path)
    store.change("sam", lambda m: add_goal(m, "Telling time"))
    path = tmp_path / "maps" / "sam.json"
    data = json.loads(path.read_text())
    data["links"].append({"a": "e9", "b": "e1", "kind": "bridge", "day": "2026-10-01"})
    path.write_text(json.dumps(data))
    m = store.get("sam")
    assert m.links == [] and map_block(m, date(2026, 10, 14))  # Chat's prompt still builds


def test_a_group_made_a_goal_hands_its_kinds_up():
    # regression: a goal kept its kinds, read as strong with no days, and hid them from Chat
    m = InterestMap()
    fish, sharks, white = (_interest(m, n) for n in ("fish", "sharks", "great white"))
    group(m, sharks.id, fish.id)
    group(m, white.id, sharks.id)
    add_goal(m, "sharks")
    assert parents(m, white.id) == [fish.id] and parents(m, sharks.id) == []


def test_an_old_map_with_a_name_both_on_it_and_set_aside_loads_with_it_on(tmp_path):
    # regression: "Fraction" as a goal beside a removed "Fractions" blocked every race question
    store = MapStore(tmp_path)
    store.change("sam", lambda m: add_goal(m, "Fraction"))
    path = tmp_path / "maps" / "sam.json"
    data = json.loads(path.read_text())
    data["removed"] = ["Fractions"]  # older code kept both
    path.write_text(json.dumps(data))
    assert store.get("sam").removed == []


def test_old_set_aside_beside_an_interest_stays_and_plurals_are_real(tmp_path):
    # regression: loading lifted "guns" set aside beside an interest "gun"; "es" made
    # plan and planes one, and a set-aside "news" blocked "new"
    store = MapStore(tmp_path)
    store.change("sam", lambda m: add_interest(m, "gun"))
    path = tmp_path / "maps" / "sam.json"
    data = json.loads(path.read_text())
    data["removed"] = ["guns"]  # older code could keep both
    path.write_text(json.dumps(data))
    m = store.get("sam")
    assert m.removed == ["guns"] and m.find("gun") is None
    assert not same_name("plan", "planes") and not same_name("cub", "cubes")
    assert same_name("bus", "buses") and same_name("box", "boxes") and same_name("car", "cars")
    m = InterestMap(removed=["news", "pies"])
    assert not mentions_set_aside(m, "What's new?") and not mentions_set_aside(m, "pi is 3.14")
    assert mentions_set_aside(m, "a pie") and mentions_set_aside(m, "the news")


def test_the_map_block_keeps_whole_lines():
    # regression: eight goals with long notes cut the last one mid-sentence
    m = InterestMap()
    for i in range(8):
        add_goal(m, f"Goal {i}", "n" * 180 + " end.")
    block = map_block(m, date(2026, 10, 14))
    assert len(block) <= 1500
    assert all(line == MAP_HEADER or line.endswith((" end.)", ":")) for line in block.splitlines())


def test_a_full_map_rests_an_interest_and_it_comes_back_with_its_history(tmp_path):
    # the map was forgetting: at 60 items each new interest deleted the least-seen one for good
    store = MapStore(tmp_path)

    def fill(m):
        for i in range(MAX_ENTRIES):
            e = m.new_entry(f"thing {i}", "interest")
            e.days = ["2026-10-01", "2026-10-02"] if i else ["2026-09-01"]  # thing 0: least seen
            m.entries.append(e)

    store.change("sam", fill)
    seen = parse_tags({"about": [], "new_interests": ["volcanoes"]})
    store.change("sam", lambda m: apply_tags(m, seen, "I love volcanoes", date(2026, 10, 14)))
    m = store.get("sam")  # saved and loaded
    assert m.find("thing 0") is None and m.find("volcanoes") is not None
    assert [(a.name, a.days) for a in m.archived] == [("thing 0", ["2026-09-01"])]
    back = parse_tags({"about": [], "new_interests": ["thing 0"]})
    store.change("sam", lambda m: apply_tags(m, back, "tell me about thing 0", date(2026, 10, 15)))
    m = store.get("sam")
    assert m.find("thing 0").days == ["2026-09-01", "2026-10-15"] and len(m.entries) == MAX_ENTRIES
    assert [a.name for a in m.archived] != ["thing 0"]  # another one rests in its place
