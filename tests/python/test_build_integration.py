"""Real Godot and GDRE against a synthetic game: no proprietary data is used."""

import csv
import hashlib
import json
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pytest

from hnh_vi.build import (
    ENGLISH_TRANSLATION_PATH,
    PROJECT_BINARY_PATH,
    VI_TRANSLATION_PATH,
    verify_build_artifact,
)
from hnh_vi.builds import sha256_file

ROOT = Path(__file__).resolve().parents[2]
GODOT = ROOT / ".tools/godot/4.6.3-stable/Godot_v4.6.3-stable_win64_console.exe"
GDRE = ROOT / ".tools/gdre-tools/2.7.0/gdre_tools.exe"
ARTIFACT_NAME = "Hearth-and-Hamlet-vi-preview-1.1.0.pck"
METADATA_NAME = "Hearth-and-Hamlet-vi-preview-1.1.0.json"

pytestmark = pytest.mark.integration

# The packed game has the Godot-imported translations and the project settings that list
# them, but no source CSV, like the real game.
PACK_GAME_SCRIPT = """extends SceneTree


func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	var pck_path: String = arguments[0]
	var project_binary_path: String = arguments[1]
	if ProjectSettings.save_custom(project_binary_path) != OK:
		quit(1)
		return
	var packer := PCKPacker.new()
	var result := packer.pck_start(pck_path)
	var packed_files := [
		"res://localisation/translations.csv.import",
		"res://localisation/translations.en.translation",
		"res://localisation/translations.fr.translation",
	]
	for extra_file in arguments.slice(2):
		packed_files.append(extra_file)
	for packed_file in packed_files:
		if result == OK:
			result = packer.add_file(packed_file, packed_file)
	if result == OK:
		result = packer.add_file("res://project.binary", project_binary_path)
	if result == OK:
		result = packer.flush()
	quit(0 if result == OK else 1)
"""

CHECK_TRANSLATIONS_SCRIPT = """extends SceneTree


func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	print("LOCALES|", ",".join(TranslationServer.get_loaded_locales()))
	TranslationServer.set_locale(arguments[0])
	for key in arguments.slice(1):
		print("TR|", key, "|", tr(key).to_utf8_buffer().hex_encode())
	quit(0)
"""

PROJECT_WITH_LOCALES = """config_version=5

[application]
config/name="Synthetic localization fixture"

[internationalization]
locale/translations=PackedStringArray("res://localisation/translations.en.translation", "res://localisation/translations.fr.translation")

[rendering]
renderer/rendering_method="gl_compatibility"
"""

NFD_NFC_TEXT = "Cần NFC"
NFD_TEXT = unicodedata.normalize("NFD", NFD_NFC_TEXT)
SELECTED_KEYS = [
    "fixture_button", "fixture_unicode", "fixture_placeholder", "fixture_multiline",
    "fixture_Case", "fixture_case",
]
VI_TEXT = {
    "fixture_button": "Nút mẫu",
    "fixture_unicode": "Mẫu Unicode",
    "fixture_placeholder": "Xin chào %s",
    "fixture_multiline": "Dòng một\nDòng hai",
    "fixture_Case": "Khóa HOA",
    "fixture_case": "khóa thường",
    "fixture_nfc": NFD_TEXT,
    "fixture_vi_missing": "",
}


@dataclass(frozen=True)
class PreviewRepo:
    repo: Path
    game: Path
    project: Path


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def pack_game(project: Path, pck_path: Path, extra_files: tuple[str, ...] = ()) -> None:
    (project / "pack_game.gd").write_text(PACK_GAME_SCRIPT, encoding="utf-8")
    subprocess.run([
        str(GODOT), "--headless", "--path", str(project), "--script", "pack_game.gd",
        "--", str(pck_path), str(project / "project.binary"), *extra_files,
    ], check=True, capture_output=True)


def make_preview_repo(tmp_path: Path, extra_files: tuple[str, ...] = ()) -> PreviewRepo:
    if not GODOT.is_file() or not GDRE.is_file():
        pytest.skip("Run scripts/bootstrap.ps1 before synthetic tool integration")
    repo, game = tmp_path / "Repo with spaces", tmp_path / "Game with spaces"
    game.mkdir()
    project = tmp_path / "Fixture project"
    shutil.copytree(ROOT / "tests/fixtures/godot_project", project)
    subprocess.run(
        [str(GODOT), "--headless", "--path", str(project), "--import"],
        check=True, capture_output=True,
    )
    (project / "project.godot").write_text(PROJECT_WITH_LOCALES, encoding="utf-8")
    for extra_file in extra_files:
        extra_path = project / extra_file.removeprefix("res://")
        extra_path.parent.mkdir(parents=True, exist_ok=True)
        extra_path.write_text("# synthetic diagnostic probe\n", encoding="utf-8")
    pck_path = game / "Game fixture.pck"
    pack_game(project, pck_path, extra_files)
    (game / "Game fixture.exe").write_bytes(b"synthetic executable")

    (repo / "manifests").mkdir(parents=True)
    (repo / "manifests/game-builds.json").write_text(json.dumps({"builds": [{
        "build_id": "fixture", "exe_version": "1.1.0.0", "confirmed_on": "2026-10-06",
        "exe_name": "Game fixture.exe", "exe_sha256": sha256_file(game / "Game fixture.exe"),
        "pck_name": "Game fixture.pck", "pck_sha256": sha256_file(pck_path),
    }]}), encoding="utf-8")
    shutil.copyfile(ROOT / "manifests/tools.json", repo / "manifests/tools.json")
    shutil.copytree(ROOT / ".tools", repo / ".tools")
    write_dataset(repo, project, pck_path)
    return PreviewRepo(repo, game, project)


def write_dataset(repo: Path, project: Path, pck_path: Path) -> None:
    """Write the recovered source (with a marker and a duplicate) and the Vietnamese files."""
    source_rows = read_csv_rows(project / "localisation/translations.csv")
    rows = [[row["key"], row["en"], row["fr"]] for row in source_rows]
    rows.insert(0, ["<!MissingKey:synthetic marker>", "Marker text", "Marqueur"])
    rows.append(["fixture_button", "Sample button", "Bouton exemple"])
    source_csv = repo / "workspace/fixture/probe/source/localisation/translations.csv"
    source_csv.parent.mkdir(parents=True)
    write_csv(source_csv, ["key", "en", "fr"], rows)

    unique_keys = [row["key"] for row in source_rows]
    localization = repo / "localization"
    localization.mkdir()
    (localization / "source-completeness.json").write_text(json.dumps({
        "schema_version": 1, "build_id": "fixture", "pck_sha256": sha256_file(pck_path),
        "recovered_csv_sha256": sha256_file(source_csv),
        "total_rows": len(rows), "recovered_rows": len(rows) - 1,
        "unique_recovered_keys": len(unique_keys), "duplicate_key_groups": 1,
        "duplicate_extra_rows": 1, "unrecovered_rows": 1,
        "fallback_locale": "en", "policy": "partial_with_english_fallback",
        "source_complete": False,
    }), encoding="utf-8")
    english_by_key = {row["key"]: row["en"] for row in source_rows}
    write_csv(localization / "translations.vi.csv", ["key", "source_sha256", "translation_vi"], [
        [key, sha256_text(english_by_key[key]), VI_TEXT[key]] for key in unique_keys
    ])
    write_csv(localization / "status.csv", ["key", "status", "note"], [
        [key, "draft" if key == "fixture_vi_missing" else "reviewed", ""] for key in unique_keys
    ])
    write_csv(localization / "glossary.csv", ["source_term", "translation_vi", "scope", "note"], [])
    (localization / "phase1.keys").write_text("\n".join(SELECTED_KEYS) + "\n", encoding="utf-8")


def run_build(preview: PreviewRepo) -> subprocess.CompletedProcess[str]:
    return subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "scripts/build.ps1"), "-GameDir", str(preview.game), "-RepoRoot", str(preview.repo),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def game_fingerprint(game: Path) -> dict[str, str]:
    return {path.name: sha256_file(path) for path in game.iterdir()}


def list_pck_paths(pck: Path) -> list[str]:
    output = subprocess.run(
        [str(GDRE), "--headless", f"--list-files={pck}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout
    return [line.strip() for line in output.splitlines() if line.startswith("res://")]


def translate_in_godot(pck: Path, tmp_path: Path, locale: str, keys: list[str]) -> tuple[set[str], dict[str, str]]:
    script = tmp_path / "check_translations.gd"
    script.write_text(CHECK_TRANSLATIONS_SCRIPT, encoding="utf-8")
    output = subprocess.run([
        str(GODOT), "--headless", "--main-pack", str(pck), "--script", str(script),
        "--", locale, *keys,
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    locales: set[str] = set()
    translated: dict[str, str] = {}
    for line in output.splitlines():
        if line.startswith("LOCALES|"):
            locales = set(line.split("|", 1)[1].split(","))
        elif line.startswith("TR|"):
            _, key, hex_text = line.split("|")
            translated[key] = bytes.fromhex(hex_text).decode("utf-8")
    return locales, translated


@pytest.fixture(scope="module")
def built_preview(tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("preview")
    preview = make_preview_repo(tmp_path)
    before_game = game_fingerprint(preview.game)
    result = run_build(preview)
    return preview, before_game, result, tmp_path


def test_build_script_publishes_verified_preview_and_leaves_game_unchanged(built_preview) -> None:
    preview, before_game, result, _ = built_preview
    assert result.returncode == 0, result.stdout + result.stderr
    assert game_fingerprint(preview.game) == before_game

    dist = preview.repo / "dist/fixture"
    assert sorted(path.name for path in dist.iterdir()) == [METADATA_NAME, ARTIFACT_NAME]
    artifact = verify_build_artifact(dist / ARTIFACT_NAME, dist / METADATA_NAME)
    metadata = artifact.metadata

    assert metadata["release_quality"] == "preview"
    assert metadata["source_complete"] is False
    assert metadata["fallback_locale"] == "en"
    assert metadata["source_pck_sha256"] == before_game["Game fixture.pck"]
    assert metadata["artifact_sha256"] == sha256_file(dist / ARTIFACT_NAME)
    assert metadata["patched_paths"] == [VI_TRANSLATION_PATH, PROJECT_BINARY_PATH]
    assert metadata["completeness"]["unrecovered_rows"] == 1
    assert metadata["completeness"]["source_complete"] is False
    assert metadata["coverage"]["selected_keys"] == len(SELECTED_KEYS)
    assert metadata["coverage"]["selected_ready_ratio"] == 1.0
    assert metadata["coverage"]["maximum_known_source_ratio"] < 1.0
    assert metadata["translated_keys"] == 7
    assert metadata["omitted_empty_keys"] == 1


def test_build_leaves_no_temporary_workspace_or_stray_outputs(built_preview) -> None:
    preview, _, result, _ = built_preview
    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in (preview.repo / "workspace/fixture").iterdir()) == ["probe"]
    assert sorted(path.name for path in (preview.repo / "dist").iterdir()) == ["fixture"]


def test_artifact_keeps_original_resources_adds_vi_and_has_no_diagnostics(built_preview) -> None:
    preview, _, result, _ = built_preview
    assert result.returncode == 0, result.stdout + result.stderr
    source_paths = list_pck_paths(preview.game / "Game fixture.pck")
    artifact_paths = list_pck_paths(preview.repo / "dist/fixture" / ARTIFACT_NAME)

    assert ENGLISH_TRANSLATION_PATH in artifact_paths
    assert "res://localisation/translations.fr.translation" in artifact_paths
    assert set(artifact_paths) - set(source_paths) == {VI_TRANSLATION_PATH}
    assert set(source_paths) <= set(artifact_paths)
    assert not any("diagnostic" in path.lower() or path.endswith(".log") for path in artifact_paths)


def test_godot_uses_vi_messages_and_falls_back_to_english(built_preview) -> None:
    preview, _, result, tmp_path = built_preview
    assert result.returncode == 0, result.stdout + result.stderr
    artifact_pck = preview.repo / "dist/fixture" / ARTIFACT_NAME
    keys = [
        "fixture_button", "fixture_vi_missing", "fixture_Case", "fixture_case",
        "fixture_placeholder", "fixture_multiline", "fixture_nfc",
    ]

    locales, vi_text = translate_in_godot(artifact_pck, tmp_path, "vi", keys)
    _, fr_text = translate_in_godot(artifact_pck, tmp_path, "fr", ["fixture_button"])

    assert {"en", "fr", "vi"} <= locales
    assert vi_text["fixture_button"] == "Nút mẫu"
    assert vi_text["fixture_vi_missing"] == "Only English text"  # falls back to en
    assert vi_text["fixture_Case"] == "Khóa HOA"
    assert vi_text["fixture_case"] == "khóa thường"
    assert vi_text["fixture_placeholder"] == "Xin chào %s"
    assert vi_text["fixture_multiline"] == "Dòng một\nDòng hai"
    assert vi_text["fixture_nfc"] == NFD_NFC_TEXT  # NFC in the generated resource only
    assert fr_text["fixture_button"] == "Bouton exemple"
    committed = (preview.repo / "localization/translations.vi.csv").read_text(encoding="utf-8")
    assert NFD_TEXT in committed


def test_rebuilding_gives_same_inputs_metadata_and_translations(built_preview) -> None:
    """Godot stores a random sub-resource id in vi.translation, so PCK bytes may differ.

    Everything the build controls (merged CSV, hashes, counts, paths, translations) must not.
    """
    preview, before_game, result, tmp_path = built_preview
    assert result.returncode == 0, result.stdout + result.stderr
    dist = preview.repo / "dist/fixture"
    first_metadata = json.loads((dist / METADATA_NAME).read_text(encoding="utf-8"))

    second_result = run_build(preview)

    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    second = verify_build_artifact(dist / ARTIFACT_NAME, dist / METADATA_NAME)
    assert second.metadata["artifact_size"] == first_metadata["artifact_size"]
    first_metadata.pop("artifact_sha256")
    second.metadata.pop("artifact_sha256")
    assert second.metadata == first_metadata
    _, vi_text = translate_in_godot(dist / ARTIFACT_NAME, tmp_path, "vi", ["fixture_button"])
    assert vi_text["fixture_button"] == "Nút mẫu"
    assert game_fingerprint(preview.game) == before_game

def test_empty_selected_translation_blocks_build_without_touching_dist(built_preview) -> None:
    preview, before_game, result, _ = built_preview
    assert result.returncode == 0, result.stdout + result.stderr
    dist = preview.repo / "dist/fixture"
    before_dist = {path.name: sha256_file(path) for path in dist.iterdir()}
    translations = preview.repo / "localization/translations.vi.csv"
    original = translations.read_bytes()
    rows = read_csv_rows(translations)
    for row in rows:
        if row["key"] == "fixture_button":
            row["translation_vi"] = ""
    write_csv(translations, ["key", "source_sha256", "translation_vi"],
              [[row["key"], row["source_sha256"], row["translation_vi"]] for row in rows])
    try:
        blocked = run_build(preview)
    finally:
        translations.write_bytes(original)

    assert blocked.returncode != 0
    assert "empty_required_translation" in blocked.stdout + blocked.stderr
    assert {path.name: sha256_file(path) for path in dist.iterdir()} == before_dist
    assert sorted(path.name for path in (preview.repo / "workspace/fixture").iterdir()) == ["probe"]
    assert game_fingerprint(preview.game) == before_game


def test_source_csv_drift_blocks_build(built_preview) -> None:
    preview, before_game, result, _ = built_preview
    assert result.returncode == 0, result.stdout + result.stderr
    source_csv = preview.repo / "workspace/fixture/probe/source/localisation/translations.csv"
    original = source_csv.read_bytes()
    source_csv.write_bytes(original + b"fixture_new,New text,Nouveau\n")
    try:
        blocked = run_build(preview)
    finally:
        source_csv.write_bytes(original)

    assert blocked.returncode != 0
    assert "source_drift" in blocked.stdout + blocked.stderr
    assert game_fingerprint(preview.game) == before_game


def test_diagnostic_files_in_game_pck_block_build(tmp_path: Path) -> None:
    preview = make_preview_repo(tmp_path, extra_files=("res://diagnostics/runtime-key-probe.gd",))
    before_game = game_fingerprint(preview.game)

    blocked = run_build(preview)

    assert blocked.returncode != 0
    assert "diagnostic_path_in_source" in blocked.stdout + blocked.stderr
    assert not (preview.repo / "dist").exists()
    assert sorted(path.name for path in (preview.repo / "workspace/fixture").iterdir()) == ["probe"]
    assert game_fingerprint(preview.game) == before_game
