import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZipFile


def test_bootstrap_offline_missing_tool_returns_nonzero(tmp_path: Path) -> None:
    repo_root = tmp_path / "Repo Việt hóa có dấu"
    (repo_root / "manifests").mkdir(parents=True)
    archive_path = tmp_path / "fixture.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("tool.exe", b"synthetic executable")
    (repo_root / "manifests/tools.json").write_text(
        json.dumps({"tools": [{
            "id": "fixture", "version": "1.0", "asset": "fixture.zip",
            "url": archive_path.as_uri(),
            "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        }]}), encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[2] / "scripts/bootstrap.ps1"

    result = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
        "-RepoRoot", str(repo_root), "-Offline",
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

    assert result.returncode != 0
    assert "tool_missing_offline" in result.stdout + result.stderr
    assert not (repo_root / ".tools").exists()
