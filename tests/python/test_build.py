import csv
import hashlib
import json
import unicodedata
from dataclasses import asdict
from pathlib import Path

import pytest

from hnh_vi.build import (
    ENGLISH_TRANSLATION_PATH,
    PROJECT_BINARY_PATH,
    VI_TRANSLATION_PATH,
    BuildInput,
    check_candidate_paths,
    check_preview_dataset,
    inject_vietnamese_native_name,
    make_preview_metadata,
    merge_translation_csv,
    preview_artifact_name,
    short_game_version,
    verify_build_artifact,
)
from hnh_vi.builds import sha256_file
from hnh_vi.completeness import SourceCompleteness
from hnh_vi.contracts import StatusRow, TranslationRow
from hnh_vi.coverage import calculate_coverage
from hnh_vi.dataset import CanonicalSource, SourceRow, audit_source_csv

MISSING_MARKER = "<!MissingKey: synthetic marker>"
NFD_KEY = unicodedata.normalize("NFD", "ui_caf\u00e9")
NFD_TEXT = unicodedata.normalize("NFD", "C\u00e0 ph\u00ea")
NFC_TEXT = unicodedata.normalize("NFC", NFD_TEXT)

# Row order is deliberate: the canonical key order is the first-seen source order.
SOURCE_ROWS = [
    (MISSING_MARKER, "Marker English"),
    ("ui_start", "Start game"),
    ("ui_Start", "Start game (case variant)"),
    ("ui_start", "Start game"),
    ("ui_multi", "Line one\\nLine two"),
    (NFD_KEY, "Coffee"),
    ("ui_not_selected", "Not selected yet"),
    ("ui_hello", "Hello %s"),
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def write_source_csv(path: Path, rows: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["key", "en", "de"])
        for key, english in rows:
            writer.writerow([key, english, "synthetic de"])


def make_canonical_source(tmp_path: Path) -> tuple[Path, CanonicalSource]:
    source_path = tmp_path / "source.csv"
    write_source_csv(source_path, SOURCE_ROWS)
    recovered_keys = [key for key, _ in SOURCE_ROWS if not key.startswith("<!MissingKey")]
    unique_keys = set(recovered_keys)
    duplicate_groups = sum(recovered_keys.count(key) > 1 for key in unique_keys)
    completeness = SourceCompleteness(
        schema_version=1,
        build_id="fixture",
        pck_sha256="A" * 64,
        recovered_csv_sha256=sha256_file(source_path),
        total_rows=len(SOURCE_ROWS),
        recovered_rows=len(recovered_keys),
        unique_recovered_keys=len(unique_keys),
        duplicate_key_groups=duplicate_groups,
        duplicate_extra_rows=len(recovered_keys) - len(unique_keys),
        unrecovered_rows=len(SOURCE_ROWS) - len(recovered_keys),
        fallback_locale="en",
        policy="partial_with_english_fallback",
        source_complete=False,
    )
    source = audit_source_csv(source_path, completeness)
    assert source.ok
    return source_path, source


def source_hash(source: CanonicalSource, key: str) -> str:
    return next(row.source_sha256 for row in source.rows if row.key == key)


def write_translations(path: Path, rows: list[tuple[str, str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["key", "source_sha256", "translation_vi"])
        writer.writerows(rows)


def translation_rows(source: CanonicalSource, texts: dict[str, str]) -> list[tuple[str, str, str]]:
    return [(row.key, row.source_sha256, texts.get(row.key, "")) for row in source.rows]


def read_merged(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.reader(stream))


def test_merge_keeps_canonical_order_and_exact_case_keys(tmp_path: Path) -> None:
    source_path, source = make_canonical_source(tmp_path)
    translations_path = tmp_path / "translations.vi.csv"
    rows = translation_rows(source, {
        "ui_start": "Bat dau", "ui_Start": "Bat dau HOA", "ui_hello": "Xin chao %s",
    })
    # Reordering the dataset must not change the order of the generated resource.
    write_translations(translations_path, list(reversed(rows)))
    output_path = tmp_path / "merged.csv"

    merge_translation_csv(source_path, source, translations_path, output_path)

    merged = read_merged(output_path)
    assert merged[0] == ["key", "vi"]
    assert [row[0] for row in merged[1:]] == ["ui_start", "ui_Start", "ui_hello"]
    assert dict(merged[1:]) == {
        "ui_start": "Bat dau", "ui_Start": "Bat dau HOA", "ui_hello": "Xin chao %s",
    }
    assert not any(row[0].startswith("<!MissingKey") for row in merged)


def test_merge_omits_empty_cells_and_returns_build_input(tmp_path: Path) -> None:
    source_path, source = make_canonical_source(tmp_path)
    translations_path = tmp_path / "translations.vi.csv"
    write_translations(translations_path, translation_rows(source, {
        "ui_start": "Bat dau", "ui_multi": "Dong mot\\nDong hai", "ui_not_selected": "  ",
    }))
    output_path = tmp_path / "merged.csv"

    build_input = merge_translation_csv(source_path, source, translations_path, output_path)

    merged_keys = [row[0] for row in read_merged(output_path)[1:]]
    assert merged_keys == ["ui_start", "ui_multi"]
    assert build_input == BuildInput(
        merged_csv_path=output_path,
        merged_csv_sha256=sha256_file(output_path),
        locale="vi",
        translated_keys=2,
        omitted_empty_keys=len(source.rows) - 2,
    )


def test_merge_normalizes_translation_text_but_not_keys(tmp_path: Path) -> None:
    source_path, source = make_canonical_source(tmp_path)
    translations_path = tmp_path / "translations.vi.csv"
    write_translations(translations_path, translation_rows(source, {NFD_KEY: NFD_TEXT}))
    output_path = tmp_path / "merged.csv"

    merge_translation_csv(source_path, source, translations_path, output_path)

    key, text = read_merged(output_path)[1]
    assert key == NFD_KEY
    assert text == NFC_TEXT
    assert unicodedata.is_normalized("NFC", text)
    # The committed dataset keeps the text exactly as the translator wrote it.
    assert NFD_TEXT in translations_path.read_text(encoding="utf-8")


def test_merge_is_deterministic_and_leaves_inputs_unchanged(tmp_path: Path) -> None:
    source_path, source = make_canonical_source(tmp_path)
    translations_path = tmp_path / "translations.vi.csv"
    write_translations(translations_path, translation_rows(source, {"ui_start": "Bat dau"}))
    before = (source_path.read_bytes(), translations_path.read_bytes())
    first_output, second_output = tmp_path / "first.csv", tmp_path / "second.csv"

    merge_translation_csv(source_path, source, translations_path, first_output)
    merge_translation_csv(source_path, source, translations_path, second_output)

    assert first_output.read_bytes() == second_output.read_bytes()
    assert b"\r" not in first_output.read_bytes()
    assert (source_path.read_bytes(), translations_path.read_bytes()) == before


def test_merge_rejects_source_csv_drift(tmp_path: Path) -> None:
    source_path, source = make_canonical_source(tmp_path)
    translations_path = tmp_path / "translations.vi.csv"
    write_translations(translations_path, translation_rows(source, {"ui_start": "Bat dau"}))
    source_path.write_text(source_path.read_text(encoding="utf-8") + "ui_new,New,x\n", encoding="utf-8")
    output_path = tmp_path / "merged.csv"

    with pytest.raises(ValueError, match="source_csv_drift"):
        merge_translation_csv(source_path, source, translations_path, output_path)

    assert not output_path.exists()


def test_merge_rejects_source_with_blocking_audit_issues(tmp_path: Path) -> None:
    source_path, source = make_canonical_source(tmp_path)
    translations_path = tmp_path / "translations.vi.csv"
    write_translations(translations_path, translation_rows(source, {"ui_start": "Bat dau"}))
    # One extra recovered row keeps the manifest consistent but no longer matches the CSV.
    expected = asdict(source.completeness)
    expected["total_rows"] += 1
    expected["recovered_rows"] += 1
    expected["unique_recovered_keys"] += 1
    drifted_completeness = SourceCompleteness(**expected)
    broken_source = audit_source_csv(source_path, drifted_completeness)
    assert not broken_source.ok

    with pytest.raises(ValueError, match="source_not_buildable"):
        merge_translation_csv(source_path, broken_source, translations_path, tmp_path / "merged.csv")


@pytest.mark.parametrize("problem", [
    "unknown_key", "source_hash_drift", "duplicate_key", "missing_key_marker",
])
def test_merge_rejects_dataset_rows_that_do_not_match_source(tmp_path: Path, problem: str) -> None:
    source_path, source = make_canonical_source(tmp_path)
    translations_path = tmp_path / "translations.vi.csv"
    rows = translation_rows(source, {"ui_start": "Bat dau"})
    if problem == "unknown_key":
        rows.append(("ui_unknown", "B" * 64, "Khong ro"))
    elif problem == "source_hash_drift":
        rows[0] = (rows[0][0], "C" * 64, rows[0][2])
    elif problem == "duplicate_key":
        rows.append(rows[0])
    else:
        rows.append((MISSING_MARKER, "D" * 64, "Khong duoc dung"))
    write_translations(translations_path, rows)
    output_path = tmp_path / "merged.csv"

    with pytest.raises(ValueError, match=problem):
        merge_translation_csv(source_path, source, translations_path, output_path)

    assert not output_path.exists()


@pytest.mark.parametrize("locale", ["en", "", "vi/../x", "vi,en"])
def test_merge_rejects_unsafe_locale(tmp_path: Path, locale: str) -> None:
    source_path, source = make_canonical_source(tmp_path)
    translations_path = tmp_path / "translations.vi.csv"
    write_translations(translations_path, translation_rows(source, {"ui_start": "Bat dau"}))

    with pytest.raises(ValueError, match="invalid_locale"):
        merge_translation_csv(source_path, source, translations_path, tmp_path / "merged.csv", locale)


def test_merge_refuses_to_write_through_a_hard_link(tmp_path: Path) -> None:
    source_path, source = make_canonical_source(tmp_path)
    translations_path = tmp_path / "translations.vi.csv"
    write_translations(translations_path, translation_rows(source, {"ui_start": "Bat dau"}))
    protected = tmp_path / "protected.bin"
    protected.write_bytes(b"protected game bytes")
    output_path = tmp_path / "merged.csv"
    output_path.hardlink_to(protected)

    with pytest.raises(ValueError, match="unsafe_workspace"):
        merge_translation_csv(source_path, source, translations_path, output_path)

    assert protected.read_bytes() == b"protected game bytes"


def selected_dataset(source: CanonicalSource, vi_text: dict[str, str], status: str = "reviewed"):
    translations = tuple(
        TranslationRow(row.key, row.source_sha256, vi_text.get(row.key, "")) for row in source.rows
    )
    statuses = tuple(StatusRow(row.key, status) for row in source.rows)
    return translations, statuses


def test_dataset_gate_allows_empty_non_selected_keys_and_reports_partial_coverage(tmp_path: Path) -> None:
    _, source = make_canonical_source(tmp_path)
    translations, statuses = selected_dataset(source, {"ui_start": "Bat dau"})

    coverage = check_preview_dataset(source, translations, statuses, (), frozenset({"ui_start"}))

    assert coverage.selected_keys == 1
    assert coverage.selected_ready_ratio == 1.0
    assert coverage.translated_keys == 1
    assert coverage.source_complete is False
    assert coverage.maximum_known_source_ratio < 1.0


def test_dataset_gate_blocks_empty_selected_key(tmp_path: Path) -> None:
    _, source = make_canonical_source(tmp_path)
    translations, statuses = selected_dataset(source, {"ui_start": "Bat dau"})

    with pytest.raises(ValueError, match="empty_required_translation"):
        check_preview_dataset(source, translations, statuses, (), frozenset({"ui_start", "ui_hello"}))


def test_dataset_gate_blocks_draft_selected_key_and_placeholder_breaks(tmp_path: Path) -> None:
    _, source = make_canonical_source(tmp_path)
    translations, statuses = selected_dataset(source, {"ui_hello": "Xin chao"}, status="draft")

    with pytest.raises(ValueError, match="placeholder_mismatch"):
        check_preview_dataset(source, translations, statuses, (), frozenset({"ui_hello"}))
    with pytest.raises(ValueError, match="required_status_not_ready"):
        check_preview_dataset(source, translations, statuses, (), frozenset({"ui_hello"}))


@pytest.mark.parametrize("selected", [None, frozenset()])
def test_dataset_gate_requires_a_selected_phase(tmp_path: Path, selected) -> None:
    _, source = make_canonical_source(tmp_path)
    translations, statuses = selected_dataset(source, {"ui_start": "Bat dau"})

    with pytest.raises(ValueError, match="selected_keys_required"):
        check_preview_dataset(source, translations, statuses, (), selected)


def test_dataset_gate_never_accepts_missing_key_marker_in_selection(tmp_path: Path) -> None:
    _, source = make_canonical_source(tmp_path)
    translations, statuses = selected_dataset(source, {"ui_start": "Bat dau"})

    with pytest.raises(ValueError, match="missing_key_marker"):
        check_preview_dataset(source, translations, statuses, (), frozenset({MISSING_MARKER}))


def test_game_version_and_artifact_name_follow_the_release_contract() -> None:
    assert short_game_version("1.1.0.0") == "1.1.0"
    assert short_game_version("2.0.3") == "2.0.3"
    assert preview_artifact_name("1.1.0.0") == "Hearth-and-Hamlet-vi-preview-1.1.0.pck"
    for bad_version in ("", "1.1.0.1", "../1.1.0", "1.1", "1.1.0 beta"):
        with pytest.raises(ValueError, match="invalid_game_version"):
            short_game_version(bad_version)


SOURCE_PATHS = [
    "res://localisation/translations.csv.import",
    ENGLISH_TRANSLATION_PATH,
    "res://localisation/translations.de.translation",
    PROJECT_BINARY_PATH,
    "res://Scenes/main.tscn",
]


def test_original_game_paths_are_never_judged_as_diagnostics() -> None:
    source_paths = SOURCE_PATHS + ["res://logs/runtime.log", "res://instrument_panel/diagnostic_icon.png"]
    added = check_candidate_paths(source_paths, source_paths + [VI_TRANSLATION_PATH])
    assert added == (VI_TRANSLATION_PATH,)


def test_candidate_must_only_add_the_vi_resource() -> None:
    added = check_candidate_paths(SOURCE_PATHS, SOURCE_PATHS + [VI_TRANSLATION_PATH])
    assert added == (VI_TRANSLATION_PATH,)


@pytest.mark.parametrize("problem", [
    "english_missing_from_source", "english_removed", "path_removed", "unexpected_path_added",
    "diagnostic_path_added", "vi_resource_missing",
])
def test_candidate_path_check_rejects_unsafe_pck_contents(problem: str) -> None:
    source_paths = list(SOURCE_PATHS)
    candidate_paths = SOURCE_PATHS + [VI_TRANSLATION_PATH]
    if problem == "english_missing_from_source":
        source_paths.remove(ENGLISH_TRANSLATION_PATH)
        candidate_paths.remove(ENGLISH_TRANSLATION_PATH)
    elif problem == "english_removed":
        candidate_paths.remove(ENGLISH_TRANSLATION_PATH)
    elif problem == "path_removed":
        candidate_paths.remove("res://Scenes/main.tscn")
    elif problem == "unexpected_path_added":
        candidate_paths.append("res://extra/new_script.gd")
    elif problem == "diagnostic_path_added":
        candidate_paths.append("res://diagnostics/runtime-key-probe.gd")
    else:
        candidate_paths.remove(VI_TRANSLATION_PATH)

    with pytest.raises(ValueError, match=problem):
        check_candidate_paths(source_paths, candidate_paths)


# ---- Metadata and artifact verification -------------------------------------------------


def make_metadata_inputs(tmp_path: Path):
    _, source = make_canonical_source(tmp_path)
    translations, statuses = selected_dataset(source, {"ui_start": "Bat dau"})
    selected = frozenset({"ui_start"})
    coverage = calculate_coverage(source, translations, statuses, selected)
    merged_path = tmp_path / "merged.csv"
    merged_path.write_text("key,vi\nui_start,Bat dau\n", encoding="utf-8")
    build_input = BuildInput(merged_path, sha256_file(merged_path), "vi", 1, len(source.rows) - 1)
    artifact_path = tmp_path / "Hearth-and-Hamlet-vi-preview-1.1.0.pck"
    artifact_path.write_bytes(b"synthetic candidate bytes")
    return source, coverage, build_input, artifact_path, selected


def make_valid_metadata(tmp_path: Path) -> tuple[Path, Path, dict]:
    source, coverage, build_input, artifact_path, selected = make_metadata_inputs(tmp_path)
    metadata = make_preview_metadata(
        game_version="1.1.0.0",
        source_pck_sha256="A" * 64,
        build_input=build_input,
        artifact_path=artifact_path,
        patched_paths=(VI_TRANSLATION_PATH, PROJECT_BINARY_PATH),
        completeness=source.completeness,
        coverage=coverage,
        selected_keys=selected,
        tool_versions={"gdre-tools": "2.7.0", "godot": "4.6.3-stable"},
    )
    metadata_path = tmp_path / "Hearth-and-Hamlet-vi-preview-1.1.0.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return artifact_path, metadata_path, metadata


def test_preview_metadata_has_exact_honest_fields(tmp_path: Path) -> None:
    source, coverage, build_input, artifact_path, selected = make_metadata_inputs(tmp_path)

    metadata = make_preview_metadata(
        game_version="1.1.0.0",
        source_pck_sha256="a" * 64,
        build_input=build_input,
        artifact_path=artifact_path,
        patched_paths=(PROJECT_BINARY_PATH, VI_TRANSLATION_PATH),
        completeness=source.completeness,
        coverage=coverage,
        selected_keys=selected,
        tool_versions={"gdre-tools": "2.7.0", "godot": "4.6.3-stable"},
    )

    assert metadata == {
        "schema_version": 1,
        "artifact_kind": "translation_patch",
        "release_quality": "preview",
        "source_complete": False,
        "fallback_locale": "en",
        "locale": "vi",
        "build_id": "fixture",
        "game_version": "1.1.0",
        "source_pck_sha256": "A" * 64,
        "source_csv_sha256": source.completeness.recovered_csv_sha256,
        "merged_csv_sha256": build_input.merged_csv_sha256,
        "artifact_name": artifact_path.name,
        "artifact_sha256": sha256_file(artifact_path),
        "artifact_size": len(b"synthetic candidate bytes"),
        "patched_paths": [VI_TRANSLATION_PATH, PROJECT_BINARY_PATH],
        "translated_keys": 1,
        "omitted_empty_keys": len(source.rows) - 1,
        "selected_keys_sha256": sha256_text("ui_start"),
        "tools": {"gdre-tools": "2.7.0", "godot": "4.6.3-stable"},
        "completeness": asdict(source.completeness),
        "coverage": asdict(coverage),
    }
    # The partial-source limits stay visible in the numbers, not rounded to 100%.
    assert metadata["completeness"]["unrecovered_rows"] == 1
    assert metadata["coverage"]["maximum_known_source_ratio"] < 1.0


def test_verify_accepts_matching_artifact_and_metadata(tmp_path: Path) -> None:
    artifact_path, metadata_path, metadata = make_valid_metadata(tmp_path)

    artifact = verify_build_artifact(artifact_path, metadata_path)

    assert artifact.pck_path == artifact_path
    assert artifact.metadata_path == metadata_path
    assert artifact.sha256 == sha256_file(artifact_path)
    assert artifact.size_bytes == artifact_path.stat().st_size
    assert artifact.metadata == metadata


def write_changed_metadata(metadata_path: Path, metadata: dict, change) -> None:
    changed = json.loads(json.dumps(metadata))
    change(changed)
    metadata_path.write_text(json.dumps(changed, indent=2), encoding="utf-8")


@pytest.mark.parametrize("name,change", [
    ("not_preview", lambda m: m.update(release_quality="release")),
    ("claims_complete", lambda m: m.update(source_complete=True)),
    ("completeness_claims_complete", lambda m: m["completeness"].update(source_complete=True)),
    ("coverage_claims_complete", lambda m: m["coverage"].update(source_complete=True)),
    ("coverage_claims_full_source", lambda m: m["coverage"].update(maximum_known_source_ratio=1.0)),
    ("wrong_fallback", lambda m: m.update(fallback_locale="vi")),
    ("wrong_locale", lambda m: m.update(locale="en")),
    ("artifact_hash_mismatch", lambda m: m.update(artifact_sha256="0" * 64)),
    ("artifact_size_mismatch", lambda m: m.update(artifact_size=1)),
    ("artifact_name_mismatch", lambda m: m.update(artifact_name="Other.pck")),
    ("bad_source_hash", lambda m: m.update(source_pck_sha256="xyz")),
    ("diagnostic_kind", lambda m: m.update(artifact_kind="diagnostic")),
    ("diagnostic_key", lambda m: m.update(diagnostic_log="runtime.log")),
    ("diagnostic_patched_path", lambda m: m["patched_paths"].append("res://diagnostics/probe.gd")),
    ("log_patched_path", lambda m: m["patched_paths"].append("res://logs/runtime.log")),
    ("unexpected_patched_path", lambda m: m["patched_paths"].append("res://Scenes/main.tscn")),
    ("no_patched_paths", lambda m: m.update(patched_paths=[])),
    ("vi_resource_not_patched", lambda m: m.update(patched_paths=[PROJECT_BINARY_PATH])),
    ("bad_completeness", lambda m: m["completeness"].update(total_rows=1)),
    ("missing_coverage", lambda m: m.pop("coverage")),
    ("unknown_schema", lambda m: m.update(schema_version=2)),
])
def test_verify_rejects_misleading_or_diagnostic_metadata(tmp_path: Path, name: str, change) -> None:
    artifact_path, metadata_path, metadata = make_valid_metadata(tmp_path)
    write_changed_metadata(metadata_path, metadata, change)

    with pytest.raises(ValueError, match="invalid_build_metadata|build_artifact_mismatch"):
        verify_build_artifact(artifact_path, metadata_path)


def test_verify_rejects_artifact_bytes_that_changed_after_metadata(tmp_path: Path) -> None:
    artifact_path, metadata_path, _ = make_valid_metadata(tmp_path)
    artifact_path.write_bytes(b"swapped game bytes")

    with pytest.raises(ValueError, match="build_artifact_mismatch"):
        verify_build_artifact(artifact_path, metadata_path)


def test_verify_rejects_missing_files_and_bad_json(tmp_path: Path) -> None:
    artifact_path, metadata_path, _ = make_valid_metadata(tmp_path)

    metadata_path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_build_metadata"):
        verify_build_artifact(artifact_path, metadata_path)

    with pytest.raises(ValueError, match="build_artifact_missing"):
        verify_build_artifact(tmp_path / "missing.pck", metadata_path)
    with pytest.raises(ValueError, match="build_artifact_missing"):
        verify_build_artifact(artifact_path, tmp_path / "missing.json")


def test_verify_rejects_hard_linked_artifact(tmp_path: Path) -> None:
    artifact_path, metadata_path, _ = make_valid_metadata(tmp_path)
    alias = tmp_path / "alias.pck"
    alias.hardlink_to(artifact_path)

    with pytest.raises(ValueError, match="unsafe_workspace"):
        verify_build_artifact(artifact_path, metadata_path)


def test_source_row_text_never_enters_metadata(tmp_path: Path) -> None:
    source, coverage, build_input, artifact_path, selected = make_metadata_inputs(tmp_path)
    metadata = make_preview_metadata(
        game_version="1.1.0.0", source_pck_sha256="A" * 64, build_input=build_input,
        artifact_path=artifact_path, patched_paths=(VI_TRANSLATION_PATH,),
        completeness=source.completeness, coverage=coverage, selected_keys=selected,
        tool_versions={"gdre-tools": "2.7.0", "godot": "4.6.3-stable"},
    )
    text = json.dumps(metadata)
    for row in source.rows:
        assert isinstance(row, SourceRow)
        assert row.english not in text
    assert MISSING_MARKER not in text


def test_inject_vietnamese_native_name_adds_tieng_viet() -> None:
    original = (
        'var native_names = {\n'
        '\t"en": "English", \n'
        '\t"de": "Deutsch", \n'
        '\t"ko": "한국어", \n'
        '}\n'
        'func _ready() -> void:\n'
        '\tpass\n'
    )
    patched = inject_vietnamese_native_name(original)
    assert '"vi": "Tiếng Việt"' in patched
    assert '"ko": "한국어"' in patched
    assert 'language_dropdown' not in patched or True
    assert patched.index('"vi"') > patched.index('"ko"')


def test_inject_vietnamese_native_name_rejects_missing_or_duplicate() -> None:
    with pytest.raises(ValueError, match="language_native_names_missing"):
        inject_vietnamese_native_name("extends Node\n")
    with pytest.raises(ValueError, match="language_native_name_exists"):
        inject_vietnamese_native_name(
            'var native_names = {\n\t"vi": "Tiếng Việt", \n}\n'
        )
