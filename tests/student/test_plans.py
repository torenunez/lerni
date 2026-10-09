"""Learning plans: the store and the educator view's plan handlers."""

import json

import pytest

from lerni.student.plans import (
    ActivityCard,
    LearningPlan,
    PlanError,
    PlannedActivity,
    PlanStore,
    drafting_notes,
    plan_from_dict,
    plan_to_dict,
)


@pytest.fixture
def store(tmp_path):
    return PlanStore(tmp_path)


def sample_plan() -> LearningPlan:
    return LearningPlan(
        plan_id="cars-abc123",
        interest="Cars",
        goal="Speed and acceleration",
        activities=(
            PlannedActivity("Cars", "Distance", "Concrete", "Which route is longer?"),
            PlannedActivity("Distance", "Time", "Next idea", "Which trip took longer?"),
        ),
    )


def test_round_trip(store):
    saved = store.save(sample_plan())
    assert store.get("cars-abc123") == saved
    assert [p.plan_id for p in store.list_plans()] == ["cars-abc123"]


def test_unknown_keys_are_rejected():
    data = plan_to_dict(sample_plan())
    data["student_name"] = "x"
    with pytest.raises(PlanError):
        plan_from_dict(data)


@pytest.mark.parametrize("bad_id", ["../escape", "Cars", "a/b", ""])
def test_ids_cannot_escape_the_folder(store, bad_id):
    with pytest.raises(PlanError):
        store.get(bad_id)


def test_save_is_atomic_and_leaves_no_temp_files(store):
    store.save(sample_plan())
    names = sorted(p.name for p in store.root.iterdir())
    assert names == ["cars-abc123.json"]
    json.loads((store.root / "cars-abc123.json").read_text())


def test_archive_moves_instead_of_deleting(store):
    store.save(sample_plan())
    store.archive("cars-abc123")
    assert store.list_plans() == []
    assert len(list(store.archive_dir.glob("cars-abc123-*.json"))) == 1


def test_text_limits_are_enforced(store):
    with pytest.raises(PlanError):
        store.save(LearningPlan(plan_id="long-abc123", goal="x" * 501))


def test_examples_seed_once_and_only_into_an_empty_store(store):
    assert store.seed_if_empty() == 2
    ids = {p.plan_id for p in store.list_plans()}
    assert ids == {"example-cars", "example-sharks"}
    assert all(p.is_example for p in store.list_plans())
    assert store.seed_if_empty() == 0


def test_the_example_car_card_is_complete(store):
    store.seed_if_empty()
    card = store.get("example-cars").activities[3].card
    assert drafting_notes(card) == []
    assert card.answer in card.choices


def test_drafting_notes_list_whats_missing():
    assert drafting_notes(None) == ["No activity card yet."]
    notes = drafting_notes(ActivityCard(question="Q?", choices=("A", "B"), answer="C"))
    assert "The right answer must be one of the choices." in notes
    assert "Add at least one hint." in notes


# --- educator view handlers (no browser needed) ---

gradio = pytest.importorskip("gradio")
from lerni.student.web import educator  # noqa: E402


def test_saving_rows_keeps_cards_with_their_activity_when_reordered(store):
    store.seed_if_empty()
    plan = store.get("example-cars")
    rows = educator.plan_rows(plan)
    rows.reverse()
    saved, message = educator.save_plan(store, plan.plan_id, "Cars", plan.goal, rows)
    assert saved.activities[0].card == plan.activities[3].card
    assert saved.activities[0].idea == "Average acceleration"
    assert not saved.is_example
    assert message == "Saved 4 activities."


def test_blank_rows_are_dropped(store):
    plan = educator.new_plan(store)
    rows = [["Cars", "Speed", "Why", "Q?"], ["", "", "", ""], [None, None, None, None]]
    saved, _ = educator.save_plan(store, plan.plan_id, "Cars", "Goal", rows)
    assert len(saved.activities) == 1


def test_copy_makes_an_editable_plan(store):
    store.seed_if_empty()
    copy = educator.copy_plan(store, "example-sharks")
    assert copy.plan_id != "example-sharks"
    assert copy.interest == "Sharks (copy)"
    assert not copy.is_example


def test_save_card_returns_whats_still_missing(store):
    plan = educator.new_plan(store)
    educator.save_plan(store, plan.plan_id, "Cars", "Goal", [["Cars", "Speed", "", ""]])
    values = educator.card_fields(store.get(plan.plan_id), 0)
    values["question"] = "Which car is faster?"
    values["choices"] = ["Car A", "Car B", ""]
    values["answer"] = "Car A"
    saved, notes = educator.save_card(store, plan.plan_id, 0, values)
    assert saved.activities[0].card.question == "Which car is faster?"
    assert "Add at least one hint." in notes
    assert "Add two or three choices." not in notes
