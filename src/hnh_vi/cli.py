"""Command-line workflows for safe Vietnamese localization data."""

import argparse
import csv
import json
import os
import sys
import tempfile
from dataclasses import asdict
from io import StringIO
from pathlib import Path

from hnh_vi.builds import load_build_specs, verify_game_dir
from hnh_vi.completeness import SourceCompleteness, load_source_completeness
from hnh_vi.contracts import (
    GlossaryTerm,
    StatusRow,
    TranslationRow,
    load_glossary_csv,
    load_status_csv,
    load_translation_csv,
    validate_dataset,
)
from hnh_vi.coverage import calculate_coverage
from hnh_vi.dataset import CanonicalSource, audit_source_csv
from hnh_vi.workspace import _reject_linked_output

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPLETENESS = ROOT / "localization/source-completeness.json"
DEFAULT_TRANSLATIONS = ROOT / "localization/translations.vi.csv"
DEFAULT_STATUSES = ROOT / "localization/status.csv"
DEFAULT_GLOSSARY = ROOT / "localization/glossary.csv"
DEFAULT_BUILDS = ROOT / "manifests/game-builds.json"


class CommandError(Exception):
    def __init__(self, code: int, error: str, issues: tuple[str, ...] = ()) -> None:
        self.code = code
        self.error = error
        self.issues = issues


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    verify = commands.add_parser("verify-game", help="verify a supported local game build")
    verify.add_argument("--game-dir", type=Path, required=True)
    verify.add_argument("--appmanifest", type=Path)
    verify.add_argument("--builds-manifest", type=Path, default=DEFAULT_BUILDS)

    for name, help_text in (
        ("skeleton", "add newly verified keys to translation and status CSVs"),
        ("validate", "validate the current localization dataset"),
        ("coverage", "report source and translation coverage"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--source-csv", type=Path)
        command.add_argument("--completeness", type=Path, default=DEFAULT_COMPLETENESS)
        command.add_argument("--translations", type=Path, default=DEFAULT_TRANSLATIONS)
        command.add_argument("--statuses", type=Path, default=DEFAULT_STATUSES)
        if name == "validate":
            command.add_argument("--glossary", type=Path, default=DEFAULT_GLOSSARY)
            command.add_argument("--required-keys", type=Path)
        elif name == "coverage":
            command.add_argument("--selected-keys", type=Path)
    return parser


def _required_file(path: Path, error: str = "input_missing") -> Path:
    if not path.is_file():
        raise CommandError(2, error)
    return path


def _load_manifest(path: Path) -> SourceCompleteness:
    _required_file(path, "completeness_missing")
    try:
        return load_source_completeness(path)
    except (OSError, ValueError):
        raise CommandError(3, "completeness_invalid") from None


def _source_path(argument: Path | None, completeness: SourceCompleteness) -> Path:
    return argument or ROOT / "workspace" / completeness.build_id / "probe/source/localisation/translations.csv"


def _audit_source(path: Path, completeness: SourceCompleteness) -> CanonicalSource:
    _required_file(path, "source_csv_missing")
    try:
        source = audit_source_csv(path, completeness)
    except (OSError, ValueError):
        raise CommandError(2, "source_csv_invalid") from None
    errors = tuple(issue.code for issue in source.issues if issue.severity == "error")
    if errors:
        raise CommandError(3, "source_completeness_mismatch", errors)
    return source


def _read_translations(path: Path) -> tuple[TranslationRow, ...]:
    _required_file(path, "translations_missing")
    try:
        return load_translation_csv(path)
    except (OSError, ValueError):
        raise CommandError(4, "translation_csv_invalid") from None


def _read_statuses(path: Path) -> tuple[StatusRow, ...]:
    _required_file(path, "statuses_missing")
    try:
        return load_status_csv(path)
    except (OSError, ValueError):
        raise CommandError(4, "status_csv_invalid") from None


def _read_glossary(path: Path) -> tuple[GlossaryTerm, ...]:
    _required_file(path, "glossary_missing")
    try:
        return load_glossary_csv(path)
    except (OSError, ValueError):
        raise CommandError(4, "glossary_csv_invalid") from None


def _read_keys(path: Path | None) -> frozenset[str] | None:
    if path is None:
        return None
    _required_file(path, "key_list_missing")
    try:
        return frozenset(path.read_text(encoding="utf-8-sig").splitlines())
    except (OSError, UnicodeError):
        raise CommandError(2, "key_list_invalid") from None


def _csv_text(headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def _write_texts_atomic(outputs: tuple[tuple[Path, str], ...]) -> None:
    for path, _ in outputs:
        if not path.parent.is_dir():
            raise OSError("output_directory_missing")
        for entry in (path, *path.parents):
            _reject_linked_output(entry)
    temporaries = []
    try:
        for path, text in outputs:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", dir=path.parent, suffix=".tmp", delete=False,
            ) as stream:
                temporary = Path(stream.name)
                temporaries.append((path, temporary))
                stream.write(text)
        for path, temporary in temporaries:
            os.replace(temporary, path)
    finally:
        for _, temporary in temporaries:
            temporary.unlink(missing_ok=True)


def _check_output_paths(source: Path, completeness: Path, translations: Path, statuses: Path) -> None:
    resolved = [path.resolve() for path in (source, completeness, translations, statuses)]
    source_path, manifest_path, translation_path, status_path = resolved
    if (
        translation_path in {source_path, manifest_path}
        or status_path in {source_path, manifest_path}
        or translation_path == status_path
        or translation_path in status_path.parents
        or status_path in translation_path.parents
    ):
        raise CommandError(2, "unsafe_output_paths")


def _skeleton(args: argparse.Namespace) -> dict:
    completeness = _load_manifest(args.completeness)
    source_path = _source_path(args.source_csv, completeness)
    source = _audit_source(source_path, completeness)
    _check_output_paths(source_path, args.completeness, args.translations, args.statuses)
    try:
        translations = load_translation_csv(args.translations) if args.translations.is_file() else ()
        statuses = load_status_csv(args.statuses) if args.statuses.is_file() else ()
    except (OSError, ValueError):
        raise CommandError(4, "localization_csv_invalid") from None

    existing_translation_keys = {row.key for row in translations}
    existing_status_keys = {row.key for row in statuses}
    if any(key.startswith("<!MissingKey") for key in existing_translation_keys | existing_status_keys):
        raise CommandError(4, "missing_key_marker_in_dataset")
    new_translations = translations + tuple(
        TranslationRow(row.key, row.source_sha256, "")
        for row in source.rows if row.key not in existing_translation_keys
    )
    new_statuses = statuses + tuple(
        StatusRow(row.key, "draft", "")
        for row in source.rows if row.key not in existing_status_keys
    )
    translation_text = _csv_text(
        ("key", "source_sha256", "translation_vi"),
        tuple((row.key, row.source_sha256, row.translation_vi) for row in new_translations),
    )
    status_text = _csv_text(
        ("key", "status", "note"),
        tuple((row.key, row.status, row.note) for row in new_statuses),
    )
    try:
        _write_texts_atomic(((args.translations, translation_text), (args.statuses, status_text)))
    except (OSError, ValueError):
        raise CommandError(5, "skeleton_write_failed") from None
    return {
        "ok": True,
        "build_id": completeness.build_id,
        "total_source_rows": completeness.total_rows,
        "recovered_rows": completeness.recovered_rows,
        "unrecovered_rows": completeness.unrecovered_rows,
        "unique_recovered_keys": completeness.unique_recovered_keys,
        "duplicate_key_groups": completeness.duplicate_key_groups,
        "duplicate_extra_rows": completeness.duplicate_extra_rows,
        "source_complete": completeness.source_complete,
        "translation_rows": len(new_translations),
        "status_rows": len(new_statuses),
        "warnings": [asdict(issue) for issue in source.issues if issue.severity == "warning"],
    }


def _validate(args: argparse.Namespace) -> tuple[dict, int]:
    completeness = _load_manifest(args.completeness)
    source = _audit_source(_source_path(args.source_csv, completeness), completeness)
    translations = _read_translations(args.translations)
    statuses = _read_statuses(args.statuses)
    glossary = _read_glossary(args.glossary)
    required = _read_keys(args.required_keys)
    report = validate_dataset(source, translations, statuses, glossary, required)
    return {"ok": report.ok, "errors": [asdict(issue) for issue in report.errors],
            "warnings": [asdict(issue) for issue in report.warnings]}, 0 if report.ok else 4


def _coverage(args: argparse.Namespace) -> dict:
    completeness = _load_manifest(args.completeness)
    source = _audit_source(_source_path(args.source_csv, completeness), completeness)
    translations = _read_translations(args.translations)
    statuses = _read_statuses(args.statuses)
    selected = _read_keys(args.selected_keys)
    try:
        return asdict(calculate_coverage(source, translations, statuses, selected))
    except ValueError:
        raise CommandError(4, "translation_contract_failure") from None


def _verify_game(args: argparse.Namespace) -> tuple[dict, int]:
    _required_file(args.builds_manifest, "build_manifest_missing")
    if not args.game_dir.is_dir() or (args.appmanifest is not None and not args.appmanifest.is_file()):
        raise CommandError(2, "game_input_missing")
    try:
        specs = load_build_specs(args.builds_manifest)
        results = tuple(
            (spec, verify_game_dir(args.game_dir, spec, args.appmanifest)) for spec in specs
        )
    except (OSError, ValueError, KeyError, TypeError):
        raise CommandError(5, "build_verification_failed") from None
    matches = [spec for spec, result in results if result.ok]
    if len(matches) == 1:
        spec = matches[0]
        return {"ok": True, "build_id": spec.build_id, "exe_version": spec.exe_version}, 0
    issues = sorted({issue for _, result in results for issue in result.issues})
    return {"ok": False, "issues": issues or ["ambiguous_build"]}, 3


def _emit(payload: dict) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict", newline="\n")
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify-game":
            report, code = _verify_game(args)
        elif args.command == "skeleton":
            report, code = _skeleton(args), 0
        elif args.command == "validate":
            report, code = _validate(args)
        else:
            report, code = _coverage(args), 0
    except CommandError as error:
        _emit({"ok": False, "error": error.error, "issues": list(error.issues)})
        return error.code
    _emit(report)
    return code
