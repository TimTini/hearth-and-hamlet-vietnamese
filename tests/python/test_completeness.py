import json
from dataclasses import asdict
from pathlib import Path

import pytest

from hnh_vi.completeness import SourceCompleteness, load_source_completeness
from hnh_vi.workspace import WorkspaceSnapshot

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/localization/source-completeness.json"


def test_loads_exact_approved_partial_manifest() -> None:
    assert asdict(load_source_completeness(ROOT / "localization/source-completeness.json")) == {
        "schema_version": 1,
        "build_id": "25600292",
        "pck_sha256": "7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201",
        "recovered_csv_sha256": "D7ADF32E2453BEAE6D716319D703C1BC5715A31143C7DB91D299FA7619003F7E",
        "total_rows": 1849,
        "recovered_rows": 1822,
        "unique_recovered_keys": 1811,
        "duplicate_key_groups": 8,
        "duplicate_extra_rows": 11,
        "unrecovered_rows": 27,
        "fallback_locale": "en",
        "policy": "partial_with_english_fallback",
        "source_complete": False,
    }


@pytest.mark.parametrize(("field", "value"), [
    ("schema_version", 2), ("schema_version", True), ("build_id", ""),
    ("pck_sha256", "bad"), ("recovered_csv_sha256", "G" * 64),
    ("total_rows", 26), ("recovered_rows", 21), ("unrecovered_rows", -1),
    ("unique_recovered_keys", 9), ("duplicate_extra_rows", 11),
    ("duplicate_key_groups", 13), ("duplicate_key_groups", True),
    ("fallback_locale", "vi"), ("policy", "complete"), ("source_complete", True),
    ("source_complete", 0),
])
def test_rejects_invalid_manifest_contract(tmp_path: Path, field: str, value: object) -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data[field] = value
    path = tmp_path / "source completeness.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_source_completeness"):
        load_source_completeness(path)


@pytest.mark.parametrize("mutation", ["missing", "extra", "not_object"])
def test_rejects_manifest_schema_shape(tmp_path: Path, mutation: str) -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if mutation == "missing":
        del data["total_rows"]
    elif mutation == "extra":
        data["unexpected"] = 1
    else:
        data = []
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_source_completeness"):
        load_source_completeness(path)


@pytest.mark.parametrize(("field", "value", "code"), [
    ("build_id", "other", "build_id_mismatch"),
    ("pck_sha256", "C" * 64, "pck_drift"),
    ("source_csv_sha256", "D" * 64, "source_csv_drift"),
])
def test_completeness_requires_matching_snapshot_identity(
    field: str, value: str, code: str,
) -> None:
    expected = load_source_completeness(FIXTURE)
    values = {
        "build_id": expected.build_id,
        "pck_sha256": expected.pck_sha256.lower(),
        "source_csv_sha256": expected.recovered_csv_sha256.lower(),
        "extracted_at_utc": "2026-10-06T00:00:00Z",
    }
    assert expected.verify_snapshot(WorkspaceSnapshot(**values)).ok
    values[field] = value
    result = expected.verify_snapshot(WorkspaceSnapshot(**values))
    assert not result.ok
    assert result.issues == (code,)


def test_completeness_constructor_enforces_contract() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["source_complete"] = True
    with pytest.raises(ValueError, match="invalid_source_completeness"):
        SourceCompleteness(**data)
