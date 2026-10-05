import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.fixture
def tools_module():
    import hnh_vi.tools

    return hnh_vi.tools


def write_archive(path: Path, members: dict[str, bytes]) -> str:
    with ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def spec(tmp_path: Path, tools_module):
    archive = tmp_path / "Công cụ portable.zip"
    digest = write_archive(archive, {"bin/tool.exe": b"synthetic executable"})
    return tools_module.ToolSpec(
        id="fixture", version="1.0", asset=archive.name,
        url=archive.as_uri(), sha256=digest,
    )


def write_manifest(path: Path, spec) -> None:
    path.write_text(json.dumps({"tools": [asdict(spec)]}), encoding="utf-8")


def test_downloads_matching_digest_and_extracts_local_zip(
    tmp_path: Path, tools_module, spec
) -> None:
    tools_dir = tmp_path / ".tools"

    installed = tools_module.ensure_tool(spec, tools_dir)

    assert installed == tools_dir / "fixture/1.0"
    assert (installed / "bin/tool.exe").read_bytes() == b"synthetic executable"
    assert list(installed.parent.iterdir()) == [installed]


def test_digest_mismatch_removes_partial_archive_and_install(
    tmp_path: Path, tools_module, spec
) -> None:
    tools_dir = tmp_path / ".tools"

    with pytest.raises(ValueError, match="tool_hash_mismatch"):
        tools_module.ensure_tool(replace(spec, sha256="0" * 64), tools_dir)

    assert list((tools_dir / "fixture").iterdir()) == []


def test_offline_reuses_downloaded_tool_without_source_archive(
    tmp_path: Path, tools_module, spec
) -> None:
    tools_dir = tmp_path / ".tools"
    installed = tools_module.ensure_tool(spec, tools_dir)
    (tmp_path / spec.asset).unlink()
    manifest = tmp_path / "tools.json"
    write_manifest(manifest, spec)

    result = tools_module.main([
        "ensure", "--manifest", str(manifest), "--tools-dir", str(tools_dir),
        "--offline",
    ])

    assert result == 0
    assert (installed / "bin/tool.exe").read_bytes() == b"synthetic executable"


def test_offline_missing_tool_fails_without_creating_cache(
    tmp_path: Path, tools_module, spec, capsys
) -> None:
    manifest = tmp_path / "tools.json"
    write_manifest(manifest, spec)
    tools_dir = tmp_path / ".tools"

    result = tools_module.main([
        "ensure", "--manifest", str(manifest), "--tools-dir", str(tools_dir),
        "--offline",
    ])

    assert result != 0
    assert "tool_missing_offline" in capsys.readouterr().err
    assert not tools_dir.exists()


def test_accepts_cache_path_with_spaces_and_unicode(
    tmp_path: Path, tools_module, spec
) -> None:
    tools_dir = tmp_path / "Bộ công cụ portable"

    installed = tools_module.ensure_tool(spec, tools_dir)

    assert (installed / "bin/tool.exe").read_bytes() == b"synthetic executable"


@pytest.mark.parametrize("member", [
    "../escape.exe", "bin/../../escape.exe", "/escape.exe",
    "C:/escape.exe", "C:escape.exe", "..\\escape.exe", "\\escape.exe",
    ".. /escape.exe", "bin/.. ./escape.exe",
])
def test_rejects_archive_path_traversal_before_extracting_any_member(
    tmp_path: Path, tools_module, spec, member: str
) -> None:
    archive = tmp_path / spec.asset
    digest = write_archive(archive, {"safe.exe": b"safe", member: b"escaped"})
    tools_dir = tmp_path / ".tools"

    with pytest.raises(ValueError, match="tool_unsafe_archive"):
        tools_module.ensure_tool(replace(spec, sha256=digest), tools_dir)

    assert list((tools_dir / "fixture").iterdir()) == []
    assert not (tmp_path / "escape.exe").exists()


def test_loads_local_manifest_for_verified_install(
    tmp_path: Path, tools_module, spec
) -> None:
    manifest = tmp_path / "tools.json"
    write_manifest(manifest, spec)

    specs = tools_module.load_tool_specs(manifest)

    assert specs == (spec,)
    installed = tools_module.ensure_tool(specs[0], tmp_path / ".tools")
    assert (installed / "bin/tool.exe").read_bytes() == b"synthetic executable"


def test_module_command_installs_from_local_manifest(
    tmp_path: Path, tools_module, spec
) -> None:
    manifest = tmp_path / "tools.json"
    write_manifest(manifest, spec)
    tools_dir = tmp_path / ".tools"

    result = tools_module.main([
        "ensure", "--manifest", str(manifest), "--tools-dir", str(tools_dir),
    ])

    assert result == 0
    assert (tools_dir / "fixture/1.0/bin/tool.exe").read_bytes() == b"synthetic executable"


@pytest.mark.parametrize("field,value", [
    ("id", "../outside"), ("version", "../outside"),
    ("asset", "../outside.zip"), ("sha256", "invalid"),
])
def test_rejects_unsafe_manifest_values(
    tmp_path: Path, tools_module, spec, field: str, value: str
) -> None:
    manifest = tmp_path / "tools.json"
    fields = asdict(spec)
    fields[field] = value
    manifest.write_text(json.dumps({"tools": [fields]}), encoding="utf-8")

    with pytest.raises(ValueError):
        tools_module.load_tool_specs(manifest)
