"""Canonical JSON encoder tests.

Content identity depends on this encoder being byte-stable. Two objects that are
semantically equal must encode identically regardless of key insertion order,
and anything whose encoding would be ambiguous must be rejected rather than
silently normalized.
"""

import math

import pytest

from lerni.explore.canonical import canonical_json_bytes


def test_mapping_keys_are_sorted():
    assert canonical_json_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_key_insertion_order_does_not_change_bytes():
    assert canonical_json_bytes({"z": 1, "a": {"y": 2, "b": 3}}) == canonical_json_bytes(
        {"a": {"b": 3, "y": 2}, "z": 1}
    )


def test_separators_are_compact():
    assert b" " not in canonical_json_bytes({"a": [1, 2, 3]})


def test_tuples_encode_as_arrays_identically_to_lists():
    assert canonical_json_bytes((1, 2)) == canonical_json_bytes([1, 2]) == b"[1,2]"


def test_non_ascii_is_emitted_literally_as_utf8():
    encoded = canonical_json_bytes({"t": "0–60"})
    assert "–".encode() in encoded
    assert b"\\u" not in encoded


def test_rejects_non_finite_numbers():
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            canonical_json_bytes({"a": bad})


def test_rejects_non_string_mapping_key():
    with pytest.raises(TypeError):
        canonical_json_bytes({1: "a"})


def test_rejects_unsupported_type():
    with pytest.raises(TypeError):
        canonical_json_bytes({"a": {1, 2}})


def test_output_has_no_trailing_bytes():
    encoded = canonical_json_bytes({"a": 1})
    assert encoded == encoded.strip()
    assert not encoded.endswith(b"\n")


def test_booleans_and_null_are_canonical():
    assert canonical_json_bytes({"a": True, "b": None}) == b'{"a":true,"b":null}'


def test_bool_is_not_treated_as_integer():
    assert canonical_json_bytes([True, 1]) == b"[true,1]"
