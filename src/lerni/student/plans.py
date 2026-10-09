"""Learning plans the educator writes in the educator view.

A plan is curriculum, not student data: an interest, a goal, and a few
activities in teaching order, each optionally with an activity card. Plans are
stored as one JSON file each, outside the repository and separate from the
admin tool's database. Standard library only.

Teaching order is the order of ``LearningPlan.activities``; it never comes
from how ideas relate (CLAUDE.md rule 6).
"""

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import asdict, dataclass, field, replace
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

from lerni.student.jsonfiles import write_json_atomic
from lerni.student.students import (  # noqa: F401 - until step 10
    DATA_ENV,
    default_data_dir,
)

SCHEMA_VERSION = 1
MAX_TEXT = 500
MAX_ACTIVITIES = 12
MAX_EXPLANATION_SCREENS = 3
MAX_CHOICES = 3
MAX_HINTS = 2
PLAN_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEED_PACKAGE = "lerni.student.seed"


class PlanError(ValueError):
    """A plan or plan file is invalid."""


@dataclass(frozen=True, slots=True)
class ActivityCard:
    """What the student will see in one activity, written by the educator.

    Every field may be blank while the educator is drafting; see
    :func:`drafting_notes` for what is still missing.
    """

    explanation: tuple[str, ...] = ()
    question: str = ""
    choices: tuple[str, ...] = ()
    answer: str = ""
    hints: tuple[str, ...] = ()
    right_text: str = ""
    hints_run_out_text: str = ""
    picture_idea: str = ""
    picture_description: str = ""
    how_youll_know: str = ""
    sources: str = ""
    avoid: str = ""


@dataclass(frozen=True, slots=True)
class PlannedActivity:
    """One row of a learning plan."""

    start_from: str = ""
    idea: str = ""
    why: str = ""
    big_question: str = ""
    card: ActivityCard | None = None


@dataclass(frozen=True, slots=True)
class LearningPlan:
    """An interest, a goal, and activities in teaching order."""

    plan_id: str
    interest: str = ""
    goal: str = ""
    activities: tuple[PlannedActivity, ...] = ()
    is_example: bool = False
    updated_on: date = field(default_factory=date.today)


def new_plan_id(interest: str) -> str:
    """Make a fresh, file-safe plan id from an interest.

    Args:
        interest: The plan's interest, e.g. "Cars". May be blank.

    Returns:
        A lowercase slug plus a random suffix, e.g. ``cars-3f9a1c``.

    Example:
        >>> bool(PLAN_ID_RE.fullmatch(new_plan_id("Sharks & Rays!")))
        True
    """
    slug = re.sub(r"[^a-z0-9]+", "-", interest.lower()).strip("-")[:30].strip("-")
    return f"{slug or 'plan'}-{secrets.token_hex(3)}"


def drafting_notes(card: ActivityCard | None) -> list[str]:
    """List what an activity card still needs before it can be packaged.

    These are notes for the educator, not errors.

    Args:
        card: The card, or ``None`` if none has been started.

    Returns:
        Plain-language notes; empty when the card looks complete.

    Example:
        >>> drafting_notes(None)
        ['No activity card yet.']
    """
    if card is None:
        return ["No activity card yet."]
    notes: list[str] = []
    if not any(card.explanation):
        notes.append("Add at least one short explanation screen.")
    if not card.question:
        notes.append("Add the question.")
    if len([c for c in card.choices if c]) < 2:
        notes.append("Add two or three choices.")
    if not card.answer:
        notes.append("Pick the right answer.")
    elif card.answer not in card.choices:
        notes.append("The right answer must be one of the choices.")
    if not any(card.hints):
        notes.append("Add at least one hint.")
    if not card.right_text:
        notes.append("Say what the app tells them when they get it right.")
    if not card.hints_run_out_text:
        notes.append("Say what the app tells them when the hints run out.")
    if card.picture_idea and not card.picture_description:
        notes.append("Describe the picture in words for anyone who can't see it.")
    if not card.sources:
        notes.append("Say where the facts come from.")
    return notes


# --- validation and JSON ---------------------------------------------------


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise PlanError(f"{where}: expected text")
    value = value.strip()
    if len(value) > MAX_TEXT:
        raise PlanError(f"{where}: longer than {MAX_TEXT} characters")
    return value


def _texts(value: Any, where: str, limit: int) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise PlanError(f"{where}: expected a list")
    items = tuple(_text(v, f"{where}[{i}]") for i, v in enumerate(value))
    items = tuple(v for v in items if v)  # drop blank entries
    if len(items) > limit:
        raise PlanError(f"{where}: at most {limit}")
    return items


def _keys(data: Any, where: str, allowed: set[str]) -> dict[str, Any]:
    # reject unexpected keys so nothing extra sneaks into a plan file
    if not isinstance(data, dict):
        raise PlanError(f"{where}: expected an object")
    unknown = set(data) - allowed
    if unknown:
        raise PlanError(f"{where}: unknown keys {sorted(unknown)}")
    return data


_CARD_KEYS = {f for f in ActivityCard.__dataclass_fields__}
_ACTIVITY_KEYS = {f for f in PlannedActivity.__dataclass_fields__}
_PLAN_KEYS = {f for f in LearningPlan.__dataclass_fields__} | {"schema_version"}


def _card_from(data: Any, where: str) -> ActivityCard:
    d = _keys(data, where, _CARD_KEYS)
    lists = {
        "explanation": MAX_EXPLANATION_SCREENS,
        "choices": MAX_CHOICES,
        "hints": MAX_HINTS,
    }
    values: dict[str, Any] = {}
    for key in _CARD_KEYS:
        if key not in d:
            continue
        if key in lists:
            values[key] = _texts(d[key], f"{where}.{key}", lists[key])
        else:
            values[key] = _text(d[key], f"{where}.{key}")
    return ActivityCard(**values)


def _activity_from(data: Any, where: str) -> PlannedActivity:
    d = _keys(data, where, _ACTIVITY_KEYS)
    card = d.get("card")
    return PlannedActivity(
        start_from=_text(d.get("start_from", ""), f"{where}.start_from"),
        idea=_text(d.get("idea", ""), f"{where}.idea"),
        why=_text(d.get("why", ""), f"{where}.why"),
        big_question=_text(d.get("big_question", ""), f"{where}.big_question"),
        card=None if card is None else _card_from(card, f"{where}.card"),
    )


def plan_from_dict(data: Any) -> LearningPlan:
    """Validate and build a plan from parsed JSON.

    Raises:
        PlanError: Unknown keys, wrong types, bad id, or limits exceeded.
    """
    d = _keys(data, "plan", _PLAN_KEYS)
    if d.get("schema_version") != SCHEMA_VERSION:
        raise PlanError(f"plan: expected schema_version {SCHEMA_VERSION}")
    plan_id = d.get("plan_id")
    if not isinstance(plan_id, str) or not PLAN_ID_RE.fullmatch(plan_id):
        raise PlanError("plan.plan_id: expected a lowercase slug")
    activities = d.get("activities", [])
    if not isinstance(activities, list):
        raise PlanError("plan.activities: expected a list")
    if len(activities) > MAX_ACTIVITIES:
        raise PlanError(f"plan.activities: at most {MAX_ACTIVITIES}")
    is_example = d.get("is_example", False)
    if not isinstance(is_example, bool):
        raise PlanError("plan.is_example: expected true or false")
    try:
        updated_on = date.fromisoformat(d.get("updated_on", date.today().isoformat()))
    except (TypeError, ValueError) as exc:
        raise PlanError("plan.updated_on: expected YYYY-MM-DD") from exc
    return LearningPlan(
        plan_id=plan_id,
        interest=_text(d.get("interest", ""), "plan.interest"),
        goal=_text(d.get("goal", ""), "plan.goal"),
        activities=tuple(
            _activity_from(a, f"plan.activities[{i}]") for i, a in enumerate(activities)
        ),
        is_example=is_example,
        updated_on=updated_on,
    )


def plan_to_dict(plan: LearningPlan) -> dict[str, Any]:
    """Return the JSON-ready form of ``plan``; :func:`plan_from_dict` reverses it."""
    data = asdict(plan)
    data["updated_on"] = plan.updated_on.isoformat()
    # A JSON round trip turns tuples into lists, exactly as the file will hold them.
    result: dict[str, Any] = json.loads(json.dumps({"schema_version": SCHEMA_VERSION, **data}))
    return result


# --- storage ---------------------------------------------------------------


class PlanStore:
    """Learning plans on disk, one JSON file each.

    Writes are atomic, ids are validated slugs so a plan can't be written
    outside its folder, and archiving moves a file aside instead of deleting it.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "plans"
        self.archive_dir = self.root / "archived"

    def _path(self, plan_id: str) -> Path:
        # slugs only, so an id can never point outside the plans folder
        if not PLAN_ID_RE.fullmatch(plan_id):
            raise PlanError(f"{plan_id!r}: not a valid plan id")
        return self.root / f"{plan_id}.json"

    def list_plans(self) -> list[LearningPlan]:
        """Return all current plans, examples last, then by interest."""
        if not self.root.is_dir():
            return []
        plans = []
        for path in sorted(self.root.glob("*.json")):
            if not PLAN_ID_RE.fullmatch(path.stem):
                continue  # temp files (".tmp-*") from an interrupted save
            try:
                plans.append(self.get(path.stem))
            except PlanError:
                continue  # one damaged file mustn't hide the rest
        return sorted(plans, key=lambda p: (p.is_example, p.interest.lower(), p.plan_id))

    def get(self, plan_id: str) -> LearningPlan:
        """Load one plan.

        Raises:
            PlanError: Unknown id or an invalid file.
        """
        path = self._path(plan_id)
        if not path.is_file():
            raise PlanError(f"{plan_id}: no such plan")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PlanError(f"{plan_id}: unreadable plan file") from exc
        plan = plan_from_dict(data)
        if plan.plan_id != plan_id:
            raise PlanError(f"{plan_id}: file declares id {plan.plan_id!r}")
        return plan

    def save(self, plan: LearningPlan) -> LearningPlan:
        """Validate and write ``plan`` atomically, stamping today's date.

        Returns:
            The plan as saved.
        """
        saved = replace(plan, updated_on=date.today())
        data = plan_to_dict(saved)
        plan_from_dict(data)  # same checks on the way out as on the way in
        write_json_atomic(self._path(saved.plan_id), data)
        return saved

    def archive(self, plan_id: str) -> None:
        """Move a plan into ``archived/``. Nothing is permanently deleted."""
        path = self._path(plan_id)
        if not path.is_file():
            raise PlanError(f"{plan_id}: no such plan")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        # random suffix so archiving the same id twice never overwrites
        os.replace(path, self.archive_dir / f"{plan_id}-{secrets.token_hex(2)}.json")

    def seed_if_empty(self) -> int:
        """Copy the packaged example plans in, but only into an empty store.

        Returns:
            How many examples were added (0 if the store already had plans).
        """
        if self.list_plans():
            return 0
        added = 0
        for item in sorted(resources.files(SEED_PACKAGE).iterdir(), key=lambda p: p.name):
            if item.name.endswith(".json"):
                self.save(plan_from_dict(json.loads(item.read_text(encoding="utf-8"))))
                added += 1
        return added
