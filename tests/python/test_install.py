import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from test_build import make_metadata_inputs

from hnh_vi import install
from hnh_vi.build import (
    PROJECT_BINARY_PATH,
    VI_TRANSLATION_PATH,
    make_preview_metadata,
)
from hnh_vi.builds import BuildSpec, sha256_file
from hnh_vi.install import (
    BackupRecord,
    InstallPlan,
    apply_install,
    apply_uninstall,
    plan_install,
    plan_uninstall,
)

EXE_NAME = "Game fixture.exe"
PCK_NAME = "Game fixture.pck"
ORIGINAL_PCK = b"original game pck bytes " * 50
ARTIFACT_PCK = b"patched preview pck bytes " * 50


@dataclass
class World:
    """A synthetic game folder, a verified preview artifact and an empty backup folder."""

    game_dir: Path
    spec: BuildSpec
    artifact_path: Path
    metadata_path: Path
    backup_root: Path

    @property
    def game_pck(self) -> Path:
        return self.game_dir / PCK_NAME

    @property
    def game_exe(self) -> Path:
        return self.game_dir / EXE_NAME

    def plan_install(self) -> InstallPlan:
        return plan_install(
            self.game_dir, self.artifact_path, self.metadata_path, self.backup_root,
            build_specs=(self.spec,),
        )

    def plan_uninstall(self, record_path: Path) -> InstallPlan:
        return plan_uninstall(self.game_dir, record_path, build_specs=(self.spec,))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def write_metadata(world_dir: Path, artifact_path: Path, spec: BuildSpec, changes: dict) -> Path:
    """Write valid preview metadata for the artifact, then apply test-specific changes."""
    inputs_dir = world_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    source, coverage, build_input, _, selected = make_metadata_inputs(inputs_dir)
    completeness = replace(
        source.completeness, build_id=spec.build_id, pck_sha256=spec.pck_sha256,
    )
    metadata = make_preview_metadata(
        game_version=spec.exe_version,
        source_pck_sha256=spec.pck_sha256,
        build_input=build_input,
        artifact_path=artifact_path,
        patched_paths=(VI_TRANSLATION_PATH, PROJECT_BINARY_PATH),
        completeness=completeness,
        coverage=coverage,
        selected_keys=selected,
        tool_versions={"gdre-tools": "2.7.0", "godot": "4.6.3-stable"},
    )
    metadata.update(changes)
    metadata_path = artifact_path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata_path


def make_world(
    tmp_path: Path, game_folder: str = "Game with spaces", artifact_dir: str = "dist/fixture",
) -> World:
    game_dir = tmp_path / game_folder
    game_dir.mkdir()
    (game_dir / EXE_NAME).write_bytes(b"synthetic exe bytes")
    (game_dir / PCK_NAME).write_bytes(ORIGINAL_PCK)
    spec = BuildSpec(
        build_id="fixture", exe_version="1.1.0.0", confirmed_on="2026-10-06",
        exe_name=EXE_NAME, exe_sha256=sha256_file(game_dir / EXE_NAME),
        pck_name=PCK_NAME, pck_sha256=sha256_file(game_dir / PCK_NAME),
    )
    artifact_folder = tmp_path / "repo" / artifact_dir
    artifact_folder.mkdir(parents=True)
    artifact_path = artifact_folder / "Hearth-and-Hamlet-vi-preview-1.1.0.pck"
    artifact_path.write_bytes(ARTIFACT_PCK)
    metadata_path = write_metadata(tmp_path / "metadata work", artifact_path, spec, {})
    return World(game_dir, spec, artifact_path, metadata_path, tmp_path / "backups")


def snapshot_tree(folder: Path) -> dict[str, str]:
    """Relative path -> content hash, so a test can prove nothing changed."""
    return {
        str(path.relative_to(folder)): sha256_file(path)
        for path in sorted(folder.rglob("*")) if path.is_file()
    }


def install_for_real(world: World) -> BackupRecord:
    return apply_install(world.plan_install())


# ---- Dry-run planning ---------------------------------------------------------------------


def test_plan_install_is_a_dry_run_that_writes_nothing(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    game_before = snapshot_tree(world.game_dir)
    repo_before = snapshot_tree(tmp_path / "repo")

    plan = world.plan_install()

    assert plan.action == "install"
    assert plan.build_id == "fixture"
    assert plan.target_pck == world.game_pck
    assert plan.current_pck_sha256 == sha256_bytes(ORIGINAL_PCK)
    assert plan.new_pck_sha256 == sha256_bytes(ARTIFACT_PCK)
    assert plan.backup_dir.parent == world.backup_root / "fixture"
    assert snapshot_tree(world.game_dir) == game_before
    assert snapshot_tree(tmp_path / "repo") == repo_before
    assert not world.backup_root.exists()


def test_plan_install_rejects_unsupported_executable(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    world.game_exe.write_bytes(b"other exe")

    with pytest.raises(ValueError, match="unsupported_build"):
        world.plan_install()


def test_plan_install_rejects_source_drift_in_game_pck(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    world.game_pck.write_bytes(b"Steam updated this pck")

    with pytest.raises(ValueError, match="unsupported_build"):
        world.plan_install()
    assert world.game_pck.read_bytes() == b"Steam updated this pck"


def test_plan_install_rejects_missing_game_files(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    world.game_pck.unlink()

    with pytest.raises(ValueError, match="unsupported_build"):
        world.plan_install()


def test_plan_install_rejects_artifact_that_is_already_installed(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    world.game_pck.write_bytes(ARTIFACT_PCK)

    with pytest.raises(ValueError, match="already_installed"):
        world.plan_install()


def test_plan_install_rejects_artifact_bytes_that_differ_from_metadata(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    world.artifact_path.write_bytes(ARTIFACT_PCK + b"tampered")

    with pytest.raises(ValueError, match="build_artifact_mismatch"):
        world.plan_install()


def test_plan_install_rejects_artifact_built_from_another_pck(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    write_metadata(tmp_path / "metadata work", world.artifact_path, world.spec, {
        "source_pck_sha256": "B" * 64,
    })

    with pytest.raises(ValueError, match="artifact_mismatch|invalid_build_metadata"):
        world.plan_install()


def test_plan_install_rejects_artifact_for_another_build(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    other_spec = replace(world.spec, build_id="other")

    with pytest.raises(ValueError, match="unsupported_build"):
        plan_install(
            world.game_dir, world.artifact_path, world.metadata_path, world.backup_root,
            build_specs=(other_spec,),
        )


def test_plan_install_rejects_artifact_for_another_game_version(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    write_metadata(tmp_path / "metadata work", world.artifact_path, world.spec, {
        "game_version": "9.9.9",
    })

    with pytest.raises(ValueError, match="artifact_mismatch"):
        world.plan_install()


def test_plan_install_rejects_diagnostic_artifact_by_folder(tmp_path: Path) -> None:
    world = make_world(tmp_path, artifact_dir="dist/fixture/diagnostic")

    with pytest.raises(ValueError, match="diagnostic_artifact_rejected"):
        world.plan_install()


def test_plan_install_rejects_diagnostic_artifact_by_metadata(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    write_metadata(tmp_path / "metadata work", world.artifact_path, world.spec, {
        "artifact_kind": "diagnostic_probe", "release_quality": "diagnostic",
    })

    with pytest.raises(ValueError, match="diagnostic_artifact_rejected"):
        world.plan_install()


def test_plan_install_rejects_diagnostic_patched_path(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    write_metadata(tmp_path / "metadata work", world.artifact_path, world.spec, {
        "patched_paths": ["res://diagnostic/runtime-key.gd", VI_TRANSLATION_PATH],
    })

    with pytest.raises(ValueError, match="invalid_build_metadata"):
        world.plan_install()


def test_plan_install_rejects_artifact_or_backups_inside_the_game_folder(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    inside_artifact = world.game_dir / world.artifact_path.name
    shutil.copy2(world.artifact_path, inside_artifact)
    shutil.copy2(world.metadata_path, inside_artifact.with_suffix(".json"))

    with pytest.raises(ValueError, match="unsafe_path"):
        plan_install(
            world.game_dir, inside_artifact, inside_artifact.with_suffix(".json"),
            world.backup_root, build_specs=(world.spec,),
        )
    with pytest.raises(ValueError, match="unsafe_path"):
        plan_install(
            world.game_dir, world.artifact_path, world.metadata_path,
            world.game_dir / "backups", build_specs=(world.spec,),
        )


# ---- Apply install ------------------------------------------------------------------------


def test_apply_install_replaces_pck_and_writes_verified_backup(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    exe_before = world.game_exe.read_bytes()

    record = install_for_real(world)

    assert world.game_pck.read_bytes() == ARTIFACT_PCK
    assert world.game_exe.read_bytes() == exe_before
    assert record.pck_path.read_bytes() == ORIGINAL_PCK
    assert record.pck_path.parent.parent == world.backup_root / "fixture"
    assert record.metadata_path.parent == record.pck_path.parent
    assert record.original_pck_sha256 == sha256_bytes(ORIGINAL_PCK)
    assert record.installed_pck_sha256 == sha256_bytes(ARTIFACT_PCK)
    saved = json.loads(record.metadata_path.read_text(encoding="utf-8"))
    assert saved["build_id"] == "fixture"
    assert saved["original_pck_sha256"] == sha256_bytes(ORIGINAL_PCK)
    # Only the game files remain: no staging leftovers beside them.
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_apply_install_works_with_unicode_and_spaces_in_paths(tmp_path: Path) -> None:
    world = make_world(tmp_path, game_folder="Trò chơi Việt hóa")

    install_for_real(world)

    assert world.game_pck.read_bytes() == ARTIFACT_PCK


def test_apply_install_never_overwrites_an_existing_backup(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    monkeypatch.setattr(install, "_new_backup_name", lambda: "20261006T000000000000Z")
    old_backup = world.backup_root / "fixture" / "20261006T000000000000Z"
    old_backup.mkdir(parents=True)
    (old_backup / "old.txt").write_text("keep me", encoding="utf-8")

    with pytest.raises(ValueError, match="backup_exists"):
        install_for_real(world)

    assert (old_backup / "old.txt").read_text(encoding="utf-8") == "keep me"
    assert world.game_pck.read_bytes() == ORIGINAL_PCK


def test_two_installs_create_two_separate_backups(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    first = install_for_real(world)
    apply_uninstall(world.plan_uninstall(first.metadata_path))

    second = install_for_real(world)

    assert first.pck_path.parent != second.pck_path.parent
    assert first.pck_path.read_bytes() == ORIGINAL_PCK
    assert second.pck_path.read_bytes() == ORIGINAL_PCK


def test_apply_install_stages_on_the_game_volume_before_replace(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    swaps: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def spy_replace(source, destination):
        swaps.append((Path(source), Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr(install.os, "replace", spy_replace)

    install_for_real(world)

    game_swaps = [(source, destination) for source, destination in swaps if destination == world.game_pck]
    assert len(game_swaps) == 1
    staging, destination = game_swaps[0]
    assert staging.parent == destination.parent == world.game_dir
    assert staging != world.artifact_path


def test_failure_before_replace_leaves_game_pck_unchanged(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    real_replace = os.replace

    def failing_replace(source, destination):
        if Path(destination) == world.game_pck:
            raise PermissionError("game file is in use")
        real_replace(source, destination)

    monkeypatch.setattr(install.os, "replace", failing_replace)

    with pytest.raises(PermissionError):
        install_for_real(world)

    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_staging_hash_mismatch_stops_before_replace(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    real_copy2 = shutil.copy2

    def corrupting_copy2(source, destination, **kwargs):
        real_copy2(source, destination, **kwargs)
        if Path(destination).parent == world.game_dir:
            Path(destination).write_bytes(b"corrupted staging copy")

    monkeypatch.setattr(install.shutil, "copy2", corrupting_copy2)

    with pytest.raises(ValueError, match="staging_verify_failed"):
        install_for_real(world)

    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_failure_after_replace_restores_the_verified_backup(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)

    def failing_verification(plan):
        assert world.game_pck.read_bytes() == ARTIFACT_PCK
        raise ValueError("synthetic post-swap failure")

    monkeypatch.setattr(install, "_verify_installed_game", failing_verification)

    with pytest.raises(ValueError, match="install_verification_failed"):
        install_for_real(world)

    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    backups = list((world.backup_root / "fixture").iterdir())
    assert len(backups) == 1
    assert (backups[0] / PCK_NAME).read_bytes() == ORIGINAL_PCK
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_rollback_failure_names_the_backup_to_restore_by_hand(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    real_replace = os.replace
    swap_count = 0

    def replace_that_fails_on_rollback(source, destination):
        nonlocal swap_count
        if Path(destination) == world.game_pck:
            swap_count += 1
            if swap_count == 2:
                raise PermissionError("cannot roll back")
        real_replace(source, destination)

    monkeypatch.setattr(install.os, "replace", replace_that_fails_on_rollback)
    monkeypatch.setattr(
        install, "_verify_installed_game",
        lambda plan: (_ for _ in ()).throw(OSError("synthetic post-swap failure")),
    )

    with pytest.raises(ValueError, match="rollback_failed") as error:
        install_for_real(world)

    assert "Game fixture.pck" in str(error.value)
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_apply_install_rechecks_the_game_after_planning(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    plan = world.plan_install()
    world.game_pck.write_bytes(b"Steam updated between plan and apply")

    with pytest.raises(ValueError, match="unsupported_build"):
        apply_install(plan)

    assert world.game_pck.read_bytes() == b"Steam updated between plan and apply"
    assert not world.backup_root.exists()


def test_apply_install_rechecks_the_artifact_after_planning(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    plan = world.plan_install()
    world.artifact_path.write_bytes(b"swapped artifact")

    with pytest.raises(ValueError, match="build_artifact_mismatch"):
        apply_install(plan)

    assert world.game_pck.read_bytes() == ORIGINAL_PCK


def test_apply_functions_refuse_the_other_kind_of_plan(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    install_plan = world.plan_install()
    record = install_for_real(world)
    uninstall_plan = world.plan_uninstall(record.metadata_path)

    with pytest.raises(ValueError, match="wrong_plan"):
        apply_install(uninstall_plan)
    with pytest.raises(ValueError, match="wrong_plan"):
        apply_uninstall(install_plan)
    assert world.game_pck.read_bytes() == ARTIFACT_PCK


# ---- Link protections ---------------------------------------------------------------------


def test_install_rejects_hard_linked_game_pck(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    os.link(world.game_pck, tmp_path / "alias.pck")

    with pytest.raises(ValueError, match="unsafe_link"):
        world.plan_install()

    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    assert not world.backup_root.exists()


def test_install_rejects_hard_linked_artifact(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    os.link(world.artifact_path, tmp_path / "alias.pck")

    with pytest.raises(ValueError, match="unsafe_workspace"):
        world.plan_install()


def test_install_rejects_symlinked_game_pck(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    real_pck = tmp_path / "real.pck"
    real_pck.write_bytes(ORIGINAL_PCK)
    world.game_pck.unlink()
    try:
        world.game_pck.symlink_to(real_pck)
    except OSError:
        pytest.skip("symbolic links need extra privileges on this machine")

    with pytest.raises(ValueError, match="unsafe_link"):
        world.plan_install()


def make_junction(link: Path, target: Path) -> None:
    result = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        pytest.skip("cannot create a junction on this machine")


def test_install_rejects_junction_as_backup_root(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    make_junction(world.backup_root, elsewhere)

    with pytest.raises(ValueError, match="unsafe_link"):
        world.plan_install()

    assert list(elsewhere.iterdir()) == []
    assert world.game_pck.read_bytes() == ORIGINAL_PCK


def test_install_rejects_junction_inside_backup_folder(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    world.backup_root.mkdir()
    make_junction(world.backup_root / "fixture", elsewhere)

    with pytest.raises(ValueError, match="unsafe_link"):
        install_for_real(world)

    assert list(elsewhere.iterdir()) == []
    assert world.game_pck.read_bytes() == ORIGINAL_PCK


def test_install_rejects_symlinked_backup_folder(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    try:
        world.backup_root.symlink_to(elsewhere, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links need extra privileges on this machine")

    with pytest.raises(ValueError, match="unsafe_link"):
        world.plan_install()


# ---- Uninstall ----------------------------------------------------------------------------


def test_uninstall_restores_the_exact_original_bytes(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    exe_before = world.game_exe.read_bytes()
    record = install_for_real(world)
    backup_before = snapshot_tree(record.pck_path.parent)

    plan = world.plan_uninstall(record.metadata_path)
    game_after_plan = snapshot_tree(world.game_dir)
    assert game_after_plan[PCK_NAME] == sha256_bytes(ARTIFACT_PCK)
    apply_uninstall(plan)

    assert plan.action == "uninstall"
    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    assert sha256_file(world.game_pck) == world.spec.pck_sha256
    assert world.game_exe.read_bytes() == exe_before
    assert snapshot_tree(record.pck_path.parent) == backup_before
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_uninstall_plan_is_a_dry_run(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    game_before = snapshot_tree(world.game_dir)
    backups_before = snapshot_tree(world.backup_root)

    world.plan_uninstall(record.metadata_path)

    assert snapshot_tree(world.game_dir) == game_before
    assert snapshot_tree(world.backup_root) == backups_before


def test_uninstall_refuses_to_restore_stale_backup_over_steam_update(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    world.game_pck.write_bytes(b"new build from a Steam update")
    world.game_exe.write_bytes(b"new exe from a Steam update")

    with pytest.raises(ValueError, match="game_changed_since_install") as error:
        world.plan_uninstall(record.metadata_path)

    assert "Steam" in str(error.value)
    assert world.game_pck.read_bytes() == b"new build from a Steam update"


def test_uninstall_refuses_when_only_the_pck_changed_after_install(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    world.game_pck.write_bytes(b"another mod replaced the pck")

    with pytest.raises(ValueError, match="game_changed_since_install"):
        world.plan_uninstall(record.metadata_path)


def test_apply_uninstall_rechecks_the_game_after_planning(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    plan = world.plan_uninstall(record.metadata_path)
    world.game_pck.write_bytes(b"Steam updated between plan and apply")

    with pytest.raises(ValueError, match="game_changed_since_install"):
        apply_uninstall(plan)

    assert world.game_pck.read_bytes() == b"Steam updated between plan and apply"


def test_uninstall_reports_game_that_is_already_original(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    apply_uninstall(world.plan_uninstall(record.metadata_path))

    with pytest.raises(ValueError, match="already_original"):
        world.plan_uninstall(record.metadata_path)


def test_failed_restore_verification_keeps_the_backup(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    monkeypatch.setattr(
        install, "_verify_restored_game",
        lambda plan: (_ for _ in ()).throw(ValueError("synthetic restore failure")),
    )

    with pytest.raises(ValueError, match="restore_verification_failed") as error:
        apply_uninstall(world.plan_uninstall(record.metadata_path))

    assert str(record.pck_path) in str(error.value)
    assert record.pck_path.read_bytes() == ORIGINAL_PCK


def test_uninstall_failure_before_replace_leaves_installed_pck(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    real_replace = os.replace

    def failing_replace(source, destination):
        if Path(destination) == world.game_pck:
            raise PermissionError("game file is in use")
        real_replace(source, destination)

    monkeypatch.setattr(install.os, "replace", failing_replace)

    with pytest.raises(PermissionError):
        apply_uninstall(world.plan_uninstall(record.metadata_path))

    assert world.game_pck.read_bytes() == ARTIFACT_PCK
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def rewrite_backup_metadata(record: BackupRecord, changes: dict) -> None:
    saved = json.loads(record.metadata_path.read_text(encoding="utf-8"))
    saved.update(changes)
    record.metadata_path.write_text(json.dumps(saved), encoding="utf-8")


@pytest.mark.parametrize("problem", [
    "backup_pck_changed", "backup_pck_missing", "metadata_not_json", "extra_field",
    "forged_original_hash", "wrong_build", "wrong_kind", "same_original_and_installed",
])
def test_uninstall_rejects_invalid_backups(tmp_path: Path, problem: str) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    if problem == "backup_pck_changed":
        record.pck_path.write_bytes(b"tampered backup")
    elif problem == "backup_pck_missing":
        record.pck_path.unlink()
    elif problem == "metadata_not_json":
        record.metadata_path.write_text("{not json", encoding="utf-8")
    elif problem == "extra_field":
        rewrite_backup_metadata(record, {"extra": 1})
    elif problem == "forged_original_hash":
        record.pck_path.write_bytes(b"forged")
        rewrite_backup_metadata(record, {
            "original_pck_sha256": sha256_bytes(b"forged"), "original_pck_size": 6,
        })
    elif problem == "wrong_build":
        rewrite_backup_metadata(record, {"build_id": "other"})
    elif problem == "wrong_kind":
        rewrite_backup_metadata(record, {"kind": "something_else"})
    else:
        rewrite_backup_metadata(record, {"installed_pck_sha256": record.original_pck_sha256})

    with pytest.raises(ValueError, match="backup_invalid"):
        world.plan_uninstall(record.metadata_path)

    assert world.game_pck.read_bytes() == ARTIFACT_PCK


def test_uninstall_rejects_hard_linked_backup_pck(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    os.link(record.pck_path, tmp_path / "alias.pck")

    with pytest.raises(ValueError, match="unsafe_link|backup_invalid"):
        world.plan_uninstall(record.metadata_path)


def test_uninstall_rejects_hard_linked_game_pck(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    os.link(world.game_pck, tmp_path / "alias.pck")

    with pytest.raises(ValueError, match="unsafe_link"):
        world.plan_uninstall(record.metadata_path)


def test_find_latest_backup_picks_newest_matching_backup(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    names = iter(["20261006T010000000000Z", "20261006T020000000000Z"])
    monkeypatch.setattr(install, "_new_backup_name", lambda: next(names))
    first = install_for_real(world)
    apply_uninstall(world.plan_uninstall(first.metadata_path))
    second = install_for_real(world)

    found = install.find_latest_backup(world.game_dir, world.backup_root, (world.spec,))

    assert found == second.metadata_path


def test_find_latest_backup_reports_missing_backup_with_steam_hint(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    world.game_pck.write_bytes(ARTIFACT_PCK)

    with pytest.raises(ValueError, match="backup_not_found") as error:
        install.find_latest_backup(world.game_dir, world.backup_root, (world.spec,))

    assert "Steam" in str(error.value)


def test_find_latest_backup_reports_original_game(tmp_path: Path) -> None:
    world = make_world(tmp_path)

    with pytest.raises(ValueError, match="already_original"):
        install.find_latest_backup(world.game_dir, world.backup_root, (world.spec,))


# ---- Interrupts and last checks -----------------------------------------------------------


def raise_keyboard_interrupt(*arguments):
    raise KeyboardInterrupt


def test_interrupt_after_replace_restores_the_verified_backup(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)

    def interrupted_verification(plan):
        assert world.game_pck.read_bytes() == ARTIFACT_PCK
        raise KeyboardInterrupt

    monkeypatch.setattr(install, "_verify_installed_game", interrupted_verification)

    with pytest.raises(KeyboardInterrupt):
        install_for_real(world)

    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    backups = list((world.backup_root / "fixture").iterdir())
    assert len(backups) == 1
    assert (backups[0] / PCK_NAME).read_bytes() == ORIGINAL_PCK
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_interrupt_right_after_the_swap_still_restores_the_backup(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    real_replace = os.replace

    def replace_then_interrupt(source, destination):
        real_replace(source, destination)
        if Path(destination) == world.game_pck:
            raise KeyboardInterrupt

    monkeypatch.setattr(install.os, "replace", replace_then_interrupt)

    with pytest.raises(KeyboardInterrupt):
        install_for_real(world)

    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_interrupt_while_staging_leaves_game_clean_and_removes_attempt_backup(
    tmp_path: Path, monkeypatch,
) -> None:
    world = make_world(tmp_path)
    real_copy2 = shutil.copy2

    def interrupted_copy2(source, destination, **kwargs):
        real_copy2(source, destination, **kwargs)
        if Path(destination).parent == world.game_dir:
            raise KeyboardInterrupt

    monkeypatch.setattr(install.shutil, "copy2", interrupted_copy2)

    with pytest.raises(KeyboardInterrupt):
        install_for_real(world)

    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]
    assert list((world.backup_root / "fixture").iterdir()) == []


def test_interrupt_while_backing_up_removes_the_half_written_backup(
    tmp_path: Path, monkeypatch,
) -> None:
    world = make_world(tmp_path)
    monkeypatch.setattr(install.shutil, "copy2", raise_keyboard_interrupt)

    with pytest.raises(KeyboardInterrupt):
        install_for_real(world)

    assert world.game_pck.read_bytes() == ORIGINAL_PCK
    assert list((world.backup_root / "fixture").iterdir()) == []


def test_uninstall_stops_when_game_pck_changes_while_staging(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    plan = world.plan_uninstall(record.metadata_path)
    real_copy2 = shutil.copy2

    def copy2_while_steam_updates(source, destination, **kwargs):
        real_copy2(source, destination, **kwargs)
        if Path(destination).parent == world.game_dir:
            world.game_pck.write_bytes(b"Steam updated while the restore was staged")

    monkeypatch.setattr(install.shutil, "copy2", copy2_while_steam_updates)

    with pytest.raises(ValueError, match="game_changed_since_install"):
        apply_uninstall(plan)

    assert world.game_pck.read_bytes() == b"Steam updated while the restore was staged"
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_uninstall_stops_when_game_exe_changes_while_staging(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    plan = world.plan_uninstall(record.metadata_path)
    real_copy2 = shutil.copy2

    def copy2_while_exe_changes(source, destination, **kwargs):
        real_copy2(source, destination, **kwargs)
        if Path(destination).parent == world.game_dir:
            world.game_exe.write_bytes(b"new exe from a Steam update")

    monkeypatch.setattr(install.shutil, "copy2", copy2_while_exe_changes)

    with pytest.raises(ValueError, match="game_changed_since_install"):
        apply_uninstall(plan)

    assert world.game_pck.read_bytes() == ARTIFACT_PCK
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]


def test_interrupt_while_staging_uninstall_leaves_installed_pck(tmp_path: Path, monkeypatch) -> None:
    world = make_world(tmp_path)
    record = install_for_real(world)
    plan = world.plan_uninstall(record.metadata_path)
    real_copy2 = shutil.copy2

    def interrupted_copy2(source, destination, **kwargs):
        real_copy2(source, destination, **kwargs)
        if Path(destination).parent == world.game_dir:
            raise KeyboardInterrupt

    monkeypatch.setattr(install.shutil, "copy2", interrupted_copy2)

    with pytest.raises(KeyboardInterrupt):
        apply_uninstall(plan)

    assert world.game_pck.read_bytes() == ARTIFACT_PCK
    assert sorted(path.name for path in world.game_dir.iterdir()) == [EXE_NAME, PCK_NAME]
