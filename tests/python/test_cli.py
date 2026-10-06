import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path

from hnh_vi.completeness import load_source_completeness

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SENTENCES = ("Synthetic source sentence one.", "Synthetic recovered sentence two.")
MISSING_MARKER = "<!MissingKey: synthetic missing prose>"


def run_cli(*args: str) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        ["uv", "run", "hnh-vi", *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        check=False,
    )


def write_source(path: Path, rows: list[tuple[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["key", "en"])
        writer.writerows(rows)
    return path


def write_completeness(path: Path, source: Path) -> Path:
    source_rows = list(csv.DictReader(source.open(encoding="utf-8", newline="")))
    recovered = [row for row in source_rows if not row["key"].startswith("<!MissingKey")]
    key_counts: dict[str, int] = {}
    for row in recovered:
        key_counts[row["key"]] = key_counts.get(row["key"], 0) + 1
    baseline = load_source_completeness(ROOT / "tests/fixtures/localization/source-completeness.json")
    data = {
        "schema_version": baseline.schema_version,
        "build_id": baseline.build_id,
        "pck_sha256": baseline.pck_sha256,
        "recovered_csv_sha256": hashlib.sha256(source.read_bytes()).hexdigest().upper(),
        "total_rows": len(source_rows),
        "recovered_rows": len(recovered),
        "unique_recovered_keys": len(key_counts),
        "duplicate_key_groups": sum(count > 1 for count in key_counts.values()),
        "duplicate_extra_rows": len(recovered) - len(key_counts),
        "unrecovered_rows": len(source_rows) - len(recovered),
        "fallback_locale": baseline.fallback_locale,
        "policy": baseline.policy,
        "source_complete": not any(row["key"].startswith("<!MissingKey") for row in source_rows),
    }
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def write_csv(path: Path, headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)


def localization_args(source: Path, manifest: Path, translations: Path, statuses: Path) -> tuple[str, ...]:
    return (
        "--source-csv", str(source), "--completeness", str(manifest),
        "--translations", str(translations), "--statuses", str(statuses),
    )


def test_skeleton_emits_safe_deterministic_json_and_preserves_rows_on_rerun(tmp_path: Path) -> None:
    source = write_source(tmp_path / "source.csv", [
        ("exact_key", SOURCE_SENTENCES[0]),
        ("exact_key", SOURCE_SENTENCES[0]),
        ("new_key", SOURCE_SENTENCES[1]),
        (MISSING_MARKER, ""),
    ])
    manifest = write_completeness(tmp_path / "source-completeness.json", source)
    translations = tmp_path / "translations.vi.csv"
    statuses = tmp_path / "status.csv"
    write_csv(translations, ("key", "source_sha256", "translation_vi"), [
        ("exact_key", hashlib.sha256(SOURCE_SENTENCES[0].encode()).hexdigest().upper(), "Bản dịch đã có"),
    ])
    write_csv(statuses, ("key", "status", "note"), [("exact_key", "reviewed", "Ghi chú đã có")])
    args = ("skeleton", *localization_args(source, manifest, translations, statuses))

    first = run_cli(*args)
    second = run_cli(*args)

    assert first.returncode == second.returncode == 0
    first_text = first.stdout.decode("utf-8")
    assert first_text == second.stdout.decode("utf-8")
    report = json.loads(first_text)
    assert report["ok"] is True
    assert report["unique_recovered_keys"] == 2
    assert report["duplicate_key_groups"] == 1
    assert report["unrecovered_rows"] == 1
    assert "exact_key" not in first_text
    assert "new_key" not in first_text
    assert MISSING_MARKER not in first_text
    assert all(sentence not in first_text for sentence in SOURCE_SENTENCES)

    with translations.open(encoding="utf-8", newline="") as stream:
        translation_rows = list(csv.DictReader(stream))
    with statuses.open(encoding="utf-8", newline="") as stream:
        status_rows = list(csv.DictReader(stream))
    assert list(translation_rows[0]) == ["key", "source_sha256", "translation_vi"]
    assert list(status_rows[0]) == ["key", "status", "note"]
    assert [row["key"] for row in translation_rows] == ["exact_key", "new_key"]
    assert [row["key"] for row in status_rows] == ["exact_key", "new_key"]
    assert translation_rows[1]["source_sha256"] == hashlib.sha256(
        SOURCE_SENTENCES[1].encode()
    ).hexdigest().upper()
    assert translation_rows[0]["translation_vi"] == "Bản dịch đã có"
    assert status_rows[0] == {"key": "exact_key", "status": "reviewed", "note": "Ghi chú đã có"}
    assert translation_rows[1]["translation_vi"] == ""
    assert status_rows[1] == {"key": "new_key", "status": "draft", "note": ""}
    output_text = translations.read_text(encoding="utf-8") + statuses.read_text(encoding="utf-8")
    assert all(sentence not in output_text for sentence in SOURCE_SENTENCES)
    assert MISSING_MARKER not in output_text


def test_skeleton_preserves_exact_case_and_whitespace_keys(tmp_path: Path) -> None:
    source = write_source(tmp_path / "source.csv", [
        ("CaseKey", "Synthetic first value."),
        (" casekey ", "Synthetic second value."),
    ])
    manifest = write_completeness(tmp_path / "source-completeness.json", source)
    translations = tmp_path / "translations.vi.csv"
    statuses = tmp_path / "status.csv"
    result = run_cli(
        "skeleton", *localization_args(source, manifest, translations, statuses),
    )

    assert result.returncode == 0
    with translations.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["key"] for row in rows] == ["CaseKey", " casekey "]


def test_validate_and_coverage_emit_utf8_json_without_source_text(tmp_path: Path) -> None:
    sentence = "Synthetic source prose with unicode: café."
    source = write_source(tmp_path / "source.csv", [("safe_key", sentence)])
    manifest = write_completeness(tmp_path / "source-completeness.json", source)
    translations = tmp_path / "translations.vi.csv"
    statuses = tmp_path / "status.csv"
    write_csv(translations, ("key", "source_sha256", "translation_vi"), [
        ("safe_key", hashlib.sha256(sentence.encode()).hexdigest().upper(), "Bản dịch tổng hợp"),
    ])
    write_csv(statuses, ("key", "status", "note"), [("safe_key", "reviewed", "")])
    args = localization_args(source, manifest, translations, statuses)

    validated = run_cli("validate", *args)
    coverage = run_cli("coverage", *args)

    assert validated.returncode == coverage.returncode == 0
    validation_report = json.loads(validated.stdout.decode("utf-8"))
    coverage_report = json.loads(coverage.stdout.decode("utf-8"))
    assert validation_report["ok"] is True
    assert coverage_report["unique_recovered_keys"] == 1
    assert coverage_report["ready_keys"] == 1
    assert sentence not in validated.stdout.decode("utf-8")
    assert sentence not in coverage.stdout.decode("utf-8")
    assert "safe_key" not in validated.stdout.decode("utf-8")
    assert "safe_key" not in coverage.stdout.decode("utf-8")


def test_skeleton_rejects_source_drift_with_exit_three_and_safe_json(tmp_path: Path) -> None:
    source = write_source(tmp_path / "source.csv", [("safe_key", "Synthetic source sentence.")])
    manifest = write_completeness(tmp_path / "source-completeness.json", source)
    write_source(source, [("safe_key", "Synthetic changed source sentence.")])
    translations = tmp_path / "translations.vi.csv"
    statuses = tmp_path / "status.csv"
    write_csv(translations, ("key", "source_sha256", "translation_vi"), [])
    write_csv(statuses, ("key", "status", "note"), [])

    result = run_cli("skeleton", *localization_args(source, manifest, translations, statuses))

    assert result.returncode == 3
    output = result.stdout.decode("utf-8")
    assert json.loads(output)["ok"] is False
    assert "Synthetic changed source sentence." not in output
    assert "safe_key" not in output
    assert not list(csv.DictReader(translations.open(encoding="utf-8", newline="")))


def test_invalid_input_contract_failure_and_output_failure_have_distinct_exit_codes(
    tmp_path: Path,
) -> None:
    missing = run_cli("skeleton", "--source-csv", str(tmp_path / "absent.csv"))
    assert missing.returncode == 2
    assert json.loads(missing.stdout.decode("utf-8"))["ok"] is False

    sentence = "Synthetic source sentence for validation."
    source = write_source(tmp_path / "source.csv", [("safe_key", sentence)])
    manifest = write_completeness(tmp_path / "source-completeness.json", source)
    translations = tmp_path / "translations.vi.csv"
    statuses = tmp_path / "status.csv"
    write_csv(translations, ("key", "source_sha256", "translation_vi"), [
        ("unknown_safe_key", hashlib.sha256(sentence.encode()).hexdigest().upper(), "Dịch"),
    ])
    write_csv(statuses, ("key", "status", "note"), [("safe_key", "reviewed", "")])
    args = localization_args(source, manifest, translations, statuses)
    invalid_contract = run_cli("validate", *args)
    assert invalid_contract.returncode == 4
    contract_report = json.loads(invalid_contract.stdout.decode("utf-8"))
    assert contract_report["ok"] is False
    assert "unknown_safe_key" not in invalid_contract.stdout.decode("utf-8")
    assert sentence not in invalid_contract.stdout.decode("utf-8")

    translations_before = translations.read_bytes()
    failed_output = run_cli(
        "skeleton", *localization_args(source, manifest, translations, tmp_path / "absent" / "out.csv"),
    )
    assert failed_output.returncode == 5
    assert json.loads(failed_output.stdout.decode("utf-8"))["ok"] is False
    assert translations.read_bytes() == translations_before


def test_verify_game_checks_only_the_synthetic_fixture_and_reports_build_drift(tmp_path: Path) -> None:
    game_dir = tmp_path / "synthetic game"
    game_dir.mkdir()
    exe, pck = game_dir / "fixture.exe", game_dir / "fixture.pck"
    exe.write_bytes(b"synthetic executable")
    pck.write_bytes(b"synthetic package")
    build_id = "test_build"
    build_manifest = tmp_path / "builds.json"
    build_manifest.write_text(json.dumps({"builds": [{
        "build_id": build_id,
        "exe_version": "0.0.0",
        "confirmed_on": "2026-10-06",
        "exe_name": exe.name,
        "exe_sha256": hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
        "pck_name": pck.name,
        "pck_sha256": hashlib.sha256(pck.read_bytes()).hexdigest().upper(),
    }]}), encoding="utf-8")

    verified = run_cli(
        "verify-game", "--game-dir", str(game_dir), "--builds-manifest", str(build_manifest),
    )
    pck.write_bytes(b"changed synthetic package")
    drifted = run_cli(
        "verify-game", "--game-dir", str(game_dir), "--builds-manifest", str(build_manifest),
    )

    assert verified.returncode == 0
    assert json.loads(verified.stdout.decode("utf-8"))["build_id"] == build_id
    assert drifted.returncode == 3
    assert json.loads(drifted.stdout.decode("utf-8"))["ok"] is False
    assert exe.read_bytes() == b"synthetic executable"


def test_help_lists_exactly_the_four_workflow_commands() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    help_text = result.stdout.decode("utf-8")
    assert all(command in help_text for command in ("verify-game", "skeleton", "validate", "coverage"))
