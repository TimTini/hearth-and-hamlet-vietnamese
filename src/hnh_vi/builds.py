"""Read-only verification of explicitly supported game builds."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildSpec:
    build_id: str
    exe_version: str
    confirmed_on: str
    exe_name: str
    exe_sha256: str
    pck_name: str
    pck_sha256: str

    def __post_init__(self) -> None:
        for name in (self.exe_name, self.pck_name):
            if not name or name in (".", "..") or any(c in name for c in "/\\:"):
                raise ValueError("Build filenames must be plain names")


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    issues: tuple[str, ...]


def load_build_specs(path: Path) -> tuple[BuildSpec, ...]:
    """Load approved fingerprints from the repository build manifest."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return tuple(BuildSpec(**build) for build in manifest["builds"])


def sha256_file(path: Path) -> str:
    """Hash a file without loading the whole EXE or PCK into memory."""
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest().upper()


def verify_game_dir(
    game_dir: Path, spec: BuildSpec, appmanifest: Path | None = None
) -> VerificationResult:
    """Check EXE, PCK and optional Steam build ID; never modify any file."""
    issues = []
    for name, expected_hash in (
        (spec.exe_name, spec.exe_sha256),
        (spec.pck_name, spec.pck_sha256),
    ):
        path = game_dir / name
        if not path.is_file():
            issues.append("missing_file")
        elif sha256_file(path) != expected_hash.upper():
            issues.append("hash_mismatch")

    if appmanifest is not None:
        if not appmanifest.is_file():
            issues.append("missing_file")
        else:
            build_ids = re.findall(
                r'^\s*"buildid"\s+"([^"\r\n]*)"\s*$',
                appmanifest.read_text(encoding="utf-8"),
                flags=re.MULTILINE,
            )
            if build_ids != [spec.build_id]:
                issues.append("steam_build_mismatch")

    return VerificationResult(ok=not issues, issues=tuple(issues))
