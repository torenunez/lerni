"""Tests for the educator-paths-v1 authoring contract and its offline checker.

Every mutation happens on a temporary copy of the shipped draft bundle. The
fixtures are synthetic edits made for these tests; they are not curriculum and
never contain approvals, review dates, or learner observations.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import random
import re
import shutil
import socket
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_curation_templates.py"
SCHEMA = json.loads((ROOT / "curation/schemas/educator-paths-v1.json").read_text())
TEMPLATES = ROOT / "curation/templates/educator-paths-v1"
EXAMPLES = ROOT / "curation/examples/educator-paths-v1-draft"
CONTRACT_DOC = ROOT / "plans/specs/08c-educator-path-authoring.md"
TABLES = {t["name"]: t for t in SCHEMA["tables"]}

_spec = importlib.util.spec_from_file_location("validate_curation_templates", SCRIPT)
assert _spec and _spec.loader
checker = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = checker  # dataclasses resolve their module during exec
_spec.loader.exec_module(checker)


# --------------------------------------------------------------------- helpers


def read_table(directory: Path, table: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(directory / TABLES[table]["file"], newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def write_table(directory: Path, table: str, header: list[str], rows: list[dict[str, str]]) -> None:
    with open(directory / TABLES[table]["file"], "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def append(directory: Path, table: str, **values: str) -> None:
    header, rows = read_table(directory, table)
    rows.append({column: values.get(column, "") for column in header})
    write_table(directory, table, header, rows)


def edit(directory: Path, table: str, record_id: str, **values: str) -> None:
    header, rows = read_table(directory, table)
    pk = TABLES[table]["primary_key"]
    matches = [r for r in rows if r[pk] == record_id]
    assert len(matches) == 1, record_id
    matches[0].update(values)
    write_table(directory, table, header, rows)


def run(
    directory: Path, capsys: pytest.CaptureFixture[str], mode: str = "--bundle"
) -> tuple[int, dict[str, Any]]:
    status = checker.main([mode, str(directory), "--json"])
    return status, json.loads(capsys.readouterr().out)


def issues(report: dict[str, Any], severity: str = "error") -> list[dict[str, Any]]:
    return [i for i in report["issues"] if i["severity"] == severity]


def keyed(report: dict[str, Any], severity: str = "error") -> set[tuple[Any, ...]]:
    return {(i["code"], i["table"], i["record_id"], i["field"]) for i in issues(report, severity)}


def digest_tree(directory: Path) -> dict[str, str]:
    return {
        str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def ordered_paths(directory: Path) -> dict[str, list[tuple[str, str, str]]]:
    """Rebuild every path by ID lookup and numeric sequence, ignoring row order."""
    _, steps = read_table(directory, "PATH_STEPS")
    paths: dict[str, list[tuple[int, tuple[str, str, str]]]] = {}
    for s in steps:
        paths.setdefault(s["path_id"], []).append(
            (int(s["sequence"]), (s["path_step_id"], s["target_node_id"], s["connection_id"]))
        )
    return {pid: [item for _, item in sorted(v)] for pid, v in paths.items()}


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    target = tmp_path / "bundle"
    shutil.copytree(EXAMPLES, target)
    return target


# ------------------------------------------------ contract, templates, examples


def test_blank_templates_have_exact_headers_and_no_records(
    capsys: pytest.CaptureFixture[str],
) -> None:
    for table, spec in TABLES.items():
        text = (TEMPLATES / spec["file"]).read_text(encoding="utf-8")
        assert text == ",".join(spec["columns"]) + "\n", table
    status, report = run(TEMPLATES, capsys, "--templates")
    assert status == 0
    assert report["issues"] == []
    assert set(report["counts"].values()) == {0}


def test_documented_contract_matches_schema_metadata() -> None:
    doc = CONTRACT_DOC.read_text(encoding="utf-8")
    blocks = re.findall(r"```csv\n(.*?)\n```", doc, flags=re.S)
    for spec in SCHEMA["tables"]:
        assert ",".join(spec["columns"]) in blocks, spec["name"]
        assert f"### {spec['file']}" in doc
    for value in SCHEMA["statuses"] + SCHEMA["relationship_types"] + SCHEMA["reviewer_roles"]:
        assert f"`{value}`" in doc


def test_lists_helper_matches_schema_enums() -> None:
    with open(TEMPLATES / "LISTS.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    got: dict[str, list[str]] = {}
    for row in rows:
        got.setdefault(row["list_name"], []).append(row["value"])
    assert got == {
        "status": SCHEMA["statuses"],
        "relationship_type": SCHEMA["relationship_types"],
        "reviewer_role": SCHEMA["reviewer_roles"],
    }


def test_example_bundle_is_valid_draft_with_visible_gaps(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status, report = run(EXAMPLES, capsys)
    assert status == 0
    assert issues(report) == []
    counts = report["counts"]
    assert counts["NODES"] >= 24 and counts["RELATIONSHIPS"] >= 30
    assert counts["CONNECTIONS"] >= 18 and counts["PATHS"] == 6 and counts["PATH_STEPS"] >= 24

    for table, spec in TABLES.items():
        if not spec["has_review"]:
            continue
        _, rows = read_table(EXAMPLES, table)
        assert {r["status"] for r in rows} == {"draft"}, table
        assert all(not r["reviewer_role"] and not r["review_date"] for r in rows), table

    steps = {s["path_step_id"]: s for s in report["activity_completeness"]}
    firsts = [sid for sid in steps if sid.endswith("-s01")]
    assert len(firsts) == 6 and all(steps[s]["missing"] == [] for s in firsts)
    later = [s for sid, s in steps.items() if not sid.endswith("-s01")]
    assert later and all(s["missing"] for s in later)


def test_example_bundle_demonstrates_reuse_branching_and_revisit() -> None:
    _, paths = read_table(EXAMPLES, "PATHS")
    entry = {p["path_id"]: p["entry_node_id"] for p in paths}
    assert entry["p-music-pulse"] == entry["p-music-pattern"] == "n-music"
    _, nodes = read_table(EXAMPLES, "NODES")
    assert [n["node_id"] for n in nodes].count("n-music") == 1

    routes = ordered_paths(EXAMPLES)
    assert [t for _, t, _ in routes["p-cars"]] == [
        "n-distance",
        "n-elapsed-time",
        "n-average-speed",
        "n-average-acceleration",
    ]
    assert "c-012" in {c for _, _, c in routes["p-music-pattern"]}
    assert "c-012" in {c for _, _, c in routes["p-cooking"]}

    building = routes["p-building"]
    assert building[0][1] == building[3][1] == "n-length"
    assert building[0][0] != building[3][0]
    _, steps = read_table(EXAMPLES, "PATH_STEPS")
    goals = {s["path_step_id"]: s["step_goal"] for s in steps}
    assert goals[building[0][0]] != goals[building[3][0]]

    _, connections = read_table(EXAMPLES, "CONNECTIONS")
    incoming: dict[str, int] = {}
    for c in connections:
        incoming[c["to_node_id"]] = incoming.get(c["to_node_id"], 0) + 1
    assert incoming["n-fractions"] >= 2 and incoming["n-measurement"] >= 3
    used = {c for route in routes.values() for _, _, c in route}
    assert {c["connection_id"] for c in connections} - used  # off-path branches exist


def test_legacy_reviews_tables_stay_header_only() -> None:
    for path in (
        ROOT / "curation/templates/v1/REVIEWS.csv",
        ROOT / "curation/examples/chain-1-v1-draft/REVIEWS.csv",
    ):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1, path


def test_checker_is_not_imported_by_the_application() -> None:
    for source in (ROOT / "src").rglob("*.py"):
        assert "validate_curation" not in source.read_text(encoding="utf-8"), source


# ------------------------------------------------------ order and extension


def test_shuffled_rows_keep_graph_identity_and_path_order(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before_paths = ordered_paths(bundle)
    _, before = run(bundle, capsys)
    rng = random.Random(20260925)
    for table in TABLES:
        header, rows = read_table(bundle, table)
        rng.shuffle(rows)
        write_table(bundle, table, header, rows)
    status, after = run(bundle, capsys)
    assert status == 0
    assert ordered_paths(bundle) == before_paths
    assert after["counts"] == before["counts"]
    assert keyed(after, "warning") == keyed(before, "warning")
    assert keyed(after, "info") == keyed(before, "info")


def test_appending_node_source_connection_and_step_is_valid(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    append(bundle, "SOURCES", source_id="s-test-ref", title="Synthetic", citation="Test fixture.")
    append(
        bundle,
        "NODES",
        node_id="n-test-jerk",
        label="Synthetic node",
        definition="A test-only concept.",
        source_ids="s-test-ref",
        status="draft",
    )
    append(
        bundle,
        "CONNECTIONS",
        connection_id="c-test-01",
        from_node_id="n-average-acceleration",
        to_node_id="n-test-jerk",
        learning_reason="Test-only transition.",
        status="draft",
    )
    append(
        bundle,
        "PATH_STEPS",
        path_step_id="p-cars-s05",
        path_id="p-cars",
        sequence="5",
        target_node_id="n-test-jerk",
        connection_id="c-test-01",
        step_goal="Test goal.",
        status="draft",
    )
    status, report = run(bundle, capsys)
    assert status == 0, issues(report)
    assert report["counts"]["NODES"] == 31 and report["counts"]["PATH_STEPS"] == 25


# ------------------------------------------------------------ record errors


def test_duplicate_primary_key_names_table_record_and_id(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    append(bundle, "NODES", node_id="n-music", label="Dup", definition="Dup.", status="draft")
    status, report = run(bundle, capsys)
    assert status == 1
    [dup] = [i for i in issues(report) if i["code"] == "duplicate-id"]
    assert (dup["table"], dup["record_id"], dup["field"], dup["record_number"]) == (
        "NODES",
        "n-music",
        "node_id",
        32,
    )


@pytest.mark.parametrize(
    ("table", "record_id", "column", "value"),
    [
        ("RELATIONSHIPS", "r-001", "to_node_id", "n-missing"),
        ("NODES", "n-cars", "source_ids", "s-nasa-motion|s-missing"),
        ("PATH_STEPS", "p-cars-s02", "path_id", "p-missing"),
        ("PATH_STEPS", "p-cars-s02", "connection_id", "c-missing"),
        ("PATHS", "p-cars", "entry_node_id", "n-missing"),
    ],
)
def test_missing_reference_is_reported_at_referencing_field(
    bundle: Path,
    capsys: pytest.CaptureFixture[str],
    table: str,
    record_id: str,
    column: str,
    value: str,
) -> None:
    edit(bundle, table, record_id, **{column: value})
    status, report = run(bundle, capsys)
    assert status == 1
    assert ("unknown-reference", table, record_id, column) in keyed(report)


@pytest.mark.parametrize(
    ("column", "value", "code"),
    [
        ("status", "approved", "invalid-status"),
        ("status", "Draft", "invalid-status"),
        ("reviewer_role", "teacher", "invalid-reviewer-role"),
        ("review_date", "2026-02-30", "invalid-date"),
        ("review_date", "09/25/2026", "invalid-date"),
        ("sequence", "0", "invalid-integer"),
        ("sequence", "2.0", "invalid-integer"),
        ("content_revision", "-1", "invalid-integer"),
    ],
)
def test_invalid_values_give_deterministic_field_errors(
    bundle: Path, capsys: pytest.CaptureFixture[str], column: str, value: str, code: str
) -> None:
    extra = {}
    if column in ("reviewer_role", "review_date"):  # keep the pair complete
        extra = {"reviewer_role": "educator", "review_date": "2026-09-01"}
    edit(bundle, "PATH_STEPS", "p-cars-s02", **{**extra, column: value})
    status, first = run(bundle, capsys)
    _, second = run(bundle, capsys)
    assert status == 1
    assert (code, "PATH_STEPS", "p-cars-s02", column) in keyed(first)
    assert first == second


def test_reviewed_without_metadata_is_an_error_and_is_not_filled_in(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit(bundle, "NODES", "n-rate", status="reviewed")
    before = digest_tree(bundle)
    status, report = run(bundle, capsys)
    assert status == 1
    assert {
        ("reviewed-missing-metadata", "NODES", "n-rate", f)
        for f in ("reviewer_role", "review_date")
    } <= keyed(report)
    assert digest_tree(bundle) == before


def test_review_pair_must_be_complete(bundle: Path, capsys: pytest.CaptureFixture[str]) -> None:
    edit(bundle, "CONNECTIONS", "c-005", reviewer_role="parent")
    _, report = run(bundle, capsys)
    assert ("review-pair-incomplete", "CONNECTIONS", "c-005", "review_date") in keyed(report)


def test_list_token_rules(bundle: Path, capsys: pytest.CaptureFixture[str]) -> None:
    edit(bundle, "NODES", "n-cars", source_ids="s-nasa-motion||s-openstax-speed")
    edit(bundle, "NODES", "n-music", aliases="song|song")
    edit(bundle, "NODES", "n-rate", source_ids="s-nasa-motion | s-ableton-tempo")
    _, report = run(bundle, capsys)
    got = keyed(report)
    assert ("list-empty-token", "NODES", "n-cars", "source_ids") in got
    assert ("list-duplicate-token", "NODES", "n-music", "aliases") in got
    assert ("list-token-whitespace", "NODES", "n-rate", "source_ids") in got


# --------------------------------------------------------- path structure


def test_duplicate_position_and_gap_are_errors_without_resequencing(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit(bundle, "PATH_STEPS", "p-cars-s03", sequence="2")
    edit(bundle, "PATH_STEPS", "p-plants-s04", sequence="5")
    before = digest_tree(bundle)
    status, report = run(bundle, capsys)
    assert status == 1
    got = keyed(report)
    assert ("duplicate-sequence", "PATH_STEPS", "p-cars-s03", "sequence") in got
    assert ("sequence-gap", "PATH_STEPS", "p-plants-s04", "sequence") in got
    assert digest_tree(bundle) == before


def test_first_and_later_origin_failures_are_distinct(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit(bundle, "PATHS", "p-cars", entry_node_id="n-music")
    edit(bundle, "CONNECTIONS", "c-018", from_node_id="n-plants")
    _, report = run(bundle, capsys)
    got = keyed(report)
    assert ("first-connection-origin-mismatch", "PATH_STEPS", "p-cars-s01", "connection_id") in got
    assert ("connection-origin-mismatch", "PATH_STEPS", "p-plants-s03", "connection_id") in got


def test_connection_ending_at_wrong_target(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit(bundle, "PATH_STEPS", "p-cooking-s04", target_node_id="n-fractions")
    _, report = run(bundle, capsys)
    assert (
        "connection-destination-mismatch",
        "PATH_STEPS",
        "p-cooking-s04",
        "connection_id",
    ) in keyed(report)


def test_path_without_steps_is_a_warning(bundle: Path, capsys: pytest.CaptureFixture[str]) -> None:
    append(
        bundle,
        "PATHS",
        path_id="p-test-new",
        title="New",
        entry_node_id="n-plants",
        learning_goal="Test goal.",
        status="draft",
    )
    status, report = run(bundle, capsys)
    assert status == 0
    assert ("path-without-steps", "PATHS", "p-test-new", "path_id") in keyed(report, "warning")


# ----------------------------------------------------------- graph shape


def test_second_rationale_for_same_endpoints_is_a_separate_valid_connection(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    append(
        bundle,
        "CONNECTIONS",
        connection_id="c-test-alt",
        from_node_id="n-equal-parts",
        to_node_id="n-fractions",
        learning_reason="A different teaching move.",
        source_ids="s-openstax-fractions",
        status="draft",
    )
    status, report = run(bundle, capsys)
    assert status == 0, issues(report)


def test_reverse_related_to_is_duplicate_but_reverse_directional_is_not(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    append(
        bundle,
        "RELATIONSHIPS",
        relationship_id="r-test-rev",
        from_node_id="n-rhythm",
        relationship_type="related_to",
        to_node_id="n-steady-beat",
        rationale="Reverse.",
        status="draft",
    )
    append(
        bundle,
        "RELATIONSHIPS",
        relationship_id="r-test-dir",
        from_node_id="n-length",
        relationship_type="uses",
        to_node_id="n-perimeter",
        rationale="Reverse uses.",
        status="draft",
    )
    _, report = run(bundle, capsys)
    dups = {i["record_id"] for i in issues(report) if i["code"] == "duplicate-relationship"}
    assert dups == {"r-test-rev"}


def test_self_links_are_rejected(bundle: Path, capsys: pytest.CaptureFixture[str]) -> None:
    edit(bundle, "RELATIONSHIPS", "r-008", to_node_id="n-length")
    edit(bundle, "CONNECTIONS", "c-024", to_node_id="n-rate")
    _, report = run(bundle, capsys)
    got = keyed(report)
    assert ("self-link", "RELATIONSHIPS", "r-008", "to_node_id") in got
    assert ("self-link", "CONNECTIONS", "c-024", "to_node_id") in got


def test_learning_and_association_cycles_are_valid(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Shipped example already loops length -> perimeter -> area -> length.
    append(
        bundle,
        "CONNECTIONS",
        connection_id="c-test-back",
        from_node_id="n-fractions",
        to_node_id="n-equal-parts",
        learning_reason="Reverse teaching move.",
        status="draft",
    )
    append(
        bundle,
        "RELATIONSHIPS",
        relationship_id="r-test-a",
        from_node_id="n-rate",
        relationship_type="uses",
        to_node_id="n-average-speed",
        rationale="Loops back.",
        status="draft",
    )
    status, report = run(bundle, capsys)
    assert status == 0, issues(report)
    assert not [i for i in report["issues"] if i["code"] == "taxonomy-cycle"]


def test_taxonomy_cycle_is_a_review_warning(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    append(
        bundle,
        "RELATIONSHIPS",
        relationship_id="r-test-loop",
        from_node_id="n-rate",
        relationship_type="is_a",
        to_node_id="n-average-speed",
        rationale="Deliberate loop.",
        status="draft",
    )
    status, report = run(bundle, capsys)
    assert status == 0
    flagged = {i["record_id"] for i in issues(report, "warning") if i["code"] == "taxonomy-cycle"}
    assert flagged == {"r-003", "r-test-loop"}


# ------------------------------------------------------- parsing behavior


def test_multiline_unicode_quoted_cells_keep_logical_record_numbers(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit(bundle, "NODES", "n-cars", educator_notes='Line one, with comma\nline two "quoted" — é ✓')
    edit(bundle, "NODES", "n-music", status="bogus")
    _, report = run(bundle, capsys)
    [bad] = [i for i in issues(report) if i["code"] == "invalid-status"]
    assert bad["record_number"] == 3 and bad["record_id"] == "n-music"


def test_crlf_and_bom_exports_give_identical_reports(
    bundle: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit(bundle, "NODES", "n-cars", educator_notes="Multi\nline note")
    crlf = tmp_path / "crlf"
    shutil.copytree(bundle, crlf)
    for path in crlf.glob("*.csv"):
        text = path.read_bytes().decode("utf-8")
        path.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8"))
    assert run(bundle, capsys) == run(crlf, capsys)


def test_blank_optional_detail_is_info_but_malformed_structure_is_error(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit(bundle, "PATH_STEPS", "p-cars-s01", understanding_check="")
    status, report = run(bundle, capsys)
    assert status == 0
    assert ("activity-field-missing", "PATH_STEPS", "p-cars-s01", "understanding_check") in keyed(
        report, "info"
    )
    edit(bundle, "PATH_STEPS", "p-cars-s01", sequence="one")
    status, report = run(bundle, capsys)
    assert status == 1
    assert ("invalid-integer", "PATH_STEPS", "p-cars-s01", "sequence") in keyed(report)


def test_wholly_empty_records_are_ignored(bundle: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = bundle / "NODES.csv"
    path.write_text(path.read_text(encoding="utf-8") + ",,,,,,,,,,\n,, ,,,,,,,,\n", "utf-8")
    status, report = run(bundle, capsys)
    assert status == 0 and report["counts"]["NODES"] == 30


def test_formula_like_text_is_flagged_not_evaluated_or_changed(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canary = "=HYPERLINK(CANARY-7731)"
    edit(bundle, "NODES", "n-cars", educator_notes=canary)
    edit(bundle, "NODES", "n-music", scope_notes="　＋fullwidth plus")  # NFKC -> "+"
    edit(bundle, "NODES", "n-rate", educator_notes="​@mention")
    before = digest_tree(bundle)
    status, report = run(bundle, capsys)
    assert status == 0
    flagged = {
        (i["record_id"], i["field"])
        for i in issues(report, "warning")
        if i["code"] == "formula-like-text"
    }
    assert flagged == {
        ("n-cars", "educator_notes"),
        ("n-music", "scope_notes"),
        ("n-rate", "educator_notes"),
    }
    assert "CANARY-7731" not in json.dumps(report)
    assert digest_tree(bundle) == before


def test_messages_never_echo_arbitrary_cell_text(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit(bundle, "NODES", "n-cars", status="SECRET-CANARY", source_ids="SECRET CANARY")
    edit(bundle, "NODES", "n-music", node_id="Bad ID SECRET-CANARY")
    checker.main(["--bundle", str(bundle)])
    text = capsys.readouterr().out
    _, report = run(bundle, capsys)
    assert "CANARY" not in text and "CANARY" not in json.dumps(report)


# ----------------------------------------------------- headers and files


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda h: h[1:] + h[:1], "header-order"),
        (lambda h: h + ["extra"], "header-unknown"),
        (lambda h: h[:-1], "header-missing"),
        (lambda h: h[:-1] + [h[0]], "header-duplicate"),
    ],
)
def test_header_problems(
    bundle: Path, capsys: pytest.CaptureFixture[str], mutate: Any, code: str
) -> None:
    path = bundle / "SOURCES.csv"
    lines = path.read_text(encoding="utf-8").split("\n", 1)
    path.write_text(",".join(mutate(lines[0].split(","))) + "\n" + lines[1], "utf-8")
    status, report = run(bundle, capsys)
    assert status == 1
    assert code in {i["code"] for i in issues(report) if i["table"] == "SOURCES"}


def test_row_width_malformed_utf8_and_missing_file(
    bundle: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (bundle / "PATHS.csv").write_text(
        (bundle / "PATHS.csv").read_text(encoding="utf-8") + "p-short,too,few\n", "utf-8"
    )
    (bundle / "SOURCES.csv").write_bytes(b"source_id,title\n\xff\xfe\n")
    (bundle / "RELATIONSHIPS.csv").unlink()
    status, report = run(bundle, capsys)
    assert status == 1
    got = {(i["code"], i["table"]) for i in issues(report)}
    assert {
        ("row-width", "PATHS"),
        ("malformed-utf8", "SOURCES"),
        ("missing-file", "RELATIONSHIPS"),
    } <= got


def test_template_mode_rejects_data_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "templates"
    shutil.copytree(TEMPLATES, target)
    shutil.copyfile(EXAMPLES / "SOURCES.csv", target / "SOURCES.csv")
    status, report = run(target, capsys, "--templates")
    assert status == 1
    assert {i["code"] for i in issues(report)} == {"template-has-data"}


def test_cli_usage_and_unreadable_input_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as both:
        checker.main(["--templates", str(TEMPLATES), "--bundle", str(EXAMPLES)])
    assert both.value.code == 2
    with pytest.raises(SystemExit) as neither:
        checker.main([])
    assert neither.value.code == 2
    assert checker.main(["--bundle", str(tmp_path / "absent")]) == 2
    err = capsys.readouterr().err
    assert "Traceback" not in err


# ------------------------------------------------------- side effects


def test_repeated_run_is_identical_and_writes_nothing(
    bundle: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_network(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("the checker must not open network connections")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    before = digest_tree(bundle.parent)
    first = run(bundle, capsys)
    second = run(bundle, capsys)
    assert first == second
    assert digest_tree(bundle.parent) == before  # no edits, no database, no new files
