# -*- coding: utf-8 -*-
"""Apply full VI translations to localization CSVs and phase1.keys."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from vi_explicit import BLOCKED_VI, BY_KEY  # noqa: E402
from vi_formulaic import translate_formulaic  # noqa: E402
from vi_names import translate_name  # noqa: E402


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    return fields, rows


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def translate_one(key: str, en: str) -> str | None:
    if key in BY_KEY:
        return BY_KEY[key]
    named = translate_name(en)
    if named is not None:
        return named
    if key.endswith("_DES") or key.endswith("_DESCRIPTION") or "DESCRIPTION" in key:
        formulaic = translate_formulaic(en)
        if formulaic is not None:
            return formulaic
    # Short UI labels sometimes equal EN string as key
    if en in BY_KEY:
        return BY_KEY[en]
    return None


def main() -> int:
    src_path = ROOT / "workspace/25600292/probe/source/localisation/translations.csv"
    vi_path = ROOT / "localization/translations.vi.csv"
    status_path = ROOT / "localization/status.csv"
    keys_path = ROOT / "localization/phase1.keys"

    src: dict[str, dict[str, str]] = {}
    with src_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            src[row["key"]] = row

    vi_fields, vi_rows = load_csv(vi_path)
    status_fields, status_rows = load_csv(status_path)
    status_by_key = {r["key"]: r for r in status_rows}
    vi_by_key = {r["key"]: r for r in vi_rows}

    translated = 0
    missing: list[tuple[str, str]] = []
    for key, st_row in status_by_key.items():
        if st_row.get("status") != "draft":
            continue
        en = src[key]["en"]
        vi = translate_one(key, en)
        if not vi:
            missing.append((key, en[:120]))
            continue
        vi_by_key[key]["translation_vi"] = vi
        st_row["status"] = "reviewed"
        st_row["note"] = ""
        translated += 1

    unblocked = 0
    still_blocked: list[str] = []
    for key, (vi, note) in BLOCKED_VI.items():
        st_row = status_by_key[key]
        if vi:
            vi_by_key[key]["translation_vi"] = vi
            st_row["status"] = "reviewed"
            st_row["note"] = note
            unblocked += 1
        else:
            st_row["note"] = note
            still_blocked.append(key)

    # Rebuild phase1.keys: all reviewed (+ in_game if any), exclude remaining blocked
    selected = sorted(
        k
        for k, row in status_by_key.items()
        if row.get("status") in {"reviewed", "in_game"}
    )
    keys_path.write_text("\n".join(selected) + ("\n" if selected else ""), encoding="utf-8")

    write_csv(vi_path, vi_fields, vi_rows)
    write_csv(status_path, status_fields, status_rows)

    # Recount
    from collections import Counter

    counts = Counter(r["status"] for r in status_rows)
    empty_vi = sum(1 for r in vi_rows if not (r.get("translation_vi") or "").strip())
    print(f"newly_translated_drafts={translated}")
    print(f"unblocked={unblocked}")
    print(f"still_blocked={still_blocked}")
    print(f"missing={len(missing)}")
    for k, e in missing[:50]:
        print(f"  MISS {k}: {e!r}")
    print(f"status={dict(counts)}")
    print(f"phase1_keys={len(selected)}")
    print(f"empty_vi_rows={empty_vi}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
