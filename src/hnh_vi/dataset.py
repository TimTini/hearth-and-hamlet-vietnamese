"""Read-only CSV audit and canonicalization; diagnostics never contain source text."""

import csv
import hashlib
from dataclasses import dataclass, field, replace
from io import StringIO
from pathlib import Path

from hnh_vi.completeness import SourceCompleteness


@dataclass(frozen=True)
class SourceRow:
    key: str
    english: str = field(repr=False)
    source_sha256: str


@dataclass(frozen=True)
class SourceIssue:
    code: str
    severity: str
    key_sha256: str | None = None
    row_numbers: tuple[int, ...] = ()
    occurrences: int | None = None
    field: str | None = None
    expected: str | int | None = None
    actual: str | int | None = None


@dataclass(frozen=True)
class CanonicalSource:
    rows: tuple[SourceRow, ...]
    completeness: SourceCompleteness
    issues: tuple[SourceIssue, ...]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def audit_source_csv(path: Path, expected: SourceCompleteness) -> CanonicalSource:
    """Audit exactly the bytes hashed, preserving first occurrences and English text.

    Conflicting keys and unrecovered markers are never returned as buildable rows.
    Row numbers are one-based CSV records after the header, including quoted newlines.
    """
    data = path.read_bytes()
    issues = []
    groups: dict[str, list[tuple[int, SourceRow]]] = {}
    total_rows = unrecovered_rows = 0
    try:
        reader = csv.reader(StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
        headers = next(reader, [])
        if (
            not headers or headers[0] != "key" or "en" not in headers
            or len(set(headers)) != len(headers) or any(not header for header in headers)
        ):
            raise ValueError("invalid_source_csv: required unique key/en columns")
        english_column = headers.index("en")
        for row_number, values in enumerate(reader, 1):
            total_rows += 1
            if len(values) != len(headers) or not values[0].strip():
                raise ValueError("invalid_source_csv: row shape or empty key")
            key, english = values[0], values[english_column]
            if key.startswith("<!MissingKey"):
                unrecovered_rows += 1
                if not (key.startswith("<!MissingKey:") and key.endswith(">")):
                    issues.append(SourceIssue(
                        "malformed_missing_key_marker", "error",
                        key_sha256=_sha256(key.encode("utf-8")), row_numbers=(row_number,),
                    ))
                continue
            source_row = SourceRow(key, english, _sha256(english.encode("utf-8")))
            groups.setdefault(key, []).append((row_number, source_row))
    except (csv.Error, UnicodeError):
        raise ValueError("invalid_source_csv: encoding or CSV syntax") from None

    recovered_rows = total_rows - unrecovered_rows
    actual = replace(
        expected, recovered_csv_sha256=_sha256(data), total_rows=total_rows,
        recovered_rows=recovered_rows, unrecovered_rows=unrecovered_rows,
        unique_recovered_keys=len(groups),
        duplicate_key_groups=sum(len(group) > 1 for group in groups.values()),
        duplicate_extra_rows=recovered_rows - len(groups),
        source_complete=unrecovered_rows == 0,
    )
    if actual.recovered_csv_sha256 != expected.recovered_csv_sha256.upper():
        issues.append(SourceIssue(
            "source_csv_drift", "error", field="recovered_csv_sha256",
            expected=expected.recovered_csv_sha256.upper(), actual=actual.recovered_csv_sha256,
        ))
    for count_field in (
        "total_rows", "recovered_rows", "unique_recovered_keys", "duplicate_key_groups",
        "duplicate_extra_rows", "unrecovered_rows",
    ):
        expected_count, actual_count = getattr(expected, count_field), getattr(actual, count_field)
        if actual_count != expected_count:
            issues.append(SourceIssue(
                "source_count_drift", "error", field=count_field,
                expected=expected_count, actual=actual_count,
            ))

    rows = []
    for key, group in groups.items():
        conflict = len({row.source_sha256 for _, row in group}) != 1
        if len(group) > 1:
            issues.append(SourceIssue(
                "conflicting_source_key" if conflict else "duplicate_source_key",
                "error" if conflict else "warning", key_sha256=_sha256(key.encode("utf-8")),
                row_numbers=tuple(number for number, _ in group), occurrences=len(group),
            ))
        if not conflict:
            rows.append(group[0][1])
    return CanonicalSource(tuple(rows), actual, tuple(issues))
