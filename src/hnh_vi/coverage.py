"""Coverage denominators distinguish source rows, canonical keys and selected phase."""

from dataclasses import dataclass

from hnh_vi.contracts import StatusRow, TranslationRow, validate_dataset
from hnh_vi.dataset import CanonicalSource


@dataclass(frozen=True)
class CoverageReport:
    total_source_rows: int
    recovered_rows: int
    unrecovered_rows: int
    unique_recovered_keys: int
    source_complete: bool
    maximum_known_source_ratio: float
    translated_keys: int
    draft_keys: int
    reviewed_keys: int
    in_game_keys: int
    blocked_keys: int
    ready_keys: int
    known_translation_ratio: float
    known_ready_ratio: float
    selected_keys: int
    selected_translated_keys: int
    selected_draft_keys: int
    selected_reviewed_keys: int
    selected_in_game_keys: int
    selected_blocked_keys: int
    selected_ready_keys: int
    selected_translation_ratio: float
    selected_ready_ratio: float


def calculate_coverage(
    source: CanonicalSource,
    translations: tuple[TranslationRow, ...],
    statuses: tuple[StatusRow, ...],
    selected_keys: frozenset[str] | None = None,
) -> CoverageReport:
    """Count valid unique rows, including empty gaps, without requiring phase readiness.

    Ratios have exact denominators and are not rounded. A zero denominator yields 0.
    maximum_known_source_ratio counts recovered rows / all source rows, including
    canonicalized duplicates, rather than mixing rows with a unique-key numerator.
    """
    report = validate_dataset(source, translations, statuses, ())
    known = frozenset(row.key for row in source.rows)
    selected = known if selected_keys is None else selected_keys
    if not report.ok or selected - known:
        raise ValueError("invalid_coverage_dataset")
    translated = frozenset(row.key for row in translations if row.translation_vi.strip())
    status_by_key = {row.key: row.status for row in statuses}

    def counts(keys: frozenset[str]) -> tuple[int, int, int, int, int, int]:
        draft, reviewed, in_game, blocked = (
            sum(status_by_key[key] == state for key in keys)
            for state in ("draft", "reviewed", "in_game", "blocked")
        )
        ready = sum(status_by_key[key] in {"reviewed", "in_game"} for key in keys & translated)
        return len(keys & translated), draft, reviewed, in_game, blocked, ready

    def ratio(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0.0

    all_counts, selected_counts = counts(known), counts(selected)
    completeness = source.completeness
    return CoverageReport(
        completeness.total_rows, completeness.recovered_rows, completeness.unrecovered_rows,
        completeness.unique_recovered_keys, completeness.source_complete,
        ratio(completeness.recovered_rows, completeness.total_rows),
        *all_counts, ratio(all_counts[0], len(known)), ratio(all_counts[-1], len(known)),
        len(selected), *selected_counts,
        ratio(selected_counts[0], len(selected)), ratio(selected_counts[-1], len(selected)),
    )
