"""Race checks by meaning (spec 10, v3.40): a reworded idea, or a set-aside topic in other
words, found by comparing embeddings of short labels and questions.

Vectors live in memory for one check, never on disk. Without an embedder every check is
the word match alone. Standard library only.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from lerni.student.concepts import normalize
from lerni.student.interests import InterestMap

ASIDE = 0.55  # a question this close to a removed name is about it (and closer than its goal)
REPEAT = 0.91  # two idea labels this close are one idea (measured on real labels)
GOALS_WIN = 0.80  # a removed name this close to a goal or an area doesn't block it


class Embedder(Protocol):
    """Turns short texts into unit vectors, in order."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def _cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))  # unit vectors: the dot product


class Meaning:
    """One call's vectors, looked up by normalized text; a text it wasn't given never matches."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors
        self.repeats = self.asides = 0  # drops, for the server log

    @classmethod
    def build(cls, embedder: Embedder, texts: Iterable[str]) -> Meaning:
        """Embed every distinct text in one call.

        Raises:
            Exception: Whatever the embedder raises; the caller falls back to words.
        """
        unique = list(dict.fromkeys(t for t in texts if normalize(t)))
        vectors = embedder.embed(unique) if unique else []
        if len(vectors) != len(unique):
            raise ValueError(f"{len(vectors)} vectors for {len(unique)} texts")
        return cls({normalize(t): v for t, v in zip(unique, vectors, strict=True)})

    def sim(self, a: str, b: str) -> float | None:
        """The cosine of two texts, or None if either wasn't embedded."""
        va, vb = self.vectors.get(normalize(a)), self.vectors.get(normalize(b))
        return _cos(va, vb) if va is not None and vb is not None else None

    def repeat(self, idea: str, against: Iterable[str]) -> bool:
        """Whether ``idea`` rewords one of ``against``; counted when it does."""
        hit = any((s := self.sim(idea, other)) is not None and s >= REPEAT for other in against)
        self.repeats += hit
        return hit

    def aside(self, text: str, goal: str, removed: Iterable[str]) -> bool:
        """Whether ``text`` is about a removed name, more than about its own ``goal``."""
        near = max((s for r in removed if (s := self.sim(text, r)) is not None), default=None)
        own = self.sim(text, goal) if goal else None
        hit = near is not None and near >= ASIDE and (own is None or near > own)
        self.asides += hit
        return hit


def skipped(m: InterestMap, embedder: Embedder) -> frozenset[str]:
    """Removed names (casefolded) close to an active goal or an area with goals: goals win, so
    race checks leave them out, while Chat still steers away from them.

    Raises:
        Exception: Whatever the embedder raises.
    """
    goals = [e for e in m.entries if e.kind == "goal"]
    targets = [*(g.name for g in goals), *{g.area for g in goals if g.area}]
    if not m.removed or not targets:
        return frozenset()
    meaning = Meaning.build(embedder, [*m.removed, *targets])
    return frozenset(r.casefold() for r in m.removed
                     if any((s := meaning.sim(r, t)) is not None and s >= GOALS_WIN
                            for t in targets))
