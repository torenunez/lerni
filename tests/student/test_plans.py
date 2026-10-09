"""Learning plans: the store and the educator view's plan handlers."""


import pytest

from lerni.student.plans import (
    LearningPlan,
    PlanError,
    PlannedActivity,
    PlanStore,
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




@pytest.mark.parametrize("bad_id", ["../escape", "Cars", "a/b", ""])
def test_ids_cannot_escape_the_folder(store, bad_id):
    with pytest.raises(PlanError):
        store.get(bad_id)








def test_examples_seed_once_and_only_into_an_empty_store(store):
    assert store.seed_if_empty() == 2
    ids = {p.plan_id for p in store.list_plans()}
    assert ids == {"example-cars", "example-sharks"}
    assert all(p.is_example for p in store.list_plans())
    assert store.seed_if_empty() == 0






# --- educator view handlers (no browser needed) ---

gradio = pytest.importorskip("gradio")
