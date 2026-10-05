"""Fingerprint checks and metadata for a local, read-only game extraction."""

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from hnh_vi.builds import (
    VerificationResult,
    load_build_specs,
    sha256_file,
    verify_game_dir,
)
from hnh_vi.tools import ensure_tool, load_tool_specs


@dataclass(frozen=True)
class WorkspaceSnapshot:
    build_id: str
    pck_sha256: str
    source_csv_sha256: str
    extracted_at_utc: str


def write_snapshot(path: Path, snapshot: WorkspaceSnapshot) -> None:
    """Write stable metadata; extracted source text is never part of the JSON."""
    path.write_text(
        json.dumps(asdict(snapshot), sort_keys=True, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )


def verify_snapshot(
    snapshot_path: Path, source_csv: Path, source_pck: Path, expected_build_id: str,
) -> VerificationResult:
    """Detect missing files, mismatched build identity and changed source bytes."""
    if any(not path.is_file() for path in (snapshot_path, source_csv, source_pck)):
        return VerificationResult(False, ("missing_file",))
    try:
        snapshot = WorkspaceSnapshot(**json.loads(snapshot_path.read_text(encoding="utf-8")))
        if any(not isinstance(value, str) for value in asdict(snapshot).values()):
            raise ValueError("Invalid snapshot field")
        for digest in (snapshot.pck_sha256, snapshot.source_csv_sha256):
            if not re.fullmatch(r"[A-Fa-f0-9]{64}", digest):
                raise ValueError("Invalid snapshot digest")
        if datetime.fromisoformat(snapshot.extracted_at_utc).utcoffset() != UTC.utcoffset(None):
            raise ValueError("Snapshot timestamp must be UTC")
    except (ValueError, TypeError):
        return VerificationResult(False, ("invalid_snapshot",))
    issues = []
    if snapshot.build_id != expected_build_id:
        issues.append("build_id_mismatch")
    if sha256_file(source_csv) != snapshot.source_csv_sha256.upper():
        issues.append("source_csv_drift")
    if sha256_file(source_pck) != snapshot.pck_sha256.upper():
        issues.append("pck_drift")
    return VerificationResult(not issues, tuple(issues))


def summarize_probe(source: Path, recovery_log: Path) -> dict:
    """Report conservative source evidence without copying extracted text."""
    issues = []
    csv_path = source / "localisation/translations.csv"
    headers, rows = [], 0
    if csv_path.is_file():
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            headers = next(reader, [])
            for row in reader:
                rows += 1
                if len(row) != len(headers):
                    issues.append("csv_column_mismatch")
        if not headers or headers[0] != "key" or len(set(headers)) != len(headers):
            issues.append("unknown_csv_schema")
    else:
        issues.append("source_csv_missing")
    log = recovery_log.read_text(encoding="utf-8-sig", errors="replace")
    incomplete = re.search(r"Could not recover (\d+)/(\d+) keys", log)
    unrecovered = int(incomplete[1]) if incomplete else 0
    if incomplete or "Translation Export Incomplete" in log:
        issues.append("translation_recovery_incomplete")
    scripts = {}
    for name in ("Scenes/language.gd", "globals/language_manager.gd"):
        path = source / name
        scripts[name] = path.read_text(encoding="utf-8") if path.is_file() else ""
    selector, manager = scripts.values()
    # Require the loaded-locale list to feed the dropdown, its metadata, and selection.
    dynamic_selector = all(re.search(pattern, selector) for pattern in (
        r"var locales\s*=\s*TranslationServer\.get_loaded_locales\(\)",
        r"for i in range\(locales\.size\(\)\):\s*var locale\s*=\s*locales\[i\]",
        r"language_dropdown\.add_item\(",
        r"language_dropdown\.set_item_metadata\(i,\s*locale\)",
        r"var selected_locale\s*=\s*language_dropdown\.get_item_metadata\(index\)",
        r"TranslationServer\.set_locale\((?:selected_locale|current_locale)\)",
    ))
    dynamic_manager = all(re.search(pattern, manager) for pattern in (
        r"var loaded_locales\s*=\s*TranslationServer\.get_loaded_locales\(\)",
        r"loaded_locales\.has\(target_locale\)",
        r"TranslationServer\.set_locale\(target_locale\)",
        r'config\.set_value\("localization",\s*"language",\s*locale\)',
    ))
    selection = "unknown"
    if dynamic_selector and dynamic_manager:
        selection = "dynamic"
    elif re.search(r"var locales\s*=\s*\[", selector):
        selection = "hardcoded"
    if selection != "dynamic":
        issues.append("locale_selection_" + selection)
    return {
        "csv_headers": headers, "csv_locales": headers[1:], "csv_rows": rows,
        "source_csv_sha256": sha256_file(csv_path) if csv_path.is_file() else None,
        "unrecovered_keys": unrecovered,
        "translation_key_count": int(incomplete[2]) if incomplete else rows,
        "locale_selection": selection,
        "script_sha256": {
            name: sha256_file(source / name) for name, text in scripts.items() if text
        },
        "compatible": not issues, "issues": sorted(set(issues)),
    }


def _verified_context(repo_root: Path, game_dir: Path) -> dict[str, str]:
    repo_root, game_dir = repo_root.resolve(strict=True), game_dir.resolve(strict=True)
    if repo_root.is_relative_to(game_dir) or game_dir.is_relative_to(repo_root):
        raise ValueError("unsafe_workspace: repository and game directories overlap")
    specs = load_build_specs(repo_root / "manifests/game-builds.json")
    results = [(spec, verify_game_dir(game_dir, spec)) for spec in specs]
    matches = [spec for spec, result in results if result.ok]
    if len(matches) != 1:
        issues = sorted({issue for _, result in results for issue in result.issues})
        raise ValueError("unsupported_build: " + ",".join(issues or ["ambiguous_build"]))
    spec = matches[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", spec.build_id):
        raise ValueError("unsafe_build_id")
    workspace = repo_root / "workspace" / spec.build_id
    for path in (repo_root / "workspace", workspace, workspace / "source"):
        if path.is_symlink() or path.is_junction():
            raise ValueError("unsafe_workspace: linked output directory")
    if workspace.exists():
        for path in workspace.rglob("*"):
            if path.is_symlink() or path.is_junction():
                raise ValueError("unsafe_workspace: linked output entry")
    tools = {}
    for tool in load_tool_specs(repo_root / "manifests/tools.json"):
        installed = ensure_tool(tool, repo_root / ".tools", offline=True)
        if tool.id == "gdre-tools":
            tools["gdre"] = str(installed / "gdre_tools.exe")
        elif tool.id == "godot":
            tools["godot"] = str(installed / f"Godot_v{tool.version}_win64_console.exe")
    if tools.keys() != {"gdre", "godot"}:
        raise ValueError("missing_pinned_tools")
    return {
        "build_id": spec.build_id, "pck": str(game_dir / spec.pck_name),
        "workspace": str(workspace), "source_csv": str(workspace / "source/localisation/translations.csv"),
        **tools,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "snapshot", "probe-report"))
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--game-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        context = _verified_context(args.repo_root, args.game_dir)
        workspace = Path(context["workspace"])
        if args.command == "prepare":
            (workspace / "source").mkdir(parents=True, exist_ok=True)
            print(json.dumps(context))
        elif args.command == "snapshot":
            write_snapshot(workspace / "snapshot.json", WorkspaceSnapshot(
                context["build_id"], sha256_file(Path(context["pck"])),
                sha256_file(Path(context["source_csv"])),
                datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            ))
        else:
            report = summarize_probe(workspace / "probe/source", workspace / "probe/recovery.log")
            report.update({
                "build_id": context["build_id"],
                "pck_sha256": sha256_file(Path(context["pck"])),
                "gdre_version": (workspace / "probe/gdre-version.txt").read_text(
                    encoding="utf-8-sig"
                ).strip(),
                "godot_version": (workspace / "probe/godot-version.txt").read_text(
                    encoding="utf-8-sig"
                ).strip(),
                "pck_file_count": sum(
                    line.strip().startswith("res://")
                    for line in (workspace / "probe/pck-files.txt").read_text(
                        encoding="utf-8-sig"
                    ).splitlines()
                ),
            })
            output = json.dumps(report, sort_keys=True, indent=2) + "\n"
            (workspace / "probe/report.json").write_text(output, encoding="utf-8", newline="\n")
            print(output, end="")
            if not report["compatible"]:
                return 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
