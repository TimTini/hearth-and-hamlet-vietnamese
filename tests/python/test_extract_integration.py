import json
import shutil
import subprocess
import sys
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


def make_packed_game(tmp_path: Path, *, missing_csv: bool = False) -> tuple[Path, Path]:
    godot = ROOT / ".tools/godot/4.6.3-stable/Godot_v4.6.3-stable_win64_console.exe"
    if not godot.is_file():
        pytest.skip("Run scripts/bootstrap.ps1 before synthetic tool integration")
    repo, game = tmp_path / "Repo with spaces", tmp_path / "Game with spaces"
    game.mkdir()
    project = tmp_path / "Fixture project"
    shutil.copytree(ROOT / "tests/fixtures/godot_project", project)
    if missing_csv:
        script = project / "make_fixture.gd"
        script.write_text(script.read_text().replace("translations.csv", "translations.tsv"))
        (project / "localisation/translations.csv").rename(project / "localisation/translations.tsv")
    subprocess.run([
        str(godot), "--headless", "--path", str(project), "--script", "make_fixture.gd",
        "--", str(game / "Game fixture.pck"),
    ], check=True, capture_output=True)
    (game / "Game fixture.exe").write_bytes(b"synthetic executable")
    create_build(repo, game)
    shutil.copytree(ROOT / ".tools", repo / ".tools")
    return repo, game


@pytest.mark.integration
def test_output_writers_reject_game_hardlinks(tmp_path: Path) -> None:
    repo, game = make_packed_game(tmp_path)
    workspace = repo / "workspace/fixture"
    csv = workspace / "source/localisation/translations.csv"
    csv.parent.mkdir(parents=True)
    csv.write_text("key,en\nfixture,Sample\n")
    before = {path.name: sha256_file(path) for path in game.iterdir()}
    outputs = [
        ("snapshot", "snapshot.json"),
        ("probe-report", "probe/report.json"),
        ("extract.ps1", "source/localisation/translations.csv"),
        ("extract.ps1", "source/gdre_export.log"),
        ("probe.ps1", "probe/gdre-version.txt"),
        ("probe.ps1", "probe/godot-version.txt"),
        ("probe.ps1", "probe/pck-files.txt"),
        ("probe.ps1", "probe/recovery.log"),
        ("probe.ps1", "probe/source/localisation/translations.csv"),
        ("probe.ps1", "probe/source/gdre_export.log"),
    ]
    for original in game.iterdir():
        for command, relative in outputs:
            alias = workspace / relative
            alias.parent.mkdir(parents=True, exist_ok=True)
            if alias.exists():
                alias.unlink()
            alias.hardlink_to(original)
            if command.endswith(".ps1"):
                args = [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(ROOT / "scripts" / command), "-RepoRoot", str(repo), "-GameDir", str(game),
                ]
            else:
                args = [
                    sys.executable, "-m", "hnh_vi.workspace", command,
                    "--repo-root", str(repo), "--game-dir", str(game),
                ]
            result = subprocess.run(args, capture_output=True, text=True, check=False)
            assert result.returncode != 0, (command, relative)
            assert "unsafe_workspace" in result.stdout + result.stderr, (command, relative)
            assert {path.name: sha256_file(path) for path in game.iterdir()} == before
            alias.unlink()
            if alias == csv:
                csv.write_text("key,en\nfixture,Sample\n")


@pytest.mark.integration
def test_extract_rejects_stale_csv_when_current_pck_has_no_csv(tmp_path: Path) -> None:
    repo, game = make_packed_game(tmp_path, missing_csv=True)
    workspace = repo / "workspace/fixture"
    stale = workspace / "source/localisation/translations.csv"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"key,en\nstale,Old source\n")
    before = {path.name: sha256_file(path) for path in game.iterdir()}
    result = run_extract(repo, game)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "workspace_source_not_empty" in result.stdout + result.stderr
    assert not (workspace / "snapshot.json").exists()
    assert stale.read_bytes() == b"key,en\nstale,Old source\n"
    assert {path.name: sha256_file(path) for path in game.iterdir()} == before
