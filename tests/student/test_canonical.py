"""Canonical JSON encoder tests.

Content identity depends on this encoder being byte-stable. Two objects that are
semantically equal must encode identically regardless of key insertion order,
and anything whose encoding would be ambiguous must be rejected rather than
silently normalized.
"""



from lerni.student.canonical import canonical_json_bytes


def test_key_insertion_order_does_not_change_bytes():
    assert canonical_json_bytes({"z": 1, "a": {"y": 2, "b": 3}}) == canonical_json_bytes(
        {"a": {"b": 3, "y": 2}, "z": 1}
    )
