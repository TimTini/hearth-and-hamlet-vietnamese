import json
from pathlib import Path

import pytest

from hnh_vi.builds import sha256_file
from hnh_vi.workspace import (
    WorkspaceSnapshot,
    summarize_probe,
    verify_snapshot,
    write_snapshot,
)


@pytest.fixture
def snapshot_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    directory = tmp_path / "Repo and game with spaces"
    directory.mkdir()
    csv = directory / "translations.csv"
    pck = directory / "Game source.pck"
    csv.write_bytes(b"key,en\nfixture,Sample\n")
    pck.write_bytes(b"synthetic pck")
    snapshot = directory / "snapshot.json"
    write_snapshot(snapshot, WorkspaceSnapshot(
        "fixture", sha256_file(pck), sha256_file(csv), "2026-10-05T00:00:00Z",
    ))
    return snapshot, csv, pck


def test_snapshot_json_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    snapshot = WorkspaceSnapshot("fixture", "A" * 64, "B" * 64, "2026-10-05T00:00:00Z")
    write_snapshot(path, snapshot)
    first = path.read_bytes()
    write_snapshot(path, snapshot)
    assert path.read_bytes() == first
    assert first == (
        '{\n  "build_id": "fixture",\n  "extracted_at_utc": "2026-10-05T00:00:00Z",\n'
        '  "pck_sha256": "' + "A" * 64 + '",\n  "source_csv_sha256": "'
        + "B" * 64 + '"\n}\n'
    ).encode()


def test_verify_snapshot_with_spaces(snapshot_files: tuple[Path, Path, Path]) -> None:
    assert verify_snapshot(*snapshot_files, "fixture").ok


@pytest.mark.parametrize(("index", "expected"), [(1, "source_csv_drift"), (2, "pck_drift")])
def test_snapshot_detects_drift(
    snapshot_files: tuple[Path, Path, Path], index: int, expected: str,
) -> None:
    snapshot_files[index].write_bytes(b"changed")
    result = verify_snapshot(*snapshot_files, "fixture")
    assert not result.ok
    assert result.issues == (expected,)


@pytest.mark.parametrize("index", [0, 1, 2])
def test_snapshot_requires_files(snapshot_files: tuple[Path, Path, Path], index: int) -> None:
    snapshot_files[index].unlink()
    result = verify_snapshot(*snapshot_files, "fixture")
    assert not result.ok
    assert result.issues == ("missing_file",)


def test_snapshot_rejects_wrong_build(snapshot_files: tuple[Path, Path, Path]) -> None:
    result = verify_snapshot(*snapshot_files, "different")
    assert result.issues == ("build_id_mismatch",)


def test_snapshot_rejects_invalid_json(snapshot_files: tuple[Path, Path, Path]) -> None:
    snapshot_files[0].write_text(json.dumps({"build_id": "fixture"}))
    assert verify_snapshot(*snapshot_files, "fixture").issues == ("invalid_snapshot",)


@pytest.mark.parametrize(("selector", "expected"), [
    (
        ('var locales = TranslationServer.get_loaded_locales()\n'
        'for i in range(locales.size()):\n'
        '    var locale = locales[i]\n'
        '    language_dropdown.add_item(native_names.get(locale, locale.to_upper()))\n'
        '    language_dropdown.set_item_metadata(i, locale)\n'
        'var selected_locale = language_dropdown.get_item_metadata(index)\n'
        'TranslationServer.set_locale(selected_locale)\n'),
        "dynamic",
    ),
    ('var locales = ["en", "de"]\n', "hardcoded"),
    ('TranslationServer.get_loaded_locales()\n', "unknown"),
])
def test_probe_requires_locale_data_flow(tmp_path: Path, selector: str, expected: str) -> None:
    source = tmp_path / "source"
    (source / "Scenes").mkdir(parents=True)
    (source / "globals").mkdir()
    (source / "localisation").mkdir()
    (source / "Scenes/language.gd").write_text(selector, encoding="utf-8")
    (source / "globals/language_manager.gd").write_text(
        'var loaded_locales = TranslationServer.get_loaded_locales()\n'
        'if not loaded_locales.has(target_locale):\n'
        '    target_locale = DEFAULT_LOCALE\n'
        'TranslationServer.set_locale(target_locale)\n'
        'config.set_value("localization", "language", locale)\n', encoding="utf-8",
    )
    (source / "localisation/translations.csv").write_text(
        'key,en,de\nfixture,"Sample, with comma",Beispiel\n', encoding="utf-8",
    )
    (tmp_path / "recovery.log").write_text("Recovery finished\n", encoding="utf-8")
    report = summarize_probe(source, tmp_path / "recovery.log")
    assert report["locale_selection"] == expected
    assert report["csv_headers"] == ["key", "en", "de"]
    assert report["csv_rows"] == 1
    assert "Sample" not in json.dumps(report)
    assert report["compatible"] is (expected == "dynamic")


def test_probe_blocks_incomplete_translation_recovery(tmp_path: Path) -> None:
    (tmp_path / "localisation").mkdir()
    (tmp_path / "localisation/translations.csv").write_text("key,en\nfixture,Sample\n")
    log = tmp_path / "recovery.log"
    log.write_text("Translation Export Incomplete:\nCould not recover 27/1849 keys\n")
    report = summarize_probe(tmp_path, log)
    assert report["unrecovered_keys"] == 27
    assert report["translation_key_count"] == 1849
    assert not report["compatible"]
    assert "translation_recovery_incomplete" in report["issues"]
