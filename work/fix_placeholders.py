# -*- coding: utf-8 -*-
"""Fix false printf placeholder mismatches caused by '%' before letters."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hnh_vi.contracts import _placeholders  # noqa: E402


def fix_text(en: str, vi: str) -> str:
    """Rewrite VI so false printf tokens match EN, preserving meaning."""
    pe, _ = _placeholders(en)
    pv, _ = _placeholders(vi)
    if pe == pv:
        return vi

    text = vi

    # Keep English keywords after % when EN used those false tokens.
    replacements = [
        # skilled / production lines: restore English resource word after %
        ("+10% Sản xuất vàng", "+10% Gold sản xuất"),
        ("+10% Sản xuất đánh cá", "+10% Fishing sản xuất"),
        ("+10% Sản xuất nông trại", "+10% Farm sản xuất"),
        ("+10% Sản xuất săn bắn", "+10% Hunting sản xuất"),
        ("+10% Sản xuất sắt", "+10% Iron sản xuất"),
        ("+10% Sản xuất đá", "+10% Stone sản xuất"),
        ("+10% Sản xuất gỗ", "+10% Wood sản xuất"),
        ("+10% Sản xuất phép thuật", "+10% Magic sản xuất"),
        # equipment-style production
        ("+50% sản xuất đánh cá", "+50% fishing sản xuất"),
        ("+100% sản xuất đánh cá", "+100% fishing sản xuất"),
        ("+30% sản xuất đánh cá", "+30% fishing sản xuất"),
        ("+20% sản xuất đánh cá", "+20% fishing sản xuất"),
        ("+10% sản xuất đánh cá", "+10% fishing sản xuất"),
        ("+50% sản xuất nông trại", "+50% farm sản xuất"),
        ("+100% sản xuất nông trại", "+100% farm sản xuất"),
        ("+60% sản xuất sắt", "+60% iron sản xuất"),
        ("+100% sản xuất sắt", "+100% iron sản xuất"),
        ("+50% sản xuất vàng", "+50% gold sản xuất"),
        ("+100% sản xuất vàng", "+100% gold sản xuất"),
        ("+60% sản xuất đá", "+60% stone sản xuất"),
        ("+100% sản xuất đá", "+100% stone sản xuất"),
        ("+60% sản xuất gỗ", "+60% wood sản xuất"),
        ("+100% sản xuất gỗ", "+100% wood sản xuất"),
        ("+50% sản xuất phép thuật", "+50% magic sản xuất"),
        ("+100% sản xuất phép thuật", "+100% magic sản xuất"),
        ("+20% sản xuất phép thuật", "+20% magic sản xuất"),
        ("+5% mọi sản xuất", "+5% to mọi sản xuất"),  # may not help
        # hunting
        ("+50% hiệu suất săn bắn", "+50% hunting hiệu suất"),
        ("+30% hiệu suất săn bắn", "+30% hunting hiệu suất"),
        ("+100% hiệu suất săn bắn", "+100% hunting hiệu suất"),
        ("+5% sản lượng săn quy ra vàng", "+5% hunting sản lượng quy ra vàng"),
        ("+10% sản lượng săn quy ra vàng", "+10% hunting sản lượng quy ra vàng"),
        # ship / caravan
        ("+20% tốc độ tàu", "+20% ship tốc độ"),
        ("+10% tốc độ tàu", "+10% ship tốc độ"),
        ("+20% tốc độ đoàn buôn", "+20% caravan tốc độ"),
        ("+10% tốc độ đoàn buôn", "+10% caravan tốc độ"),
        ("+15% tốc độ đoàn buôn", "+15% caravan tốc độ"),
        ("+5% tốc độ đoàn buôn", "+5% caravan tốc độ"),
        # food / happiness production
        ("+20% sản xuất lương thực", "+20% food sản xuất"),
        ("+10% sản xuất lương thực", "+10% food sản xuất"),
        ("+5% sản xuất lương thực", "+5% food sản xuất"),
        ("+15% sản xuất lương thực", "+15% food sản xuất"),
        ("+50% sản xuất lương thực", "+50% food sản xuất"),
        ("+15% tiêu thụ lương thực", "+15% food tiêu thụ"),
        ("+10% tiêu thụ lương thực", "+10% food tiêu thụ"),
        ("+20% tiêu thụ lương thực", "+20% food tiêu thụ"),
        # items timed
        ("+50% gỗ trong 120 giây", "+50% wood trong 120 giây"),
        ("+50% đá trong 120 giây", "+50% stone trong 120 giây"),
        ("+50% sắt trong 120 giây", "+50% iron trong 120 giây"),
        ("+50% vàng trong 120 giây", "+50% gold trong 120 giây"),
        ("+50% sản xuất vàng trong 120 giây", "+50% gold sản xuất trong 120 giây"),
        ("+50% sản xuất phép thuật trong 120 giây", "+50% magic sản xuất trong 120 giây"),
        ("+50% sản xuất lương thực trong 120 giây", "+50% food sản xuất trong 120 giây"),
        ("+50% mọi sản xuất trong 120 giây", "+50% to mọi sản xuất trong 120 giây"),
        ("+10% hạnh phúc trong 120 giây", "+10% happiness trong 120 giây"),
        # healing / of
        ("+30% binh lính hồi phục sau trận trong 120 giây", "+30% of binh lính hồi phục sau trận trong 120 giây"),
        # monsters less frequently
        ("Quái xuất hiện ít hơn 20%", "Quái xuất hiện 20% less thường xuyên"),
        # efficiency keep EN
        ("-20% Hiệu suất", "-20% Efficiency"),
        # inspiration additional production — EN has no ph, VI introduced % s
        ("Cảm hứng giờ thêm +10% sản xuất", "Cảm hứng giờ thêm thêm 10% production"),
        # magic research lines that EN has no ph (space before %? "+ 20% to" - % to doesn't match)
        # VI "+20% sản xuất" creates % s — use "to"
        ("+20% sản xuất phép thuật\n[b](Hệ số nghiên cứu phép thuật)[/b]",
         "+20% to sản xuất phép thuật\n[b](Hệ số nghiên cứu phép thuật)[/b]"),
        ("+5% mọi sản xuất\n[b](Hệ số hiệu suất toàn cục)[/b]",
         "+5% to mọi sản xuất\n[b](Hệ số hiệu suất toàn cục)[/b]"),
        ("+15% mọi sản xuất\n[b](Hệ số giáo dục toàn cục)[/b]",
         "+15% to mọi sản xuất\n[b](Hệ số giáo dục toàn cục)[/b]"),
        ("+10% mọi sản xuất\n[b](Hệ số giáo dục toàn cục)[/b]",
         "+10% to mọi sản xuất\n[b](Hệ số giáo dục toàn cục)[/b]"),
        ("+20% mọi sản xuất\n[b](Hệ số giáo dục toàn cục)[/b]",
         "+20% to mọi sản xuất\n[b](Hệ số giáo dục toàn cục)[/b]"),
        ("+25% mọi sản xuất\n[b](Hệ số giáo dục toàn cục)[/b]",
         "+25% to mọi sản xuất\n[b](Hệ số giáo dục toàn cục)[/b]"),
        # resource gathering
        ("+15% thu hoạch tài nguyên\n[b](Hệ số nghiên cứu toàn cục)[/b]",
         "+15% resource thu hoạch\n[b](Hệ số nghiên cứu toàn cục)[/b]"),
        ("+10% thu hoạch tài nguyên\n[b](Hệ số nghiên cứu toàn cục)[/b]",
         "+10% resource thu hoạch\n[b](Hệ số nghiên cứu toàn cục)[/b]"),
        ("+5% thu hoạch tài nguyên\n[b](Hệ số nghiên cứu toàn cục)[/b]",
         "+5% resource thu hoạch\n[b](Hệ số nghiên cứu toàn cục)[/b]"),
        ("+20% thu hoạch tài nguyên\n[b](Hệ số nghiên cứu toàn cục)[/b]",
         "+20% resource thu hoạch\n[b](Hệ số nghiên cứu toàn cục)[/b]"),
        # portal reduce — EN `% i` from `% if`
        ("Giảm 90% thời gian đoàn buôn tiếp theo nếu gửi trong 120 giây",
         "Giảm 90% if thời gian đoàn buôn tiếp theo gửi trong 120 giây"),
        ("Giảm 45% thời gian đoàn buôn tiếp theo nếu gửi trong 120 giây",
         "Giảm 45% if thời gian đoàn buôn tiếp theo gửi trong 120 giây"),
        # church policy happiness + food
        ("+15% hạnh phúc, +15% tiêu thụ lương thực. Chi phí vàng vừa theo dân số",
         "+15% happiness, +15% food tiêu thụ. Chi phí vàng vừa theo dân số"),
        ("+20% hạnh phúc, +20% tiêu thụ lương thực. Chi phí vàng lớn theo dân số",
         "+20% happiness, +20% food tiêu thụ. Chi phí vàng lớn theo dân số"),
        ("+10% hạnh phúc, +10% tiêu thụ lương thực. Chi phí vàng nhỏ theo dân số",
         "+10% happiness, +10% food tiêu thụ. Chi phí vàng nhỏ theo dân số"),
        ("+10% hạnh phúc, +20% tiêu thụ lương thực",
         "+10% happiness, +20% food tiêu thụ"),
        # birth rate
        ("+10% tốc độ sinh", "+10% birth tốc độ sinh"),
        ("+20% tốc độ sinh", "+20% birth tốc độ sinh"),
        # happiness bonus alone
        ("+5% hạnh phúc", "+5% happiness"),
        ("+10% hạnh phúc", "+10% happiness"),
        ("+15% hạnh phúc", "+15% happiness"),
        ("+20% hạnh phúc", "+20% happiness"),
        # unnatural growth / all production per
        ("+5% mọi sản xuất mỗi cấp Học viện phép trong 120 giây.",
         "+5% to mọi sản xuất mỗi cấp Học viện phép trong 120 giây."),
        ("+50% mọi sản xuất", "+50% to mọi sản xuất"),
        # spirit of justice
        ("-20% chi phí huấn luyện và duy trì binh lính",
         "-20% soldier chi phí huấn luyện và duy trì"),
        # gold production research multiplier
        ("+10% sản xuất vàng\n[b](Hệ số nghiên cứu)[/b]",
         "+10% gold sản xuất\n[b](Hệ số nghiên cứu)[/b]"),
        ("+20% sản xuất vàng\n[b](Hệ số nghiên cứu)[/b]",
         "+20% gold sản xuất\n[b](Hệ số nghiên cứu)[/b]"),
        ("+15% sản xuất vàng\n[b](Hệ số nghiên cứu)[/b]",
         "+15% gold sản xuất\n[b](Hệ số nghiên cứu)[/b]"),
        ("+5% sản xuất vàng\n[b](Hệ số nghiên cứu)[/b]",
         "+5% gold sản xuất\n[b](Hệ số nghiên cứu)[/b]"),
    ]

    for old, new in replacements:
        if old in text:
            text = text.replace(old, new)

    # Generic salvage: if EN has no printf and VI still has, rewrite "+N% <word>" to "+N phần trăm <word>"
    pe2, _ = _placeholders(en)
    pv2, _ = _placeholders(text)
    if pe2 == () and pv2 != ():
        import re
        text2 = re.sub(r"([+-]?\d+(?:\.\d+)?)% (?=\S)", r"\1 phần trăm ", text)
        if _placeholders(text2)[0] == pe2:
            text = text2

    return text


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

    fixed = 0
    still = []
    for row in rows:
        key = row["key"]
        en = src.get(key, "")
        old = row.get("translation_vi", "")
        if not old or not en:
            continue
        if _placeholders(en) == _placeholders(old):
            continue
        new = fix_text(en, old)
        if _placeholders(en) != _placeholders(new):
            still.append((key, en, new, _placeholders(en), _placeholders(new)))
        else:
            row["translation_vi"] = new
            fixed += 1

    with vi_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"fixed={fixed} still={len(still)}")
    for item in still[:40]:
        print("---", item[0])
        print("EN", repr(item[1][:140]))
        print("VI", repr(item[2][:140]))
        print("want", item[3], "got", item[4])
    return 1 if still else 0


if __name__ == "__main__":
    raise SystemExit(main())
