#!/usr/bin/env python3
"""Offline drafting checker for ``educator-paths-v1`` authoring CSVs.

This tool catches broken authoring artifacts and explains incomplete drafts. It
reads six CSV files, checks them against ``curation/schemas/educator-paths-v1.json``,
and prints what it found. It never writes, fixes, sorts, or renames anything; it
creates no database, fetches no URL, and generates no review hash or attestation.

Structural validity is not approval. A clean report means the IDs, references,
and path order are coherent. It says nothing about scientific accuracy, fit for
a particular child, or whether a human review happened.

Usage, from the repository root::

    python scripts/validate_curation_templates.py --templates curation/templates/educator-paths-v1
    python scripts/validate_curation_templates.py --bundle curation/examples/educator-paths-v1-draft
    python scripts/validate_curation_templates.py --bundle DIR --json

Exit status:
    0  structurally valid (incomplete draft activities are still valid)
    1  at least one data error
    2  invalid command line, or an input that could not be read at all

Parsing choices (documented in plans/specs/08c-educator-path-authoring.md):
    - UTF-8 with or without a leading byte-order mark; LF or CRLF line endings.
    - A record whose cells are all empty or whitespace is ignored. It still
      counts toward record numbering so locations match the file.
    - Record numbers are logical CSV records with the header as record 1, so a
      quoted multi-line cell does not shift later numbers.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "curation" / "schemas" / "educator-paths-v1.json"

NOTICE = (
    "Structural checks only. A valid result, a complete activity, or a 'reviewed' "
    "status does not approve content, qualify the app, or make anything ready for a child."
)
FORMULA_PREFIXES = ("=", "+", "-", "@")
SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class Issue:
    """One diagnostic.

    Attributes:
        code: Stable machine-readable rule identifier, e.g. ``"unknown-reference"``.
        severity: ``"error"``, ``"warning"``, or ``"info"``.
        table: Table name such as ``"PATH_STEPS"``, or ``None`` for bundle-level issues.
        record_number: Logical CSV record number (header = 1), or ``None``.
        record_id: The record's primary key, only when it is a well-formed ID.
        field: Column the issue concerns, or ``None``.
        message: Explanation of the rule. Never contains raw cell text.
    """

    code: str
    severity: str
    table: str | None
    record_number: int | None
    record_id: str | None
    field: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable form used by ``--json``."""
        return {
            "code": self.code,
            "severity": self.severity,
            "table": self.table,
            "record_number": self.record_number,
            "record_id": self.record_id,
            "field": self.field,
            "message": self.message,
        }


@dataclass
class Record:
    """One populated CSV record, keyed by column name."""

    number: int
    values: dict[str, str]


@dataclass
class TableData:
    """Parsed contents of one table; ``usable`` is False when the header was wrong."""

    spec: dict[str, Any]
    usable: bool = False
    records: list[Record] = field(default_factory=list)


class InputUnreadable(Exception):
    """Raised when an input cannot be read at all (exit status 2)."""


class Checker:
    """Validate one directory of educator-paths-v1 CSVs against the schema metadata.

    Args:
        schema: Parsed contents of ``educator-paths-v1.json``.
        directory: Folder holding the six CSV files.
        template_mode: When True, every data table must be header-only.

    Example:
        >>> checker = Checker(load_schema(), Path("curation/examples/educator-paths-v1-draft"),
        ...                   template_mode=False)  # doctest: +SKIP
        >>> report = checker.run()  # doctest: +SKIP
    """

    def __init__(self, schema: dict[str, Any], directory: Path, template_mode: bool) -> None:
        self.schema = schema
        self.directory = directory
        self.template_mode = template_mode
        self.id_re = re.compile(schema["id_pattern"])
        self.int_re = re.compile(schema["integer_pattern"])
        self.sep: str = schema["list_separator"]
        self.table_order = [t["name"] for t in schema["tables"]]
        self.tables: dict[str, TableData] = {t["name"]: TableData(spec=t) for t in schema["tables"]}
        self.issues: list[Issue] = []
        # Primary key -> record, for well-formed, first-seen IDs only.
        self.index: dict[str, dict[str, Record]] = {name: {} for name in self.table_order}

    # ---------------------------------------------------------------- helpers

    def _issue(
        self,
        code: str,
        severity: str,
        message: str,
        table: str | None = None,
        record: Record | None = None,
        field_name: str | None = None,
    ) -> None:
        record_id = None
        if record is not None and table is not None:
            pk = self.tables[table].spec["primary_key"]
            candidate = record.values.get(pk, "")
            if self.id_re.fullmatch(candidate):
                record_id = candidate
        self.issues.append(
            Issue(
                code=code,
                severity=severity,
                table=table,
                record_number=record.number if record is not None else None,
                record_id=record_id,
                field=field_name,
                message=message,
            )
        )

    def _is_id(self, value: str) -> bool:
        return bool(self.id_re.fullmatch(value))

    def _list_items(self, value: str) -> list[str]:
        return value.split(self.sep) if value else []

    # ---------------------------------------------------------------- reading

    def _read_table(self, data: TableData) -> None:
        spec = data.spec
        name, path = spec["name"], self.directory / spec["file"]
        if not path.exists():
            self._issue("missing-file", "error", f"expected file {spec['file']} is absent", name)
            return
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise InputUnreadable(f"cannot read {spec['file']}: {exc.strerror}") from None
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            self._issue("malformed-utf8", "error", "file is not valid UTF-8 text", name)
            return
        try:
            rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
        except csv.Error:
            self._issue(
                "malformed-csv", "error", "file is not well-formed CSV (check quotes)", name
            )
            return
        if not rows:
            self._issue(
                "header-missing", "error", "file is empty; the header row is required", name
            )
            return
        header, expected = rows[0], spec["columns"]
        if not self._header_ok(name, header, expected):
            return
        data.usable = True
        for number, row in enumerate(rows[1:], start=2):
            if all(not cell.strip() for cell in row):
                continue  # wholly empty records are ignored (see module docstring)
            record = Record(number, {})
            if len(row) != len(expected):
                self._issue(
                    "row-width",
                    "error",
                    f"record has {len(row)} cells; the header has {len(expected)}",
                    name,
                    record,
                )
                continue
            record.values = dict(zip(expected, row, strict=True))
            if self.template_mode:
                self._issue(
                    "template-has-data",
                    "error",
                    "blank templates must be header-only",
                    name,
                    record,
                )
                continue
            data.records.append(record)

    def _header_ok(self, table: str, header: list[str], expected: list[str]) -> bool:
        ok = True
        seen: set[str] = set()
        for column in header:
            if column in seen:
                self._issue("header-duplicate", "error", "a column name appears twice", table)
                ok = False
            seen.add(column)
        unknown = [c for c in header if c not in expected]
        missing = [c for c in expected if c not in header]
        if unknown:
            self._issue(
                "header-unknown", "error", f"{len(unknown)} column(s) not in {table}", table
            )
            ok = False
        for column in missing:
            self._issue(
                "header-missing", "error", "required column is absent", table, field_name=column
            )
            ok = False
        if ok and header != expected:
            self._issue(
                "header-order", "error", "columns are present but not in contract order", table
            )
            ok = False
        return ok

    # ---------------------------------------------------------- record checks

    def _check_record(self, table: str, spec: dict[str, Any], record: Record) -> None:
        values = record.values
        for column in spec["required"]:
            if not values[column].strip():
                self._issue(
                    "required-missing", "error", "required field is blank", table, record, column
                )

        pk = spec["primary_key"]
        pk_value = values[pk]
        if pk_value.strip() and not self._is_id(pk_value):
            self._issue(
                "invalid-id", "error", "ID must match [a-z][a-z0-9-]{0,79}", table, record, pk
            )
        elif pk_value:
            if pk_value in self.index[table]:
                first = self.index[table][pk_value].number
                self._issue(
                    "duplicate-id",
                    "error",
                    f"ID {pk_value!r} already used by record {first}",
                    table,
                    record,
                    pk,
                )
            else:
                self.index[table][pk_value] = record

        for column, target in spec["references"].items():
            if column in spec["list_columns"]:
                continue  # checked with the other list columns below
            value = values[column]
            if value.strip() and not self._is_id(value):
                self._issue(
                    "invalid-id", "error", f"reference must be a {target} ID", table, record, column
                )

        for column in spec["list_columns"]:
            self._check_list(table, spec, record, column)

        for column in spec["integer_columns"]:
            value = values[column]
            if value and not self.int_re.fullmatch(value):
                self._issue(
                    "invalid-integer",
                    "error",
                    "must be a positive whole number written as digits (1, 2, 3 ...)",
                    table,
                    record,
                    column,
                )

        if "status" in values:
            self._check_status_and_review(table, spec, record)

        if table == "RELATIONSHIPS":
            rel_type = values["relationship_type"]
            if rel_type and rel_type not in self.schema["relationship_types"]:
                self._issue(
                    "invalid-relationship-type",
                    "error",
                    "relationship_type must be one of: "
                    + ", ".join(self.schema["relationship_types"]),
                    table,
                    record,
                    "relationship_type",
                )
        if table in ("RELATIONSHIPS", "CONNECTIONS"):
            src, dst = values["from_node_id"], values["to_node_id"]
            if src and src == dst:
                self._issue(
                    "self-link",
                    "error",
                    "a record may not link a node to itself; a revisit is a later path step",
                    table,
                    record,
                    "to_node_id",
                )

        for column, value in values.items():
            if self._looks_like_formula(value):
                self._issue(
                    "formula-like-text",
                    "warning",
                    "text begins with a spreadsheet formula character; keep it literal "
                    "(the checker does not evaluate or change it)",
                    table,
                    record,
                    column,
                )

    def _check_list(self, table: str, spec: dict[str, Any], record: Record, column: str) -> None:
        value = record.values[column]
        if not value:
            return
        items = self._list_items(value)
        seen: set[str] = set()
        is_ref = column in spec["references"]
        for item in items:
            if item == "":
                self._issue(
                    "list-empty-token",
                    "error",
                    "list has an empty item (doubled, leading, or trailing |)",
                    table,
                    record,
                    column,
                )
                continue
            if item != item.strip():
                self._issue(
                    "list-token-whitespace",
                    "error",
                    "list item has spaces next to the | separator",
                    table,
                    record,
                    column,
                )
            if item in seen:
                self._issue(
                    "list-duplicate-token", "error", "list repeats an item", table, record, column
                )
            seen.add(item)
            if is_ref and item.strip() and not self._is_id(item.strip()):
                self._issue(
                    "invalid-id",
                    "error",
                    "list item is not a well-formed ID",
                    table,
                    record,
                    column,
                )

    def _check_status_and_review(self, table: str, spec: dict[str, Any], record: Record) -> None:
        values = record.values
        status = values["status"]
        if status and status not in self.schema["statuses"]:
            self._issue(
                "invalid-status",
                "error",
                "status must be one of: " + ", ".join(self.schema["statuses"]),
                table,
                record,
                "status",
            )
        if not spec["has_review"]:
            return
        role, date = values["reviewer_role"], values["review_date"]
        if role and role not in self.schema["reviewer_roles"]:
            self._issue(
                "invalid-reviewer-role",
                "error",
                "reviewer_role must be one of: " + ", ".join(self.schema["reviewer_roles"]),
                table,
                record,
                "reviewer_role",
            )
        if date and not _valid_iso_date(date):
            self._issue(
                "invalid-date",
                "error",
                "review_date must be a real calendar date written YYYY-MM-DD",
                table,
                record,
                "review_date",
            )
        if status == "reviewed" and not (role and date):
            for column, value in (("reviewer_role", role), ("review_date", date)):
                if not value:
                    self._issue(
                        "reviewed-missing-metadata",
                        "error",
                        "status 'reviewed' needs the real reviewer role and review date; "
                        "the checker never fills these in",
                        table,
                        record,
                        column,
                    )
        elif bool(role) != bool(date):
            missing = "review_date" if role else "reviewer_role"
            self._issue(
                "review-pair-incomplete",
                "error",
                "reviewer_role and review_date are recorded together or not at all",
                table,
                record,
                missing,
            )
        if status in ("draft", "needs_revision") and (role or date):
            self._issue(
                "review-metadata-without-review",
                "warning",
                f"status '{status}' should not carry review metadata; clear stale values",
                table,
                record,
                "reviewer_role" if role else "review_date",
            )

    def _looks_like_formula(self, value: str) -> bool:
        if not value:
            return False
        normalized = unicodedata.normalize("NFKC", value)
        stripped = normalized.lstrip(
            "".join(
                ch
                for ch in set(normalized)
                if ch.isspace() or unicodedata.category(ch) in ("Cc", "Cf")
            )
        )
        return stripped.startswith(FORMULA_PREFIXES)

    # ------------------------------------------------------- cross-table checks

    def _check_references(self) -> None:
        for table in self.table_order:
            data = self.tables[table]
            for record in data.records:
                for column, target in data.spec["references"].items():
                    if not self.tables[target].usable:
                        continue  # the target's own header error is already reported
                    raw = record.values[column]
                    items = self._list_items(raw) if column in data.spec["list_columns"] else [raw]
                    for item in items:
                        item = item.strip()
                        if not item or not self._is_id(item):
                            continue
                        target_record = self.index[target].get(item)
                        if target_record is None:
                            self._issue(
                                "unknown-reference",
                                "error",
                                f"{item!r} is not defined in {target}",
                                table,
                                record,
                                column,
                            )
                        elif (
                            target_record.values.get("status") == "retired"
                            and record.values.get("status") != "retired"
                        ):
                            self._issue(
                                "references-retired",
                                "warning",
                                f"{item!r} in {target} is retired; choose a current record",
                                table,
                                record,
                                column,
                            )
                if (
                    data.spec["has_review"]
                    and record.values.get("status") == "draft"
                    and not record.values.get("source_ids")
                ):
                    self._issue(
                        "draft-without-sources",
                        "warning",
                        "no sources listed yet; a blank list is fine for a draft but is not "
                        "evidence for later publication",
                        table,
                        record,
                        "source_ids",
                    )

    def _check_relationships(self) -> None:
        symmetric = set(self.schema["symmetric_relationship_types"])
        seen: dict[tuple[str, str, str], int] = {}
        for record in self.tables["RELATIONSHIPS"].records:
            v = record.values
            src, rel, dst = v["from_node_id"], v["relationship_type"], v["to_node_id"]
            if not (src and rel and dst):
                continue
            ends = tuple(sorted((src, dst))) if rel in symmetric else (src, dst)
            key = (ends[0], rel, ends[1])
            if key in seen:
                self._issue(
                    "duplicate-relationship",
                    "error",
                    f"repeats the relationship in record {seen[key]}"
                    + (" (related_to has no direction)" if rel in symmetric else ""),
                    "RELATIONSHIPS",
                    record,
                    "to_node_id",
                )
            else:
                seen[key] = record.number
        for rel_type in self.schema["taxonomy_relationship_types"]:
            edges = [
                r
                for r in self.tables["RELATIONSHIPS"].records
                if r.values["relationship_type"] == rel_type
                and r.values["from_node_id"] != r.values["to_node_id"]
            ]
            pairs = [(r.values["from_node_id"], r.values["to_node_id"]) for r in edges]
            component = _cycle_components(pairs)
            for r in edges:
                src, dst = r.values["from_node_id"], r.values["to_node_id"]
                if src in component and component.get(dst) == component[src]:
                    self._issue(
                        "taxonomy-cycle",
                        "warning",
                        f"this {rel_type} record is part of a cycle; a kind-of or part-of "
                        "chain that loops back is usually a modeling mistake - please review",
                        "RELATIONSHIPS",
                        r,
                        "to_node_id",
                    )

    def _check_paths(self) -> None:
        if not (self.tables["PATHS"].usable and self.tables["PATH_STEPS"].usable):
            return
        steps_by_path: dict[str, list[tuple[int, Record]]] = {}
        for record in self.tables["PATH_STEPS"].records:
            v = record.values
            if v["path_id"] in self.index["PATHS"] and self.int_re.fullmatch(v["sequence"]):
                steps_by_path.setdefault(v["path_id"], []).append((int(v["sequence"]), record))

        for path_id, path in self.index["PATHS"].items():
            steps = sorted(steps_by_path.get(path_id, []), key=lambda s: (s[0], s[1].number))
            if not steps:
                self._issue(
                    "path-without-steps",
                    "warning",
                    "path has no steps yet; it is an outline, not a usable route",
                    "PATHS",
                    path,
                    "path_id",
                )
                continue
            by_position: dict[int, list[Record]] = {}
            for position, record in steps:
                by_position.setdefault(position, []).append(record)
            for _position, records in by_position.items():
                for duplicate in records[1:]:
                    self._issue(
                        "duplicate-sequence",
                        "error",
                        f"path {path_id!r} already has a step at this sequence (record "
                        f"{records[0].number}); nothing is renumbered automatically",
                        "PATH_STEPS",
                        duplicate,
                        "sequence",
                    )
            expected = 1
            for position in sorted(by_position):
                if position != expected:
                    self._issue(
                        "sequence-gap",
                        "error",
                        f"path {path_id!r} skips sequence {expected}"
                        + (f"-{position - 1}" if position - 1 > expected else "")
                        + "; sequences start at 1 with no gaps",
                        "PATH_STEPS",
                        by_position[position][0],
                        "sequence",
                    )
                expected = position + 1
            self._check_continuity(path_id, path, by_position)

    def _check_continuity(
        self, path_id: str, path: Record, by_position: dict[int, list[Record]]
    ) -> None:
        for position in sorted(by_position):
            records = by_position[position]
            if len(records) != 1:
                continue  # ambiguous position; duplicate-sequence already reported
            step = records[0]
            connection = self.index["CONNECTIONS"].get(step.values["connection_id"])
            if connection is None:
                continue  # unknown-reference already reported
            c_from, c_to = connection.values["from_node_id"], connection.values["to_node_id"]
            if c_to != step.values["target_node_id"]:
                self._issue(
                    "connection-destination-mismatch",
                    "error",
                    "the connection must end at this step's target_node_id",
                    "PATH_STEPS",
                    step,
                    "connection_id",
                )
            if position == 1:
                if c_from != path.values["entry_node_id"]:
                    self._issue(
                        "first-connection-origin-mismatch",
                        "error",
                        f"the first step's connection must start at path {path_id!r}'s "
                        "entry_node_id",
                        "PATH_STEPS",
                        step,
                        "connection_id",
                    )
                continue
            previous = by_position.get(position - 1)
            if previous is None or len(previous) != 1:
                continue  # gap or duplicate already reported; the origin is ambiguous
            if c_from != previous[0].values["target_node_id"]:
                self._issue(
                    "connection-origin-mismatch",
                    "error",
                    "this connection must start at the previous step's target_node_id",
                    "PATH_STEPS",
                    step,
                    "connection_id",
                )

    def _activity_completeness(self) -> list[dict[str, Any]]:
        spec = self.tables["PATH_STEPS"].spec
        fields = spec["activity_fields"]
        report = []
        for record in self.tables["PATH_STEPS"].records:
            missing = [f for f in fields if not record.values[f].strip()]
            for column in missing:
                self._issue(
                    "activity-field-missing",
                    "info",
                    "not prepared yet; complete and review before this activity is tried",
                    "PATH_STEPS",
                    record,
                    column,
                )
            step_id = record.values["path_step_id"]
            report.append(
                {
                    "path_step_id": step_id if self._is_id(step_id) else None,
                    "record_number": record.number,
                    "filled": len(fields) - len(missing),
                    "total": len(fields),
                    "missing": missing,
                }
            )
        return sorted(report, key=lambda r: (r["path_step_id"] or "", r["record_number"]))

    # -------------------------------------------------------------------- run

    def run(self) -> dict[str, Any]:
        """Check the directory and return the report dictionary.

        Returns:
            A dict with ``schema_version``, ``mode``, ``counts``, ``summary``,
            ``issues``, ``activity_completeness``, and ``notice`` keys.

        Raises:
            InputUnreadable: when a file exists but cannot be read.
        """
        known = {t["file"] for t in self.schema["tables"]} | set(self.schema["helper_files"])
        for extra in sorted(p.name for p in self.directory.glob("*.csv")):
            if extra not in known:
                self._issue(
                    "unexpected-file",
                    "warning",
                    f"{extra} is not part of educator-paths-v1 and was not checked",
                )
        for name in self.table_order:
            self._read_table(self.tables[name])
        for name in self.table_order:
            data = self.tables[name]
            for record in data.records:
                self._check_record(name, data.spec, record)
        self._check_references()
        if self.tables["RELATIONSHIPS"].usable:
            self._check_relationships()
        if self.tables["CONNECTIONS"].usable:
            self._check_paths()
        completeness = self._activity_completeness() if self.tables["PATH_STEPS"].usable else []

        order = {name: i for i, name in enumerate(self.table_order)}
        issues = sorted(
            set(self.issues),
            key=lambda i: (
                -1 if i.table is None else order[i.table],
                i.record_number or 0,
                i.field or "",
                i.code,
                i.message,
            ),
        )
        summary = {sev: sum(1 for i in issues if i.severity == sev) for sev in SEVERITY_RANK}
        return {
            "schema_version": self.schema["schema_version"],
            "mode": "templates" if self.template_mode else "bundle",
            "counts": {name: len(self.tables[name].records) for name in self.table_order},
            "summary": summary,
            "issues": [i.as_dict() for i in issues],
            "activity_completeness": completeness,
            "notice": NOTICE,
        }


def _valid_iso_date(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _cycle_components(edges: list[tuple[str, str]]) -> dict[str, int]:
    """Map each node on a directed cycle to its strongly connected component.

    Uses Kosaraju's algorithm. Nodes not on any cycle are absent from the result,
    so an edge lies on a cycle exactly when both ends map to the same component.

    Example:
        >>> sorted(_cycle_components([("a", "b"), ("b", "a"), ("b", "c")]).items())
        [('a', 0), ('b', 0)]
    """
    graph: dict[str, list[str]] = {}
    reverse: dict[str, list[str]] = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, [])
        reverse.setdefault(b, []).append(a)
        reverse.setdefault(a, [])
    order: list[str] = []
    visited: set[str] = set()
    for start in sorted(graph):
        if start in visited:
            continue
        stack = [(start, iter(graph[start]))]
        visited.add(start)
        while stack:
            node, children = stack[-1]
            for child in children:
                if child not in visited:
                    visited.add(child)
                    stack.append((child, iter(graph[child])))
                    break
            else:
                order.append(node)
                stack.pop()
    assigned: set[str] = set()
    cyclic: dict[str, int] = {}
    for start in reversed(order):
        if start in assigned:
            continue
        component = []
        stack2 = [start]
        assigned.add(start)
        while stack2:
            node = stack2.pop()
            component.append(node)
            for parent in reverse[node]:
                if parent not in assigned:
                    assigned.add(parent)
                    stack2.append(parent)
        if len(component) > 1:
            label = len(set(cyclic.values()))
            cyclic.update(dict.fromkeys(component, label))
    return cyclic


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    """Load the educator-paths-v1 metadata.

    Args:
        path: Location of the JSON inventory; defaults to the repository copy.

    Returns:
        The parsed metadata dictionary.

    Raises:
        InputUnreadable: when the file is missing or not valid JSON.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputUnreadable(f"cannot load schema metadata: {type(exc).__name__}") from None


def format_text(report: dict[str, Any], directory_label: str) -> str:
    """Render a report for people.

    Args:
        report: Output of :meth:`Checker.run`.
        directory_label: How to name the checked folder in the heading.

    Returns:
        Multi-line plain text ending with the approval notice.
    """
    lines = [
        f"{report['schema_version']} {report['mode']} check: {directory_label}",
        "",
        "Records: " + ", ".join(f"{name} {n}" for name, n in report["counts"].items()),
    ]
    by_sev = {sev: [i for i in report["issues"] if i["severity"] == sev] for sev in SEVERITY_RANK}
    for severity, title in (("error", "Errors"), ("warning", "Warnings")):
        items = by_sev[severity]
        lines += ["", f"{title} ({len(items)}):"]
        if not items:
            lines.append("  none")
        for i in items:
            where = i["table"] or "bundle"
            if i["record_number"] is not None:
                where += f" record {i['record_number']}"
            if i["record_id"]:
                where += f" ({i['record_id']})"
            if i["field"]:
                where += f" {i['field']}"
            lines.append(f"  [{i['code']}] {where}: {i['message']}")
    if report["activity_completeness"]:
        lines += ["", "Activity preparation (drafting information, not errors):"]
        for step in report["activity_completeness"]:
            label = step["path_step_id"] or f"record {step['record_number']}"
            if step["missing"]:
                state = f"outline, missing {', '.join(step['missing'])}"
            else:
                state = "all activity fields filled (still needs real review)"
            lines.append(f"  {label}: {step['filled']}/{step['total']} - {state}")
    s = report["summary"]
    verdict = "structurally valid" if s["error"] == 0 else "NOT structurally valid"
    lines += [
        "",
        f"Result: {verdict} - {s['error']} error(s), {s['warning']} warning(s), "
        f"{s['info']} drafting note(s).",
        report["notice"],
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point. Returns the process exit status."""
    parser = argparse.ArgumentParser(
        description="Offline structural check for educator-paths-v1 authoring CSVs. "
        "Reads only; never approves content."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--templates", type=Path, help="blank template folder (header-only)")
    group.add_argument("--bundle", type=Path, help="draft bundle folder")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args(argv)  # exits with status 2 on usage errors

    directory: Path = args.templates or args.bundle
    try:
        if not directory.is_dir():
            raise InputUnreadable("the folder does not exist or is not a directory")
        schema = load_schema()
        report = Checker(schema, directory, template_mode=args.templates is not None).run()
    except InputUnreadable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(format_text(report, str(directory)), end="")
    return 1 if report["summary"]["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
