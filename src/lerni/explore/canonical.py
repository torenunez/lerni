"""Canonical JSON encoding for content identity.

Lesson review binds a human attestation to an exact content hash. That hash is
only meaningful if the same lesson always encodes to the same bytes, so this
module fixes every degree of freedom JSON normally leaves open: mapping keys are
sorted, separators are compact, text is literal UTF-8, and anything whose
encoding would be ambiguous is rejected rather than coerced.

Reject-don't-coerce is deliberate. A silently normalized value would change a
hash without changing the content a reviewer approved.
"""

import json
import math
from collections.abc import Mapping, Sequence

__all__ = ["canonical_json_bytes"]


def _check(value: object, path: str) -> object:
    """Validate recursively and convert tuples to lists.

    Args:
        value: The node to validate.
        path: Dotted path to this node, used in error messages.

    Returns:
        A structure containing only ``dict``, ``list``, ``str``, ``int``,
        ``float``, ``bool``, and ``None``.

    Raises:
        TypeError: A mapping key is not a string, or a value has a type with no
            canonical JSON form (sets, bytes, dates, arbitrary objects).
        ValueError: A float is NaN or infinite, neither of which JSON can
            represent without a non-standard extension.
    """
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path}: non-finite number {value!r} has no canonical form")
        return value
    if isinstance(value, Mapping):
        out: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path}: mapping key {key!r} is not a string")
            out[key] = _check(item, f"{path}.{key}" if path else key)
        return out
    if isinstance(value, Sequence):  # str/bytes handled above or below
        if isinstance(value, (bytes, bytearray)):
            raise TypeError(f"{path}: bytes have no canonical JSON form")
        return [_check(item, f"{path}[{i}]") for i, item in enumerate(value)]
    raise TypeError(f"{path}: {type(value).__name__} has no canonical JSON form")


def canonical_json_bytes(value: object) -> bytes:
    """Encode ``value`` to canonical JSON bytes.

    Args:
        value: A structure of mappings, sequences, strings, finite numbers,
            booleans, and ``None``. Tuples encode identically to lists.

    Returns:
        UTF-8 bytes with sorted mapping keys, ``,``/``:`` separators, literal
        non-ASCII characters, and no trailing whitespace or newline.

    Raises:
        TypeError: An unsupported type or a non-string mapping key appears.
        ValueError: A non-finite number appears.

    Example:
        >>> canonical_json_bytes({"b": 1, "a": [2, 3]})
        b'{"a":[2,3],"b":1}'
    """
    checked = _check(value, "")
    return json.dumps(
        checked,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
