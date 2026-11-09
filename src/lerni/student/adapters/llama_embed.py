"""Embeddings on the home server: llama.cpp's ``llama-embedding`` with a local model (spec 10).

One call per batch, the texts as one argument (never a file), nothing kept.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

MODEL_ENV = "LERNI_EMBED_MODEL"
DEFAULT_MODEL = Path.home() / ".lerni" / "models" / "Qwen3-Embedding-0.6B-Q8_0.gguf"
PREFIX = "Instruct: Find text with the same meaning. Query: "  # as in the bake-off
SEP = "<#sep#>"  # between texts; never inside a label
TIMEOUT = 10  # seconds per call
NO_TOOLS = "install llama.cpp and the model: admin reference, Race checks by meaning"


class LlamaEmbedder:
    """``llama-embedding`` for unit vectors of short texts."""

    def __init__(self, model: Path | str, runner: Callable[..., Any] = subprocess.run) -> None:
        self.model, self._run = Path(model), runner

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in order.

        Raises:
            OSError, subprocess.SubprocessError: The tool failed or took too long.
            ValueError: Its answer wasn't one vector per text.
        """
        clean = [" ".join(t.replace(SEP, " ").split()) for t in texts]  # one line each
        out = self._run(
            ["llama-embedding", "-m", str(self.model), "--embd-output-format", "array",
             "--embd-separator", SEP, "--embd-normalize", "2",
             "-p", SEP.join(PREFIX + t for t in clean)],
            capture_output=True, timeout=TIMEOUT, check=True)  # stderr kept, never printed
        text = out.stdout.decode("utf-8", errors="replace")
        start = text.find("[")
        vectors = json.loads(text[start:]) if start >= 0 else None
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise ValueError("llama-embedding didn't give one vector per text")
        return [[float(x) for x in v] for v in vectors]


def embedder_from_env() -> tuple[LlamaEmbedder | None, str]:
    """The embedder, or ``None`` and why it's off (the tool or the model is missing)."""
    model = Path(os.environ.get(MODEL_ENV, DEFAULT_MODEL)).expanduser()
    if not (shutil.which("llama-embedding") and model.is_file()):
        return None, NO_TOOLS
    return LlamaEmbedder(model), ""
