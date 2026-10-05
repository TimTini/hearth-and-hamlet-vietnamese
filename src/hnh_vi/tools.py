"""Bootstrap pinned portable tools into a repository-local cache."""

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True)
class ToolSpec:
    id: str
    version: str
    asset: str
    url: str
    sha256: str

    def __post_init__(self) -> None:
        for name in (self.id, self.version, self.asset):
            if (
                not name or name in (".", "..")
                or any(c in name for c in "/\\:\0")
                or name.endswith((".", " "))
            ):
                raise ValueError("tool_invalid_manifest: names must be plain names")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.sha256):
            raise ValueError("tool_invalid_manifest: expected SHA-256 digest")


def load_tool_specs(path: Path) -> tuple[ToolSpec, ...]:
    """Read the exact versions and archive fingerprints approved by the repo."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return tuple(ToolSpec(**tool) for tool in manifest["tools"])


def ensure_tool(spec: ToolSpec, tools_dir: Path) -> Path:
    """Reuse an installed tool or download, verify and atomically publish it."""
    installed = tools_dir / spec.id / spec.version
    if installed.is_dir():
        return installed

    installed.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=installed.parent, prefix=f".{spec.version}-", suffix=".zip.tmp", delete=False
    ) as temporary:
        archive_path = Path(temporary.name)
    try:
        with urllib.request.urlopen(spec.url) as response, archive_path.open("wb") as archive:
            shutil.copyfileobj(response, archive)
        with archive_path.open("rb") as archive:
            digest = hashlib.file_digest(archive, "sha256").hexdigest()
        if digest.lower() != spec.sha256.lower():
            raise ValueError(f"tool_hash_mismatch: {spec.id}")

        with ZipFile(archive_path) as archive:
            for member in archive.infolist():
                name = member.filename.replace("\\", "/")
                windows_path = PureWindowsPath(member.filename)
                if (
                    name.startswith("/") or windows_path.drive or windows_path.root
                    or ".." in name.split("/") or ":" in name
                    or any(
                        part not in ("", ".") and part.endswith((".", " "))
                        for part in name.split("/")
                    )
                ):
                    raise ValueError(f"tool_unsafe_archive: {spec.id}")
            with tempfile.TemporaryDirectory(
                dir=installed.parent, prefix=f".{spec.version}-"
            ) as extracted:
                archive.extractall(extracted)
                Path(extracted).rename(installed)
        return installed
    finally:
        archive_path.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    ensure = commands.add_parser("ensure", help="ensure pinned tools are installed")
    ensure.add_argument("--manifest", type=Path, required=True)
    ensure.add_argument("--tools-dir", type=Path, required=True)
    ensure.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    try:
        for spec in load_tool_specs(args.manifest):
            installed = args.tools_dir / spec.id / spec.version
            if args.offline and not installed.is_dir():
                raise ValueError(f"tool_missing_offline: {spec.id} {spec.version}")
            ensure_tool(spec, args.tools_dir)
    except (OSError, ValueError, KeyError, TypeError, BadZipFile) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
