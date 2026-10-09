"""Upload: notes become proposals, checked, and only the ticked ones are added."""

import pytest

from lerni.student.interests import InterestMap, add_goal
from lerni.student.upload import UploadError, apply_proposals, extract_upload, parse_proposals


def test_proposals_are_checked_and_only_ticked_ones_are_added():
    proposals, notes = parse_proposals({
        "entries": [
            {"kind": "interest", "name": "monster trucks"},
            {"kind": "goal", "name": "Fractions", "notes": "halves first"},
            {"kind": "goal", "name": "<b>x</b>"},  # not a plain name
            {"kind": "boss", "name": "Cars"},  # not a kind
            {"kind": "interest", "name": "Monster Trucks"},  # a repeat
        ],
        "notes": ["Wrote 'the student' for a name."],
        "plan": "ignored",  # unknown fields are dropped
    })
    assert [(p.kind, p.name) for p in proposals] == [("interest", "monster trucks"),
                                                       ("goal", "Fractions")]
    assert notes == ["Wrote 'the student' for a name."]
    m = InterestMap()
    add_goal(m, "Fractions")  # added meanwhile: that one is skipped and named
    added, skipped = apply_proposals(m, proposals)
    assert added == 1 and skipped == ["Fractions: Fractions is already a goal."]
    trucks = m.find("monster trucks")
    assert trucks.kind == "interest" and trucks.days == []  # grows as it comes up


def test_uploads_are_read_or_refused_politely():
    assert extract_upload("Cars, then speed").text == "Cars, then speed"
    assert extract_upload("", "notes.md", b"# Sharks").text == "# Sharks"
    for name, data in (("run.exe", b"x"), ("notes.pdf", b"not a pdf"),
                       ("big.txt", b"x" * 5_000_001)):
        with pytest.raises(UploadError):
            extract_upload("", name, data)
    with pytest.raises(UploadError):
        extract_upload("   ")
