import csv
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from hnh_vi.completeness import load_source_completeness
from hnh_vi.contracts import (
    GlossaryTerm,
    StatusRow,
    TranslationRow,
    load_glossary_csv,
    load_status_csv,
    load_translation_csv,
    validate_dataset,
)
from hnh_vi.dataset import CanonicalSource, SourceIssue, SourceRow, audit_source_csv

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/localization"
ROOT = Path(__file__).resolve().parents[2]


def synthetic_source(*pairs: tuple[str, str]) -> CanonicalSource:
    baseline = load_source_completeness(FIXTURES / "source-completeness.json")
    rows = tuple(SourceRow(key, english, hashlib.sha256(english.encode()).hexdigest().upper())
                 for key, english in pairs)
    completeness = replace(
        baseline, total_rows=len(rows) + 3, recovered_rows=len(rows),
        unique_recovered_keys=len(rows), duplicate_key_groups=0, duplicate_extra_rows=0,
    )
    return CanonicalSource(rows, completeness, ())


def one_row(english: str = "Synthetic greeting.", translation: str = "Lời chào tổng hợp."):
    source = synthetic_source(("exact_key", english))
    translations = (TranslationRow("exact_key", source.rows[0].source_sha256, translation),)
    statuses = (StatusRow("exact_key", "reviewed", ""),)
    return source, translations, statuses


def codes(report) -> list[str]:
    return [issue.code for issue in report.errors]


def test_loaders_read_safe_fixtures_and_the_committed_skeleton() -> None:
    assert load_translation_csv(FIXTURES / "translations.vi.csv") == (
        TranslationRow("synthetic_ui", "A" * 64, "Nút tổng hợp"),
    )
    assert load_status_csv(FIXTURES / "status.csv") == (
        StatusRow("synthetic_ui", "draft", "Ghi chú tổng hợp"),
    )
    assert load_glossary_csv(FIXTURES / "glossary.csv") == (
        GlossaryTerm("synthetic timber", "gỗ tổng hợp", "", "Thuật ngữ tổng hợp"),
    )
    completeness = load_source_completeness(ROOT / "localization/source-completeness.json")
    translations = load_translation_csv(ROOT / "localization/translations.vi.csv")
    statuses = load_status_csv(ROOT / "localization/status.csv")
    assert len(translations) == len(statuses) == completeness.unique_recovered_keys
    assert tuple(row.key for row in translations) == tuple(row.key for row in statuses)
    phase1_keys = frozenset((ROOT / "localization/phase1.keys").read_text(encoding="utf-8").splitlines())
    assert all(
        len(row.source_sha256) == 64 and all(char in "0123456789ABCDEF" for char in row.source_sha256)
        for row in translations
    )
    # Only selected Phase 1 keys are translated; every other known key stays empty.
    assert all((row.translation_vi != "") == (row.key in phase1_keys) for row in translations)
    for row in statuses:
        if row.key in phase1_keys:
            assert row.status == "reviewed"
        elif row.status == "blocked":
            assert row.note != ""
        else:
            assert row.status == "draft" and row.note == ""
    assert not any(row.key.startswith("<!MissingKey") for row in translations + statuses)
    source_path = ROOT / "workspace" / completeness.build_id / "probe/source/localisation/translations.csv"
    if source_path.is_file():
        source = audit_source_csv(source_path, completeness)
        assert source.ok
        assert tuple((row.key, row.source_sha256) for row in source.rows) == tuple(
            (row.key, row.source_sha256) for row in translations
        )
    glossary = load_glossary_csv(ROOT / "localization/glossary.csv")
    assert len(glossary) == 28
    assert all(term.source_term.strip() and term.translation_vi.strip() for term in glossary)


def test_loader_preserves_bom_quoted_newline_exact_key_and_decomposed_unicode(tmp_path) -> None:
    path = tmp_path / "Bảng dịch có khoảng trắng.csv"
    text = "Ca\u0300i, đặt\nDòng thứ hai"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["key", "source_sha256", "translation_vi"])
        writer.writerow([" Exact_Key ", "a" * 64, text])
    before = path.read_bytes()
    assert load_translation_csv(path) == (TranslationRow(" Exact_Key ", "a" * 64, text),)
    assert path.read_bytes() == before


@pytest.mark.parametrize(("loader", "header"), [
    (load_translation_csv, "key,source_sha256,translation_vi"),
    (load_status_csv, "key,status,note"),
    (load_glossary_csv, "source_term,translation_vi,scope,note"),
])
@pytest.mark.parametrize("mutation", ["empty", "wrong_header", "short", "long", "syntax", "encoding"])
def test_loaders_reject_schema_safely(tmp_path, loader, header, mutation) -> None:
    path = tmp_path / "bad.csv"
    payload = {
        "empty": b"", "wrong_header": b"private_raw_key,private_source_sentence\n",
        "short": (header + "\nprivate_raw_key\n").encode(),
        "long": (header + "\n" + ",".join(["private_raw_key"] * 6) + "\n").encode(),
        "syntax": (header + '\n"private_source_sentence\n').encode(),
        "encoding": header.encode() + b"\n\xff",
    }[mutation]
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="invalid_.*_csv") as caught:
        loader(path)
    assert "private_raw_key" not in str(caught.value)
    assert "private_source_sentence" not in str(caught.value)


def test_valid_reviewed_translation_passes() -> None:
    assert validate_dataset(*one_row(), ()).ok


@pytest.mark.parametrize(("mutation", "expected"), [
    ("duplicate_translation", "duplicate_translation_key"),
    ("missing_translation", "missing_translation_key"),
    ("extra_translation", "extra_translation_key"),
    ("hash_drift", "source_hash_drift"),
    ("invalid_hash", "invalid_source_hash"),
    ("missing_status", "missing_status"),
    ("duplicate_status", "duplicate_status_key"),
    ("extra_status", "extra_status_key"),
    ("invalid_status", "invalid_status"),
    ("empty_key", "empty_translation_key"),
])
def test_detects_dataset_contract_failure(mutation, expected) -> None:
    source, translations, statuses = one_row()
    row = translations[0]
    if mutation == "duplicate_translation":
        translations += translations
    elif mutation == "missing_translation":
        translations = ()
    elif mutation == "extra_translation":
        translations += (replace(row, key="extra_private_key"),)
    elif mutation in {"hash_drift", "invalid_hash"}:
        translations = (replace(row, source_sha256="B" * 64 if mutation == "hash_drift" else "bad"),)
    elif mutation == "missing_status":
        statuses = ()
    elif mutation == "duplicate_status":
        statuses += statuses
    elif mutation == "extra_status":
        statuses += (StatusRow("extra_private_key", "draft", ""),)
    elif mutation == "invalid_status":
        statuses = (replace(statuses[0], status="REVIEWED"),)
    elif mutation == "empty_key":
        translations = (replace(row, key=" "),)
    report = validate_dataset(source, translations, statuses, ())
    assert not report.ok
    assert expected in codes(report)


@pytest.mark.parametrize("status", ["draft", "blocked"])
def test_required_unreviewed_key_blocks(status) -> None:
    source, translations, statuses = one_row()
    report = validate_dataset(source, translations, (replace(statuses[0], status=status),), (),
                              frozenset({"exact_key"}))
    assert codes(report) == ["required_status_not_ready"]


def test_required_in_game_key_is_ready() -> None:
    source, translations, statuses = one_row()
    assert validate_dataset(source, translations, (replace(statuses[0], status="in_game"),), ()).ok


@pytest.mark.parametrize("empty", ["", " \t"])
def test_required_empty_translation_blocks_but_nonrequired_gap_is_allowed(empty) -> None:
    source, translations, statuses = one_row(translation=empty)
    assert "empty_required_translation" in codes(validate_dataset(
        source, translations, statuses, (), frozenset({"exact_key"}),
    ))
    assert validate_dataset(source, translations, statuses, (), required_keys=frozenset()).ok
    assert validate_dataset(source, translations, statuses, ()).ok


@pytest.mark.parametrize("required", ["EXACT_KEY", " exact_key", "exact_key ", "unknown"])
def test_required_key_identity_is_exact(required) -> None:
    source, translations, statuses = one_row(translation="")
    report = validate_dataset(source, translations, statuses, (), frozenset({required}))
    assert codes(report) == ["unknown_required_key"]


@pytest.mark.parametrize("target", ["translation", "status", "phase"])
@pytest.mark.parametrize("marker", ["<!MissingKey:private synthetic text>", "<!MissingKey malformed>"])
def test_rejects_missing_key_markers_without_exposing_them(target, marker) -> None:
    source, translations, statuses = one_row()
    required = frozenset()
    if target == "translation":
        translations += (TranslationRow(marker, "A" * 64, ""),)
    elif target == "status":
        statuses += (StatusRow(marker, "draft", ""),)
    else:
        required = frozenset({marker})
    report = validate_dataset(source, translations, statuses, (), required)
    assert "missing_key_marker" in codes(report)
    assert marker not in json.dumps(asdict(report))


@pytest.mark.parametrize(("english", "translation", "expected"), [
    ("Synthetic %s %2$d %% {name}", "Tổng hợp %s %2$d %% {name}", None),
    ("Synthetic %s %s", "Tổng hợp %s", "placeholder_mismatch"),
    ("Synthetic %s %d", "Tổng hợp %d %s", "placeholder_mismatch"),
    ("Synthetic %1$s %2$d", "Tổng hợp %2$d %1$s", None),
    ("Synthetic {name} {count}", "Tổng hợp {count} {name}", None),
    ("Synthetic %2$d", "Tổng hợp %d", "placeholder_mismatch"),
    ("Synthetic %%", "Tổng hợp %s", "placeholder_mismatch"),
    ("Synthetic {name}", "Tổng hợp {other}", "placeholder_mismatch"),
    (r"Synthetic\nline", r"Tổng hợp\ndòng", None),
    (r"Synthetic\nline", "Tổng hợp\ndòng", "newline_mismatch"),
    ("Synthetic\nline", "Tổng hợp dòng", "newline_mismatch"),
    ("[b]Synthetic [i]nested[/i][/b]", "[b]Tổng hợp [i]lồng[/i][/b]", None),
    ("[b]Synthetic [i]nested[/i][/b]", "[b]Tổng hợp [i]lồng[/b][/i]", "bbcode_mismatch"),
    ("[b]Synthetic[/b]", "[b]Tổng hợp", "bbcode_mismatch"),
    ("[color=red]Synthetic[/color]", "[color=blue]Tổng hợp[/color]", "bbcode_mismatch"),
    ("[b][i]Synthetic[/i][/b]", "[i][b]Tổng hợp[/b][/i]", "bbcode_mismatch"),
    ("[img]synthetic.png[/img]", "[img]synthetic.png[/img]", None),
    ("Synthetic", "Tổng hợp\x00", "invalid_unicode"),
    ("Synthetic", "Tổng hợp\ud800", "invalid_unicode"),
])
def test_checks_text_contracts(english, translation, expected) -> None:
    report = validate_dataset(*one_row(english, translation), ())
    assert report.ok == (expected is None)
    if expected:
        assert expected in codes(report)


def test_non_nfc_is_reported_without_mutating_translation() -> None:
    source, translations, statuses = one_row(translation="Ca\u0300i đặt")
    report = validate_dataset(source, translations, statuses, ())
    assert report.ok
    assert [issue.code for issue in report.warnings] == ["non_nfc_translation"]
    assert translations[0].translation_vi == "Ca\u0300i đặt"


def test_glossary_warning_matches_whole_source_term_and_optional_exact_scope() -> None:
    source, translations, statuses = one_row("Synthetic timber stockpile", "Kho nguyên liệu")
    terms = (GlossaryTerm("timber", "gỗ", "", ""),)
    report = validate_dataset(source, translations, statuses, terms)
    assert report.ok
    assert [issue.code for issue in report.warnings] == ["glossary_mismatch"]
    assert validate_dataset(source, translations, statuses,
                            (replace(terms[0], scope="EXACT_KEY"),)).warnings == ()
    assert validate_dataset(*one_row("Synthetic timberland", "Kho nguyên liệu"), terms).warnings == ()
    assert validate_dataset(source, (replace(translations[0], translation_vi="Kho gỗ"),),
                            statuses, terms).warnings == ()


def test_propagates_safe_source_issues_and_blocks_source_errors() -> None:
    source, translations, statuses = one_row()
    issue = SourceIssue("source_csv_drift", "error", field="recovered_csv_sha256")
    source = replace(source, issues=(issue,))
    assert codes(validate_dataset(source, translations, statuses, ())) == ["source_csv_drift"]
    expected = load_source_completeness(FIXTURES / "source-completeness.json")
    source = audit_source_csv(FIXTURES / "source-partial.csv", expected)
    translations = tuple(TranslationRow(
        row.key, row.source_sha256, "Tổng hợp\nDòng tổng hợp" if row.key == "multiline" else "Tổng hợp",
    ) for row in source.rows)
    statuses = tuple(StatusRow(row.key, "reviewed", "") for row in source.rows)
    report = validate_dataset(source, translations, statuses, ())
    assert report.ok
    assert len(report.warnings) == 9
    assert report.warnings[0].occurrences == 3


def test_issues_have_deterministic_order_and_safe_json(tmp_path, capsys) -> None:
    source, translations, statuses = one_row("PRIVATE FULL SYNTHETIC ENGLISH.")
    translations += (replace(translations[0], key="PRIVATE_KEY"),)
    statuses += (StatusRow("PRIVATE_STATUS_KEY", "bad", "PRIVATE_NOTE"),)
    required = frozenset({"Z_PRIVATE", "A_PRIVATE"})
    report = validate_dataset(source, translations, statuses, (), required)
    assert report == validate_dataset(source, translations, statuses, (), required)
    payload = json.dumps(asdict(report))
    path = tmp_path / "safe-report.json"
    path.write_text(payload, encoding="utf-8")
    print(payload)
    for private in ("PRIVATE FULL SYNTHETIC ENGLISH.", "PRIVATE_KEY", "PRIVATE_STATUS_KEY",
                    "PRIVATE_NOTE", "Z_PRIVATE", "A_PRIVATE", "exact_key"):
        assert private not in payload
        assert private not in path.read_text(encoding="utf-8")
    assert capsys.readouterr().out.strip() == payload


def test_glossary_invalid_empty_terms_have_safe_blocking_issue() -> None:
    report = validate_dataset(*one_row(), (GlossaryTerm("", "gỗ", "", ""),))
    assert codes(report) == ["invalid_glossary_term"]


def test_hash_case_is_not_source_drift() -> None:
    source, translations, statuses = one_row()
    assert validate_dataset(source, (replace(translations[0],
                                             source_sha256=translations[0].source_sha256.lower()),),
                            statuses, ()).ok


@pytest.mark.parametrize(("english", "translation", "valid"), [
    ("Synthetic {0} {1}", "Tổng hợp {0} {1}", True),
    ("Synthetic {0} {1}", "Tổng hợp {1} {0}", True),
    ("Synthetic {0} {1}", "Tổng hợp {0}", False),
    ("Synthetic {0}", "Tổng hợp {1}", False),
    ("Synthetic {0} {0}", "Tổng hợp {0}", False),
    ("Synthetic {0}", "Tổng hợp {0} {0}", False),
])
def test_numeric_format_placeholder_parity(english, translation, valid) -> None:
    report = validate_dataset(*one_row(english, translation), ())
    assert report.ok == valid
    assert ("placeholder_mismatch" in codes(report)) == (not valid)


@pytest.mark.parametrize(("english", "translation"), [
    ("Synthetic [Space] action", "Thao tác tổng hợp [Space]"),
    ("[b]Synthetic [Space] action[/b]", "[b]Thao tác tổng hợp [Space][/b]"),
])
def test_literal_key_label_is_not_bbcode(english, translation) -> None:
    assert validate_dataset(*one_row(english, translation), ()).ok


@pytest.mark.parametrize("control", ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x1f", "\x85"])
def test_control_only_translation_cannot_be_accepted_as_nonrequired_gap(control) -> None:
    report = validate_dataset(*one_row(translation=control), (), required_keys=frozenset())
    assert codes(report) == ["invalid_unicode"]


@pytest.mark.parametrize("tag", [
    "char=0041", "lrm", "rlm", "lre", "rle", "lro", "rlo", "pdf", "alm", "lri", "rli",
    "fsi", "pdi", "zwj", "zwnj", "wj", "shy",
])
@pytest.mark.parametrize("mutation", ["preserve", "change", "omit"])
def test_godot_singleton_tag_parity(tag, mutation) -> None:
    english = f"[b]Synthetic [{tag}] [Space][/b]"
    if mutation == "preserve":
        translation = f"[b]Tổng hợp [{tag}] [Space][/b]"
    elif mutation == "change":
        translation = "[b]Tổng hợp [char=0042] [Space][/b]"
    else:
        translation = "[b]Tổng hợp [Space][/b]"
    report = validate_dataset(*one_row(english, translation), ())
    assert report.ok == (mutation == "preserve")
    assert ("bbcode_mismatch" in codes(report)) == (mutation != "preserve")
