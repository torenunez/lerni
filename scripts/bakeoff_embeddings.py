"""Embedding bake-off for spec 10: which local model tells the same idea from a different one.

Run by hand, like the evals: ``.venv/bin/python scripts/bakeoff_embeddings.py``. Each model
in ``~/.lerni/models/`` named below is run through ``llama-embedding`` on the labelled pairs
in ``scripts/data/embedding_pairs.jsonl`` (made up, never from a real map). Prints, per use,
ROC AUC, the threshold that keeps false matches to the use's limit, the recall there, and
English and Spanish apart; then one call's time for 60 short texts, model load included.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

MODELS_DIR = Path.home() / ".lerni" / "models"
PAIRS = Path(__file__).parent / "data" / "embedding_pairs.jsonl"
SEP = "<#sep#>"  # between texts in one call; never inside a label
FALSE_LIMIT = {"set_aside": 0.10, "repeat": 0.05}  # false matches allowed per use
POSITIVE = {"set_aside": "close", "repeat": "same"}
# file -> the prefix its model card asks for on symmetric similarity
MODELS = {
    "all-MiniLM-L6-v2-Q8_0.gguf": "",
    "bge-small-en-v1.5-q8_0.gguf": "",
    "nomic-embed-text-v1.5.Q8_0.gguf": "clustering: ",
    "multilingual-e5-small-q8_0.gguf": "query: ",
    "embeddinggemma-300M-Q8_0.gguf": "task: sentence similarity | query: ",
    "Qwen3-Embedding-0.6B-Q8_0.gguf": "Instruct: Find text with the same meaning. Query: ",
}


def embed(model: Path, prefix: str, texts: list[str]) -> list[list[float]]:
    """One ``llama-embedding`` call: a unit vector per text, in order."""
    out = subprocess.run(
        ["llama-embedding", "-m", str(model), "--embd-output-format", "array",
         "--embd-separator", SEP, "--embd-normalize", "2", "-p",
         SEP.join(prefix + t for t in texts)],
        capture_output=True, check=True, timeout=300)
    text = out.stdout.decode("utf-8", errors="replace")
    vectors = json.loads(text[text.index("["):])  # anything printed before the array is skipped
    if len(vectors) != len(texts):
        raise ValueError(f"{len(vectors)} vectors for {len(texts)} texts")
    return vectors


def cosine(a: list[float], b: list[float]) -> float:
    # unit vectors: the dot product is the cosine
    return sum(x * y for x, y in zip(a, b, strict=True))


def auc(pos: list[float], neg: list[float]) -> float:
    """The chance a positive pair scores above a negative one (ties count half)."""
    if not pos or not neg:
        return math.nan
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def threshold(pos: list[float], neg: list[float], limit: float) -> tuple[float, float]:
    """The lowest cut that keeps false matches within ``limit``, and the recall there."""
    allowed = math.floor(limit * len(neg))  # negatives that may score at or above the cut
    ranked = sorted(neg, reverse=True)
    cut = ranked[allowed] + 1e-6 if allowed < len(ranked) else min(neg)
    return cut, sum(p >= cut for p in pos) / len(pos)


def score(pairs: list[dict], vec: dict[str, list[float]]) -> None:
    """Print each use's numbers for one model."""
    for use, limit in FALSE_LIMIT.items():
        rows = [(cosine(vec[p["a"]], vec[p["b"]]), p["label"] == POSITIVE[use], p["lang"])
                for p in pairs if p["use"] == use]
        pos = [s for s, good, _ in rows if good]
        neg = [s for s, good, _ in rows if not good]
        cut, recall = threshold(pos, neg, limit)
        by_lang = {lang: auc([s for s, g, x in rows if g and (x == "en") == (lang == "en")],
                             [s for s, g, x in rows if not g and (x == "en") == (lang == "en")])
                   for lang in ("en", "es")}
        print(f"  {use:9}  AUC {auc(pos, neg):.3f}  (en {by_lang['en']:.3f}, "
              f"es {by_lang['es']:.3f})  cut {cut:.3f}  recall {recall:.0%} "
              f"at ≤{limit:.0%} false")


def main() -> int:
    pairs = [json.loads(line) for line in PAIRS.read_text(encoding="utf-8").splitlines()]
    texts = list(dict.fromkeys(t for p in pairs for t in (p["a"], p["b"])))
    for name, prefix in MODELS.items():
        model = MODELS_DIR / name
        if not model.is_file():
            print(f"{name}: not downloaded, skipped")
            continue
        print(f"{name} ({model.stat().st_size / 1e6:.0f} MB)")
        try:
            vec = dict(zip(texts, embed(model, prefix, texts), strict=True))
            started = time.monotonic()
            embed(model, prefix, texts[:60])  # the time a race check would wait
            print(f"  60 texts in one call: {time.monotonic() - started:.2f} s")
        except subprocess.CalledProcessError as exc:  # llama.cpp's last line says why
            lines = exc.stderr.decode("utf-8", errors="replace").strip().splitlines()
            print(f"  failed: {lines[-1] if lines else exc.returncode}")
            continue
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            print(f"  failed: {type(exc).__name__}: {exc}")
            continue
        score(pairs, vec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
