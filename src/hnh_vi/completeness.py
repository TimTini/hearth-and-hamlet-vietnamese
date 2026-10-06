"""Pinned, text-free metadata for a recovered localization source."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from hnh_vi.builds import VerificationResult
from hnh_vi.workspace import WorkspaceSnapshot


@dataclass(frozen=True)
class SourceCompleteness:
    schema_version: int
    build_id: str
    pck_sha256: str
    recovered_csv_sha256: str
    total_rows: int
    recovered_rows: int
    unique_recovered_keys: int
    duplicate_key_groups: int
    duplicate_extra_rows: int
    unrecovered_rows: int
    fallback_locale: str
    policy: str
    source_complete: bool

    def __post_init__(self) -> None:
        counts = (
            self.total_rows, self.recovered_rows, self.unique_recovered_keys,
            self.duplicate_key_groups, self.duplicate_extra_rows, self.unrecovered_rows,
        )
        if (
            type(self.schema_version) is not int or self.schema_version != 1
            or not isinstance(self.build_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]+", self.build_id)
            or any(not isinstance(digest, str) or not re.fullmatch(r"[A-Fa-f0-9]{64}", digest)
                   for digest in (self.pck_sha256, self.recovered_csv_sha256))
            or any(type(count) is not int or count < 0 for count in counts)
            or type(self.source_complete) is not bool
            or self.fallback_locale != "en"
            or self.policy != "partial_with_english_fallback"
        ):
            raise ValueError("invalid_source_completeness: field contract")
        if (
            self.total_rows != self.recovered_rows + self.unrecovered_rows
            or self.recovered_rows != self.unique_recovered_keys + self.duplicate_extra_rows
            or self.duplicate_key_groups > self.unique_recovered_keys
            or self.duplicate_key_groups > self.duplicate_extra_rows
            or (self.duplicate_key_groups == 0) != (self.duplicate_extra_rows == 0)
            or self.source_complete != (self.unrecovered_rows == 0)
        ):
            raise ValueError("invalid_source_completeness: inconsistent counts")

    def verify_snapshot(self, snapshot: WorkspaceSnapshot) -> VerificationResult:
        """Compare identity metadata; callers must also run the existing file verifier."""
        issues = []
        if snapshot.build_id != self.build_id:
            issues.append("build_id_mismatch")
        if snapshot.pck_sha256.upper() != self.pck_sha256.upper():
            issues.append("pck_drift")
        if snapshot.source_csv_sha256.upper() != self.recovered_csv_sha256.upper():
            issues.append("source_csv_drift")
        return VerificationResult(not issues, tuple(issues))


def load_source_completeness(path: Path) -> SourceCompleteness:
    """Load the approved manifest without silently approving drift or new schemas."""
    try:
        return SourceCompleteness(**json.loads(path.read_text(encoding="utf-8")))
    except (TypeError, ValueError):
        raise ValueError("invalid_source_completeness") from None
