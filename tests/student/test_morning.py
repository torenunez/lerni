"""The morning plan (v3.44): connections to try, goal suggestions, and goal steps."""

import random
from datetime import date, timedelta

from lerni.student.concepts import ConceptStore
from lerni.student.interests import MapStore, add_goal, add_interest, map_block, remove
from lerni.student.morning import SuggestionStore, decide, run_morning
from lerni.student.race import deal, quiz_input

TODAY = date(2026, 11, 11)


class Planner:
    """A fake morning call: returns what it's given and keeps the prompts."""

    def __init__(self, raw):
        self.raw, self.prompts = raw, []

    def write(self, system, prompt, schema=None):
        self.prompts.append(prompt)
        return self.raw


def steps(n):
    return [f"step {k}" for k in range(n)]


def setup(tmp_path):
    maps, concepts, store = MapStore(tmp_path), ConceptStore(tmp_path), SuggestionStore(tmp_path)
    ids = {}

    def fill(m):
        ids["Fractions"] = add_goal(m, "Fractions", "halves and quarters").id
        ids["Nouns"] = add_goal(m, "Nouns").id
        for name in ("trains", "baking", "dogs", "music", "volcanoes"):
            add_interest(m, name)
        remove(m, add_interest(m, "spiders").id)

    maps.change("sam", fill)
    month = TODAY - timedelta(days=10)
    concepts.add("sam", [(ids["Fractions"], "Fractions", f"idea {n}") for n in range(12)], month)
    return maps, concepts, store, ids


RAW = {
    "connections": [
        {"interest": "trains", "goal": "Fractions", "hook": "a train's seats shared out equally"},
        {"interest": "baking", "goal": "Nouns", "hook": "naming everything in a kitchen"},
        {"interest": "dogs", "goal": "Fractions", "hook": "half a bowl of food"},
        {"interest": "music", "goal": "Nouns", "hook": "the names of instruments"},
        {"interest": "volcanoes", "goal": "Fractions", "hook": "a quarter of a mountain"},
        {"interest": "spiders", "goal": "Nouns", "hook": "eight legs"},  # set aside
        {"interest": "robots", "goal": "Nouns", "hook": "parts of a robot"},  # not on the map
    ],
    "goal_suggestions": [{"goal": "Fractions", "notes": "halves and quarters, then thirds"}],
    "steps": [{"goal": "Fractions", "steps": steps(10)}],
}


def test_the_morning_plan_suggests_and_a_tick_steers_races_and_chat(tmp_path, capsys):
    maps, concepts, store, ids = setup(tmp_path)
    before = maps.get("sam")
    planner = Planner(RAW)
    run_morning("sam", planner, maps, concepts, store, TODAY)
    assert maps.get("sam") == before  # the morning only proposes: the map never changes
    assert "Fractions" in planner.prompts[0] and "running out" in planner.prompts[0]
    waiting = store.waiting("sam")
    assert len(waiting) == 6  # 5 connections and a goal suggestion
    assert not any("spiders" in w or "robots" in w for w in waiting)  # set aside, off the map
    out = capsys.readouterr().out
    assert "Morning plan: 5 connections, 1 goal suggestion, 1 goal's steps" in out
    # the educator ticks a connection and the goal suggestion: Use ticked
    trains = next(w for w in waiting if w.startswith("trains → Fractions"))
    goal = next(w for w in waiting if "then thirds" in w)
    decide(store, maps, "sam", [trains, goal], use=True, today=TODAY)
    m = maps.get("sam")
    assert m.find("Fractions").notes == "halves and quarters, then thirds"  # their own change
    targets = store.in_use("sam", m, TODAY)
    assert targets[ids["Fractions"]] == ("trains", "a train's seats shared out equally")
    slots = deal(m, ["Fractions", "Nouns"], {}, random.Random(1), targets=targets)
    assert next(s for s in slots if s.goal == "Fractions").setting == "trains"  # it leads
    prompt = quiz_input(m, TODAY, True, goals=["Fractions"], plan=slots, connections=targets)
    assert "connection to try: trains (a train's seats shared out equally)" in prompt
    assert "trains → Fractions: a train's seats shared out equally" in map_block(
        m, TODAY, connections=targets)  # Chat may use it as an opening
    # Not these, and a note from the Tell Lerni box, reach tomorrow's call
    dogs = next(w for w in store.waiting("sam") if w.startswith("dogs"))
    decide(store, maps, "sam", [dogs], use=False, today=TODAY)
    store.add_note("sam", "fewer train ideas, more music", TODAY)
    assert dogs not in store.waiting("sam")
    run_morning("sam", planner, maps, concepts, store, TODAY + timedelta(days=1))
    tomorrow = planner.prompts[-1]
    assert "dogs → Fractions" in tomorrow.split("Dismissed")[1]  # never suggested again
    assert "fewer train ideas, more music" in tomorrow


def test_goal_steps_reach_races_until_asked(tmp_path):
    maps, concepts, store, ids = setup(tmp_path)
    run_morning("sam", Planner(RAW), maps, concepts, store, TODAY)
    m = maps.get("sam")
    asked = concepts.asked_by_goal("sam", TODAY)
    left = store.untried_steps("sam", m, asked)
    assert left[ids["Fractions"]] == steps(10)
    concepts.add("sam", [(ids["Fractions"], "Fractions", "step 0")], TODAY)  # a race asked one
    left = store.untried_steps("sam", m, concepts.asked_by_goal("sam", TODAY))
    assert "step 0" not in left[ids["Fractions"]] and len(left[ids["Fractions"]]) == 9
    prompt = quiz_input(m, TODAY, True, goals=["Fractions"], steps=left)
    assert "steps not tried yet: step 1; step 2" in prompt
    # steps written for older notes are dropped once the notes change
    maps.change("sam", lambda m: setattr(m.find("Fractions"), "notes", "thirds now") or None)
    assert store.untried_steps("sam", maps.get("sam"), {}) == {}


def test_a_note_from_tell_lerni_is_a_proposal_never_a_map_change(tmp_path):
    from lerni.student.educator_agent import apply_educator_proposals, parse_educator_proposals

    maps, _, _, _ = setup(tmp_path)
    m = maps.get("sam")
    block = '```proposals\n{"proposals": [{"kind": "note", "notes": "fewer train ideas"}]}\n```'
    found = parse_educator_proposals(block, m)
    assert [p.label for p in found] == ["📝 Note for suggestions: fewer train ideas"]
    assert apply_educator_proposals(m, found) == (0, [])  # kept for the morning, not the map


def test_review_long_steps_used_goals_and_stale_waits(tmp_path):
    # review (v3.44): long steps never counted as tried; a used goal suggestion came back daily;
    # a waiting connection whose interest was set aside stayed for good
    from lerni.student.concepts import MAX_CONCEPT
    from lerni.student.morning import untried_steps_held

    maps, concepts, store, ids = setup(tmp_path)
    long_step = "split a pizza into equal halves for two hungry friends"  # over 40 characters
    raw = {**RAW, "steps": [{"goal": "Fractions", "steps": [long_step, *steps(9)]}]}
    run_morning("sam", Planner(raw), maps, concepts, store, TODAY)
    concepts.add("sam", [(ids["Fractions"], "Fractions", long_step[:MAX_CONCEPT])], TODAY)
    left = store.untried_steps("sam", maps.get("sam"), concepts.asked_by_goal("sam", TODAY))
    assert long_step not in left[ids["Fractions"]]  # a race's cut label counts
    # a step held for a later race isn't offered again to the next set
    held = untried_steps_held(store, "sam", maps.get("sam"), {}, [(ids["Fractions"], "step 0")])
    assert "step 0" not in held[ids["Fractions"]]
    goal = next(w for w in store.waiting("sam") if "then thirds" in w)
    decide(store, maps, "sam", [goal], use=True, today=TODAY)
    maps.change("sam", lambda m: remove(m, m.find("trains").id))  # set aside while waiting
    planner = Planner(RAW)
    run_morning("sam", planner, maps, concepts, store, TODAY + timedelta(days=1))
    assert "running out" not in planner.prompts[0].split("Interests")[0]  # used: not again yet
    assert not any(w.startswith("trains") for w in store.waiting("sam"))  # gone with it
    later = TODAY + timedelta(days=20)  # waiting this long: it expires
    run_morning("sam", Planner({"connections": [], "goal_suggestions": [], "steps": []}), maps,
                concepts, store, later)
    assert store.waiting("sam") == []
