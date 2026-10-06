import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

from test_install import (
    ARTIFACT_PCK,
    ORIGINAL_PCK,
    PCK_NAME,
    World,
    make_world,
)

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def make_script_world(tmp_path: Path, game_folder: str = "Game with spaces") -> tuple[World, dict]:
    """A synthetic game, a verified artifact, a manifest for it and a private LOCALAPPDATA."""
    world = make_world(tmp_path, game_folder=game_folder)
    manifests = tmp_path / "repo" / "manifests"
    manifests.mkdir(parents=True)
    (manifests / "game-builds.json").write_text(
        json.dumps({"builds": [asdict(world.spec)]}), encoding="utf-8",
    )
    local_app_data = tmp_path / "local app data"
    local_app_data.mkdir()
    environment = {**os.environ, "LOCALAPPDATA": str(local_app_data)}
    return world, environment


def run_script(name: str, arguments: list[str], environment: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(SCRIPTS / name), *arguments],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=environment, check=False,
    )


def install_arguments(world: World, tmp_path: Path) -> list[str]:
    return [
        "-GameDir", str(world.game_dir), "-Artifact", str(world.artifact_path),
        "-RepoRoot", str(tmp_path / "repo"),
    ]


def backup_root_of(environment: dict) -> Path:
    return Path(environment["LOCALAPPDATA"]) / "HearthAndHamletVietnamese" / "backups"


def test_install_script_is_a_dry_run_by_default(tmp_path: Path) -> None:
    world, environment = make_script_world(tmp_path)

    result = run_script("install.ps1", install_arguments(world, tmp_path), environment)

    assert result.returncode == 0, result.stderr
    assert "dry-run" in result.stdout
    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    assert not backup_root_of(environment).exists()


def test_install_script_apply_writes_backup_under_local_app_data(tmp_path: Path) -> None:
    world, environment = make_script_world(tmp_path, game_folder="Trò chơi Việt hóa")

    result = run_script("install.ps1", [*install_arguments(world, tmp_path), "-Apply"], environment)

    assert result.returncode == 0, result.stderr
    assert world.game_pck.read_bytes() == ARTIFACT_PCK
    backups = list((backup_root_of(environment) / "fixture").iterdir())
    assert len(backups) == 1
    assert (backups[0] / PCK_NAME).read_bytes() == ORIGINAL_PCK
    assert (backups[0] / "backup.json").is_file()


def test_install_script_fails_closed_for_unsupported_game(tmp_path: Path) -> None:
    world, environment = make_script_world(tmp_path)
    world.game_pck.write_bytes(b"Steam updated this pck")

    result = run_script("install.ps1", [*install_arguments(world, tmp_path), "-Apply"], environment)

    assert result.returncode != 0
    assert "unsupported_build" in result.stderr
    assert world.game_pck.read_bytes() == b"Steam updated this pck"
    assert not backup_root_of(environment).exists()


def test_install_script_rejects_diagnostic_artifact(tmp_path: Path) -> None:
    world, environment = make_script_world(tmp_path)
    diagnostic_folder = world.artifact_path.parent / "diagnostic"
    diagnostic_folder.mkdir()
    diagnostic_pck = diagnostic_folder / world.artifact_path.name
    diagnostic_pck.write_bytes(world.artifact_path.read_bytes())
    diagnostic_pck.with_suffix(".json").write_bytes(world.metadata_path.read_bytes())
    arguments = install_arguments(world, tmp_path)
    arguments[3] = str(diagnostic_pck)

    result = run_script("install.ps1", [*arguments, "-Apply"], environment)

    assert result.returncode != 0
    assert "diagnostic_artifact_rejected" in result.stderr
    assert world.game_pck.read_bytes() == ORIGINAL_PCK


def test_scripts_use_literal_paths_and_release_the_exe_lock() -> None:
    for name in ("install.ps1", "uninstall.ps1"):
        text = (SCRIPTS / name).read_text(encoding="utf-8")
        assert "[switch]$Apply" in text
        assert "Test-Path -LiteralPath" in text
        assert "FileShare]::Read" in text
        assert "finally" in text


def test_install_script_apply_works_with_wildcard_characters_in_game_path(tmp_path: Path) -> None:
    world, environment = make_script_world(tmp_path, game_folder="Game [1] with spaces")

    result = run_script("install.ps1", [*install_arguments(world, tmp_path), "-Apply"], environment)

    assert result.returncode == 0, result.stderr
    assert world.game_pck.read_bytes() == ARTIFACT_PCK


def test_uninstall_script_dry_run_then_apply_restores_original(tmp_path: Path) -> None:
    world, environment = make_script_world(tmp_path)
    run_script("install.ps1", [*install_arguments(world, tmp_path), "-Apply"], environment)
    uninstall_arguments = ["-GameDir", str(world.game_dir), "-RepoRoot", str(tmp_path / "repo")]

    dry_run = run_script("uninstall.ps1", uninstall_arguments, environment)

    assert dry_run.returncode == 0, dry_run.stderr
    assert "dry-run" in dry_run.stdout
    assert world.game_pck.read_bytes() == ARTIFACT_PCK

    applied = run_script("uninstall.ps1", [*uninstall_arguments, "-Apply"], environment)

    assert applied.returncode == 0, applied.stderr
    assert world.game_pck.read_bytes() == ORIGINAL_PCK


def test_uninstall_script_accepts_an_explicit_backup_folder(tmp_path: Path) -> None:
    world, environment = make_script_world(tmp_path)
    run_script("install.ps1", [*install_arguments(world, tmp_path), "-Apply"], environment)
    backup_folder = next((backup_root_of(environment) / "fixture").iterdir())

    result = run_script("uninstall.ps1", [
        "-GameDir", str(world.game_dir), "-Backup", str(backup_folder),
        "-RepoRoot", str(tmp_path / "repo"), "-Apply",
    ], environment)

    assert result.returncode == 0, result.stderr
    assert world.game_pck.read_bytes() == ORIGINAL_PCK


def test_uninstall_script_refuses_to_overwrite_steam_update(tmp_path: Path) -> None:
    world, environment = make_script_world(tmp_path)
    run_script("install.ps1", [*install_arguments(world, tmp_path), "-Apply"], environment)
    world.game_pck.write_bytes(b"new build from a Steam update")

    result = run_script(
        "uninstall.ps1",
        ["-GameDir", str(world.game_dir), "-RepoRoot", str(tmp_path / "repo"), "-Apply"],
        environment,
    )

    assert result.returncode != 0
    assert "backup_not_found" in result.stderr
    assert "Steam" in result.stderr
    assert world.game_pck.read_bytes() == b"new build from a Steam update"


def test_uninstall_script_refuses_explicit_stale_backup_over_steam_update(tmp_path: Path) -> None:
    world, environment = make_script_world(tmp_path)
    run_script("install.ps1", [*install_arguments(world, tmp_path), "-Apply"], environment)
    backup_folder = next((backup_root_of(environment) / "fixture").iterdir())
    world.game_pck.write_bytes(b"new build from a Steam update")

    result = run_script("uninstall.ps1", [
        "-GameDir", str(world.game_dir), "-Backup", str(backup_folder),
        "-RepoRoot", str(tmp_path / "repo"), "-Apply",
    ], environment)

    assert result.returncode != 0
    assert "game_changed_since_install" in result.stderr
    assert world.game_pck.read_bytes() == b"new build from a Steam update"
