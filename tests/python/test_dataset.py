import csv
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from hnh_vi.completeness import SourceCompleteness, load_source_completeness
from hnh_vi.dataset import audit_source_csv

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/localization"


def write_source(tmp_path: Path, rows: list[list[str]]) -> tuple[Path, SourceCompleteness]:
    path = tmp_path / "Nguồn tổng hợp có khoảng trắng.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["key", "en", "de"])
        writer.writerows(rows)
    baseline = load_source_completeness(FIXTURES / "source-completeness.json")
    return path, replace(baseline, recovered_csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper())


def fixture_rows() -> list[list[str]]:
    with (FIXTURES / "source-partial.csv").open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.reader(stream))[1:]


def test_canonicalizes_nine_groups_in_first_occurrence_order() -> None:
    expected = load_source_completeness(FIXTURES / "source-completeness.json")
    path = FIXTURES / "source-partial.csv"
    before = path.read_bytes()
    source = audit_source_csv(path, expected)
    assert source.ok
    assert source.completeness == expected
    assert [row.key for row in source.rows] == [
        "group1", "group2", "group3", "group4", "group5", "group6",
        "group7", "group8", "group9", "multiline",
    ]
    assert len(source.rows) == 10
    assert source.rows[-1].english == "Synthetic line one,\nsynthetic line two."
    assert source.rows[0].source_sha256 == hashlib.sha256(b"Synthetic item 1.").hexdigest().upper()
    warnings = [issue for issue in source.issues if issue.code == "duplicate_source_key"]
    assert [issue.occurrences for issue in warnings] == [3, 3, 3, 2, 2, 2, 2, 2, 2]
    assert warnings[0].row_numbers == (2, 15, 22)
    assert all(issue.severity == "warning" for issue in warnings)
    serialized = json.dumps([asdict(issue) for issue in source.issues])
    for row in fixture_rows():
        assert row[1] not in serialized
        if row[0].startswith("<!MissingKey:"):
            assert row[0] not in serialized
    assert source.issues == audit_source_csv(path, expected).issues
    assert path.read_bytes() == before


@pytest.mark.parametrize("position", [0, 10, 24])
def test_changed_marker_text_with_same_counts_still_blocks(tmp_path: Path, position: int) -> None:
    rows = fixture_rows()
    rows[position][0] = "<!MissingKey:changed synthetic marker>"
    path, _ = write_source(tmp_path, rows)
    expected = load_source_completeness(FIXTURES / "source-completeness.json")
    source = audit_source_csv(path, expected)
    assert not source.ok
    assert [issue.code for issue in source.issues if issue.severity == "error"] == ["source_csv_drift"]
    assert len(source.rows) == 10
    assert source.completeness.unrecovered_rows == 3


def test_changed_marker_distribution_blocks_even_with_approved_hash(tmp_path: Path) -> None:
    rows = fixture_rows()
    rows[0][0] = "recovered_new"
    path, expected = write_source(tmp_path, rows)
    source = audit_source_csv(path, expected)
    assert not source.ok
    assert {issue.field for issue in source.issues if issue.code == "source_count_drift"} == {
        "recovered_rows", "unique_recovered_keys", "unrecovered_rows",
    }


def test_changed_duplicate_distribution_blocks_with_same_row_count(tmp_path: Path) -> None:
    rows = fixture_rows()
    rows[11][0] = "group9"
    rows[11][1] = "Synthetic item 9."
    path, expected = write_source(tmp_path, rows)
    source = audit_source_csv(path, expected)
    assert not source.ok
    assert {issue.field for issue in source.issues if issue.code == "source_count_drift"} == {
        "unique_recovered_keys", "duplicate_extra_rows",
    }


def test_changed_duplicate_group_count_blocks_without_other_count_changes(tmp_path: Path) -> None:
    rows = fixture_rows()
    rows[15][0] = "group5"
    rows[15][1] = "Synthetic item 5."
    path, expected = write_source(tmp_path, rows)
    source = audit_source_csv(path, expected)
    assert not source.ok
    errors = [issue for issue in source.issues if issue.severity == "error"]
    assert [(issue.code, issue.field, issue.expected, issue.actual) for issue in errors] == [
        ("source_count_drift", "duplicate_key_groups", 9, 8),
    ]


def test_rejects_same_key_different_english_without_exposing_source(tmp_path: Path) -> None:
    rows = fixture_rows()
    rows[14][1] = "A conflicting synthetic sentence."
    path, expected = write_source(tmp_path, rows)
    source = audit_source_csv(path, expected)
    assert not source.ok
    conflicts = [issue for issue in source.issues if issue.code == "conflicting_source_key"]
    assert len(conflicts) == 1
    assert conflicts[0].severity == "error"
    assert conflicts[0].occurrences == 3
    assert "group1" not in [row.key for row in source.rows]
    assert "A conflicting synthetic sentence." not in repr(source.issues)


def test_missingkey_word_inside_regular_key_is_buildable(tmp_path: Path) -> None:
    rows = fixture_rows()
    rows[1][0] = rows[14][0] = rows[21][0] = "regular_MissingKey_name"
    path, expected = write_source(tmp_path, rows)
    source = audit_source_csv(path, expected)
    assert source.ok
    assert source.rows[0].key == "regular_MissingKey_name"


@pytest.mark.parametrize("distinct_key", ["GROUP1", " group1", "group1 "])
def test_case_and_whitespace_variant_keys_remain_distinct_with_same_english(
    tmp_path: Path, distinct_key: str,
) -> None:
    rows = fixture_rows()
    for position in (2, 13, 22):
        rows[position][0] = distinct_key
        rows[position][1] = "Synthetic item 1."
    path, expected = write_source(tmp_path, rows)
    source = audit_source_csv(path, expected)
    assert source.ok
    assert source.completeness.unique_recovered_keys == 10
    assert [row.key for row in source.rows[:2]] == ["group1", distinct_key]
    assert source.rows[0].source_sha256 == source.rows[1].source_sha256


@pytest.mark.parametrize("marker", ["<!MissingKey:unclosed", "<!MissingKey malformed>"])
def test_malformed_marker_prefix_blocks_without_becoming_buildable(tmp_path: Path, marker: str) -> None:
    rows = fixture_rows()
    rows[0][0] = marker
    path, expected = write_source(tmp_path, rows)
    source = audit_source_csv(path, expected)
    assert not source.ok
    assert marker not in [row.key for row in source.rows]
    assert [issue.code for issue in source.issues if issue.severity == "error"] == ["malformed_missing_key_marker"]
    assert marker not in repr(source.issues)


def test_total_row_drift_is_blocking(tmp_path: Path) -> None:
    path, expected = write_source(tmp_path, fixture_rows() + [["new", "Synthetic new.", "Neu"]])
    source = audit_source_csv(path, expected)
    assert not source.ok
    assert {issue.field for issue in source.issues if issue.code == "source_count_drift"} == {
        "total_rows", "recovered_rows", "unique_recovered_keys",
    }


@pytest.mark.parametrize("content", [
    "key,de\na,Value\n", "en,de\nValue,Wert\n", "key,en,en\na,Value,Value\n",
    "key,en\na\n", "key,en\na,Value,extra\n", "key,en\n,Value\n",
    'key,en\na,"Unclosed\n', "",
])
def test_rejects_invalid_source_schema_with_safe_error(tmp_path: Path, content: str) -> None:
    path = tmp_path / "source.csv"
    path.write_text(content, encoding="utf-8")
    expected = load_source_completeness(FIXTURES / "source-completeness.json")
    with pytest.raises(ValueError, match="invalid_source_csv") as caught:
        audit_source_csv(path, expected)
    assert "Value" not in str(caught.value)


def test_english_content_change_blocks_even_when_counts_match(tmp_path: Path) -> None:
    rows = fixture_rows()
    rows[11][1] = "A changed synthetic multiline sentence."
    path, _ = write_source(tmp_path, rows)
    expected = load_source_completeness(FIXTURES / "source-completeness.json")
    source = audit_source_csv(path, expected)
    assert not source.ok
    assert [issue.code for issue in source.issues if issue.severity == "error"] == ["source_csv_drift"]
