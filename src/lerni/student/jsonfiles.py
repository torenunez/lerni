"""Atomic JSON writes shared by the plan and student stores. Standard library only."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Write ``data`` as pretty JSON to ``path`` without ever leaving half a file.

    Args:
        path: The destination; its folder is created if needed.
        data: A JSON-ready dict.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # write to a temp file in the same folder, then swap it in
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
