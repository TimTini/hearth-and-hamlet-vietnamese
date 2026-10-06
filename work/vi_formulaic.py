# -*- coding: utf-8 -*-
"""Formulaic EN→VI for improvement/item/debuff description patterns."""
from __future__ import annotations

import re

# Ordered phrase replacements. Numbers/BBCode stay untouched by using capture groups
# only around words we rewrite. Preserve leading '+' spacing style of EN where possible.

_PHRASE_RULES: list[tuple[re.Pattern[str], str]] = [
    # Multiplier labels inside [b](...)[/b]
    (re.compile(r"Global Efficiency Multiplier"), "Hệ số hiệu suất toàn cục"),
    (re.compile(r"Global Research Multiplier"), "Hệ số nghiên cứu toàn cục"),
    (re.compile(r"Global Education Multiplier"), "Hệ số giáo dục toàn cục"),
    (re.compile(r"Magic Research Multiplier"), "Hệ số nghiên cứu phép thuật"),
    (re.compile(r"Skilled Labour Multiplier"), "Hệ số lao động lành nghề"),
    (re.compile(r"Equipment Multiplier"), "Hệ số trang bị"),
    (re.compile(r"Research Multiplier"), "Hệ số nghiên cứu"),
    # Common unlock / upgrade phrasing
    (re.compile(r"Unlocks Premium Magical Trade Goods"), "Mở khóa Hàng giao thương phép thuật cao cấp"),
    (re.compile(r"Unlocks Quality Magical Trade Goods"), "Mở khóa Hàng giao thương phép thuật chất lượng"),
    (re.compile(r"Unlocks Magical Trade Goods"), "Mở khóa Hàng giao thương phép thuật"),
    (re.compile(r"Unlocks Premium Stone Trade Goods"), "Mở khóa Hàng giao thương đá cao cấp"),
    (re.compile(r"Unlocks Quality Stone Trade Goods"), "Mở khóa Hàng giao thương đá chất lượng"),
    (re.compile(r"Unlocks Stone Trade Goods"), "Mở khóa Hàng giao thương đá"),
    (re.compile(r"Unlocks Premium Gold Trade Goods"), "Mở khóa Hàng giao thương vàng cao cấp"),
    (re.compile(r"Unlocks Quality Gold Trade Goods"), "Mở khóa Hàng giao thương vàng chất lượng"),
    (re.compile(r"Unlocks Gold Trade Goods"), "Mở khóa Hàng giao thương vàng"),
    (re.compile(r"Unlocks Premium Agrarian Trade Goods"), "Mở khóa Hàng giao thương nông sản cao cấp"),
    (re.compile(r"Unlocks Quality Agrarian Trade Goods"), "Mở khóa Hàng giao thương nông sản chất lượng"),
    (re.compile(r"Unlocks Agrarian Trade Goods"), "Mở khóa Hàng giao thương nông sản"),
    (re.compile(r"Unlocks Premium Wooden Trade Goods"), "Mở khóa Hàng giao thương gỗ cao cấp"),
    (re.compile(r"Unlocks Quality Wooden Trade Goods"), "Mở khóa Hàng giao thương gỗ chất lượng"),
    (re.compile(r"Unlocks Wooden Trade Goods"), "Mở khóa Hàng giao thương gỗ"),
    (re.compile(r"Unlocks Premium Metalwork Trade Goods"), "Mở khóa Hàng giao thương kim loại cao cấp"),
    (re.compile(r"Unlocks Quality Metalwork Trade Goods"), "Mở khóa Hàng giao thương kim loại chất lượng"),
    (re.compile(r"Unlocks Metalwork Trade Goods"), "Mở khóa Hàng giao thương kim loại"),
    (re.compile(r"Unlocks Luxury Trade Goods"), "Mở khóa Hàng giao thương xa xỉ"),
    (re.compile(r"Unlocks Quality Luxury Trade Goods"), "Mở khóa Hàng giao thương xa xỉ chất lượng"),
    (re.compile(r"Unlocks Premium Luxury Trade Goods"), "Mở khóa Hàng giao thương xa xỉ cao cấp"),
    (re.compile(r"Unlocks Travellers IV"), "Mở khóa Lữ khách IV"),
    (re.compile(r"Unlocks Travellers III"), "Mở khóa Lữ khách III"),
    (re.compile(r"Unlocks Travellers II"), "Mở khóa Lữ khách II"),
    (re.compile(r"Unlocks Travellers I"), "Mở khóa Lữ khách I"),
    (re.compile(r"Unlocks battle rewards for defeating Demons"), "Mở khóa phần thưởng trận khi đánh bại Quỷ"),
    (re.compile(r"Unlocks battle rewards for defeating Undead"), "Mở khóa phần thưởng trận khi đánh bại Undead"),
    (re.compile(r"Doubles battle loot from Human Enemies"), "Nhân đôi chiến lợi phẩm từ địch là người"),
    (re.compile(r"Upgrades your caravans to large caravans"), "Nâng đoàn buôn lên đoàn lớn"),
    (re.compile(r"Upgrades your caravans to medium caravans"), "Nâng đoàn buôn lên đoàn vừa"),
    (re.compile(r"Constructs a small trading caravan enabling trade expeditions"), "Tạo đoàn buôn nhỏ để mở viễn chinh giao thương"),
    (re.compile(r"Hunting produces a small amount \((%?\d+%?)\) of gold\."), r"Săn bắn tạo thêm một ít vàng (\1)."),
    (re.compile(r"Hunting generates gold \(\+(\d+)% hunting production as gold\)"), r"Săn bắn tạo vàng (+\1% sản lượng săn quy ra vàng)"),
    (re.compile(r"\+(\d+)% more gold from hunting \(\+(\d+)% hunting production as gold\)"), r"+\1% vàng từ săn bắn (+\2% sản lượng săn quy ra vàng)"),
    (re.compile(r"\+(\d+)% hunting production added as gold"), r"+\1% sản lượng săn quy ra vàng"),
    # Shop / unlock templates with numbers
    (
        re.compile(
            r"Unlocks Legendary Building Design \n\[b\]Shop Item:\[/b\] \+(\d+) legendary blueprint design"
        ),
        r"Mở khóa Thiết kế công trình huyền thoại\n[b]Vật phẩm cửa hàng:[/b] +\1 bản thiết kế huyền thoại",
    ),
    (
        re.compile(
            r"Unlocks Master Building Design \n\[b\]Shop Item:\[/b\] \+(\d+) master blueprint design"
        ),
        r"Mở khóa Thiết kế công trình bậc thầy\n[b]Vật phẩm cửa hàng:[/b] +\1 bản thiết kế bậc thầy",
    ),
    (
        re.compile(
            r"Unlocks Expert Building Design \n\[b\]Shop Item:\[/b\] \+(\d+) expert blueprint design"
        ),
        r"Mở khóa Thiết kế công trình chuyên gia\n[b]Vật phẩm cửa hàng:[/b] +\1 bản thiết kế chuyên gia",
    ),
    (
        re.compile(
            r"Unlocks Advanced Building Design \n\[b\]Shop Item:\[/b\] \+(\d+) advanced blueprint design"
        ),
        r"Mở khóa Thiết kế công trình nâng cao\n[b]Vật phẩm cửa hàng:[/b] +\1 bản thiết kế nâng cao",
    ),
    (
        re.compile(
            r"Unlocks Unnatural Growth \n\[b\]Shop Item:\[/b\] \+(\d+)% to all production per Magic Academy level for (\d+) seconds\."
        ),
        r"Mở khóa Tăng trưởng phi tự nhiên\n[b]Vật phẩm cửa hàng:[/b] +\1% mọi sản xuất mỗi cấp Học viện phép trong \2 giây.",
    ),
    (
        re.compile(
            r"Unlocks Stable Portal \n\[b\]Shop Item:\[/b\] Reduce next caravan time by (\d+)%"
        ),
        r"Mở khóa Cổng ổn định\n[b]Vật phẩm cửa hàng:[/b] Giảm \1% thời gian đoàn buôn tiếp theo",
    ),
    (
        re.compile(
            r"Unlocks One Way Portal \n\[b\]Shop Item:\[/b\] Reduce next caravan time by (\d+)%"
        ),
        r"Mở khóa Cổng một chiều\n[b]Vật phẩm cửa hàng:[/b] Giảm \1% thời gian đoàn buôn tiếp theo",
    ),
    (
        re.compile(r"Unlocks Mana Tap \n\[b\]Shop Item:\[/b\] \+(\d+)% magic production"),
        r"Mở khóa Hút mana\n[b]Vật phẩm cửa hàng:[/b] +\1% sản xuất phép thuật",
    ),
    (
        re.compile(r"Unlocks Enchant Weapons I \n\[b\]Shop Item:\[/b\] \+(\d+) soldier attack"),
        r"Mở khóa Phù phép vũ khí I\n[b]Vật phẩm cửa hàng:[/b] +\1 tấn công binh lính",
    ),
    (
        re.compile(r"Unlocks Enchant Armour I \n\[b\]Shop Item:\[/b\] \+(\d+) soldier defence"),
        r"Mở khóa Phù phép giáp I\n[b]Vật phẩm cửa hàng:[/b] +\1 phòng thủ binh lính",
    ),
    (
        re.compile(r"Upgrades Enchant Weapons to level II \(\+(\d+) soldier attack\)"),
        r"Nâng Phù phép vũ khí lên cấp II (+\1 tấn công binh lính)",
    ),
    (
        re.compile(r"Upgrades Enchant Armour to level II \(\+(\d+) soldier defence\)"),
        r"Nâng Phù phép giáp lên cấp II (+\1 phòng thủ binh lính)",
    ),
    # Keep / advisor
    (
        re.compile(r"A Construction Advisor will notify you when you can afford to upgrade a building\."),
        "Cố vấn xây dựng sẽ báo khi bạn đủ tài nguyên để nâng cấp công trình.",
    ),
    (
        re.compile(r"A Research Advisor will notify you when new research is available at a location"),
        "Cố vấn nghiên cứu sẽ báo khi có nghiên cứu mới tại một địa điểm",
    ),
    (re.compile(r"Adds Advisor Shields to all shop locations"), "Thêm khiên cố vấn vào mọi địa điểm cửa hàng"),
    (re.compile(r"Adds Advisor Shields to all policy locations"), "Thêm khiên cố vấn vào mọi địa điểm chính sách"),
    (re.compile(r"Adds Advisor Shields to all trade locations"), "Thêm khiên cố vấn vào mọi địa điểm giao thương"),
    (
        re.compile(r"Inspiration now gives an additional (\d+)% production"),
        r"Cảm hứng giờ thêm +\1% sản xuất",
    ),
    (
        re.compile(r"Gives critical hits a (\d+)% chance to be upgraded to Mega Criticals"),
        r"Đòn chí mạng có \1% cơ hội nâng thành Siêu chí mạng",
    ),
    (
        re.compile(r"Gives a (\d+)% chance of a Critical Success when personally harvesting"),
        r"Có \1% cơ hội Thành công lớn khi tự thu hoạch",
    ),
    (
        re.compile(r"Working at a location gives workers the inspiration buff \(\+(\d+)% Production\)"),
        r"Làm việc tại một địa điểm cho nhân công hiệu ứng cảm hứng (+\1% Sản xuất)",
    ),
    (
        re.compile(r"Inspiration buff stays active for an additional (\d+) seconds"),
        r"Hiệu ứng cảm hứng kéo dài thêm \1 giây",
    ),
    (
        re.compile(r"\+(\d+)% chance of Critical Success when personally harvesting"),
        r"+\1% cơ hội Thành công lớn khi tự thu hoạch",
    ),
    (re.compile(r"Critical hits give \+(\d+)x resources"), r"Đòn chí mạng cho +\1x tài nguyên"),
    (re.compile(r"\+(\d+) Personal Gold Click Power"), r"+\1 Sức click vàng cá nhân"),
    (
        re.compile(r"\+ ?(\d+) personal click power to all resource gathering"),
        r"+\1 sức click cá nhân cho mọi thu hoạch tài nguyên",
    ),
    (re.compile(r"\+ ?(\d+) personal clicks per second"), r"+\1 click cá nhân mỗi giây"),
    (
        re.compile(r"\+ ?(\d+)% personal resource gathering power"),
        r"+\1% sức thu hoạch tài nguyên cá nhân",
    ),
    # Population / starvation debuff
    (
        re.compile(
            r"-(\d+)% Happiness \n\+(\d+)% food production \nPopulation Declining"
        ),
        r"-\1% Hạnh phúc\n+\2% sản xuất lương thực\nDân số đang giảm",
    ),
    (re.compile(r"Population Declining"), "Dân số đang giảm"),
    # Guard combat packages
    (
        re.compile(
            r"\+(\d+(?:\.\d+)?) Attack Damage, \+(\d+(?:\.\d+)?) Combat Defence, \+(\d+(?:\.\d+)?) Gold upkeep per soldier, \+(\d+(?:\.\d+)?) Food upkeep per soldier"
        ),
        r"+\1 Sát thương tấn công, +\2 Phòng thủ chiến đấu, +\3 chi phí duy trì Vàng mỗi binh, +\4 chi phí duy trì Lương thực mỗi binh",
    ),
    (
        re.compile(
            r"\+(\d+(?:\.\d+)?) Attack Damage, \+(\d+(?:\.\d+)?) Iron and Gold and \+(\d+(?:\.\d+)?) Magic upkeep per soldier"
        ),
        r"+\1 Sát thương tấn công, +\2 chi phí duy trì Sắt và Vàng và +\3 Phép thuật mỗi binh",
    ),
    (
        re.compile(
            r"\+(\d+(?:\.\d+)?) Combat Defence, \+(\d+(?:\.\d+)?) Iron and Gold and \+(\d+(?:\.\d+)?) Magic upkeep per soldier"
        ),
        r"+\1 Phòng thủ chiến đấu, +\2 chi phí duy trì Sắt và Vàng và +\3 Phép thuật mỗi binh",
    ),
    (
        re.compile(
            r"\+(\d+(?:\.\d+)?) Attack Damage, \+(\d+(?:\.\d+)?) Combat Defence, \+(\d+(?:\.\d+)?) Gold, \+(\d+(?:\.\d+)?) Food and \+(\d+(?:\.\d+)?) Magic upkeep per soldier"
        ),
        r"+\1 Sát thương tấn công, +\2 Phòng thủ chiến đấu, +\3 Vàng, +\4 Lương thực và +\5 Phép thuật chi phí duy trì mỗi binh",
    ),
    (
        re.compile(
            r"\+(\d+(?:\.\d+)?) Attack Damage, \+(\d+(?:\.\d+)?) Iron and Gold upkeep per soldier"
        ),
        r"+\1 Sát thương tấn công, +\2 chi phí duy trì Sắt và Vàng mỗi binh",
    ),
    (
        re.compile(
            r"\+(\d+(?:\.\d+)?) Combat Defence, \+(\d+(?:\.\d+)?) Iron and Gold upkeep per soldier"
        ),
        r"+\1 Phòng thủ chiến đấu, +\2 chi phí duy trì Sắt và Vàng mỗi binh",
    ),
    # Item / timed buffs
    (re.compile(r"Double Soldier Training Speed\nDouble Soldier Training Cost"), "Gấp đôi tốc độ huấn luyện binh lính\nGấp đôi chi phí huấn luyện binh lính"),
    (
        re.compile(r"Reduce the next caravan time by (\d+)% if sent within (\d+) seconds"),
        r"Giảm \1% thời gian đoàn buôn tiếp theo nếu gửi trong \2 giây",
    ),
    (
        re.compile(r"\+(\d+)% to all production per Magic Academy level for (\d+) seconds\."),
        r"+\1% mọi sản xuất mỗi cấp Học viện phép trong \2 giây.",
    ),
    (re.compile(r"\+(\d+) and \+(\d+)% to fishing for (\d+) seconds\."), r"+\1 và +\2% đánh cá trong \3 giây."),
    (re.compile(r"\+(\d+) to Soldier Defence for (\d+) seconds"), r"+\1 Phòng thủ binh lính trong \2 giây"),
    (re.compile(r"\+(\d+) soldier defence for (\d+) seconds"), r"+\1 phòng thủ binh lính trong \2 giây"),
    (re.compile(r"\+(\d+) soldier attack for (\d+) seconds"), r"+\1 tấn công binh lính trong \2 giây"),
    (re.compile(r"\+(\d+)% to all production for (\d+) seconds"), r"+\1% mọi sản xuất trong \2 giây"),
    (re.compile(r"\+(\d+)% food production for (\d+) seconds"), r"+\1% sản xuất lương thực trong \2 giây"),
    (re.compile(r"\+(\d+)% magic production for (\d+) seconds"), r"+\1% sản xuất phép thuật trong \2 giây"),
    (re.compile(r"\+(\d+)% happiness bonus for (\d+) seconds"), r"+\1% hạnh phúc trong \2 giây"),
    (re.compile(r"\+(\d+)% iron for (\d+) seconds"), r"+\1% sắt trong \2 giây"),
    (re.compile(r"\+(\d+)% stone for (\d+) seconds"), r"+\1% đá trong \2 giây"),
    (re.compile(r"\+(\d+)% wood for (\d+) seconds"), r"+\1% gỗ trong \2 giây"),
    (re.compile(r"\+(\d+)% gold for (\d+) seconds"), r"+\1% vàng trong \2 giây"),
    (re.compile(r"\+(\d+)% farm(?:ing)? for (\d+) seconds"), r"+\1% nông trại trong \2 giây"),
    (re.compile(r"\+(\d+) Advanced Blueprint"), r"+\1 Bản thiết kế nâng cao"),
    (re.compile(r"\+(\d+) Expert Blueprint"), r"+\1 Bản thiết kế chuyên gia"),
    (re.compile(r"\+(\d+) Legendary Blueprint"), r"+\1 Bản thiết kế huyền thoại"),
    (re.compile(r"\+(\d+) Master Blueprint"), r"+\1 Bản thiết kế bậc thầy"),
    # ACH short lines
    (re.compile(r"Complete the game on Challenging difficulty\."), "Hoàn thành game ở độ khó Thử thách."),
    (re.compile(r"Complete the game on Gentle difficulty\."), "Hoàn thành game ở độ khó Nhẹ nhàng."),
    (re.compile(r"Complete the game on Intense difficulty\."), "Hoàn thành game ở độ khó Khốc liệt."),
    (re.compile(r"Complete the game on Steady difficulty\."), "Hoàn thành game ở độ khó Ổn định."),
    (re.compile(r"Defeat the Ashenholt Army\."), "Đánh bại quân Ashenholt."),
    (re.compile(r"Encounter your first enemy\."), "Gặp quân địch đầu tiên."),
    (re.compile(r"Trade with a Distant Settlement for the first time\."), "Giao thương lần đầu với một Khu định cư xa."),
    (re.compile(r"Win the game without suffering any defeats\."), "Thắng game mà không thua trận nào."),
    (re.compile(r"Fully upgrade your city\."), "Nâng cấp thành phố đến tối đa."),
    (re.compile(r"Be crowned rulers of a new kingdom\."), "Được đội vương miện làm vua của vương quốc mới."),
    (re.compile(r"Reach a happiness of (\d+)%"), r"Đạt hạnh phúc \1%"),
    (re.compile(r"Complete the game without ever trading with Ashenholt\."), "Hoàn thành game mà không bao giờ giao thương với Ashenholt."),
    (re.compile(r"Recruit a Wizard\."), "Tuyển một Pháp sư."),
    (re.compile(r"Research Blueprints\."), "Nghiên cứu Bản thiết kế."),
    (re.compile(r"Set up Camp\."), "Dựng Trại."),
    (re.compile(r"Upgrade to Stone Walls\."), "Nâng cấp lên Tường đá."),
    (re.compile(r"Survive the Zombie Plague\."), "Sống sót qua Dịch zombie."),
    (re.compile(r"Build a Gold Mine\."), "Xây một Mỏ vàng."),
    (re.compile(r"Build the Chief's Hut"), "Xây Nhà trưởng làng"),
    (re.compile(r"Build a Keep\."), "Xây một Pháo đài."),
    (re.compile(r"Reach a population of (\d+)"), r"Đạt dân số \1"),
    (re.compile(r"Monsters spawn (\d+)% less frequently"), r"Quái xuất hiện ít hơn \1%"),
    # Storage / workers / production generics (after specific unlocks)
    (re.compile(r"\+ ?([\d,\.]+) food, wood, stone, and iron storage\."), r"+\1 kho lương thực, gỗ, đá và sắt."),
    (re.compile(r"\+([\d,\.]+) food, wood, stone, and iron storage\."), r"+\1 kho lương thực, gỗ, đá và sắt."),
    (re.compile(r"\+ ?([\d,\.]+) food storage capacity"), r"+\1 dung lượng kho lương thực"),
    (re.compile(r"\+ ?([\d,\.]+) magic storage capacity"), r"+\1 dung lượng kho phép thuật"),
    (re.compile(r"\+ ?([\d,\.]+) gold storage capacity"), r"+\1 dung lượng kho vàng"),
    (re.compile(r"\+ ?([\d,\.]+) iron storage capacity"), r"+\1 dung lượng kho sắt"),
    (re.compile(r"\+ ?([\d,\.]+) stone storage capacity"), r"+\1 dung lượng kho đá"),
    (re.compile(r"\+ ?([\d,\.]+) wood storage capacity"), r"+\1 dung lượng kho gỗ"),
    (re.compile(r"\+ ?([\d,\.]+) max farm workers"), r"+\1 nhân công nông trại tối đa"),
    (re.compile(r"\+ ?([\d,\.]+) max fishing workers"), r"+\1 nhân công đánh cá tối đa"),
    (re.compile(r"\+ ?([\d,\.]+) max hunting workers"), r"+\1 nhân công săn bắn tối đa"),
    (re.compile(r"\+ ?([\d,\.]+) max gold workers"), r"+\1 nhân công vàng tối đa"),
    (re.compile(r"\+ ?([\d,\.]+) max iron workers"), r"+\1 nhân công sắt tối đa"),
    (re.compile(r"\+ ?([\d,\.]+) max stone workers"), r"+\1 nhân công đá tối đa"),
    (re.compile(r"\+ ?([\d,\.]+) max wood workers"), r"+\1 nhân công gỗ tối đa"),
    (re.compile(r"\+ ?([\d,\.]+) max magic workers"), r"+\1 nhân công phép thuật tối đa"),
    (re.compile(r"\+([\d,\.]+)% caravan speed"), r"+\1% tốc độ đoàn buôn"),
    (re.compile(r"\+([\d,\.]+) max caravan quantity"), r"+\1 số đoàn buôn tối đa"),
    (re.compile(r"\+ ?([\d,\.]+)% ship speed"), r"+\1% tốc độ tàu"),
    (re.compile(r"\+ ?([\d,\.]+)% birth rate speed"), r"+\1% tốc độ sinh"),
    (re.compile(r"\+ ?([\d,\.]+)% happiness bonus"), r"+\1% hạnh phúc"),
    (re.compile(r"\+ ?([\d,\.]+) soldier attack damage"), r"+\1 sát thương tấn công binh lính"),
    (re.compile(r"\+ ?([\d,\.]+) soldier defence"), r"+\1 phòng thủ binh lính"),
    (re.compile(r"\+ ?([\d,\.]+) max population"), r"+\1 dân số tối đa"),
    (re.compile(r"\+ ?([\d,\.]+) extra wood production"), r"+\1 sản xuất gỗ thêm"),
    (re.compile(r"\+ ?([\d,\.]+) extra gold production"), r"+\1 sản xuất vàng thêm"),
    (re.compile(r"\+ ?([\d,\.]+) extra wood and stone production"), r"+\1 sản xuất gỗ và đá thêm"),
    (re.compile(r"\+ ?([\d,\.]+) extra wood, stone, and iron production"), r"+\1 sản xuất gỗ, đá và sắt thêm"),
    (re.compile(r"\+ ?([\d,\.]+) global resource harvesting"), r"+\1 thu hoạch tài nguyên toàn cục"),
    (
        re.compile(r"\+ ?([\d,\.]+)% to all production \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% mọi sản xuất\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% to magic production \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% sản xuất phép thuật\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% resource gathering \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% thu hoạch tài nguyên\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% fishing production \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% sản xuất đánh cá\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% farm production \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% sản xuất nông trại\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% gold production \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% sản xuất vàng\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% iron production \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% sản xuất sắt\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% stone production \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% sản xuất đá\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% wood production \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% sản xuất gỗ\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% magic production \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% sản xuất phép thuật\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+ ?([\d,\.]+)% hunting efficiency \n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% hiệu suất săn bắn\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+([\d,\.]+)% Farm Production\n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% Sản xuất nông trại\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+([\d,\.]+)% Fishing Production\n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% Sản xuất đánh cá\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+([\d,\.]+)% Hunting Production\n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% Sản xuất săn bắn\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+([\d,\.]+)% Gold Production\n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% Sản xuất vàng\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+([\d,\.]+)% Iron Production\n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% Sản xuất sắt\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+([\d,\.]+)% Stone Production\n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% Sản xuất đá\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+([\d,\.]+)% Wood Production\n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% Sản xuất gỗ\n[b](\2)[/b]",
    ),
    (
        re.compile(r"\+([\d,\.]+)% Magic Production\n\[b\]\(([^)]+)\)\[/b\]"),
        r"+\1% Sản xuất phép thuật\n[b](\2)[/b]",
    ),
]


def translate_formulaic(en: str) -> str | None:
    """Return VI if every English word-ish leftover is gone enough; else None if still looks English."""
    text = en
    for pattern, repl in _PHRASE_RULES:
        text = pattern.sub(repl, text)
    # Heuristic: if still contains common English leftover tokens, treat as incomplete
    leftovers = (
        "Unlocks ",
        "Upgrades ",
        " production",
        "Multiplier",
        "soldier ",
        "workers",
        "storage capacity",
        "Shop Item",
        "Build a ",
        "Complete the",
        "Reach a ",
        "Trade with",
        "Hunting ",
        "Critical ",
        "Inspiration ",
        "Advisor",
        "caravan",
        "blueprint",
        "seconds",
        "Defence",
        "Attack Damage",
        "Combat Defence",
        "upkeep",
        "Population ",
        "happiness bonus",
        "birth rate",
        "resource gathering",
        "Personal Gold",
        "max population",
        "extra wood",
        "global resource",
        "Monsters spawn",
        "Travellers",
        "Trade Goods",
    )
    if any(token in text for token in leftovers):
        return None
    if text == en:
        # unchanged short labels may still be OK if we handle via name map
        return None
    return text
