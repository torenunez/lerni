"""Approved-activity listing and the educator-only draft preview (MVP step 2).

Each test builds a small synthetic lesson package in a temporary folder, with
an index generated from the real bytes, so nothing touches production content.
"""

import hashlib
import sys
import uuid

import pytest

from lerni.student.catalog import (
    PackageLessonCatalog,
    lesson_payload_sha256,
    parse_lesson_toml,
)
from lerni.student.domain import (
    ApprovalStatus,
    AssetRef,
    DraftPreview,
    Lesson,
    LessonNotApprovedError,
)


def with_id(toml: str, lesson_id: str) -> str:
    return toml.replace('lesson_id = "test-lesson"', f'lesson_id = "{lesson_id}"', 1)


def approved_as(approved: str, draft: str, lesson_id: str) -> str:
    """The approved fixture under a new ID, with attestations re-pinned to its hash."""
    old = lesson_payload_sha256(parse_lesson_toml(draft))
    new = lesson_payload_sha256(parse_lesson_toml(with_id(draft, lesson_id)))
    return with_id(approved, lesson_id).replace(old, new)


def build_package(tmp_path, monkeypatch, lessons, assets=None, tamper=()):
    """Write a lesson package, index it from the real bytes, and return its name.

    Args:
        lessons: ``{lesson_id: toml_text}``.
        assets: ``{resource_name: bytes}``.
        tamper: lesson IDs whose file is changed after indexing.
    """
    name = f"fake_lessons_{uuid.uuid4().hex}"
    root = tmp_path / name
    (root / "assets").mkdir(parents=True)
    (root / "__init__.py").write_text("")
    index = ["schema_version = 1", ""]
    for lesson_id, text in lessons.items():
        resource = f"{lesson_id}.toml"
        data = text.encode("utf-8")
        (root / resource).write_bytes(data)
        payload = lesson_payload_sha256(parse_lesson_toml(text))
        index += [
            "[[lessons]]",
            f'lesson_id = "{lesson_id}"',
            f'resource_name = "{resource}"',
            f'sha256 = "{hashlib.sha256(data).hexdigest()}"',
            f'lesson_payload_sha256 = "{payload}"',
            "",
        ]
    for resource, data in (assets or {}).items():
        (root / resource).write_bytes(data)
        index += [
            "[[assets]]",
            f'resource_name = "{resource}"',
            'media_type = "image/svg+xml"',
            f'sha256 = "{hashlib.sha256(data).hexdigest()}"',
            "",
        ]
    (root / "lesson_index.toml").write_text("\n".join(index))
    for lesson_id in tamper:
        path = root / f"{lesson_id}.toml"
        path.write_text(path.read_text().replace("Intro body.", "Changed body.", 1))
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(sys.modules, name, __import__(name))
    return name


@pytest.fixture
def mixed_catalog(tmp_path, monkeypatch, approved_lesson_toml, draft_lesson_toml):
    """One approved, one draft, and one approved-then-altered activity."""
    package = build_package(
        tmp_path,
        monkeypatch,
        {
            "approved-one": approved_as(approved_lesson_toml, draft_lesson_toml, "approved-one"),
            "draft-one": with_id(draft_lesson_toml, "draft-one"),
            "altered-one": approved_as(approved_lesson_toml, draft_lesson_toml, "altered-one"),
        },
        tamper=("altered-one",),
    )
    return PackageLessonCatalog(package)


def test_lists_only_approved_unaltered_activities(mixed_catalog):
    listed = mixed_catalog.list_approved()
    assert [a.lesson_id for a in listed] == ["approved-one"]
    assert listed[0].status is ApprovalStatus.APPROVED
    assert listed[0].title == "Test lesson"






def test_draft_preview_is_not_a_lesson(mixed_catalog):
    preview = mixed_catalog.load_preview("draft-one")
    assert isinstance(preview, DraftPreview)
    assert not isinstance(preview, Lesson)
    assert preview.lesson.review.status is ApprovalStatus.DRAFT
    with pytest.raises(LessonNotApprovedError):
        mixed_catalog.load("draft-one")






def visual_of(preview: DraftPreview) -> AssetRef:
    return next(step.visual for step in preview.lesson.steps if step.visual)










def test_production_package_has_nothing_approved_and_previews_the_car_draft():
    catalog = PackageLessonCatalog()
    assert catalog.list_approved() == ()
    drafts = catalog.list_drafts()
    assert [a.lesson_id for a in drafts] == ["chain-1-acceleration"]
    preview = catalog.load_preview("chain-1-acceleration")
    assert catalog.read_preview_asset(preview, visual_of(preview)).startswith(b"<svg")
