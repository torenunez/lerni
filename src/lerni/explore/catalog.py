"""Strict lesson loading and the approved-content boundary.

Two jobs live here. :func:`parse_lesson_toml` turns authored TOML into a
:class:`~lerni.explore.domain.Lesson`, rejecting anything ambiguous rather than
coercing it. :class:`PackageLessonCatalog` is the boundary a child's session
crosses: it serves only content that is approved, hash-verified against the
package index, and identical to what a human reviewed.

Everything fails closed. A lesson that cannot be proven to match its review is
not shown.
"""

import hashlib
import re
import tomllib
import unicodedata
from datetime import date
from importlib import resources
from typing import Any, NoReturn, Protocol

from lerni.explore.canonical import canonical_json_bytes
from lerni.explore.domain import (
    ApprovalStatus,
    AssetRef,
    CheckChoice,
    GroundedFact,
    GroundingBundle,
    Lesson,
    LessonContentError,
    LessonNotApprovedError,
    LessonNotFoundError,
    LessonPackageIdentity,
    LessonStep,
    RetrievalCheck,
    ReviewAttestation,
    ReviewMetadata,
    ReviewScope,
    SourceReference,
    StepKind,
)

__all__ = [
    "LessonCatalog",
    "PackageLessonCatalog",
    "canonical_policy_token",
    "lesson_payload_sha256",
    "parse_lesson_toml",
]

LESSON_PACKAGE = "lerni.explore.lessons"
LESSON_INDEX_RESOURCE = "lesson_index.toml"

#: Read limits applied before any decode or allocation. A hostile or corrupt
#: resource must not be able to exhaust memory before validation runs.
INDEX_BYTE_LIMIT = 65_536
LESSON_BYTE_LIMIT = 256_000
ASSET_BYTE_LIMIT = 1_000_000

SUPPORTED_MEDIA_TYPES = frozenset({"image/svg+xml"})
SCHEMA_VERSION = 1
MAX_TURNS_RANGE = (1, 20)
ALLOWED_NUMBER_MAX_LEN = 32

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_NUMBER_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")

#: Matches spec 03a. Deliberately ASCII-only for the first English lesson.
TOKEN_RE = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)*", re.ASCII)

_CURLY_APOSTROPHES = "‘’ʼ′"
_DASHES = "‐‑‒–—―−"


def canonical_policy_token(text: str) -> str:
    """Fold ``text`` to the single canonical form policy matching uses.

    NFKC, curly apostrophes and Unicode dashes folded to ASCII, then
    ``casefold()``. PR-09 applies the identical function to spreadsheet input,
    so TOML and CSV compilation cannot diverge by case or Unicode punctuation.

    Args:
        text: An authored scope term or short reply.

    Returns:
        The canonical token form.

    Example:
        >>> canonical_policy_token("Don\\u2019t")
        "don't"
    """
    folded = unicodedata.normalize("NFKC", text)
    folded = "".join("'" if ch in _CURLY_APOSTROPHES else ch for ch in folded)
    folded = "".join("-" if ch in _DASHES else ch for ch in folded)
    return folded.casefold()


class _V:
    """Validation helper carrying the origin used in every error message."""

    def __init__(self, origin: str) -> None:
        self.origin = origin

    def fail(self, path: str, message: str) -> NoReturn:
        raise LessonContentError(f"{self.origin}:{path}: {message}")

    def keys(
        self,
        node: Any,
        path: str,
        required: set[str],
        optional: set[str] = frozenset(),  # type: ignore[assignment]
    ) -> dict[str, Any]:
        if not isinstance(node, dict):
            self.fail(path, f"expected a table, got {type(node).__name__}")
        unknown = sorted(set(node) - required - set(optional))
        if unknown:
            self.fail(path, f"unknown key(s): {', '.join(unknown)}")
        missing = sorted(required - set(node))
        if missing:
            self.fail(path, f"missing key(s): {', '.join(missing)}")
        return node

    def text(self, node: dict[str, Any], path: str, key: str, *, allow_blank: bool = False) -> str:
        value = node.get(key)
        if type(value) is not str:
            self.fail(f"{path}.{key}" if path else key, "expected a string")
        if not allow_blank and not value.strip():
            self.fail(f"{path}.{key}" if path else key, "must not be blank")
        return value

    def integer(self, node: dict[str, Any], path: str, key: str) -> int:
        value = node.get(key)
        # bool is an int subclass; a boolean here is authored error, not a count.
        if type(value) is not int:
            self.fail(f"{path}.{key}" if path else key, "expected an integer, not a string or bool")
        return value

    def identifier(self, node: dict[str, Any], path: str, key: str) -> str:
        value = self.text(node, path, key)
        if not ID_RE.fullmatch(value):
            self.fail(
                f"{path}.{key}" if path else key,
                f"{value!r} is not a valid id (lowercase words joined by single hyphens)",
            )
        return value

    def str_list(self, node: dict[str, Any], path: str, key: str) -> tuple[str, ...]:
        value = node.get(key)
        if not isinstance(value, list) or any(type(v) is not str for v in value):
            self.fail(f"{path}.{key}" if path else key, "expected a list of strings")
        return tuple(value)

    def tokens(self, node: dict[str, Any], path: str, key: str) -> frozenset[str]:
        """Validate that every item is *already* the exact canonical token form."""
        full = f"{path}.{key}" if path else key
        raw = self.str_list(node, path, key)
        seen: set[str] = set()
        for item in raw:
            canonical = canonical_policy_token(item)
            if canonical != item or not TOKEN_RE.fullmatch(item):
                self.fail(full, f"{item!r} is not already a canonical policy token")
            if canonical in seen:
                self.fail(full, f"duplicate token {item!r} after canonicalization")
            seen.add(canonical)
        return frozenset(seen)

    def when(self, condition: bool, path: str, message: str) -> None:
        if condition:
            self.fail(path, message)


def _parse_review(v: _V, node: Any) -> ReviewMetadata:
    table = v.keys(node, "review", {"status"}, {"attestations"})
    status_text = v.text(table, "review", "status")
    if status_text not in tuple(ApprovalStatus):
        v.fail("review.status", f"{status_text!r} is not a valid approval status")
    status = ApprovalStatus(status_text)

    raw = table.get("attestations", [])
    if not isinstance(raw, list):
        v.fail("review.attestations", "expected a list of tables")

    if status is ApprovalStatus.DRAFT and raw:
        v.fail("review.attestations", "a draft lesson must carry no attestations")

    attestations: list[ReviewAttestation] = []
    seen_ids: set[str] = set()
    seen_scopes: set[str] = set()
    for i, entry in enumerate(raw):
        path = f"review.attestations[{i}]"
        table_i = v.keys(
            entry,
            path,
            {"id", "scope", "reviewer_role", "reviewed_on", "reviewed_payload_sha256"},
            {"evidence_ref"},
        )
        att_id = v.identifier(table_i, path, "id")
        v.when(att_id in seen_ids, path, f"duplicate attestation id {att_id!r}")
        seen_ids.add(att_id)

        scope_text = v.text(table_i, path, "scope")
        if scope_text not in tuple(ReviewScope):
            v.fail(f"{path}.scope", f"{scope_text!r} is not a valid review scope")
        v.when(scope_text in seen_scopes, path, f"duplicate review scope {scope_text!r}")
        seen_scopes.add(scope_text)

        reviewed_on = table_i.get("reviewed_on")
        if not isinstance(reviewed_on, date):
            v.fail(f"{path}.reviewed_on", "expected a TOML local date")

        digest = v.text(table_i, path, "reviewed_payload_sha256")
        if not SHA256_RE.fullmatch(digest):
            v.fail(f"{path}.reviewed_payload_sha256", "expected a lowercase 64-hex SHA-256")

        evidence = table_i.get("evidence_ref")
        if evidence is not None and type(evidence) is not str:
            v.fail(f"{path}.evidence_ref", "expected a string")

        attestations.append(
            ReviewAttestation(
                id=att_id,
                scope=ReviewScope(scope_text),
                reviewer_role=v.text(table_i, path, "reviewer_role"),
                reviewed_on=reviewed_on,
                evidence_ref=evidence,
                reviewed_payload_sha256=digest,
            )
        )

    if status is ApprovalStatus.APPROVED:
        missing = sorted({scope.value for scope in ReviewScope} - seen_scopes)
        if missing:
            v.fail("review.attestations", f"approved lesson missing scope(s): {', '.join(missing)}")
        digests = {a.reviewed_payload_sha256 for a in attestations}
        if len(digests) != 1:
            v.fail(
                "review.attestations",
                "every attestation must record the same reviewed_payload_sha256",
            )

    return ReviewMetadata(status=status, attestations=tuple(attestations))


def _parse_visual(v: _V, table: dict[str, Any], path: str, *, is_draft: bool) -> AssetRef | None:
    keys = {"visual_resource", "visual_media_type", "visual_alt", "visual_sha256"}
    present = keys & set(table)
    if not present:
        return None
    if present != keys:
        v.fail(path, f"visual requires all of: {', '.join(sorted(keys))}")

    resource = v.text(table, path, "visual_resource")
    if not resource.startswith("assets/") or ".." in resource or resource.startswith("/"):
        v.fail(f"{path}.visual_resource", "must be a relative path under assets/ with no '..'")

    media_type = v.text(table, path, "visual_media_type")
    if media_type not in SUPPORTED_MEDIA_TYPES:
        v.fail(f"{path}.visual_media_type", f"unsupported media type {media_type!r}")

    digest = v.text(table, path, "visual_sha256", allow_blank=True)
    if digest == "":
        if not is_draft:
            v.fail(f"{path}.visual_sha256", "an approved lesson asset requires a SHA-256")
        sha: str | None = None
    else:
        if not SHA256_RE.fullmatch(digest):
            v.fail(f"{path}.visual_sha256", "expected a lowercase 64-hex SHA-256")
        sha = digest

    return AssetRef(
        resource_name=resource,
        media_type=media_type,
        alt_text=v.text(table, path, "visual_alt"),
        sha256=sha,
    )


def _parse_grounding(v: _V, node: Any) -> GroundingBundle:
    table = v.keys(
        node,
        "grounding",
        {"scope", "fallback_text", "redirect_text"},
        {"sources", "facts"},
    )
    scope = v.text(table, "grounding", "scope")
    fallback = v.text(table, "grounding", "fallback_text")
    redirect = v.text(table, "grounding", "redirect_text")

    raw_sources = table.get("sources", [])
    if not isinstance(raw_sources, list) or not raw_sources:
        v.fail("grounding.sources", "expected at least one source table")

    sources: list[SourceReference] = []
    seen_source_ids: set[str] = set()
    for i, entry in enumerate(raw_sources):
        path = f"grounding.sources[{i}]"
        st = v.keys(entry, path, {"id", "title", "publisher", "url", "retrieved_on"})
        sid = v.identifier(st, path, "id")
        v.when(sid in seen_source_ids, path, f"duplicate source id {sid!r}")
        seen_source_ids.add(sid)

        url = v.text(st, path, "url")
        if not url.startswith("https://"):
            v.fail(f"{path}.url", "source url must use https")

        retrieved_on = st.get("retrieved_on")
        if not isinstance(retrieved_on, date):
            v.fail(f"{path}.retrieved_on", "expected a TOML local date")

        sources.append(
            SourceReference(
                id=sid,
                title=v.text(st, path, "title"),
                publisher=v.text(st, path, "publisher"),
                url=url,
                retrieved_on=retrieved_on,
            )
        )

    raw_facts = table.get("facts", [])
    if not isinstance(raw_facts, list) or not raw_facts:
        v.fail("grounding.facts", "expected at least one fact table")

    facts: list[GroundedFact] = []
    seen_fact_ids: set[str] = set()
    for i, entry in enumerate(raw_facts):
        path = f"grounding.facts[{i}]"
        ft = v.keys(
            entry, path, {"id", "canonical_text", "child_text", "source_ids", "allowed_numbers"}
        )
        fid = v.identifier(ft, path, "id")
        v.when(fid in seen_fact_ids, path, f"duplicate fact id {fid!r}")
        seen_fact_ids.add(fid)

        source_ids = v.str_list(ft, path, "source_ids")
        if not source_ids:
            v.fail(f"{path}.source_ids", "every fact must cite at least one source")
        unknown = [s for s in source_ids if s not in seen_source_ids]
        if unknown:
            v.fail(f"{path}.source_ids", f"unknown source(s): {', '.join(sorted(unknown))}")

        allowed_numbers = v.str_list(ft, path, "allowed_numbers")
        for number in allowed_numbers:
            if len(number) > ALLOWED_NUMBER_MAX_LEN or not ALLOWED_NUMBER_RE.fullmatch(number):
                v.fail(
                    f"{path}.allowed_numbers",
                    f"{number!r} is not a supported number literal",
                )

        facts.append(
            GroundedFact(
                id=fid,
                canonical_text=v.text(ft, path, "canonical_text"),
                child_text=v.text(ft, path, "child_text"),
                source_ids=source_ids,
                allowed_numbers=allowed_numbers,
            )
        )

    return GroundingBundle(
        scope=scope,
        fallback_text=fallback,
        redirect_text=redirect,
        facts=tuple(facts),
        sources=tuple(sources),
    )


def _parse_steps(
    v: _V, node: Any, *, is_draft: bool, known_facts: set[str]
) -> tuple[LessonStep, ...]:
    if not isinstance(node, list) or not node:
        v.fail("steps", "expected at least one step table")

    steps: list[LessonStep] = []
    seen: set[str] = set()
    for i, entry in enumerate(node):
        path = f"steps[{i}]"
        st = v.keys(
            entry,
            path,
            {"id", "kind", "heading", "body", "fact_ids", "scope_terms"},
            {"visual_resource", "visual_media_type", "visual_alt", "visual_sha256"},
        )
        sid = v.identifier(st, path, "id")
        v.when(sid in seen, path, f"duplicate step id {sid!r}")
        seen.add(sid)

        kind_text = v.text(st, path, "kind")
        if kind_text not in tuple(StepKind):
            v.fail(f"{path}.kind", f"{kind_text!r} is not a valid step kind")
        kind = StepKind(kind_text)
        if i == 0 and kind is not StepKind.INTRO:
            v.fail(f"{path}.kind", "the first authored step must be an intro step")
        if i > 0 and kind is not StepKind.TEACH:
            v.fail(f"{path}.kind", "every step after the first must be a teach step")

        fact_ids = v.str_list(st, path, "fact_ids")
        if not fact_ids:
            v.fail(f"{path}.fact_ids", "a step must bind at least one fact")
        unknown = [f for f in fact_ids if f not in known_facts]
        if unknown:
            v.fail(f"{path}.fact_ids", f"unknown fact(s): {', '.join(sorted(unknown))}")

        scope_terms = v.tokens(st, path, "scope_terms")
        if not scope_terms:
            v.fail(f"{path}.scope_terms", "a step must declare at least one scope term")

        steps.append(
            LessonStep(
                id=sid,
                kind=kind,
                heading=v.text(st, path, "heading"),
                body=v.text(st, path, "body"),
                visual=_parse_visual(v, st, path, is_draft=is_draft),
                fact_ids=fact_ids,
                scope_terms=scope_terms,
            )
        )

    if not any(step.kind is StepKind.TEACH for step in steps):
        v.fail("steps", "a lesson must contain at least one teach step")
    return tuple(steps)


def _parse_check(v: _V, node: Any, *, known_facts: set[str]) -> RetrievalCheck:
    table = v.keys(
        node,
        "check",
        {
            "id",
            "prompt",
            "correct_choice_id",
            "hints",
            "success_text",
            "reveal_text",
            "fact_ids",
            "scope_terms",
            "allowed_short_replies",
        },
        {"choices"},
    )
    raw_choices = table.get("choices", [])
    if not isinstance(raw_choices, list) or len(raw_choices) < 2:
        v.fail("check.choices", "a retrieval check needs at least two choices")

    choices: list[CheckChoice] = []
    seen: set[str] = set()
    for i, entry in enumerate(raw_choices):
        path = f"check.choices[{i}]"
        ct = v.keys(entry, path, {"id", "label"})
        cid = v.identifier(ct, path, "id")
        v.when(cid in seen, path, f"duplicate choice id {cid!r}")
        seen.add(cid)
        choices.append(CheckChoice(id=cid, label=v.text(ct, path, "label")))

    correct = v.identifier(table, "check", "correct_choice_id")
    if correct not in seen:
        v.fail("check.correct_choice_id", f"{correct!r} is not one of the declared choices")

    hints = v.str_list(table, "check", "hints")
    if not hints:
        v.fail("check.hints", "a retrieval check needs at least one hint")
    for i, hint in enumerate(hints):
        if not hint.strip():
            v.fail(f"check.hints[{i}]", "hint must not be blank")

    fact_ids = v.str_list(table, "check", "fact_ids")
    if not fact_ids:
        v.fail("check.fact_ids", "a check must bind at least one fact")
    unknown = [f for f in fact_ids if f not in known_facts]
    if unknown:
        v.fail("check.fact_ids", f"unknown fact(s): {', '.join(sorted(unknown))}")

    scope_terms = v.tokens(table, "check", "scope_terms")
    if not scope_terms:
        v.fail("check.scope_terms", "a check must declare at least one scope term")

    return RetrievalCheck(
        id=v.identifier(table, "check", "id"),
        prompt=v.text(table, "check", "prompt"),
        choices=tuple(choices),
        correct_choice_id=correct,
        hints=hints,
        success_text=v.text(table, "check", "success_text"),
        reveal_text=v.text(table, "check", "reveal_text"),
        fact_ids=fact_ids,
        scope_terms=scope_terms,
        allowed_short_replies=v.tokens(table, "check", "allowed_short_replies"),
    )


def parse_lesson_toml(text: str, *, origin: str = "<memory>") -> Lesson:
    """Parse authored lesson TOML into a validated :class:`Lesson`.

    This is the draft-tolerant entry point. It validates structure, references,
    and review consistency, but it does not check package hashes — use
    :class:`PackageLessonCatalog` for anything a child will see.

    Args:
        text: The lesson TOML source.
        origin: Label used in error messages, typically the resource name.

    Returns:
        The parsed lesson.

    Raises:
        LessonContentError: Any validation failure. The message is formatted as
            ``{origin}:{field-path}: {message}``.
    """
    v = _V(origin)
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        v.fail("<document>", f"malformed TOML: {exc}")

    top = v.keys(
        raw,
        "",
        {
            "schema_version",
            "lesson_id",
            "content_version",
            "title",
            "locale",
            "audience",
            "max_turns",
            "sequence",
            "review",
            "grounding",
            "check",
        },
        {"steps"},
    )

    schema_version = v.integer(top, "", "schema_version")
    if schema_version != SCHEMA_VERSION:
        v.fail("schema_version", f"expected {SCHEMA_VERSION}, got {schema_version}")

    lesson_id = v.identifier(top, "", "lesson_id")

    content_version = v.integer(top, "", "content_version")
    if content_version < 1:
        v.fail("content_version", "must be 1 or greater")

    max_turns = v.integer(top, "", "max_turns")
    low, high = MAX_TURNS_RANGE
    if not low <= max_turns <= high:
        v.fail("max_turns", f"must be between {low} and {high}, got {max_turns}")

    review = _parse_review(v, top["review"])
    is_draft = review.status is ApprovalStatus.DRAFT

    grounding = _parse_grounding(v, top["grounding"])
    known_facts = {fact.id for fact in grounding.facts}

    steps = _parse_steps(v, top.get("steps"), is_draft=is_draft, known_facts=known_facts)
    check = _parse_check(v, top["check"], known_facts=known_facts)

    sequence = v.str_list(top, "", "sequence")
    if not sequence:
        v.fail("sequence", "a lesson must declare its step order explicitly")
    seen_seq: set[str] = set()
    for item in sequence:
        if item in seen_seq:
            v.fail("sequence", f"duplicate sequence id {item!r}")
        seen_seq.add(item)
    step_ids = [step.id for step in steps]
    dangling = [s for s in sequence if s not in step_ids]
    if dangling:
        v.fail("sequence", f"references missing step(s): {', '.join(dangling)}")
    orphans = [s for s in step_ids if s not in seen_seq]
    if orphans:
        v.fail("steps", f"authored step(s) absent from sequence: {', '.join(orphans)}")
    if list(sequence) != step_ids:
        v.fail("sequence", "sequence order must match authored step order")

    # Repeated visuals must agree on their hash, or package identity is ambiguous.
    by_resource: dict[str, str | None] = {}
    for step in steps:
        if step.visual is None:
            continue
        prior = by_resource.setdefault(step.visual.resource_name, step.visual.sha256)
        if prior != step.visual.sha256:
            v.fail("steps", f"inconsistent sha256 for asset {step.visual.resource_name!r}")

    lesson = Lesson(
        schema_version=schema_version,
        id=lesson_id,
        content_version=content_version,
        title=v.text(top, "", "title"),
        locale=v.text(top, "", "locale"),
        audience=v.text(top, "", "audience"),
        max_turns=max_turns,
        review=review,
        sequence=sequence,
        steps=steps,
        check=check,
        grounding=grounding,
    )

    # An approval is only meaningful if it names the payload actually present.
    if not is_draft:
        actual = lesson_payload_sha256(lesson)
        for attestation in review.attestations:
            if attestation.reviewed_payload_sha256 != actual:
                v.fail(
                    "review.attestations",
                    f"attestation {attestation.id!r} approves payload "
                    f"{attestation.reviewed_payload_sha256} but this lesson is {actual}",
                )

    return lesson


def _sorted_tokens(terms: frozenset[str]) -> list[str]:
    """Sort canonical tokens by UTF-8 bytes, matching PR-09's CSV compilation."""
    return sorted(terms, key=lambda s: s.encode("utf-8"))


def _lesson_payload(lesson: Lesson) -> dict[str, Any]:
    """Build the review-independent payload that content identity hashes.

    ``review`` is the only omitted field. That omission is the whole point: a
    reviewer's role, date, or evidence reference can change without changing
    what the child sees, so it must not change the hash their approval is bound
    to. Anything child-visible or grounding/runtime-affecting is included.
    """
    referenced: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    for step in lesson.steps:
        if step.visual is None:
            continue
        key = (step.visual.resource_name, step.visual.media_type, step.visual.sha256)
        referenced[key] = {
            "resource_name": step.visual.resource_name,
            "media_type": step.visual.media_type,
            "sha256": step.visual.sha256,
        }

    return {
        "schema_version": lesson.schema_version,
        "id": lesson.id,
        "content_version": lesson.content_version,
        "title": lesson.title,
        "locale": lesson.locale,
        "audience": lesson.audience,
        "max_turns": lesson.max_turns,
        "sequence": list(lesson.sequence),
        "steps": [
            {
                "id": step.id,
                "kind": step.kind.value,
                "heading": step.heading,
                "body": step.body,
                "visual": None
                if step.visual is None
                else {
                    "resource_name": step.visual.resource_name,
                    "media_type": step.visual.media_type,
                    "alt_text": step.visual.alt_text,
                    "sha256": step.visual.sha256,
                },
                "fact_ids": list(step.fact_ids),
                "scope_terms": _sorted_tokens(step.scope_terms),
            }
            for step in lesson.steps
        ],
        "check": {
            "id": lesson.check.id,
            "prompt": lesson.check.prompt,
            "choices": [{"id": c.id, "label": c.label} for c in lesson.check.choices],
            "correct_choice_id": lesson.check.correct_choice_id,
            "hints": list(lesson.check.hints),
            "success_text": lesson.check.success_text,
            "reveal_text": lesson.check.reveal_text,
            "fact_ids": list(lesson.check.fact_ids),
            "scope_terms": _sorted_tokens(lesson.check.scope_terms),
            "allowed_short_replies": _sorted_tokens(lesson.check.allowed_short_replies),
        },
        "grounding": {
            "scope": lesson.grounding.scope,
            "fallback_text": lesson.grounding.fallback_text,
            "redirect_text": lesson.grounding.redirect_text,
            "facts": [
                {
                    "id": f.id,
                    "canonical_text": f.canonical_text,
                    "child_text": f.child_text,
                    "source_ids": list(f.source_ids),
                    "allowed_numbers": list(f.allowed_numbers),
                }
                for f in lesson.grounding.facts
            ],
            "sources": [
                {
                    "id": s.id,
                    "title": s.title,
                    "publisher": s.publisher,
                    "url": s.url,
                    "retrieved_on": s.retrieved_on.isoformat(),
                }
                for s in lesson.grounding.sources
            ],
        },
        "referenced_assets": [
            referenced[key]
            for key in sorted(
                referenced,
                key=lambda k: (k[0].encode("utf-8"), k[1].encode("utf-8"), (k[2] or "").encode()),
            )
        ],
    }


def lesson_payload_sha256(lesson: Lesson) -> str:
    """Return the canonical review-independent content hash for ``lesson``.

    This is the value every review attestation records. It changes for any
    child-visible or grounding change and for any asset change, but not for a
    change to reviewer role, date, or evidence reference.

    Args:
        lesson: A parsed lesson.

    Returns:
        Lowercase 64-character hex SHA-256.
    """
    return hashlib.sha256(canonical_json_bytes(_lesson_payload(lesson))).hexdigest()


class LessonCatalog(Protocol):
    """Source of lessons a session may use."""

    def load(self, lesson_id: str) -> Lesson: ...

    def read_asset(self, asset: AssetRef) -> bytes: ...

    def identity(self, lesson_id: str) -> LessonPackageIdentity: ...


def _read_bounded(package: str, resource: str, limit: int, *, what: str) -> bytes:
    """Read at most ``limit`` bytes plus one, rejecting anything larger.

    Reading limit+1 and checking is what makes the bound meaningful: it fails
    before a full decode or allocation, not after.
    """
    try:
        handle = resources.files(package).joinpath(resource).open("rb")
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise LessonNotFoundError(f"{resource}: not present in package {package}") from exc
    with handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise LessonContentError(f"{resource}: {what} exceeds {limit} bytes")
    return data


class _IndexEntry:
    __slots__ = ("resource_name", "sha256", "lesson_payload_sha256", "media_type")

    def __init__(
        self,
        resource_name: str,
        sha256: str,
        lesson_payload_sha256: str | None = None,
        media_type: str | None = None,
    ) -> None:
        self.resource_name = resource_name
        self.sha256 = sha256
        self.lesson_payload_sha256 = lesson_payload_sha256
        self.media_type = media_type


class PackageLessonCatalog:
    """The child-safe boundary over packaged lesson resources.

    :meth:`load` returns a lesson only when it is approved, its bytes match the
    package index, and its independently recomputed payload hash matches what
    every attestation records. A draft, a tampered asset, or a stale index all
    fail closed.
    """

    def __init__(self, package: str = LESSON_PACKAGE) -> None:
        self._package = package
        self._index: dict[str, _IndexEntry] | None = None
        self._assets: dict[str, _IndexEntry] | None = None

    def _load_index(self) -> tuple[dict[str, _IndexEntry], dict[str, _IndexEntry]]:
        if self._index is not None and self._assets is not None:
            return self._index, self._assets

        raw = _read_bounded(
            self._package, LESSON_INDEX_RESOURCE, INDEX_BYTE_LIMIT, what="lesson index"
        )
        v = _V(LESSON_INDEX_RESOURCE)
        try:
            table = tomllib.loads(raw.decode("utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
            v.fail("<document>", f"malformed TOML: {exc}")

        top = v.keys(table, "", {"schema_version"}, {"lessons", "assets"})
        if v.integer(top, "", "schema_version") != SCHEMA_VERSION:
            v.fail("schema_version", f"expected {SCHEMA_VERSION}")

        lessons: dict[str, _IndexEntry] = {}
        for i, entry in enumerate(top.get("lessons", [])):
            path = f"lessons[{i}]"
            e = v.keys(
                entry,
                path,
                {"lesson_id", "resource_name", "sha256", "lesson_payload_sha256"},
            )
            lesson_id = v.identifier(e, path, "lesson_id")
            if lesson_id in lessons:
                v.fail(path, f"duplicate lesson_id {lesson_id!r}")
            for key in ("sha256", "lesson_payload_sha256"):
                if not SHA256_RE.fullmatch(v.text(e, path, key)):
                    v.fail(f"{path}.{key}", "expected a lowercase 64-hex SHA-256")
            lessons[lesson_id] = _IndexEntry(
                resource_name=v.text(e, path, "resource_name"),
                sha256=e["sha256"],
                lesson_payload_sha256=e["lesson_payload_sha256"],
            )

        assets: dict[str, _IndexEntry] = {}
        for i, entry in enumerate(top.get("assets", [])):
            path = f"assets[{i}]"
            e = v.keys(entry, path, {"resource_name", "media_type", "sha256"})
            name = v.text(e, path, "resource_name")
            if name in assets:
                v.fail(path, f"duplicate asset {name!r}")
            if not SHA256_RE.fullmatch(v.text(e, path, "sha256")):
                v.fail(f"{path}.sha256", "expected a lowercase 64-hex SHA-256")
            media_type = v.text(e, path, "media_type")
            if media_type not in SUPPORTED_MEDIA_TYPES:
                v.fail(f"{path}.media_type", f"unsupported media type {media_type!r}")
            assets[name] = _IndexEntry(
                resource_name=name, sha256=e["sha256"], media_type=media_type
            )

        self._index, self._assets = lessons, assets
        return lessons, assets

    def load(self, lesson_id: str) -> Lesson:
        """Return the approved, hash-verified lesson for ``lesson_id``.

        Raises:
            LessonNotFoundError: No such lesson in the package index.
            LessonNotApprovedError: The lesson exists but is still draft.
            LessonContentError: Byte, index, or payload hash mismatch.
        """
        lessons, _ = self._load_index()
        entry = lessons.get(lesson_id)
        if entry is None:
            raise LessonNotFoundError(f"{lesson_id}: not present in the lesson index")

        data = _read_bounded(
            self._package, entry.resource_name, LESSON_BYTE_LIMIT, what="lesson TOML"
        )
        actual = hashlib.sha256(data).hexdigest()
        if actual != entry.sha256:
            raise LessonContentError(
                f"{entry.resource_name}: bytes hash {actual}, index expects {entry.sha256}"
            )

        lesson = parse_lesson_toml(data.decode("utf-8"), origin=entry.resource_name)

        if lesson.review.status is not ApprovalStatus.APPROVED:
            raise LessonNotApprovedError(
                f"{lesson_id}: status is {lesson.review.status.value}; "
                "a child catalog serves approved content only"
            )
        if lesson.id != lesson_id:
            raise LessonContentError(
                f"{entry.resource_name}: declares id {lesson.id!r}, indexed as {lesson_id!r}"
            )

        payload = lesson_payload_sha256(lesson)
        if payload != entry.lesson_payload_sha256:
            raise LessonContentError(
                f"{entry.resource_name}: payload hash {payload}, "
                f"index expects {entry.lesson_payload_sha256}"
            )
        return lesson

    def read_asset(self, asset: AssetRef) -> bytes:
        """Return asset bytes, verified four ways before the renderer sees them.

        The resource must be indexed, its media type must match, the reference's
        own hash must match the index, and the bytes must hash to the same value.

        Raises:
            LessonNotFoundError: The asset is not in the package index.
            LessonContentError: Any media type or hash mismatch.
        """
        _, assets = self._load_index()
        entry = assets.get(asset.resource_name)
        if entry is None:
            raise LessonNotFoundError(f"{asset.resource_name}: not present in the asset index")
        if asset.media_type != entry.media_type:
            raise LessonContentError(
                f"{asset.resource_name}: media type {asset.media_type!r} "
                f"does not match indexed {entry.media_type!r}"
            )
        if asset.sha256 != entry.sha256:
            raise LessonContentError(
                f"{asset.resource_name}: reference hash {asset.sha256} "
                f"does not match indexed {entry.sha256}"
            )
        data = _read_bounded(self._package, asset.resource_name, ASSET_BYTE_LIMIT, what="asset")
        actual = hashlib.sha256(data).hexdigest()
        if actual != entry.sha256:
            raise LessonContentError(
                f"{asset.resource_name}: bytes hash {actual}, index expects {entry.sha256}"
            )
        return data

    def identity(self, lesson_id: str) -> LessonPackageIdentity:
        """Return the package and payload identity of an approved lesson."""
        lessons, _ = self._load_index()
        entry = lessons.get(lesson_id)
        if entry is None:
            raise LessonNotFoundError(f"{lesson_id}: not present in the lesson index")
        lesson = self.load(lesson_id)
        assert entry.lesson_payload_sha256 is not None
        return LessonPackageIdentity(
            lesson_id=lesson_id,
            content_version=lesson.content_version,
            package_sha256=entry.sha256,
            lesson_payload_sha256=entry.lesson_payload_sha256,
        )
