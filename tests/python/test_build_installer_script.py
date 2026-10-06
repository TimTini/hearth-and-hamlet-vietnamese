import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests" / "installer-tools.json"
SCRIPT = REPO / "scripts" / "build-installer.ps1"
LICENSE = REPO / "installer" / "third_party" / "zstd-LICENSE"
CSPROJ = (
    REPO
    / "installer"
    / "src"
    / "HearthAndHamlet.Vietnamese.Setup"
    / "HearthAndHamlet.Vietnamese.Setup.csproj"
)
PATCHER = (
    REPO
    / "installer"
    / "src"
    / "HearthAndHamlet.Vietnamese.Setup"
    / "PayloadPatcher.cs"
)
GITIGNORE = REPO / ".gitignore"

ZSTD_URL = "https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-v1.5.7-win64.zip"
ZSTD_SHA256 = "ACB4E8111511749DC7A3EBEDCA9B04190E37A17AFEB73F55D4425DBF0B90FAD9"
OUTPUT_NAME = "Hearth-and-Hamlet-Tieng-Viet-Setup.exe"


def test_installer_tools_manifest_pins_https_zstd_release() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tools = {item["id"]: item for item in data["tools"]}
    zstd = tools["zstd"]
    assert zstd["version"] == "1.5.7"
    assert zstd["url"] == ZSTD_URL
    assert zstd["url"].startswith("https://")
    assert zstd["sha256"].upper() == ZSTD_SHA256
    assert zstd["asset"] == "zstd-v1.5.7-win64.zip"


def test_build_script_verifies_hash_before_extract_and_uses_literal_paths() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "installer-tools.json" in text
    assert "Get-FileHash" in text or "SHA256" in text
    assert "hash_mismatch" in text.lower() or "Hash mismatch" in text or "sha256" in text.lower()
    assert "Expand-Archive" in text
    assert "-LiteralPath" in text
    assert "OriginalPck" in text and "TranslatedPck" in text
    assert "--patch-from" in text
    assert "-19" in text
    assert OUTPUT_NAME in text
    assert ".sha256" in text
    assert "PublishSingleFile" in text
    assert "SelfContained" in text or "self-contained" in text
    assert "win-x64" in text
    assert "PublishTrimmed" in text


def test_csproj_publishes_self_contained_single_file_and_embeds_payload() -> None:
    text = CSPROJ.read_text(encoding="utf-8")
    assert "PublishSingleFile" in text
    assert "SelfContained" in text
    assert "win-x64" in text or "$(RuntimeIdentifier)" in text
    assert "PublishTrimmed" in text
    assert "EmbeddedResource" in text
    assert "zstd.exe" in text
    assert "payload.patch.zst" in text


def test_payload_patcher_invokes_zstd_decompress_patch_from_with_explicit_output() -> None:
    text = PATCHER.read_text(encoding="utf-8")
    assert 'ArgumentList.Add("-d")' in text or 'ArgumentList.Add("--decompress")' in text
    assert 'ArgumentList.Add("--long=30")' in text
    assert 'ArgumentList.Add("--patch-from")' in text
    assert 'ArgumentList.Add("-o")' in text
    assert 'ArgumentList.Add("-f")' not in text
    assert 'ArgumentList.Add("--force")' not in text


def test_zstd_license_is_bundled_and_payload_outputs_are_ignored() -> None:
    license_text = LICENSE.read_text(encoding="utf-8")
    assert "BSD" in license_text or "Redistribution" in license_text
    ignore = GITIGNORE.read_text(encoding="utf-8")
    assert "dist/" in ignore
    assert ".tools/" in ignore
    assert "installer/payload/" in ignore or "payload.patch.zst" in ignore
