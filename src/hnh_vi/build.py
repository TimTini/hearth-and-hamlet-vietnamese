"""Build a deterministic partial-source Vietnamese preview patch for a supported game build.

The game PCK is only ever read. GDRE writes a new candidate PCK in a temporary workspace
directory, the candidate is inspected, and only then are the PCK and its metadata published
to dist/<build-id>/.
"""

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from hnh_vi.builds import load_build_specs, sha256_file
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
from hnh_vi.coverage import CoverageReport, calculate_coverage
from hnh_vi.dataset import CanonicalSource, audit_source_csv
from hnh_vi.tools import load_tool_specs
from hnh_vi.workspace import (
    WorkspaceSnapshot,
    _reject_linked_output,
    _verified_context,
    _write_text_atomic,
)

PREVIEW_LOCALE = "vi"
FALLBACK_LOCALE = "en"
TRANSLATION_CSV_PATH = "res://localisation/translations.csv"
ENGLISH_TRANSLATION_PATH = "res://localisation/translations.en.translation"
VI_TRANSLATION_PATH = "res://localisation/translations.vi.translation"
PROJECT_BINARY_PATH = "res://project.binary"
LANGUAGE_GDC_PATH = "res://Scenes/language.gdc"
LANGUAGE_GD_RELATIVE = Path("Scenes/language.gd")
# Game bytecode from recovery: Godot 4.6.3 with GDScript bytecode 4.5.0-stable.
LANGUAGE_BYTECODE_VERSION = "4.5.0"
VI_NATIVE_DISPLAY_NAME = "Tiếng Việt"
# GDRE adds the vi resource, registers it in the project's locale list, and may
# also replace language.gdc so the picker shows "Tiếng Việt" instead of "VI".
ALLOWED_PATCHED_PATHS = frozenset({VI_TRANSLATION_PATH, PROJECT_BINARY_PATH, LANGUAGE_GDC_PATH})
REQUIRED_PATCHED_PATHS = frozenset({VI_TRANSLATION_PATH, PROJECT_BINARY_PATH})
# Path fragments that mean a script, log or probe left over from recovery work.
DIAGNOSTIC_PATH_PARTS = ("diagnostic", "runtime-key", "runtime_key", "key-recovery", "instrument")
DIAGNOSTIC_PATH_SUFFIXES = (".log", ".jsonl")
GDRE_TIMEOUT_SECONDS = 1800
GODOT_CHECK_TIMEOUT_SECONDS = 300
METADATA_SCHEMA_VERSION = 1
ARTIFACT_KIND = "translation_patch"

METADATA_FIELDS = frozenset({
    "schema_version", "artifact_kind", "release_quality", "source_complete", "fallback_locale",
    "locale", "build_id", "game_version", "source_pck_sha256", "source_csv_sha256",
    "merged_csv_sha256", "artifact_name", "artifact_sha256", "artifact_size", "patched_paths",
    "translated_keys", "omitted_empty_keys", "selected_keys_sha256", "tools", "completeness",
    "coverage",
})
SHA256_PATTERN = re.compile(r"[A-F0-9]{64}")


@dataclass(frozen=True)
class BuildInput:
    """The merged CSV that GDRE turns into the vi translation resource."""

    merged_csv_path: Path
    merged_csv_sha256: str
    locale: str
    translated_keys: int
    omitted_empty_keys: int


@dataclass(frozen=True)
class BuildArtifact:
    """A published preview PCK together with its verified metadata."""

    pck_path: Path
    metadata_path: Path
    sha256: str
    size_bytes: int
    metadata: dict


# ---- Merge the dataset into the CSV that GDRE patches into the PCK ----------------------


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def merge_translation_csv(
    source_path: Path,
    canonical_source: CanonicalSource,
    translations_path: Path,
    output_path: Path,
    locale: str = PREVIEW_LOCALE,
) -> BuildInput:
    """Write a `key,<locale>` CSV in canonical source order with only filled translations.

    Empty cells are left out so Godot falls back to English for those keys. Keys are copied
    exactly; only translation text is converted to NFC, and only in the generated output.
    """
    if not re.fullmatch(r"[a-z]{2,3}(_[A-Za-z0-9]+)*", locale) or locale == FALLBACK_LOCALE:
        raise ValueError("invalid_locale: use a non-English locale code such as vi")

    expected_hash = canonical_source.completeness.recovered_csv_sha256.upper()
    if sha256_file(source_path) != expected_hash:
        raise ValueError("source_csv_drift: source CSV no longer matches the audited source")
    if not canonical_source.ok:
        raise ValueError("source_not_buildable: source audit has blocking issues")

    translations = load_translation_csv(translations_path)
    source_hash_by_key = {row.key: row.source_sha256 for row in canonical_source.rows}
    text_by_key: dict[str, str] = {}
    for translation in translations:
        if translation.key.startswith("<!MissingKey"):
            raise ValueError("missing_key_marker: translation dataset contains a marker row")
        if translation.key not in source_hash_by_key:
            raise ValueError("unknown_key: translation key is not a recovered source key")
        if translation.key in text_by_key:
            raise ValueError("duplicate_key: translation key appears more than once")
        if translation.source_sha256.upper() != source_hash_by_key[translation.key].upper():
            raise ValueError("source_hash_drift: translation was written for a different source")
        text_by_key[translation.key] = translation.translation_vi

    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["key", locale])
    translated_keys = 0
    for source_row in canonical_source.rows:
        text = text_by_key[source_row.key]
        if not text.strip():
            continue
        writer.writerow([source_row.key, unicodedata.normalize("NFC", text)])
        translated_keys += 1

    _write_text_atomic(output_path, output.getvalue())
    return BuildInput(
        merged_csv_path=output_path,
        merged_csv_sha256=sha256_file(output_path),
        locale=locale,
        translated_keys=translated_keys,
        omitted_empty_keys=len(canonical_source.rows) - translated_keys,
    )


def check_preview_dataset(
    source: CanonicalSource,
    translations: tuple[TranslationRow, ...],
    statuses: tuple[StatusRow, ...],
    glossary: tuple[GlossaryTerm, ...],
    selected_keys: frozenset[str] | None,
) -> CoverageReport:
    """Block the build on any contract error; return coverage for the selected phase."""
    if not selected_keys:
        raise ValueError("build_blocked: selected_keys_required")
    report = validate_dataset(source, translations, statuses, glossary, selected_keys)
    if not report.ok:
        codes = sorted({issue.code for issue in report.errors})
        raise ValueError("build_blocked: " + ", ".join(codes))
    return calculate_coverage(source, translations, statuses, selected_keys)


# ---- Names and path checks ----------------------------------------------------------------


def short_game_version(exe_version: str) -> str:
    """Turn the EXE version 1.1.0.0 into the release version 1.1.0."""
    if not re.fullmatch(r"\d+\.\d+\.\d+(\.0)?", exe_version):
        raise ValueError("invalid_game_version: expected major.minor.patch[.0]")
    return ".".join(exe_version.split(".")[:3])


def preview_artifact_name(exe_version: str) -> str:
    return f"Hearth-and-Hamlet-vi-preview-{short_game_version(exe_version)}.pck"


def _is_diagnostic_path(path: str) -> bool:
    lowered = path.lower()
    return lowered.endswith(DIAGNOSTIC_PATH_SUFFIXES) or any(
        part in lowered for part in DIAGNOSTIC_PATH_PARTS
    )


def check_candidate_paths(source_paths: list[str], candidate_paths: list[str]) -> tuple[str, ...]:
    """Check that the candidate PCK only gained the vi resource; return the added paths."""
    source_set, candidate_set = set(source_paths), set(candidate_paths)
    if ENGLISH_TRANSLATION_PATH not in source_set:
        raise ValueError("english_missing_from_source: fallback resource is not in the game PCK")
    # Only paths the candidate ADDS are judged for diagnostics. Original game assets may have
    # any name, so judging them could block every real build.

    removed = source_set - candidate_set
    if ENGLISH_TRANSLATION_PATH in removed:
        raise ValueError("english_removed: candidate lost the English resource")
    if removed:
        raise ValueError("path_removed: candidate lost original files")

    added = candidate_set - source_set
    if any(_is_diagnostic_path(path) for path in added):
        raise ValueError("diagnostic_path_added: candidate contains diagnostic files")
    if VI_TRANSLATION_PATH not in added:
        raise ValueError("vi_resource_missing: candidate has no vi translation resource")
    if added != {VI_TRANSLATION_PATH}:
        raise ValueError("unexpected_path_added: candidate added files other than vi resource")
    return tuple(sorted(added))


# ---- Metadata ---------------------------------------------------------------------------


def make_preview_metadata(
    *,
    game_version: str,
    source_pck_sha256: str,
    build_input: BuildInput,
    artifact_path: Path,
    patched_paths: tuple[str, ...],
    completeness: SourceCompleteness,
    coverage: CoverageReport,
    selected_keys: frozenset[str],
    tool_versions: dict[str, str],
) -> dict:
    """Describe the artifact without overstating how much of the game is translated."""
    selected_text = "\n".join(sorted(selected_keys))
    return {
        "schema_version": METADATA_SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "release_quality": "preview",
        "source_complete": False,
        "fallback_locale": FALLBACK_LOCALE,
        "locale": build_input.locale,
        "build_id": completeness.build_id,
        "game_version": short_game_version(game_version),
        "source_pck_sha256": source_pck_sha256.upper(),
        "source_csv_sha256": completeness.recovered_csv_sha256.upper(),
        "merged_csv_sha256": build_input.merged_csv_sha256.upper(),
        "artifact_name": artifact_path.name,
        "artifact_sha256": sha256_file(artifact_path),
        "artifact_size": artifact_path.stat().st_size,
        "patched_paths": sorted(patched_paths),
        "translated_keys": build_input.translated_keys,
        "omitted_empty_keys": build_input.omitted_empty_keys,
        "selected_keys_sha256": _sha256_text(selected_text),
        "tools": dict(tool_versions),
        "completeness": asdict(completeness),
        "coverage": asdict(coverage),
    }


def _invalid_metadata(reason: str) -> ValueError:
    return ValueError(f"invalid_build_metadata: {reason}")


def _check_metadata_fields(metadata: dict) -> tuple[SourceCompleteness, CoverageReport]:
    """Validate the preview contract; returns the parsed completeness and coverage."""
    if set(metadata) != METADATA_FIELDS:
        raise _invalid_metadata("unexpected or missing fields")
    if metadata["schema_version"] != METADATA_SCHEMA_VERSION:
        raise _invalid_metadata("unsupported schema_version")
    if metadata["artifact_kind"] != ARTIFACT_KIND:
        raise _invalid_metadata("artifact_kind must be translation_patch")
    if metadata["release_quality"] != "preview":
        raise _invalid_metadata("release_quality must be preview")
    if metadata["source_complete"] is not False:
        raise _invalid_metadata("source_complete must be false")
    if metadata["fallback_locale"] != FALLBACK_LOCALE:
        raise _invalid_metadata("fallback_locale must be en")
    if metadata["locale"] != PREVIEW_LOCALE:
        raise _invalid_metadata("locale must be vi")
    for name in ("source_pck_sha256", "source_csv_sha256", "merged_csv_sha256", "artifact_sha256"):
        value = metadata[name]
        if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
            raise _invalid_metadata(f"{name} must be an uppercase SHA-256")
    if not isinstance(metadata["selected_keys_sha256"], str) or not SHA256_PATTERN.fullmatch(
        metadata["selected_keys_sha256"]
    ):
        raise _invalid_metadata("selected_keys_sha256 must be an uppercase SHA-256")
    for name in ("artifact_size", "translated_keys", "omitted_empty_keys"):
        if type(metadata[name]) is not int or metadata[name] < 0:
            raise _invalid_metadata(f"{name} must be a non-negative integer")
    if not isinstance(metadata["game_version"], str) or not re.fullmatch(
        r"\d+\.\d+\.\d+", metadata["game_version"]
    ):
        raise _invalid_metadata("game_version must be major.minor.patch")
    tools = metadata["tools"]
    if not isinstance(tools, dict) or not tools or not all(
        isinstance(name, str) and isinstance(version, str) for name, version in tools.items()
    ):
        raise _invalid_metadata("tools must map tool ids to versions")

    patched_paths = metadata["patched_paths"]
    if not isinstance(patched_paths, list) or not all(isinstance(p, str) for p in patched_paths):
        raise _invalid_metadata("patched_paths must be a list of paths")
    if any(_is_diagnostic_path(path) for path in patched_paths):
        raise _invalid_metadata("patched_paths contain diagnostic files")
    if patched_paths != sorted(set(patched_paths)) or not set(patched_paths) <= ALLOWED_PATCHED_PATHS:
        raise _invalid_metadata("patched_paths must be a sorted subset of the allowed paths")
    if VI_TRANSLATION_PATH not in patched_paths:
        raise _invalid_metadata("patched_paths must include the vi translation resource")
    if not REQUIRED_PATCHED_PATHS <= set(patched_paths):
        raise _invalid_metadata("patched_paths must include the vi resource and project.binary")

    try:
        completeness = SourceCompleteness(**metadata["completeness"])
        coverage = CoverageReport(**metadata["coverage"])
    except (TypeError, ValueError):
        raise _invalid_metadata("completeness or coverage is malformed") from None
    if completeness.source_complete or coverage.source_complete:
        raise _invalid_metadata("completeness and coverage must report a partial source")
    if not isinstance(coverage.maximum_known_source_ratio, float) or (
        coverage.maximum_known_source_ratio >= 1.0
    ):
        raise _invalid_metadata("coverage must not claim the whole source is known")
    if coverage.selected_keys < 1:
        raise _invalid_metadata("coverage must describe a selected phase")
    if (
        completeness.build_id != metadata["build_id"]
        or completeness.pck_sha256.upper() != metadata["source_pck_sha256"]
        or completeness.recovered_csv_sha256.upper() != metadata["source_csv_sha256"]
    ):
        raise _invalid_metadata("completeness does not match the source fingerprints")
    return completeness, coverage


def verify_build_artifact(path: Path, metadata_path: Path) -> BuildArtifact:
    """Check that a PCK and its metadata agree and describe an honest preview."""
    if not path.is_file() or not metadata_path.is_file():
        raise ValueError("build_artifact_missing: PCK or metadata file does not exist")
    for entry in (path, metadata_path):
        _reject_linked_output(entry)

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise _invalid_metadata("not readable JSON") from None
    if not isinstance(metadata, dict):
        raise _invalid_metadata("top level must be an object")
    _check_metadata_fields(metadata)

    if metadata["artifact_name"] != path.name:
        raise ValueError("build_artifact_mismatch: artifact name differs from metadata")
    size_bytes = path.stat().st_size
    if metadata["artifact_size"] != size_bytes:
        raise ValueError("build_artifact_mismatch: artifact size differs from metadata")
    sha256 = sha256_file(path)
    if metadata["artifact_sha256"] != sha256:
        raise ValueError("build_artifact_mismatch: artifact hash differs from metadata")
    return BuildArtifact(
        pck_path=path, metadata_path=metadata_path, sha256=sha256, size_bytes=size_bytes,
        metadata=metadata,
    )


# ---- GDRE steps ---------------------------------------------------------------------------


def _run_gdre(gdre: Path, arguments: list[str], working_directory: Path) -> str:
    """Run GDRE with a time limit: it can hang after reporting an error."""
    try:
        result = subprocess.run(
            [str(gdre), "--headless", *arguments],
            cwd=working_directory, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=GDRE_TIMEOUT_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired:
        raise ValueError("gdre_timeout: GDRE did not finish in time") from None
    if result.returncode != 0:
        raise ValueError(f"gdre_failed: {arguments[0].split('=')[0]} exited with {result.returncode}")
    return result.stdout


def _list_pck_paths(gdre: Path, pck: Path, working_directory: Path) -> list[str]:
    output = _run_gdre(gdre, [f"--list-files={pck}"], working_directory)
    return [line.rstrip("\r\n") for line in output.splitlines() if line.startswith("res://")]


def inject_vietnamese_native_name(script_text: str) -> str:
    """Add vi to language.gd native_names so the picker shows Tiếng Việt, not VI."""
    if re.search(r'["\']vi["\']\s*:', script_text):
        raise ValueError("language_native_name_exists: language.gd already defines a vi display name")
    match = re.search(r"(var native_names\s*=\s*\{)(.*?)(\n\})", script_text, flags=re.DOTALL)
    if match is None:
        raise ValueError("language_native_names_missing: language.gd has no native_names dictionary")
    body = match.group(2).rstrip()
    # Keep the decompiled trailing-comma style used by the recovered script.
    inserted = f'{body}\n\t"vi": "{VI_NATIVE_DISPLAY_NAME}", \n'
    return script_text[: match.start()] + match.group(1) + inserted + match.group(3) + script_text[match.end() :]


def _prepare_language_label_gdc(
    gdre: Path, language_gd: Path, output_dir: Path,
) -> Path:
    """Compile a temporary language.gdc that includes the Vietnamese display name."""
    if not language_gd.is_file():
        raise ValueError("language_script_missing: probe source has no Scenes/language.gd")
    patched_gd = output_dir / "language.gd"
    patched_gd.write_text(
        inject_vietnamese_native_name(language_gd.read_text(encoding="utf-8")),
        encoding="utf-8",
        newline="\n",
    )
    _run_gdre(gdre, [
        f"--compile={patched_gd}",
        f"--bytecode={LANGUAGE_BYTECODE_VERSION}",
        f"--output={output_dir}",
    ], output_dir)
    compiled = output_dir / "language.gdc"
    if not compiled.is_file():
        raise ValueError("language_compile_failed: GDRE did not write language.gdc")
    return compiled


def _extract_patchable_files(
    gdre: Path,
    pck: Path,
    output_dir: Path,
    working_directory: Path,
    extra_includes: tuple[str, ...] = (),
) -> None:
    includes = [
        "--include=res://localisation/*",
        f"--include={PROJECT_BINARY_PATH}",
        *[f"--include={path}" for path in extra_includes],
    ]
    _run_gdre(gdre, [f"--extract={pck}", f"--output={output_dir}", *includes], working_directory)


def _find_changed_paths(source_dir: Path, candidate_dir: Path) -> tuple[str, ...]:
    """Compare extracted bytes so patched_paths lists what really differs from the game PCK."""
    changed = []
    for candidate_file in sorted(candidate_dir.rglob("*")):
        if not candidate_file.is_file() or candidate_file.name == "gdre_export.log":
            continue
        relative_path = candidate_file.relative_to(candidate_dir)
        source_file = source_dir / relative_path
        if not source_file.is_file() or sha256_file(source_file) != sha256_file(candidate_file):
            changed.append("res://" + relative_path.as_posix())
    return tuple(changed)


def _check_patched_paths(
    changed_paths: tuple[str, ...], expected_paths: frozenset[str],
) -> None:
    if not set(changed_paths) <= ALLOWED_PATCHED_PATHS:
        raise ValueError("unexpected_path_changed: GDRE changed files outside the allowed paths")
    if set(changed_paths) != expected_paths:
        raise ValueError(
            "locale_not_registered: GDRE did not update the expected translation/locale files"
        )


CHECK_VI_MESSAGES_SCRIPT = """extends SceneTree


func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	var expected_file := FileAccess.open(arguments[0], FileAccess.READ)
	if expected_file == null:
		print("ERROR|expected_file_unreadable")
		quit(1)
		return
	var expected: Array = JSON.parse_string(expected_file.get_as_text())
	var translation := TranslationServer.get_translation_object("vi")
	if translation == null or translation.locale != "vi":
		print("ERROR|vi_locale_not_loaded")
		quit(1)
		return
	var missing_rows := PackedStringArray()
	for index in range(expected.size()):
		var key: String = expected[index][0]
		var expected_text: String = expected[index][1]
		# Ask the vi resource itself, so an English fallback cannot hide a missing key.
		var actual_text := String(translation.get_message(key))
		# GDRE may turn a literal backslash-n into a real newline when it imports the CSV.
		if actual_text != expected_text and actual_text != expected_text.c_unescape():
			missing_rows.append(str(index + 1))
	print("CHECKED|", expected.size())
	print("MISSING|", ",".join(missing_rows))
	quit(0)
"""


def _check_vi_messages_in_candidate(
    godot: Path, candidate: Path, build_input: BuildInput, temp_dir: Path,
) -> None:
    """Ask pinned Godot whether every translated key has its message in the candidate's vi."""
    with build_input.merged_csv_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        next(reader)
        expected_messages = [[key, text] for key, text in reader]
    if len(expected_messages) != build_input.translated_keys:
        raise ValueError("vi_messages_missing: merged CSV does not match the translated key count")

    expected_path = temp_dir / "expected-vi-messages.json"
    script_path = temp_dir / "check_vi_messages.gd"
    expected_path.write_text(json.dumps(expected_messages), encoding="utf-8")
    script_path.write_text(CHECK_VI_MESSAGES_SCRIPT, encoding="utf-8")
    try:
        result = subprocess.run(
            [str(godot), "--headless", "--main-pack", str(candidate), "--script", str(script_path),
             "--", str(expected_path)],
            cwd=temp_dir, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=GODOT_CHECK_TIMEOUT_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired:
        raise ValueError("godot_check_timeout: Godot did not finish checking the candidate") from None
    output_lines = result.stdout.splitlines()
    error_lines = [line for line in output_lines if line.startswith("ERROR|")]
    if result.returncode != 0 or error_lines:
        reason = error_lines[0].removeprefix("ERROR|") if error_lines else f"exit {result.returncode}"
        raise ValueError(f"godot_check_failed: {reason}")

    checked = [line.removeprefix("CHECKED|") for line in output_lines if line.startswith("CHECKED|")]
    missing = [line.removeprefix("MISSING|") for line in output_lines if line.startswith("MISSING|")]
    if checked != [str(len(expected_messages))] or len(missing) != 1:
        raise ValueError("godot_check_failed: unexpected Godot output")
    if missing[0]:
        row_numbers = missing[0].split(",")
        raise ValueError(
            f"vi_messages_missing: {len(row_numbers)} translated keys are not in the candidate "
            f"vi resource (merged CSV rows {', '.join(row_numbers[:10])})"
        )


def _publish_file(source: Path, destination: Path) -> None:
    """Copy into a fresh temp file beside the destination, then replace it atomically."""
    for entry in (destination, *destination.parents):
        _reject_linked_output(entry)
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=destination.parent, suffix=".tmp", delete=False
    ) as stream:
        temporary = Path(stream.name)
        with source.open("rb") as candidate:
            shutil.copyfileobj(candidate, stream)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


# ---- Whole build --------------------------------------------------------------------------


def _read_selected_keys(path: Path) -> frozenset[str]:
    if not path.is_file():
        raise ValueError("selected_keys_missing: localization/phase1.keys does not exist")
    try:
        return frozenset(path.read_text(encoding="utf-8-sig").splitlines())
    except (OSError, UnicodeError):
        raise ValueError("selected_keys_invalid: key list is not readable UTF-8") from None


def build_preview(repo_root: Path, game_dir: Path) -> BuildArtifact:
    """Verify everything, build the candidate in a temp workspace, then publish to dist/."""
    context = _verified_context(repo_root, game_dir)
    repo_root = repo_root.resolve(strict=True)
    build_id = context["build_id"]
    source_pck = Path(context["pck"])
    spec = next(
        s for s in load_build_specs(repo_root / "manifests/game-builds.json") if s.build_id == build_id
    )
    tool_versions = {
        tool.id: tool.version for tool in load_tool_specs(repo_root / "manifests/tools.json")
    }

    completeness = load_source_completeness(repo_root / "localization/source-completeness.json")
    if completeness.source_complete:
        raise ValueError("preview_requires_partial_source: manifest already reports a complete source")
    source_csv = repo_root / "workspace" / build_id / "probe/source/localisation/translations.csv"
    if not source_csv.is_file():
        raise ValueError("source_csv_missing: run scripts/probe.ps1 first")

    # The PCK was already verified against the build manifest; compare it and the CSV to the
    # completeness manifest too, so Steam or workspace drift stops the build.
    snapshot = WorkspaceSnapshot(
        build_id, sha256_file(source_pck), sha256_file(source_csv),
        datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    snapshot_result = completeness.verify_snapshot(snapshot)
    if not snapshot_result.ok:
        raise ValueError("source_drift: " + ", ".join(snapshot_result.issues))
    source = audit_source_csv(source_csv, completeness)
    source_errors = sorted({issue.code for issue in source.issues if issue.severity == "error"})
    if source_errors:
        raise ValueError("source_completeness_mismatch: " + ", ".join(source_errors))

    localization = repo_root / "localization"
    translations = load_translation_csv(localization / "translations.vi.csv")
    statuses = load_status_csv(localization / "status.csv")
    glossary = load_glossary_csv(localization / "glossary.csv")
    selected_keys = _read_selected_keys(localization / "phase1.keys")
    coverage = check_preview_dataset(source, translations, statuses, glossary, selected_keys)

    artifact_name = preview_artifact_name(spec.exe_version)
    workspace = repo_root / "workspace" / build_id
    for entry in (repo_root / "workspace", workspace):
        _reject_linked_output(entry)
    with tempfile.TemporaryDirectory(dir=workspace, prefix="build-") as temp_name:
        temp_dir = Path(temp_name)
        build_input = merge_translation_csv(
            source_csv, source, localization / "translations.vi.csv", temp_dir / "merged.csv",
        )
        if "=" in str(build_input.merged_csv_path):
            raise ValueError("unsupported_path: GDRE patch arguments cannot contain '='")

        gdre = Path(context["gdre"])
        candidate = temp_dir / artifact_name
        source_paths = _list_pck_paths(gdre, source_pck, temp_dir)
        patch_args = [
            f"--pck-patch={source_pck}",
            f"--patch-translations={build_input.merged_csv_path}={TRANSLATION_CSV_PATH}",
            f"--locales={build_input.locale}",
            f"--output={candidate}",
        ]
        expected_paths = set(REQUIRED_PATCHED_PATHS)
        extra_extract: tuple[str, ...] = ()
        language_gd = workspace / "probe/source" / LANGUAGE_GD_RELATIVE
        if LANGUAGE_GDC_PATH in source_paths:
            if not language_gd.is_file():
                raise ValueError(
                    "language_script_missing: game PCK has language.gdc but probe has no language.gd"
                )
            language_dir = temp_dir / "language-label"
            language_dir.mkdir()
            language_gdc = _prepare_language_label_gdc(gdre, language_gd, language_dir)
            if "=" in str(language_gdc):
                raise ValueError("unsupported_path: GDRE patch arguments cannot contain '='")
            patch_args.append(f"--patch-file={language_gdc}={LANGUAGE_GDC_PATH}")
            expected_paths.add(LANGUAGE_GDC_PATH)
            extra_extract = (LANGUAGE_GDC_PATH,)

        _run_gdre(gdre, patch_args, temp_dir)
        if not candidate.is_file():
            raise ValueError("gdre_failed: no candidate PCK was written")

        # Reopen the candidate with GDRE before trusting it.
        candidate_paths = _list_pck_paths(gdre, candidate, temp_dir)
        check_candidate_paths(source_paths, candidate_paths)
        _extract_patchable_files(
            gdre, source_pck, temp_dir / "source-files", temp_dir, extra_extract,
        )
        _extract_patchable_files(
            gdre, candidate, temp_dir / "candidate-files", temp_dir, extra_extract,
        )
        patched_paths = _find_changed_paths(temp_dir / "source-files", temp_dir / "candidate-files")
        _check_patched_paths(patched_paths, frozenset(expected_paths))
        # GDRE silently ignores vi keys that the game's resources do not contain.
        _check_vi_messages_in_candidate(
            Path(context["godot"]), candidate, build_input, temp_dir,
        )

        metadata = make_preview_metadata(
            game_version=spec.exe_version,
            source_pck_sha256=snapshot.pck_sha256,
            build_input=build_input,
            artifact_path=candidate,
            patched_paths=patched_paths,
            completeness=source.completeness,
            coverage=coverage,
            selected_keys=selected_keys,
            tool_versions=tool_versions,
        )

        dist_dir = repo_root / "dist" / build_id
        dist_dir.mkdir(parents=True, exist_ok=True)
        for entry in (repo_root / "dist", dist_dir):
            _reject_linked_output(entry)
        final_pck = dist_dir / artifact_name
        final_metadata = final_pck.with_suffix(".json")
        _publish_file(candidate, final_pck)
        _write_text_atomic(final_metadata, json.dumps(metadata, indent=2, sort_keys=True) + "\n")

    return verify_build_artifact(final_pck, final_metadata)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("context", "build"))
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--game-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "context":
            context = _verified_context(args.repo_root, args.game_dir)
            print(json.dumps(context))
        else:
            artifact = build_preview(args.repo_root, args.game_dir)
            print(json.dumps({
                "ok": True,
                "pck": str(artifact.pck_path),
                "metadata": str(artifact.metadata_path),
                "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
                "translated_keys": artifact.metadata["translated_keys"],
                "patched_paths": artifact.metadata["patched_paths"],
            }, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
