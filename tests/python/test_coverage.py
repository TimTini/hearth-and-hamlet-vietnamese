from dataclasses import asdict, replace

import pytest
from test_contracts import synthetic_source

from hnh_vi.contracts import StatusRow, TranslationRow
from hnh_vi.coverage import calculate_coverage


def coverage_dataset():
    source = synthetic_source(*((key, "Synthetic " + key) for key in ("a", "b", "c", "d", "e")))
    source = replace(source, completeness=replace(
        source.completeness, total_rows=10, recovered_rows=7, duplicate_key_groups=1,
        duplicate_extra_rows=2,
    ))
    translations = tuple(TranslationRow(row.key, row.source_sha256, "" if row.key == "e" else "Dịch")
                         for row in source.rows)
    statuses = tuple(StatusRow(key, status, "") for key, status in (
        ("a", "reviewed"), ("b", "in_game"), ("c", "blocked"), ("d", "draft"), ("e", "draft"),
    ))
    return source, translations, statuses


def test_reports_full_known_and_selected_coverage_without_claiming_full_game() -> None:
    report = calculate_coverage(*coverage_dataset(), frozenset({"a", "b", "e"}))
    assert asdict(report) == {
        "total_source_rows": 10, "recovered_rows": 7, "unrecovered_rows": 3,
        "unique_recovered_keys": 5, "source_complete": False,
        "maximum_known_source_ratio": 0.7,
        "translated_keys": 4, "draft_keys": 2, "reviewed_keys": 1,
        "in_game_keys": 1, "blocked_keys": 1, "ready_keys": 2,
        "known_translation_ratio": 0.8, "known_ready_ratio": 0.4,
        "selected_keys": 3, "selected_translated_keys": 2,
        "selected_draft_keys": 1, "selected_reviewed_keys": 1,
        "selected_in_game_keys": 1, "selected_blocked_keys": 0, "selected_ready_keys": 2,
        "selected_translation_ratio": 2 / 3, "selected_ready_ratio": 2 / 3,
    }


def test_selected_all_ready_can_be_100_percent_while_source_is_partial() -> None:
    report = calculate_coverage(*coverage_dataset(), frozenset({"a", "b"}))
    assert report.selected_ready_ratio == report.selected_translation_ratio == 1
    assert not report.source_complete
    assert report.maximum_known_source_ratio == 0.7
    assert report.known_translation_ratio == 0.8


def test_none_selects_all_known_keys_and_empty_selection_has_zero_ratios() -> None:
    report = calculate_coverage(*coverage_dataset())
    assert report.selected_keys == 5
    assert report.selected_translation_ratio == 0.8
    empty = calculate_coverage(*coverage_dataset(), frozenset())
    assert empty.selected_keys == 0
    assert empty.selected_translation_ratio == empty.selected_ready_ratio == 0


@pytest.mark.parametrize("key", ["A", " a", "a ", "unknown", "<!MissingKey:synthetic>"])
def test_rejects_invalid_exact_selection(key) -> None:
    with pytest.raises(ValueError, match="invalid_coverage_dataset") as caught:
        calculate_coverage(*coverage_dataset(), frozenset({key}))
    assert key not in str(caught.value)


def test_rejects_duplicate_dataset_instead_of_inflating_counts() -> None:
    source, translations, statuses = coverage_dataset()
    with pytest.raises(ValueError, match="invalid_coverage_dataset"):
        calculate_coverage(source, translations + translations[:1], statuses)


def test_empty_source_has_defined_zero_ratios() -> None:
    source = synthetic_source()
    source = replace(source, completeness=replace(
        source.completeness, total_rows=0, unrecovered_rows=0, source_complete=True,
    ))
    report = calculate_coverage(source, (), ())
    assert report.maximum_known_source_ratio == 0
    assert report.known_translation_ratio == report.known_ready_ratio == 0
    assert report.source_complete


def test_reviewed_status_without_translation_is_not_ready_coverage() -> None:
    source, translations, statuses = coverage_dataset()
    statuses = statuses[:-1] + (StatusRow("e", "reviewed", ""),)
    report = calculate_coverage(source, translations, statuses, frozenset({"e"}))
    assert report.reviewed_keys == 2
    assert report.ready_keys == 2
    assert report.selected_reviewed_keys == 1
    assert report.selected_ready_keys == 0
    assert report.selected_ready_ratio == 0
