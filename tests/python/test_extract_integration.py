import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from hnh_vi import workspace as workspace_module
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


@pytest.mark.integration
@pytest.mark.parametrize("target", ["Game fixture.exe", "Game fixture.pck"])
def test_probe_late_recovery_log_alias_cannot_change_game(tmp_path: Path, target: str) -> None:
    repo, game = make_packed_game(tmp_path)
    probe_dir = repo / "workspace/fixture/probe"
    before = {path.name: sha256_file(path) for path in game.iterdir()}
    watcher_errors = []
    attempted = threading.Event()
    finished = threading.Event()

    def insert_alias() -> None:
        while not (probe_dir / "gdre-version.txt").exists():
            if finished.wait(0.001):
                watcher_errors.append("probe exited before version output appeared")
                return
        attempted.set()
        guard_check = subprocess.run([
            sys.executable, "-c",
            ("import pathlib, sys\n"
            "for name in sys.argv[1:]:\n"
            "    path = pathlib.Path(name)\n"
            "    try:\n"
            "        with path.open('r+b'):\n"
            "            sys.exit('write access was allowed')\n"
            "    except PermissionError:\n"
            "        pass\n"
            "    try:\n"
            "        path.unlink()\n"
            "        sys.exit('delete access was allowed')\n"
            "    except PermissionError:\n"
            "        pass\n"),
            str(game / "Game fixture.exe"), str(game / "Game fixture.pck"),
        ], capture_output=True, text=True, check=False)
        if guard_check.returncode:
            watcher_errors.append(guard_check.stdout + guard_check.stderr)
        try:
            (probe_dir / "recovery.log").hardlink_to(game / target)
        except PermissionError:
            pass  # Windows may also deny creation of an alias to a protected file.
        except OSError as error:
            watcher_errors.append(str(error))

    watcher = threading.Thread(target=insert_alias)
    watcher.start()
    try:
        result = subprocess.run([
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(ROOT / "scripts/probe.ps1"), "-RepoRoot", str(repo), "-GameDir", str(game),
        ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    finally:
        finished.set()
    watcher.join()
    assert attempted.is_set(), watcher_errors
    assert not watcher_errors
    assert result.returncode in (1, 2), result.stdout + result.stderr
    assert {path.name: sha256_file(path) for path in game.iterdir()} == before
    # Script finally must release both protection handles, even when a writer failed.
    with (game / target).open("r+b") as source:
        assert source.read(1)


@pytest.mark.integration
@pytest.mark.parametrize("target", ["Game fixture.exe", "Game fixture.pck"])
def test_extract_late_gdre_output_alias_cannot_change_game(tmp_path: Path, target: str) -> None:
    repo, game = make_packed_game(tmp_path)
    before = {path.name: sha256_file(path) for path in game.iterdir()}
    process = subprocess.Popen([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "scripts/extract.ps1"), "-RepoRoot", str(repo), "-GameDir", str(game),
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    started = False
    for line in process.stdout:
        if "Godot Engine" in line:
            started = True
            alias = repo / "workspace/fixture/source/localisation/translations.csv"
            alias.parent.mkdir(parents=True, exist_ok=True)
            try:
                alias.hardlink_to(game / target)
            except PermissionError:
                pass
            break
    output, _ = process.communicate()
    assert started, output
    assert process.returncode in (0, 1), output
    assert {path.name: sha256_file(path) for path in game.iterdir()} == before
    for path in game.iterdir():
        with path.open("r+b") as source:
            assert source.read(1)


@pytest.mark.integration
def test_python_report_after_gate_alias_does_not_truncate_game(tmp_path: Path, monkeypatch) -> None:
    repo, game = make_packed_game(tmp_path)
    probe = repo / "workspace/fixture/probe"
    (probe / "source/localisation").mkdir(parents=True)
    (probe / "source/localisation/translations.csv").write_text("key,en\nfixture,Sample\n")
    (probe / "recovery.log").write_text("Recovery finished\n")
    (probe / "gdre-version.txt").write_text("Godot RE Tools v2.7.0")
    (probe / "godot-version.txt").write_text("4.6.3.stable.official.7d41c59c4")
    (probe / "pck-files.txt").write_text("res://localisation/translations.csv\n")
    before = {path.name: sha256_file(path) for path in game.iterdir()}
    original_context = workspace_module._verified_context

    def inject_after_gate(repo_root: Path, game_dir: Path) -> dict:
        context = original_context(repo_root, game_dir)
        (probe / "report.json").hardlink_to(game / "Game fixture.exe")
        return context

    monkeypatch.setattr(workspace_module, "_verified_context", inject_after_gate)
    monkeypatch.setattr(sys, "argv", [
        "workspace", "probe-report", "--repo-root", str(repo), "--game-dir", str(game),
    ])
    assert workspace_module.main() in (1, 2)
    assert {path.name: sha256_file(path) for path in game.iterdir()} == before
