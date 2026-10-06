# -*- coding: utf-8 -*-
"""Explicit key→VI for drafts not covered by name/formulaic engines."""
from __future__ import annotations

BY_KEY: dict[str, str] = {
    # --- misc labels ---
    "%s to %s: Trading %s for %s": "%s đến %s: Đổi %s lấy %s",
    "ACH_TRADE_20_DES": "Giao thương với Vương quốc xa 20 lần.",
    "ACH_UNLOCK_MAGIC_SWAMP_DES": "Mở khóa Đầm phép thuật.",
    "ANKHET-NAR": "Ankhet-Nar",
    "ASHENHOLT": "Ashenholt",
    "CHURCH_CHARITY": "Từ thiện nhà thờ",
    "CRIMSONVALE": "Crimsonvale",
    "EVENT_ARCHIVE": "Kho sự kiện",
    "Efficiency": "Hiệu suất",
    "FANGMIRE": "Fangmire",
    "FARMS": "Nông trại",
    "FISHING": "Đánh cá",
    "FOOD_SECURITY": "An ninh lương thực",
    "Farm Extras": "Cộng thêm nông trại",
    "Fishing Extras": "Cộng thêm đánh cá",
    "GLOBAL_HUNGRY": "Hệ số đói",
    "GROWTH_HIGH": "Cao",
    "GROWTH_MEDIUM": "Trung bình",
    "GROWTH_NONE": "Không",
    "GROWTH_SMALL": "Nhỏ",
    "Gold Extras": "Cộng thêm vàng",
    "HIGH_FOOD_BONUS": "Thưởng lương thực cao",
    "HOUSING_CAPACITY": "Sức chứa nhà ở",
    "HOUSING_FULL": "Nhà ở đã đầy",
    "HUNTING": "Săn bắn",
    "Hunting Extras": "Cộng thêm săn bắn",
    "IRONREND": "Ironrend",
    "Inspiration": "Cảm hứng",
    "Iron Extras": "Cộng thêm sắt",
    "Items": "Vật phẩm",
    "LEADERSHIP": "Lãnh đạo",
    "LUXURIES": "Xa xỉ phẩm",
    "MAXIMUM_REACHED": "Đã đạt tối đa 200%",
    "MEDIUM_FOOD_BONUS": "Thưởng lương thực vừa",
    "MINIMUM_REACHED": "Đã đạt tối thiểu 50%",
    "Magic Extras": "Cộng thêm phép thuật",
    "NEW_PEOPLE": "dân mới",
    "NO_FOOD_BONUS": "Không thưởng lương thực",
    "ONGOING_EFFECT": "Đang duy trì",
    "POPULATION_GROWTH": "Tăng dân số",
    "POPULATION_GROWTH_BONUS": "Thưởng tăng dân số",
    "PRODUCTION_BONUS": "Thưởng sản xuất",
    "PRODUCTION_PENALTY": "Phạt sản xuất",
    "Per Worker": "Mỗi nhân công",
    "RUBESCAIRN": "Rubescairn",
    "RUBESCAIRN_TRADE_AGREEMENT": "Hiệp ước giao thương Rubescairn",
    "Research": "Nghiên cứu",
    "SANITATION": "Vệ sinh",
    "SANITATION_MULTIPLIER": "Vệ sinh",
    "SEPHIRAH": "Sephirah",
    "SHIP": "Tàu",
    "SMALL_FOOD_BONUS": "Thưởng lương thực nhỏ",
    "SNIKTCRAG": "Sniktcrag",
    "STARVATION_LEVEL": "Mức nạn đói: %d/5\n-%d%% Hạnh phúc\nDân số đang giảm",
    "Select options to see cost.": "Chọn tùy chọn để xem chi phí.",
    "Stone Extras": "Cộng thêm đá",
    "Storage": "Kho chứa",
    "TABLE_OF_CONTENTS": "Mục lục",
    "TAXES_TITHES": "Thuế/Thập phân",
    "TAX_BREAK": "Giảm thuế",
    "TOTAL_ATTACK": "Tổng tấn công",
    "TOTAL_HP": "Tổng HP",
    "TOTAL_UPKEEP": "Tổng chi phí duy trì",
    "TOTAL_WORKERS": "Tổng nhân công",
    "Tools": "Trang bị",
    "Total Consumption": "Tổng tiêu thụ",
    "Total Production": "Tổng sản xuất",
    "WISHLIST": "Thêm vào wishlist!",
    "Wood Extras": "Cộng thêm gỗ",
    "cargo": "hàng hóa",
    "supplies": "tiếp tế",
    "wages": "tiền công",
    "✦ INSPIRED! ✦": "✦ CẢM HỨNG! ✦",
    # --- LOC ---
    "LOC_ALCHEMIST": "Giả kim",
    "LOC_BLACKSMITH": "Lò rèn",
    "LOC_CARPENTER": "Thợ mộc",
    "LOC_CHURCH": "Nhà thờ",
    "LOC_CLIFF": "Vách đá",
    "LOC_DOCKS": "Bến cảng",
    "LOC_FARM": "Nông trại",
    "LOC_FISHING": "Lều đánh cá",
    "LOC_GOLD_MINE": "Cầu dây",
    "LOC_HOUSES": "Nhà ở",
    "LOC_HUNTING": "Săn bắn",
    "LOC_IRON_MINE": "Mỏ sắt",
    "LOC_KEEP": "Nhà trưởng làng",
    "LOC_LEATHER": "Xưởng",
    "LOC_LIBRARY": "Thư viện",
    "LOC_LUMBER": "Gỗ",
    "LOC_MAGIC": "Phế tích",
    "LOC_MARKET": "Chợ",
    "LOC_MILITARY_CAMP": "Trại quân",
    "LOC_NORTHERN_WALL": "Tường Bắc",
    "LOC_QUARRY": "Mỏ đá",
    "LOC_RENAME_CASTLE": "Lâu đài",
    "LOC_RENAME_DOCKS": "Xưởng đóng tàu",
    "LOC_RENAME_GOLD": "Mỏ vàng",
    "LOC_RENAME_HARBOR": "Khu cảng",
    "LOC_RENAME_KEEP": "Pháo đài",
    "LOC_RENAME_LIBRARY": "Trường học",
    "LOC_RENAME_MAGIC_ACADEMY": "Học viện phép thuật",
    "LOC_RENAME_MANOR": "Dinh quý tộc",
    "LOC_RENAME_MAYORS_HOUSE": "Nhà thị trưởng",
    "LOC_RENAME_SWAMP": "Đầm lầy",
    "LOC_RENAME_TAVERN": "Quán rượu",
    "LOC_RENAME_TOWN_SQUARE": "Quảng trường thị trấn",
    "LOC_RENAME_UNIVERSITY": "Đại học",
    "LOC_ROAD": "Đường",
    "LOC_SOUTHERN_WALL": "Tường Nam",
    "LOC_SWAMP": "Cầu đầm lầy",
    "LOC_TAVERN": "Quán công cộng",
    "LOC_TOWN_GUARDS": "Vệ binh thị trấn",
    "LOC_TOWN_SQUARE": "Trại",
    "LOC_WAREHOUSE": "Kho",
    # --- world map ---
    "WORLD_MAP_DEMAND_HIGH": "Nhu cầu cao",
    "WORLD_MAP_DEMAND_INCREASED": "Nhu cầu tăng",
    "WORLD_MAP_DEMAND_LOW": "Nhu cầu thấp",
    "WORLD_MAP_DEMAND_NORMAL": "Nhu cầu bình thường",
    "WORLD_MAP_DEMAND_REDUCED": "Nhu cầu giảm",
    "WORLD_MAP_DEMAND_UNKNOWN": "Nhu cầu không rõ",
    "WORLD_MAP_DEMAND_VERY_HIGH": "Nhu cầu rất cao",
    "WORLD_MAP_DEMAND_VERY_LOW": "Nhu cầu rất thấp",
    "WORLD_MAP_NO_RESOURCE_DEMANDS": "Không có nhu cầu tài nguyên",
    # --- remaining DES / items / debuffs ---
    "ALCHEMIST_IMPROVEMENT_1_DES": "+1 sản xuất cá, nông trại và săn bắn thêm",
    "ALCHEMIST_IMPROVEMENT_3_DES": "Mở khóa Thuốc tìm sắt\n[b]Vật phẩm cửa hàng:[/b] +50% sắt trong 120 giây",
    "ALCHEMIST_IMPROVEMENT_4_DES": "Mở khóa Bột phá đá\n[b]Vật phẩm cửa hàng:[/b] +50% đá trong 120 giây",
    "ALCHEMIST_IMPROVEMENT_6_DES": "Mở khóa Thuốc tìm vàng\n[b]Vật phẩm cửa hàng:[/b] +50% vàng trong 120 giây",
    "ALCHEMIST_IMPROVEMENT_8_DES": "Mở khóa Thuốc hồi máu\n[b]Vật phẩm cửa hàng:[/b] +30% binh lính hồi phục sau trận trong 120 giây",
    "ALCHEMIST_IMPROVEMENT_10_DES": "Mở khóa Đại chuyển hóa\n[b]Vật phẩm cửa hàng:[/b] Đổi sắt thành vàng",
    "ALCHEMIST_IMPROVEMENT_11_DES": "Mở khóa phần thưởng trận khi đánh bại Quái thực vật",
    "BLACKSMITH_IMPROVEMENT_19_DES": "Mở khóa phần thưởng trận từ Goblin bằng cách luyện lại kim loại goblin thô",
    "BLACKSMITH_IMPROVEMENT_20_DES": "Mở khóa phần thưởng trận từ Orc bằng cách luyện lại kim loại orc tha hóa",
    "CHURCH_IMPROVEMENT_1_DES": "Mở khóa Phước lành thiên đường\n[b]Vật phẩm cửa hàng:[/b] +3 sản xuất đánh cá thêm trong 120 giây",
    "CHURCH_IMPROVEMENT_3_DES": "Mở khóa Bếp từ thiện\n[b]Chính sách:[/b] +10% hạnh phúc, +20% tiêu thụ lương thực",
    "CHURCH_IMPROVEMENT_4_DES": "Mở khóa Thập phân\n[b]Chính sách:[/b] -20% hạnh phúc, +1 vàng mỗi 15 dân mỗi giây",
    "CHURCH_IMPROVEMENT_5_DES": "Mở khóa Cầu nguyện cầu bầu\n[b]Vật phẩm cửa hàng:[/b] +50% sản xuất lương thực trong 120 giây",
    "CHURCH_IMPROVEMENT_6_DES": "Mở khóa Bố thí người nghèo\n[b]Chính sách:[/b] +10% hạnh phúc, +10% tiêu thụ lương thực. Chi phí vàng nhỏ theo dân số",
    "CHURCH_IMPROVEMENT_8_DES": "Mở khóa Phục vụ cộng đồng\n[b]Chính sách:[/b] +15% hạnh phúc, +15% tiêu thụ lương thực. Chi phí vàng vừa theo dân số",
    "CHURCH_IMPROVEMENT_9_DES": "Mở khóa Phước lành bảo hộ\n[b]Vật phẩm cửa hàng:[/b] +10 phòng thủ binh lính trong 120 giây",
    "CHURCH_IMPROVEMENT_11_DES": "Mở khóa An sinh xã hội\n[b]Chính sách:[/b] +20% hạnh phúc, +20% tiêu thụ lương thực. Chi phí vàng lớn theo dân số",
    "CHURCH_IMPROVEMENT_12_DES": "Mở khóa Thiên sứ can thiệp\n[b]Vật phẩm cửa hàng:[/b] +50% mọi sản xuất",
    "CHURCH_IMPROVEMENT_14_DES": "+20% Sát thương lên Undead\nNgăn Undead hồi sinh",
    "DEBUFF_ANCIENT_EVIL_DESCRIPTION": "-40% Hạnh phúc\nNgười chết bước đi",
    "DEBUFF_RECENTLY_RAIDED_DESCRIPTION": "-50% Hạnh phúc\n-20% Hiệu suất",
    "DOCKS_IMPROVEMENT_4_DES": "Mở khóa viễn chinh giao thương bằng tàu vừa",
    "DOCKS_IMPROVEMENT_7_DES": "Mở khóa viễn chinh giao thương bằng tàu lớn",
    "GUARDS_IMPROVEMENT_1_DES": "+1 Sát thương tấn công, +0.5 chi phí duy trì Sắt mỗi binh",
    "GUARDS_IMPROVEMENT_2_DES": "+4 Phòng thủ chiến đấu, +1 chi phí duy trì Lương thực mỗi binh",
    "GUARDS_IMPROVEMENT_16_DES": "Mở khóa khả năng Hiệu triệu quân, tạm thời gấp đôi tốc độ huấn luyện binh với gấp đôi chi phí tài nguyên thường.\n[b](Nút Quân sự)[/b]",
    "HUNTING_IMPROVEMENT_7_DES": "Nhận thêm thông tin về quân địch sắp tới",
    "HUNTING_IMPROVEMENT_11_DES": "Nhận thông tin chính xác về quân địch sắp tới",
    "HUNTING_IMPROVEMENT_18_DES": "Mở khóa phần thưởng trận khi đánh bại Động vật",
    "ITEM_ALCHEMIST_CONVERT_IRON_TO_GOLD_DESCRIPTION": "Đổi sắt thành vàng",
    "ITEM_ALCHEMIST_GOLD_FINDING_POTION_DESCRIPTION": "+50% sản xuất vàng trong 120 giây",
    "ITEM_ALCHEMIST_HEALING_POTIONS_DESCRIPTION": "+30% binh lính hồi phục sau trận trong 120 giây",
    "SPIRIT_OF_JUSTICE_DESCRIPTION": "-20% chi phí huấn luyện và duy trì binh lính\n\nDân của bạn hăng hái đứng lên chống bất công.",
    # --- quest UI ---
    "QUEST_ACCEPT": "Chấp nhận",
    "QUEST_NEXT": "Tiếp",
    "QUEST_LOG_ALL_QUESTS_COMPLETED": "Đã hoàn thành mọi nhiệm vụ",
    "QUEST_LOG_CLOSE": "Đóng",
    "QUEST_LOG_CONGRATULATIONS": "Chúc mừng! Bạn đã hoàn thành mọi nhiệm vụ chính.",
    "QUEST_LOG_INVALID_QUEST": "Đã hoàn thành mọi nhiệm vụ hoặc số nhiệm vụ không hợp lệ.",
    "QUEST_LOG_MAIN_BUTTON": "Nhiệm vụ",
    "QUEST_LOG_NO_ADDITIONAL_REQUIREMENTS": "Nhiệm vụ đã xong.\n Nhấn Hoàn thành để kết thúc game!",
    "QUEST_LOG_NO_QUEST_AVAILABLE": "Không có nhiệm vụ",
    "QUEST_LOG_READY_TO_COMPLETE": "Sẵn sàng hoàn thành game!",
    "QUEST_LOG_REQ_CHURCH_LEVEL": "Cấp nhà thờ %d",
    "QUEST_LOG_REQ_KEEP_LEVEL": "Cấp pháo đài %d",
    "QUEST_LOG_REQ_LIBRARY_LEVEL": "Cấp đại học %d",
    "QUEST_LOG_REQ_SOLDIERS": "Binh lính %d",
    "QUEST_LOG_REQ_SPARE_SHIP": "Có tàu dự phòng (%d)",
    "QUEST_LOG_REQ_TAVERN_LEVEL": "Cấp quán rượu %d",
    "QUEST_LOG_REQ_TOWN_GUARDS_LEVEL": "Cấp vệ binh thị trấn %d",
    "QUEST_LOG_VIEW_DETAILS": "Xem chi tiết",
    "QUEST_WARNING_PROCEED": "Tiến tới chiến thắng!",
    "QUEST_WARNING_RETURN": "Ta phải chuẩn bị thêm",
    "QUEST_WARNING_TITLE": "Cảnh báo! Nhiệm vụ nguy hiểm",
    "QUEST_WARNING_TEXT": (
        "Thưa Ngài và Phu nhân, trận này chắc chắn sẽ quyết định số phận chúng ta. "
        "Tường thành vững và binh lính đông, nhưng liệu chúng ta đã sẵn sàng chống lại quân Ashenholt đáng khinh?\n\n"
        "(Không thể lưu game trong nhiệm vụ này)"
    ),
    # --- quest objectives ---
    "QUEST_OBJECTIVE1A": "Dựng trại",
    "QUEST_OBJECTIVE1B": "Dựng trại",
    "QUEST_OBJECTIVE2": "Cải thiện trại",
    "QUEST_OBJECTIVE3": "Thu thập lương thực và mở rộng trại",
    "QUEST_OBJECTIVE4": "Xây Lều ngư dân và Lều tiều phu",
    "QUEST_OBJECTIVE5": "Đạt 50 dân số",
    "QUEST_OBJECTIVE6": "Xây Quảng trường thị trấn và đạt 100 dân số",
    "QUEST_OBJECTIVE7": "Đạt 200 dân số",
    "QUEST_OBJECTIVE8": "Xây nhà canh và huấn luyện 5 vệ binh",
    "QUEST_OBJECTIVE9": "Bảo vệ làng",
    "QUEST_OBJECTIVE10A": "Đáp ứng đòi hỏi của binh sĩ",
    "QUEST_OBJECTIVE10B": "Lấy vàng bên kia sông và đáp ứng đòi hỏi của binh sĩ",
    "QUEST_OBJECTIVE11": "Đạt 400 dân số",
    "QUEST_OBJECTIVE12": "Sở hữu bản đầy đủ của Hearth and Hamlet",
    "QUEST_OBJECTIVE13": "Xây Tường Bắc và Tường Nam",
    "QUEST_OBJECTIVE14": "Đáp ứng đòi hỏi của Ashenholt",
    "QUEST_OBJECTIVE15": "Giao thương với các khu định cư xa",
    "QUEST_OBJECTIVE16": "Nâng cấp Thư viện và nghiên cứu Bản thiết kế",
    "QUEST_OBJECTIVE17": "Đáp ứng đòi hỏi của Ashenholt",
    "QUEST_OBJECTIVE18": "Nâng cấp lên Tường đá",
    "QUEST_OBJECTIVE19": "Đóng tàu và tuyển pháp sư từ Rubescairn",
    "QUEST_OBJECTIVE20": "Bắt đầu giao thương lương thực lâu dài với Rubescairn",
    "QUEST_OBJECTIVE21": "Xây Cầu đầm lầy, giao thương lấy phép thuật, rồi xây Đầm phù thủy trong đầm.",
    "QUEST_OBJECTIVE22": "Khai quật phế tích và xây Học viện phép thuật",
    "QUEST_OBJECTIVE23": "Đạt 1200 dân số",
    "QUEST_OBJECTIVE24": "Tuyển tổng cộng 120 binh lính",
    "QUEST_OBJECTIVE25": "Đánh bại quân Ashenholt",
    "QUEST_OBJECTIVE26": "Duy trì 120 binh lính và nâng Dinh quý tộc thành Pháo đài",
    "QUEST_OBJECTIVE27": "Xây Nhà thờ lớn và dùng để nghiên cứu Vũ khí thánh hóa",
    "QUEST_OBJECTIVE28": "Nâng Quán rượu lên Lò sưởi Rồng và thuê Anh hùng",
    "QUEST_OBJECTIVE29": "Đạt 1600 dân số",
    "QUEST_OBJECTIVE30B": "Xây Đại học và chuẩn bị sứ giả",
    "QUEST_OBJECTIVE31B": "Xây Đại giáo đường và chuẩn bị sứ giả",
    "QUEST_OBJECTIVE32B": "Xây Đồn hoàng gia và chuẩn bị sứ giả",
    "QUEST_OBJECTIVE33B": "Xây Lâu đài và gia cố tường bằng Hào nước",
    "QUEST_OBJECTIVE34": "Sống trong hòa bình và thịnh vượng",
    # --- quest narrative ---
    "QUEST_DESCRIPTION1A": (
        "Ngày xưa, khi chiến tranh tàn phá vùng đất phía nam, ba người tị nạn chạy lên miền bắc hoang dã. "
        "Chỉ mang theo mất mát và hy vọng mong manh, họ tìm kiếm sự bình yên và một nơi yên tĩnh để bắt đầu lại."
    ),
    "QUEST_DESCRIPTION1B": (
        "Sau hành trình dài và nguy hiểm, nhóm phát hiện một nơi thanh bình và quyết định dựng trại nghỉ ngơi."
    ),
    "QUEST_DESCRIPTION2": (
        "Nơi này dường như có đủ mọi thứ: nước chảy trong lành, đất màu mỡ, và chẳng thấy quái vật nào. "
        "Ở lại lâu hơn là quyết định dễ dàng."
    ),
    "QUEST_DESCRIPTION3": (
        "Chẳng bao lâu trại đã dễ chịu hơn nhiều, nhưng thêm người tị nạn đang tới và không đủ lương thực cho mọi người. "
        "May thay, sông gần đó đầy cá, và rừng phía bắc có nhiều thú săn."
    ),
    "QUEST_DESCRIPTION4": (
        "Không muốn từ chối ai, trại đang lớn nhanh chóng đầy ắp. Chúng ta cần thêm gỗ và lương thực để mở rộng."
    ),
    "QUEST_DESCRIPTION5": (
        "Với đủ lương thực và gỗ, cộng đồng nhỏ của chúng ta đang lớn rất nhanh."
    ),
    "QUEST_DESCRIPTION6": (
        "Trại khiêm tốn không còn đủ cho cộng đồng đang lớn. Chúng ta quyết định thay bằng quảng trường thị trấn "
        "để gắn kết khu định cư và chào đón người tị nạn mới."
    ),
    "QUEST_DESCRIPTION7": (
        "Với đủ lương thực và gỗ, trại nhỏ nhanh chóng trở thành một thôn ấp thịnh vượng."
    ),
    "QUEST_DESCRIPTION8": (
        "Khi thôn ấp nở rộ, rắc rối cũng theo đến. Chẳng bao lâu chúng ta gặp những sinh vật hung dữ trong vùng, "
        "và quyết định cần vệ binh để bảo vệ."
    ),
    "QUEST_DESCRIPTION9": (
        "Khi đi kiếm đồ trong rừng, một đôi trẻ phát hiện một nhóm goblin nhỏ đang tiến về thị trấn. "
        "Chúng ta chỉ còn ít thời gian để sẵn sàng!"
    ),
    "QUEST_DESCRIPTION10A": (
        "Ngay sau cuộc chạm trán với goblin, binh sĩ từ quê cũ Ashenholt đến đòi chúng ta nộp thuế. "
        "Chúng ta đã bỏ Ashenholt để tránh chiến tranh bất tận và tham nhũng, nhưng chưa đủ sức chống lại họ."
    ),
    "QUEST_DESCRIPTION10B": (
        "Là cộng đồng nghèo với ít của cải, Ashenholt chẳng mong chúng ta đáp ứng đòi hỏi thái quá. "
        "Họ chỉ muốn tống tiền và kiểm soát. Ít ai biết dấu vết vàng đã được tìm thấy ở phía bắc, bên kia sông."
    ),
    "QUEST_DESCRIPTION11": (
        "Rõ ràng ngạc nhiên vì chúng ta đã trả được đòi hỏi thái quá, binh sĩ Ashenholt rút đi. "
        "Đồng thời, mỏ vàng mới tìm thấy mang lại thịnh vượng mới cho dân làng."
    ),
    "QUEST_DESCRIPTION12": (
        "Cảm ơn bạn đã chơi bản demo Hearth and Hamlet. Bạn có thể tiếp tục khám phá, nhưng đừng quên thêm vào wishlist!"
    ),
    "QUEST_DESCRIPTION13": (
        "Theo thời gian, người từ các vương quốc gần xa nghe đến thị trấn tự do {town_name}. "
        "Nhưng khi dân số tăng, chúng ta bắt đầu thu hút sự chú ý của những nhóm địch lớn hơn và nguy hiểm hơn."
    ),
    "QUEST_DESCRIPTION14": (
        "Quân chủ tham nhũng của Ashenholt lại gửi binh về làng. Lần này họ đòi 40.000 vàng làm triều cống và thuế liên tục, "
        "mà không chịu cử dù chỉ một binh để bảo vệ chúng ta."
    ),
    "QUEST_DESCRIPTION15": (
        "An toàn sau tường mới, một thương nhân ghé thăm kể chuyện về của cải lớn ở các vương quốc xa. "
        "Với chợ được nâng cấp, chúng ta có thể tự tổ chức viễn chinh giao thương."
    ),
    "QUEST_DESCRIPTION16": (
        "Qua nhiều năm rõ ràng thôn ấp khiêm tốn trước đây giờ có tham vọng lớn hơn. "
        "Chúng ta quyết định đã đến lúc tìm những trí tuệ được khai sáng để giúp xây dựng tương lai."
    ),
    "QUEST_DESCRIPTION17": (
        "Một lần nữa vương quốc Ashenholt gửi binh đòi thuế. Kinh ngạc trước sự phát triển của thị trấn kể từ lần trước, "
        "đòi hỏi của họ thái quá và lực lượng đông hơn nhiều."
    ),
    "QUEST_DESCRIPTION18": (
        "Nếu muốn thoát khỏi gọng kìm Ashenholt, chúng ta cần tường vững hơn để tự vệ."
    ),
    "QUEST_DESCRIPTION19": (
        "Các pháp sư Rubescairn từ lâu phục vụ các đại vương quốc. Nếu muốn tuyển một người về phe ta, "
        "trước hết phải mở rộng hạ tầng đánh cá, đóng tàu, rồi vượt biển đến Rubescairn với món quà hậu hĩnh. "
        "Tri thức của họ không cho không."
    ),
    "QUEST_DESCRIPTION20": (
        "Ấn tượng trước tăng trưởng kinh tế mạnh của {town_name} và bị thuyết phục bởi sức hút cùng ngoại giao của sứ giả quý tộc, "
        "các pháp sư chấp nhận một thỏa thuận hiếm: một pháp sư được đào tạo đổi lấy việc cung cấp lương thực cho Rubescairn trong 50 năm tới."
    ),
    "QUEST_DESCRIPTION21": (
        "Trong lúc chờ pháp sư mới tới, một phụ nữ bí ẩn nói rằng phép thuật cổ xưa ẩn trong phế tích quên lãng của đầm lầy. "
        "Bà ấy sẵn sàng chia sẻ bí mật — với một cái giá. Chúng ta cần giao thương với các quốc gia khác để lấy phép thuật cần thiết khám phá những bí ẩn này."
    ),
    "QUEST_DESCRIPTION22": (
        "Pháp sư mới tuyển kinh ngạc trước nguồn phép phong phú trong vùng. Ông đã thuyết phục Đại pháp sư Rubescairn "
        "cho phép xây Học viện phép thuật trong thành phố."
    ),
    "QUEST_DESCRIPTION23": (
        "Nơi bắt đầu như nơi trú ẩn cho người tị nạn chạy chiến tranh phía nam đã lớn thành thành phố tự do, "
        "nay giữ lòng trung thành của người từ nhiều góc thế giới."
    ),
    "QUEST_DESCRIPTION24": (
        "Một sứ giả Ashenholt lại tới, đòi thuế còn cao hơn. Kinh hoàng thay, họ còn đòi trưng binh một trong năm đàn ông khỏe mạnh vào quân đội của họ. "
        "Chúng ta giả vờ chấp nhận trong khi lặng lẽ tập hợp lực lượng đủ mạnh để từ chối."
    ),
    "QUEST_DESCRIPTION25": (
        "Giận dữ vì chúng ta từ chối giao con trai và cha ông để chết trong chiến tranh xa, quân Ashenholt chuẩn bị đập tan sự kháng cự."
    ),
    "QUEST_DESCRIPTION26": (
        "Chúng ta không còn bị lệ thuộc vào ý thích của láng giềng hùng mạnh. Chúng ta quyết rằng nếu Ashenholt quay lại, "
        "họ sẽ đối mặt một vương quốc thật sự, sẵn sàng tự vệ."
    ),
    "QUEST_DESCRIPTION27": (
        "Theo thời gian, việc thu hoạch phép thuật đầm lầy dai dẳng đã khuấy dậy một tà ác cổ xưa. "
        "Những linh hồn quên lãng từ nền văn minh mất tích nổi lên, nửa được bảo tồn, từ bùn lầy. "
        "Vũ khí của chúng ta gần như vô dụng, và chúng quá đông so với pháp sư. Chỉ sức mạnh thần thánh mới mong đẩy lui chúng."
    ),
    "QUEST_DESCRIPTION28": (
        "Với vũ khí thánh hóa mới giữ undead ở ngoài, lời hiệu triệu được gửi tới những anh hùng dũng cảm "
        "để vào phế tích chìm và tiêu diệt nguồn gốc undead."
    ),
    "QUEST_DESCRIPTION29": (
        "Các anh hùng dũng cảm đã tìm và tiêu diệt một tà ác cổ xưa sâu trong phế tích đầm. "
        "Một lần nữa, thành phố chúng ta lại thịnh vượng trong hòa bình."
    ),
    "QUEST_DESCRIPTION30A": (
        "Để {town_name} vẫn là thành phố tự do và độc lập, chúng ta cần gắn kết chặt hơn với các vương quốc xa "
        "Ankhet-Nar, Crimsonvale và Ironrend, và được họ công nhận chủ quyền."
    ),
    "QUEST_DESCRIPTION30B": (
        "Chúng ta đã có quan hệ thân với pháp sư Rubescairn, nên chuyển sự chú ý sang Ankhet-Nar. "
        "Họ coi trọng của cải và học vấn, nên chúng ta tìm cách gây ấn tượng xứng đáng với Nữ tộc trưởng của họ."
    ),
    "QUEST_DESCRIPTION31A": (
        "Ấn tượng trước tri thức và sự khéo léo của vương quốc, cùng sức hút của Phu nhân tối cao, "
        "Nữ tộc trưởng Ankhet-Nar cam kết tình hữu nghị với vương quốc đang lớn {town_name}."
    ),
    "QUEST_DESCRIPTION31B": (
        "Tiếp theo, chúng ta tìm cách thắt chặt quan hệ với Thánh vương quốc Crimsonvale, "
        "một cõi dựng trên đức tin và thần quyền."
    ),
    "QUEST_DESCRIPTION32A": (
        "Ngưỡng mộ đức tin và chiến thắng gần đây trước tà ác của chúng ta, "
        "Quân chủ Crimsonvale vui lòng công nhận {town_name} là vương quốc có chủ quyền."
    ),
    "QUEST_DESCRIPTION32B": (
        "Cuối cùng, với Ashenholt suy yếu và đang kẹt trong chiến tranh với Vương quốc Ironrend, "
        "cơ hội hiện ra để kết giao ngoại giao vững với Nữ công tước Ironrend."
    ),
    "QUEST_DESCRIPTION33A": (
        "Nhờ sức mạnh quân sự vượt trội và thương thuyết tài tình, chúng ta lập nền hòa bình mong manh giữa Ironrend và Ashenholt, "
        "giành được sự kính trọng của chính Nữ công tước Ironrend."
    ),
    "QUEST_DESCRIPTION33B": (
        "Sau khi được các vương quốc xa công nhận, chúng ta chuẩn bị đội vương miện cho Quốc vương và Hoàng hậu đầu tiên của {town_name}. "
        "Một lâu đài huy hoàng sẽ đứng như biểu tượng bền vững của chủ quyền."
    ),
    "QUEST_DESCRIPTION34": (
        "Trước sự chứng kiến của lãnh đạo nước ngoài và dân chúng yêu mến, "
        "lễ đăng quang Quốc vương và Hoàng hậu {town_name} được mong đợi từ lâu đã tới."
    ),
}

# Also unblockable blocked keys (attempted)
BLOCKED_VI: dict[str, tuple[str, str]] = {
    # key -> (vi, note) ; empty vi means keep blocked
    "HAPPINESS_A": ("Không có", "Cross-lang (DE/ZH/KO/JA/RU) đều nghĩa 'không có/không'; nhãn trạng thái hạnh phúc."),
    "DIF_TRIVIAL": ("Tầm thường", "Thang cường độ 5 bậc; DE/JA thiên độ khó/casual, dịch theo EN."),
    "DIF_LOW": ("Thấp", "Thang cường độ 5 bậc; cross-lang thấp/dễ."),
    "DIF_MODERATE": ("Vừa", "EN Moderate; ZH/KO ghi 'trung bình/quy mô vừa' — giữ nhãn cường độ trung tính."),
    "DIF_HIGH": ("Cao", "Thang cường độ 5 bậc; JA có 'lớn' nhưng EN/KO là cao."),
    "DIF_EXTREME": ("Cực đoan", "Thang cường độ 5 bậc; ZH 'cực khó' khớp Extreme."),
    "BU_CLIFF_1_REWARD": ("Chưa xác định", "Giữ placeholder rõ ràng theo EN 'To be defined'."),
    "BU_MILITARY_CAMP_1_REWARD": ("Chưa xác định", "Giữ placeholder rõ ràng theo EN 'To be defined'."),
}
