import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hnh_vi.builds import sha256_file

ROOT = Path(__file__).resolve().parents[2]


def run_extract(repo: Path, game: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "scripts/extract.ps1"), "-GameDir", str(game), "-RepoRoot", str(repo),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def create_build(repo: Path, game: Path) -> None:
    (repo / "manifests").mkdir(parents=True)
    (repo / "manifests/game-builds.json").write_text(json.dumps({"builds": [{
        "build_id": "fixture", "exe_version": "synthetic", "confirmed_on": "2026-10-05",
        "exe_name": "Game fixture.exe", "exe_sha256": sha256_file(game / "Game fixture.exe"),
        "pck_name": "Game fixture.pck", "pck_sha256": sha256_file(game / "Game fixture.pck"),
    }]}), encoding="utf-8")
    shutil.copyfile(ROOT / "manifests/tools.json", repo / "manifests/tools.json")


def test_extract_rejects_fingerprint_before_tool_or_workspace(tmp_path: Path) -> None:
    repo, game = tmp_path / "Repo with spaces", tmp_path / "Game with spaces"
    game.mkdir()
    (game / "Game fixture.exe").write_bytes(b"synthetic exe")
    (game / "Game fixture.pck").write_bytes(b"synthetic pck")
    create_build(repo, game)
    (game / "Game fixture.pck").write_bytes(b"drift")
    result = run_extract(repo, game)
    assert result.returncode != 0
    assert "hash_mismatch" in result.stdout + result.stderr
    assert "tool_missing" not in result.stdout + result.stderr
    assert not (repo / "workspace").exists()
    assert sorted(path.name for path in game.iterdir()) == ["Game fixture.exe", "Game fixture.pck"]


def test_extract_default_repo_root_reaches_build_gate(tmp_path: Path) -> None:
    result = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "scripts/extract.ps1"), "-GameDir", str(tmp_path),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    assert result.returncode != 0
    assert "unsupported_build: missing_file" in result.stdout + result.stderr


def test_probe_default_repo_root_reaches_build_gate(tmp_path: Path) -> None:
    result = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "scripts/probe.ps1"), "-GameDir", str(tmp_path),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    assert result.returncode != 0
    assert "unsupported_build: missing_file" in result.stdout + result.stderr


@pytest.mark.integration
def test_real_godot_pck_and_gdre_extraction(tmp_path: Path) -> None:
    godot = ROOT / ".tools/godot/4.6.3-stable/Godot_v4.6.3-stable_win64_console.exe"
    gdre = ROOT / ".tools/gdre-tools/2.7.0/gdre_tools.exe"
    if not godot.is_file() or not gdre.is_file():
        pytest.skip("Run scripts/bootstrap.ps1 before synthetic tool integration")
    repo, game = tmp_path / "Repo Việt with spaces", tmp_path / "Game Việt with spaces"
    game.mkdir()
    project = tmp_path / "Godot fixture with spaces"
    shutil.copytree(ROOT / "tests/fixtures/godot_project", project)
    pck = game / "Game fixture.pck"
    subprocess.run([
        str(godot), "--headless", "--path", str(project), "--script", "make_fixture.gd",
        "--", str(pck),
    ], check=True, capture_output=True)
    (game / "Game fixture.exe").write_bytes(b"synthetic executable")
    create_build(repo, game)
    shutil.copytree(ROOT / ".tools", repo / ".tools")
    before = {path.name: sha256_file(path) for path in game.iterdir()}
    result = run_extract(repo, game)
    assert result.returncode == 0, result.stdout + result.stderr
    workspace = repo / "workspace/fixture"
    source_csv = workspace / "source/localisation/translations.csv"
    assert source_csv.read_bytes() == (project / "localisation/translations.csv").read_bytes()
    snapshot = json.loads((workspace / "snapshot.json").read_text())
    assert snapshot["build_id"] == "fixture"
    assert snapshot["pck_sha256"] == before[pck.name]
    assert snapshot["source_csv_sha256"] == sha256_file(source_csv)
    assert {path.name: sha256_file(path) for path in game.iterdir()} == before
    probe = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "scripts/probe.ps1"), "-GameDir", str(game), "-RepoRoot", str(repo),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    assert probe.returncode == 2, probe.stdout + probe.stderr
    report = json.loads((workspace / "probe/report.json").read_text())
    assert report["gdre_version"] == "Godot RE Tools v2.7.0"
    assert report["godot_version"].startswith("4.6.3.stable.")
    assert report["pck_file_count"] == 1
    assert report["locale_selection"] == "unknown"
    assert not report["compatible"]
    assert {path.name: sha256_file(path) for path in game.iterdir()} == before
