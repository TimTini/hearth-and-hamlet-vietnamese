"""Dry-run planning, atomic apply and exact restore of the partial Vietnamese preview PCK.

Every step fails closed. Planning only reads files. Applying makes a verified backup of the
game PCK, stages the new PCK next to it on the same volume, swaps it in with os.replace and
checks the result. If anything fails after the swap, the verified backup is put back.
"""

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from hnh_vi.build import BuildArtifact, short_game_version, verify_build_artifact
from hnh_vi.builds import BuildSpec, load_build_specs, sha256_file, verify_game_dir

DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "manifests" / "game-builds.json"
BACKUP_METADATA_NAME = "backup.json"
BACKUP_KIND = "pck_backup"
BACKUP_SCHEMA_VERSION = 1
BACKUP_FIELDS = frozenset({
    "schema_version", "kind", "build_id", "pck_name", "original_pck_sha256",
    "original_pck_size", "installed_pck_sha256", "installed_pck_size", "artifact_name",
    "created_utc",
})
SHA256_PATTERN = re.compile(r"[A-F0-9]{64}")
DIAGNOSTIC_FOLDER_NAMES = ("diagnostic", "diagnostics")
STEAM_HINT = (
    "In Steam open the game's Properties > Installed Files > Verify integrity of game files, "
    "or use a backup that was made for the current game build."
)


@dataclass(frozen=True)
class InstallPlan:
    """What an install or uninstall would do. Creating a plan never writes anything."""

    action: str  # "install" or "uninstall"
    build_id: str
    build_spec: BuildSpec
    game_dir: Path
    game_exe: Path
    target_pck: Path
    current_pck_sha256: str
    new_pck_sha256: str
    source_pck: Path  # the artifact for install, the backup PCK for uninstall
    source_metadata_path: Path  # artifact JSON for install, backup JSON for uninstall
    backup_root: Path
    backup_dir: Path


@dataclass(frozen=True)
class BackupRecord:
    """A verified backup folder: the original game PCK plus its JSON metadata."""

    build_id: str
    pck_path: Path
    metadata_path: Path
    original_pck_sha256: str
    installed_pck_sha256: str


# ---- Small checks -------------------------------------------------------------------------


def _new_backup_name() -> str:
    """UTC timestamp with microseconds: unique, and sorts oldest to newest as text."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _reject_link_entry(path: Path) -> None:
    """Refuse symlinks, junctions and files that have more than one hard link."""
    if path.is_symlink() or path.is_junction():
        raise ValueError(f"unsafe_link: {path} is a symlink or junction")
    if path.is_file() and path.stat().st_nlink != 1:
        raise ValueError(f"unsafe_link: {path} has more than one hard link")


def _reject_links_in_chain(path: Path) -> None:
    """Check the path itself and every folder above it."""
    for entry in (path, *path.parents):
        _reject_link_entry(entry)


def _reject_paths_overlapping_game(game_dir: Path, other_paths: list[Path]) -> None:
    for other_path in other_paths:
        resolved = other_path.resolve()
        if resolved.is_relative_to(game_dir) or game_dir.is_relative_to(resolved):
            raise ValueError(
                f"unsafe_path: {other_path} must be outside the game folder {game_dir}"
            )


def _reject_diagnostic_artifact(artifact_path: Path, metadata_path: Path) -> None:
    """Diagnostic probes must never be installed, whatever their metadata claims."""
    for path in (artifact_path, metadata_path):
        folder_names = [part.lower() for part in path.parts[:-1]]
        if any(name in DIAGNOSTIC_FOLDER_NAMES for name in folder_names):
            raise ValueError("diagnostic_artifact_rejected: artifact is in a diagnostic folder")
        if "diagnostic" in path.name.lower():
            raise ValueError("diagnostic_artifact_rejected: artifact file name is diagnostic")

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return  # verify_build_artifact reports unreadable metadata with a clearer message
    if not isinstance(metadata, dict):
        return
    for field in ("artifact_kind", "release_quality"):
        value = metadata.get(field)
        if isinstance(value, str) and "diagnostic" in value.lower():
            raise ValueError(f"diagnostic_artifact_rejected: metadata {field} is {value}")


def _find_supported_spec(game_dir: Path, build_specs: tuple[BuildSpec, ...]) -> BuildSpec:
    """Return the one approved build whose EXE and PCK hashes match the game folder."""
    results = [(spec, verify_game_dir(game_dir, spec)) for spec in build_specs]
    matches = [spec for spec, result in results if result.ok]
    if len(matches) != 1:
        issues = sorted({issue for _, result in results for issue in result.issues})
        raise ValueError("unsupported_build: " + ",".join(issues or ["ambiguous_build"]))
    return matches[0]


def _load_specs(build_specs: tuple[BuildSpec, ...] | None) -> tuple[BuildSpec, ...]:
    if build_specs is not None:
        return build_specs
    return load_build_specs(DEFAULT_MANIFEST)


def _resolve_game_dir(game_dir: Path) -> Path:
    try:
        return game_dir.resolve(strict=True)
    except OSError:
        raise ValueError(f"unsupported_build: game folder {game_dir} does not exist") from None


def _flush_to_disk(path: Path) -> None:
    """Force the bytes of a finished file out of the OS cache before it is trusted."""
    with path.open("r+b") as stream:
        stream.flush()
        os.fsync(stream.fileno())


def _stage_copy(source: Path, target_pck: Path, expected_sha256: str) -> Path:
    """Copy a PCK beside the game PCK (same volume) and verify the copy by hash."""
    staging = target_pck.with_name(f".{target_pck.name}.{uuid.uuid4().hex}.staging")
    try:
        shutil.copy2(source, staging)
        _flush_to_disk(staging)
        if sha256_file(staging) != expected_sha256:
            raise ValueError("staging_verify_failed: staged copy does not match its source hash")
    except Exception:
        staging.unlink(missing_ok=True)
        raise
    return staging


# ---- Backup files -------------------------------------------------------------------------


def _backup_problem(reason: str) -> ValueError:
    return ValueError(f"backup_invalid: {reason}")


def _check_backup_fields(saved: dict) -> None:
    if set(saved) != BACKUP_FIELDS:
        raise _backup_problem("unexpected or missing fields")
    if saved["schema_version"] != BACKUP_SCHEMA_VERSION:
        raise _backup_problem("unsupported schema_version")
    if saved["kind"] != BACKUP_KIND:
        raise _backup_problem("kind must be pck_backup")
    for name in ("original_pck_sha256", "installed_pck_sha256"):
        value = saved[name]
        if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
            raise _backup_problem(f"{name} must be an uppercase SHA-256")
    for name in ("original_pck_size", "installed_pck_size"):
        if type(saved[name]) is not int or saved[name] < 0:
            raise _backup_problem(f"{name} must be a non-negative integer")
    for name in ("build_id", "pck_name", "artifact_name", "created_utc"):
        if not isinstance(saved[name], str) or not saved[name]:
            raise _backup_problem(f"{name} must be text")


def _load_backup_record(
    metadata_path: Path, build_specs: tuple[BuildSpec, ...],
) -> tuple[BackupRecord, BuildSpec]:
    """Read a backup folder and prove its JSON and PCK copy are intact and trustworthy."""
    if not metadata_path.is_file():
        raise _backup_problem(f"metadata file {metadata_path} does not exist")
    _reject_links_in_chain(metadata_path)

    try:
        saved = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise _backup_problem("metadata is not readable JSON") from None
    if not isinstance(saved, dict):
        raise _backup_problem("metadata top level must be an object")
    _check_backup_fields(saved)

    matching_specs = [spec for spec in build_specs if spec.build_id == saved["build_id"]]
    if not matching_specs:
        raise _backup_problem(f"build {saved['build_id']} is not a supported build")
    spec = matching_specs[0]
    if saved["pck_name"] != spec.pck_name:
        raise _backup_problem("backup PCK name does not match the supported build")
    # The backup must hold the exact approved original PCK, never some other bytes.
    if saved["original_pck_sha256"] != spec.pck_sha256.upper():
        raise _backup_problem("original PCK hash is not the supported build's hash")
    if saved["installed_pck_sha256"] == saved["original_pck_sha256"]:
        raise _backup_problem("installed and original PCK hashes must differ")

    backup_pck = metadata_path.parent / spec.pck_name
    if not backup_pck.is_file():
        raise _backup_problem(f"backup PCK {backup_pck} is missing")
    _reject_link_entry(backup_pck)
    if backup_pck.stat().st_size != saved["original_pck_size"]:
        raise _backup_problem("backup PCK size changed")
    if sha256_file(backup_pck) != saved["original_pck_sha256"]:
        raise _backup_problem("backup PCK hash changed")

    record = BackupRecord(
        build_id=spec.build_id,
        pck_path=backup_pck,
        metadata_path=metadata_path,
        original_pck_sha256=saved["original_pck_sha256"],
        installed_pck_sha256=saved["installed_pck_sha256"],
    )
    return record, spec


def _write_backup_metadata(plan: InstallPlan, backup_pck: Path, metadata_path: Path) -> None:
    saved = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "kind": BACKUP_KIND,
        "build_id": plan.build_id,
        "pck_name": plan.build_spec.pck_name,
        "original_pck_sha256": plan.current_pck_sha256,
        "original_pck_size": backup_pck.stat().st_size,
        "installed_pck_sha256": plan.new_pck_sha256,
        "installed_pck_size": plan.source_pck.stat().st_size,
        "artifact_name": plan.source_pck.name,
        "created_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    # "x" fails if the file exists, so an old backup record can never be overwritten.
    with metadata_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(saved, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _create_backup(plan: InstallPlan) -> BackupRecord:
    """Copy the current game PCK into a brand-new backup folder and verify the copy."""
    backup_dir = plan.backup_dir
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    _reject_links_in_chain(backup_dir.parent)
    try:
        backup_dir.mkdir()
    except FileExistsError:
        raise ValueError(f"backup_exists: {backup_dir} already exists and is never overwritten") from None

    # From here the folder is ours, so a failed backup may remove it again.
    try:
        backup_pck = backup_dir / plan.build_spec.pck_name
        shutil.copy2(plan.target_pck, backup_pck)
        _flush_to_disk(backup_pck)
        if sha256_file(backup_pck) != plan.current_pck_sha256:
            raise ValueError("backup_verify_failed: backup copy does not match the game PCK")
        metadata_path = backup_dir / BACKUP_METADATA_NAME
        _write_backup_metadata(plan, backup_pck, metadata_path)
        record, _ = _load_backup_record(metadata_path, (plan.build_spec,))
    except Exception:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise
    return record


# ---- Install ------------------------------------------------------------------------------


def _check_install_inputs(
    game_dir: Path,
    artifact_path: Path,
    artifact_metadata_path: Path,
    backup_root: Path,
    build_specs: tuple[BuildSpec, ...],
) -> tuple[Path, BuildSpec, BuildArtifact]:
    """All read-only checks, shared by planning and by the re-check right before applying."""
    game_dir = _resolve_game_dir(game_dir)
    _reject_paths_overlapping_game(game_dir, [artifact_path, artifact_metadata_path, backup_root])
    _reject_diagnostic_artifact(artifact_path, artifact_metadata_path)
    _reject_links_in_chain(backup_root)

    artifact = verify_build_artifact(artifact_path, artifact_metadata_path)

    # Game files that are links could redirect the swap somewhere else, so they come first.
    for file_name in {spec.exe_name for spec in build_specs} | {spec.pck_name for spec in build_specs}:
        game_file = game_dir / file_name
        if game_file.exists() or game_file.is_symlink():
            _reject_link_entry(game_file)

    # A game PCK that already equals the artifact would otherwise look like source drift.
    for spec in build_specs:
        game_pck = game_dir / spec.pck_name
        if game_pck.is_file() and sha256_file(game_pck) == artifact.sha256:
            raise ValueError("already_installed: the game already contains this preview PCK")

    spec = _find_supported_spec(game_dir, build_specs)
    metadata = artifact.metadata
    if metadata["build_id"] != spec.build_id:
        raise ValueError(
            f"unsupported_build: artifact is for build {metadata['build_id']}, "
            f"the game is build {spec.build_id}"
        )
    if metadata["game_version"] != short_game_version(spec.exe_version):
        raise ValueError("artifact_mismatch: artifact was made for another game version")
    if metadata["source_pck_sha256"] != spec.pck_sha256.upper():
        raise ValueError("artifact_mismatch: artifact was patched from a different game PCK")

    _reject_links_in_chain(backup_root / spec.build_id)
    return game_dir, spec, artifact


def plan_install(
    game_dir: Path,
    artifact_path: Path,
    artifact_metadata_path: Path,
    backup_root: Path,
    build_specs: tuple[BuildSpec, ...] | None = None,
) -> InstallPlan:
    """Check everything an install needs and describe it. Writes nothing."""
    specs = _load_specs(build_specs)
    backup_root = backup_root.absolute()
    game_dir, spec, artifact = _check_install_inputs(
        game_dir, artifact_path, artifact_metadata_path, backup_root, specs,
    )
    return InstallPlan(
        action="install",
        build_id=spec.build_id,
        build_spec=spec,
        game_dir=game_dir,
        game_exe=game_dir / spec.exe_name,
        target_pck=game_dir / spec.pck_name,
        current_pck_sha256=spec.pck_sha256.upper(),
        new_pck_sha256=artifact.sha256,
        source_pck=artifact.pck_path,
        source_metadata_path=artifact.metadata_path,
        backup_root=backup_root,
        backup_dir=backup_root / spec.build_id / _new_backup_name(),
    )


def _verify_installed_game(plan: InstallPlan) -> None:
    """After the swap: the game PCK is the artifact and the EXE is untouched."""
    _reject_link_entry(plan.target_pck)
    if sha256_file(plan.target_pck) != plan.new_pck_sha256:
        raise ValueError("game PCK does not match the installed artifact")
    if sha256_file(plan.game_exe) != plan.build_spec.exe_sha256.upper():
        raise ValueError("game EXE changed during the install")


def _restore_backup_after_failed_install(
    plan: InstallPlan, backup: BackupRecord, original_error: Exception,
) -> ValueError:
    """Put the verified backup back; the returned error is raised by the caller."""
    staging = None
    try:
        staging = _stage_copy(backup.pck_path, plan.target_pck, plan.current_pck_sha256)
        os.replace(staging, plan.target_pck)
        if sha256_file(plan.target_pck) != plan.current_pck_sha256:
            raise ValueError("restored PCK does not match the original hash")
    except (OSError, ValueError) as rollback_error:
        return ValueError(
            f"rollback_failed: the install failed ({original_error}) and restoring the backup "
            f"also failed ({rollback_error}). Restore by hand: copy \"{backup.pck_path}\" over "
            f"\"{plan.target_pck}\" while the game is closed."
        )
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)
    return ValueError(
        f"install_verification_failed: {original_error}. "
        "The original game PCK was restored from the backup."
    )


def apply_install(plan: InstallPlan) -> BackupRecord:
    """Back up the game PCK, then replace it with the preview PCK and verify the result."""
    if plan.action != "install":
        raise ValueError("wrong_plan: apply_install needs an install plan")

    # The game or the artifact may have changed since the dry-run, so check again.
    game_dir, spec, artifact = _check_install_inputs(
        plan.game_dir, plan.source_pck, plan.source_metadata_path,
        plan.backup_root, (plan.build_spec,),
    )
    if (
        game_dir != plan.game_dir or spec != plan.build_spec
        or artifact.sha256 != plan.new_pck_sha256
    ):
        raise ValueError("build_artifact_mismatch: inputs changed since the plan was made")

    backup = _create_backup(plan)
    try:
        staging = _stage_copy(plan.source_pck, plan.target_pck, plan.new_pck_sha256)
    except Exception:
        shutil.rmtree(plan.backup_dir, ignore_errors=True)
        raise

    try:
        # Last look at the game right before the swap, in case Steam changed it meanwhile.
        _reject_link_entry(plan.target_pck)
        if not verify_game_dir(plan.game_dir, spec).ok:
            raise ValueError("unsupported_build: game files changed while preparing the install")
        os.replace(staging, plan.target_pck)
    except Exception:
        # The swap did not happen, so the game PCK is unchanged and the backup is not needed.
        staging.unlink(missing_ok=True)
        shutil.rmtree(plan.backup_dir, ignore_errors=True)
        raise

    try:
        _verify_installed_game(plan)
    except Exception as error:
        raise _restore_backup_after_failed_install(plan, backup, error) from error
    return backup


# ---- Uninstall ----------------------------------------------------------------------------


def _game_changed_error(reason: str) -> ValueError:
    return ValueError(
        f"game_changed_since_install: {reason}. The backup was not restored so it cannot "
        f"overwrite a newer game. {STEAM_HINT}"
    )


def plan_uninstall(
    game_dir: Path,
    backup_record_path: Path,
    build_specs: tuple[BuildSpec, ...] | None = None,
) -> InstallPlan:
    """Check that the backup is intact and still matches the installed game. Writes nothing."""
    specs = _load_specs(build_specs)
    game_dir = _resolve_game_dir(game_dir)
    backup_record_path = backup_record_path.absolute()
    _reject_paths_overlapping_game(game_dir, [backup_record_path])
    backup, spec = _load_backup_record(backup_record_path, specs)

    game_exe = game_dir / spec.exe_name
    target_pck = game_dir / spec.pck_name
    for game_file in (game_exe, target_pck):
        if game_file.exists() or game_file.is_symlink():
            _reject_link_entry(game_file)
    if not game_exe.is_file() or not target_pck.is_file():
        raise _game_changed_error("the game EXE or PCK is missing")

    current_pck_sha256 = sha256_file(target_pck)
    exe_matches = sha256_file(game_exe) == spec.exe_sha256.upper()
    if exe_matches and current_pck_sha256 == backup.original_pck_sha256:
        raise ValueError("already_original: the game already has its original PCK")
    if not exe_matches or current_pck_sha256 != backup.installed_pck_sha256:
        raise _game_changed_error("the game files differ from the build this backup belongs to")

    return InstallPlan(
        action="uninstall",
        build_id=spec.build_id,
        build_spec=spec,
        game_dir=game_dir,
        game_exe=game_exe,
        target_pck=target_pck,
        current_pck_sha256=current_pck_sha256,
        new_pck_sha256=backup.original_pck_sha256,
        source_pck=backup.pck_path,
        source_metadata_path=backup.metadata_path,
        backup_root=backup.pck_path.parent.parent.parent,
        backup_dir=backup.pck_path.parent,
    )


def _verify_restored_game(plan: InstallPlan) -> None:
    """After the restore: the game is exactly the approved original build again."""
    _reject_link_entry(plan.target_pck)
    result = verify_game_dir(plan.game_dir, plan.build_spec)
    if not result.ok:
        raise ValueError("game files do not match the supported build: " + ",".join(result.issues))


def apply_uninstall(plan: InstallPlan) -> None:
    """Restore the verified original PCK from the backup. The backup is kept."""
    if plan.action != "uninstall":
        raise ValueError("wrong_plan: apply_uninstall needs an uninstall plan")

    # Plan again from the saved backup so Steam updates since the dry-run are caught.
    fresh_plan = plan_uninstall(plan.game_dir, plan.source_metadata_path, (plan.build_spec,))
    if fresh_plan.current_pck_sha256 != plan.current_pck_sha256:
        raise _game_changed_error("the game PCK changed since the plan was made")

    staging = _stage_copy(plan.source_pck, plan.target_pck, plan.new_pck_sha256)
    try:
        os.replace(staging, plan.target_pck)
    except Exception:
        staging.unlink(missing_ok=True)
        raise

    try:
        _verify_restored_game(plan)
    except Exception as error:
        raise ValueError(
            f"restore_verification_failed: {error}. The backup is kept at {plan.source_pck}; "
            f"copy it over \"{plan.target_pck}\" by hand or verify the game files in Steam."
        ) from error


def find_latest_backup(
    game_dir: Path, backup_root: Path, build_specs: tuple[BuildSpec, ...] | None = None,
) -> Path:
    """Find the newest backup whose installed PCK is the one currently in the game."""
    specs = _load_specs(build_specs)
    game_dir = _resolve_game_dir(game_dir)
    backup_root = backup_root.absolute()
    _reject_links_in_chain(backup_root)

    for spec in specs:
        if verify_game_dir(game_dir, spec).ok:
            raise ValueError("already_original: the game already has its original PCK")

    game_exe_files = [game_dir / spec.exe_name for spec in specs]
    exe_specs = [
        spec for spec, exe in zip(specs, game_exe_files, strict=True)
        if exe.is_file() and sha256_file(exe) == spec.exe_sha256.upper()
    ]
    if not exe_specs:
        raise ValueError("unsupported_build: the game EXE is not a supported build")

    for spec in exe_specs:
        game_pck = game_dir / spec.pck_name
        if not game_pck.is_file():
            continue
        current_sha256 = sha256_file(game_pck)
        build_folder = backup_root / spec.build_id
        if not build_folder.is_dir():
            continue
        _reject_links_in_chain(build_folder)
        for backup_folder in sorted(build_folder.iterdir(), reverse=True):
            metadata_path = backup_folder / BACKUP_METADATA_NAME
            try:
                record, _ = _load_backup_record(metadata_path, (spec,))
            except ValueError:
                continue  # an unusable backup is skipped, never restored
            if record.installed_pck_sha256 == current_sha256:
                return metadata_path

    raise ValueError(f"backup_not_found: no backup matches the installed PCK. {STEAM_HINT}")


# ---- Command line -------------------------------------------------------------------------


def _describe_plan(plan: InstallPlan, mode: str) -> dict:
    return {
        "mode": mode,
        "action": plan.action,
        "build_id": plan.build_id,
        "game_exe": str(plan.game_exe),
        "game_pck": str(plan.target_pck),
        "current_pck_sha256": plan.current_pck_sha256,
        "new_pck_sha256": plan.new_pck_sha256,
        "source": str(plan.source_pck),
        "backup_dir": str(plan.backup_dir),
    }


def _run_install(args: argparse.Namespace, specs: tuple[BuildSpec, ...] | None) -> dict:
    artifact_path = args.artifact
    plan = plan_install(
        args.game_dir, artifact_path, artifact_path.with_suffix(".json"), args.backup_root, specs,
    )
    if not args.apply:
        return _describe_plan(plan, "dry-run")
    backup = apply_install(plan)
    description = _describe_plan(plan, "applied")
    description["backup_dir"] = str(backup.pck_path.parent)
    return description


def _run_uninstall(args: argparse.Namespace, specs: tuple[BuildSpec, ...] | None) -> dict:
    if args.backup is None:
        record_path = find_latest_backup(args.game_dir, args.backup_root, specs)
    elif args.backup.is_dir():
        record_path = args.backup / BACKUP_METADATA_NAME
    else:
        record_path = args.backup
    plan = plan_uninstall(args.game_dir, record_path, specs)
    if not args.apply:
        return _describe_plan(plan, "dry-run")
    apply_uninstall(plan)
    return _describe_plan(plan, "applied")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "uninstall"))
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    # Error text can contain Unicode paths that a legacy console code page cannot print.
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    try:
        specs = None
        if args.repo_root is not None:
            specs = load_build_specs(args.repo_root / "manifests" / "game-builds.json")
        if args.command == "install":
            if args.artifact is None:
                raise ValueError("missing_argument: install needs --artifact")
            description = _run_install(args, specs)
        else:
            description = _run_uninstall(args, specs)
        print(json.dumps(description, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
