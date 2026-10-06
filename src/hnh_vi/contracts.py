"""Translation CSV contracts and text-free, deterministic validation diagnostics."""

import csv
import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from hnh_vi.dataset import CanonicalSource

STATUSES = frozenset({"draft", "reviewed", "in_game", "blocked"})
PRINTF = re.compile(r"%%|%(?:\d+\$)?[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlL]*[diouxXeEfFgGcs]")
BRACED = re.compile(r"(?<!\{)\{(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+)\}(?!\})")
TAG = re.compile(r"\[(/?)([A-Za-z_][A-Za-z0-9_]*)([^\[\]]*)\]")
SINGLE_TAGS = frozenset({"br", "hr", "lb", "rb"})
SUPPORTED_TAGS = SINGLE_TAGS | frozenset({
    "b", "i", "u", "s", "code", "p", "center", "left", "right", "fill", "indent",
    "url", "hint", "img", "font", "font_size", "dropcap", "opentype_features", "lang",
    "color", "bgcolor", "fgcolor", "outline_size", "outline_color", "table", "cell",
    "ul", "ol", "wave", "tornado", "shake", "fade", "rainbow", "pulse",
})


@dataclass(frozen=True)
class TranslationRow:
    key: str
    source_sha256: str
    translation_vi: str = field(repr=False)


@dataclass(frozen=True)
class StatusRow:
    key: str
    status: str
    note: str = field(default="", repr=False)


@dataclass(frozen=True)
class GlossaryTerm:
    source_term: str = field(repr=False)
    translation_vi: str = field(repr=False)
    scope: str = ""
    note: str = field(default="", repr=False)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    key_sha256: str | None = None
    row_numbers: tuple[int, ...] = ()
    occurrences: int | None = None
    field: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    errors: tuple[ValidationIssue, ...]
    warnings: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_csv(path: Path, columns: tuple[str, ...], row_type: type, name: str) -> tuple:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            if next(reader, []) != list(columns):
                raise ValueError
            rows = []
            for values in reader:
                if len(values) != len(columns):
                    raise ValueError
                rows.append(row_type(*values))
            return tuple(rows)
    except (ValueError, csv.Error, UnicodeError):
        raise ValueError(f"invalid_{name}_csv: schema, encoding or CSV syntax") from None


def load_translation_csv(path: Path) -> tuple[TranslationRow, ...]:
    return _load_csv(path, ("key", "source_sha256", "translation_vi"), TranslationRow, "translation")


def load_status_csv(path: Path) -> tuple[StatusRow, ...]:
    return _load_csv(path, ("key", "status", "note"), StatusRow, "status")


def load_glossary_csv(path: Path) -> tuple[GlossaryTerm, ...]:
    return _load_csv(path, ("source_term", "translation_vi", "scope", "note"), GlossaryTerm, "glossary")


def _bbcode(text: str) -> tuple[str, ...] | None:
    stack = []
    tokens = []
    for match in TAG.finditer(text):
        closing, name, attributes = match.groups()
        if name not in SUPPORTED_TAGS:
            continue
        tokens.append(match.group())
        if closing:
            if attributes or not stack or stack.pop() != name:
                return None
        elif name not in SINGLE_TAGS:
            stack.append(name)
    return None if stack else tuple(tokens)


def _placeholders(text: str) -> tuple[tuple[str, ...], Counter]:
    # Unnumbered printf consumes arguments in sequence; numbered/brace tokens can move.
    printf = PRINTF.findall(text)
    ordered = tuple(token for token in printf if token != "%%" and not re.match(r"%\d+\$", token))
    return ordered, Counter(printf + BRACED.findall(text))


def validate_dataset(
    source: CanonicalSource,
    translations: tuple[TranslationRow, ...],
    statuses: tuple[StatusRow, ...],
    glossary: tuple[GlossaryTerm, ...],
    required_keys: frozenset[str] | None = None,
) -> ValidationReport:
    """Validate all row integrity; only explicitly required keys must be nonempty/ready.

    Diagnostics use key hashes and record numbers, never key/source/translation prose.
    Non-NFC text is preserved and warned about; generated build output normalizes it.
    """
    issues = [ValidationIssue(
        issue.code, issue.severity, issue.key_sha256, issue.row_numbers,
        issue.occurrences, issue.field,
    ) for issue in source.issues]
    known = {row.key: row for row in source.rows}
    required = required_keys or frozenset()

    def issue(code: str, key: str | None = None, severity: str = "error", **metadata) -> None:
        key_hash = hashlib.sha256(key.encode("utf-8", errors="surrogatepass")).hexdigest().upper() if key is not None else None
        issues.append(ValidationIssue(code, severity, key_hash, **metadata))

    def index(rows: tuple, label: str) -> dict:
        groups = {}
        for number, row in enumerate(rows, 1):
            if row.key.startswith("<!MissingKey"):
                issue("missing_key_marker", row.key, row_numbers=(number,), field=label)
                continue
            if not row.key.strip():
                issue(f"empty_{label}_key", row.key, row_numbers=(number,))
                continue
            groups.setdefault(row.key, []).append((number, row))
        result = {}
        for key, group in groups.items():
            if len(group) > 1:
                issue(f"duplicate_{label}_key", key, row_numbers=tuple(n for n, _ in group),
                      occurrences=len(group))
            if key not in known:
                issue(f"extra_{label}_key", key)
            result[key] = group[0][1]
        return result

    translated = index(translations, "translation")
    status_by_key = index(statuses, "status")
    for key in sorted(required):
        if key.startswith("<!MissingKey"):
            issue("missing_key_marker", key, field="required_keys")
        elif key not in known:
            issue("unknown_required_key", key)

    for key, row in status_by_key.items():
        if row.status not in STATUSES:
            issue("invalid_status", key)

    for number, term in enumerate(glossary, 1):
        if not term.source_term.strip() or not term.translation_vi.strip():
            issue("invalid_glossary_term", row_numbers=(number,))

    for key, original in known.items():
        row = translated.get(key)
        status = status_by_key.get(key)
        if row is None:
            issue("missing_translation_key", key)
        if status is None:
            issue("missing_status", key)
        if key in required and status and status.status in {"draft", "blocked"}:
            issue("required_status_not_ready", key)
        if row is None:
            continue
        if not re.fullmatch(r"[A-Fa-f0-9]{64}", row.source_sha256):
            issue("invalid_source_hash", key)
        elif row.source_sha256.upper() != original.source_sha256.upper():
            issue("source_hash_drift", key)
        text = row.translation_vi
        if any(unicodedata.category(char) in {"Cs", "Cc"} and char not in "\n\r\t" for char in text):
            issue("invalid_unicode", key)
        if not text.strip():
            if key in required:
                issue("empty_required_translation", key)
            continue
        if not unicodedata.is_normalized("NFC", text):
            issue("non_nfc_translation", key, "warning")
        if _placeholders(original.english) != _placeholders(text):
            issue("placeholder_mismatch", key)
        if (original.english.count(r"\n"), original.english.count("\n")) != (text.count(r"\n"), text.count("\n")):
            issue("newline_mismatch", key)
        original_tags, translated_tags = _bbcode(original.english), _bbcode(text)
        if original_tags is None or translated_tags is None or original_tags != translated_tags:
            issue("bbcode_mismatch", key)
        for number, term in enumerate(glossary, 1):
            if not term.source_term.strip() or not term.translation_vi.strip():
                continue
            if term.scope and term.scope != key:
                continue
            if (re.search(r"(?<!\w)" + re.escape(term.source_term) + r"(?!\w)", original.english,
                          flags=re.IGNORECASE)
                    and not re.search(r"(?<!\w)" + re.escape(term.translation_vi) + r"(?!\w)", text,
                                      flags=re.IGNORECASE)):
                issue("glossary_mismatch", key, "warning", row_numbers=(number,), field="glossary")
    return ValidationReport(
        tuple(item for item in issues if item.severity == "error"),
        tuple(item for item in issues if item.severity == "warning"),
    )
