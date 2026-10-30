"""Atomic JSON writes, reads that keep a broken file, and private folders, shared by the
stores. Standard library only."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
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


def read_json(path: Path) -> dict[str, Any] | None:
    """A JSON object from ``path``, or None when it's missing or broken. A broken file (not
    JSON, or not an object) is renamed ``<name>.broken-<time>.json`` beside it, so the next
    write never overwrites it, and the log names it."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:  # unreadable (permissions): left where it is
        print(f"Couldn't read {path} ({type(exc).__name__}).", flush=True)
        return None
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if isinstance(data, dict):
        return data
    aside = path.with_name(f"{path.stem}.broken-{datetime.now():%Y%m%d-%H%M%S-%f}.json")
    try:
        os.replace(path, aside)  # kept for the admin, out of the next write's way
    except FileNotFoundError:
        return None  # another reader moved it aside first
    print(f"Moved aside a broken file: {aside}", flush=True)
    return None


def private(root: Path) -> None:
    """Make ``root`` and everything in it readable by this account only: folders 0700, files
    0600. A file that can't be changed is skipped and logged."""
    if not root.is_dir():
        return
    for folder, _dirs, files in os.walk(root):
        for path, mode in [(Path(folder), 0o700), *((Path(folder) / f, 0o600) for f in files)]:
            try:
                if not path.is_symlink() and path.stat().st_mode & 0o777 != mode:
                    path.chmod(mode)
            except OSError as exc:
                print(f"Couldn't make {path} private ({type(exc).__name__}).", flush=True)
