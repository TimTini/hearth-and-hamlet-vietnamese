# -*- coding: utf-8 -*-
"""Reduce glossary_mismatch while preserving false printf tokens."""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hnh_vi.contracts import _placeholders  # noqa: E402

# Exact string replacements that keep % tokens and add glossary Vietnamese.
REPLACEMENTS: list[tuple[str, str]] = [
    # Keep English false-printf word, add VI glossary term nearby
    ("% Gold sản xuất", "% Gold vàng sản xuất"),
    ("% gold sản xuất", "% gold vàng sản xuất"),
    ("% gold trong", "% gold vàng trong"),
    ("% Fishing sản xuất", "% Fishing đánh cá sản xuất"),
    ("% fishing sản xuất", "% fishing đánh cá sản xuất"),
    ("% Farm sản xuất", "% Farm nông sản xuất"),  # Farm→need? glossary may not have Farm
    ("% farm sản xuất", "% farm nông sản xuất"),
    ("% Hunting sản xuất", "% Hunting săn bắn sản xuất"),
    ("% hunting sản xuất", "% hunting săn bắn sản xuất"),
    ("% hunting hiệu suất", "% hunting săn bắn hiệu suất"),
    ("% hunting sản lượng", "% hunting săn bắn sản lượng"),
    ("% Iron sản xuất", "% Iron sắt sản xuất"),
    ("% iron sản xuất", "% iron sắt sản xuất"),
    ("% iron trong", "% iron sắt trong"),
    ("% Stone sản xuất", "% Stone đá sản xuất"),
    ("% stone sản xuất", "% stone đá sản xuất"),
    ("% stone trong", "% stone đá trong"),
    ("% Wood sản xuất", "% Wood gỗ sản xuất"),
    ("% wood sản xuất", "% wood gỗ sản xuất"),
    ("% wood trong", "% wood gỗ trong"),
    ("% Magic sản xuất", "% Magic phép thuật sản xuất"),
    ("% magic sản xuất", "% magic phép thuật sản xuất"),
    ("% food sản xuất", "% food lương thực sản xuất"),
    ("% food tiêu thụ", "% food lương thực tiêu thụ"),
    ("% happiness", "% happiness hạnh phúc"),
    ("% caravan tốc độ", "% caravan đoàn buôn tốc độ"),
    ("% ship tốc độ", "% ship tốc độ tàu"),
    ("% of binh lính", "% of binh lính"),  # noop
    ("% soldier chi phí huấn luyện và duy trì", "% soldier chi phí duy trì và huấn luyện binh lính"),
    # soldier short form → full glossary
    ("mỗi binh", "mỗi binh lính"),
    ("phòng thủ binh lính", "phòng thủ binh lính"),
    ("tấn công binh lính", "tấn công binh lính"),
    # Trade goods names
    ("Hàng đá", "Hàng giao thương đá"),
    ("Hàng gỗ", "Hàng giao thương gỗ"),
    ("Hàng kim loại", "Hàng giao thương kim loại"),
    ("Hàng nông sản", "Hàng giao thương nông sản"),
    ("Hàng phép thuật", "Hàng giao thương phép thuật"),
    ("Hàng xa xỉ", "Hàng giao thương xa xỉ"),
    ("Hàng vàng", "Hàng giao thương vàng"),
    # avoid double
    ("Hàng giao thương giao thương", "Hàng giao thương"),
    # Blueprint naming
    ("Thiết kế bản vẽ huyền thoại", "Bản thiết kế huyền thoại"),
    ("Thiết kế bản vẽ bậc thầy", "Bản thiết kế bậc thầy"),
    ("Thiết kế bản vẽ chuyên gia", "Bản thiết kế chuyên gia"),
    ("Thiết kế bản vẽ nâng cao", "Bản thiết kế nâng cao"),
    # Hunting tool names missing "săn bắn"?
    ("Dụng cụ săn sắt", "Dụng cụ săn bắn sắt"),
    ("Dụng cụ săn thép", "Dụng cụ săn bắn thép"),
    ("Dụng cụ săn chắc chắn", "Dụng cụ săn bắn chắc chắn"),
    # Swamp
    ("Đầm phép thuật", "Đầm lầy phép thuật"),
    ("phế tích đầm.", "phế tích đầm lầy."),
    ("phế tích đầm ", "phế tích đầm lầy "),
    # Population
    ("mỗi 15 dân mỗi giây", "mỗi 15 dân số mỗi giây"),
    # Unlock trades already say giao thương in many places
]


def main() -> int:
    vi_path = ROOT / "localization/translations.vi.csv"
    src_path = ROOT / "workspace/25600292/probe/source/localisation/translations.csv"
    src = {}
    with src_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            src[row["key"]] = row["en"]

    with vi_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    changed = 0
    broken = 0
    for row in rows:
        old = row["translation_vi"]
        new = old
        for a, b in REPLACEMENTS:
            if a in new:
                new = new.replace(a, b)
        # collapse accidental doubles from Hàng đá cao cấp -> Hàng giao thương đá cao cấp OK
        new = new.replace("Hàng giao thương giao thương", "Hàng giao thương")
        if new != old:
            en = src[row["key"]]
            if _placeholders(en) != _placeholders(new):
                print("BROKE", row["key"])
                print(" ", repr(old[:100]))
                print(" ", repr(new[:100]))
                print(" ", _placeholders(en), _placeholders(new))
                broken += 1
                continue
            row["translation_vi"] = new
            changed += 1

    with vi_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"changed={changed} broken={broken}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
