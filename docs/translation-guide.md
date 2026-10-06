# Hướng dẫn dịch Hearth and Hamlet sang tiếng Việt

Tài liệu này dành cho người tiếp tục dịch hoặc rà soát bản dịch. Nó không chứa
bảng tiếng Anh của game; câu gốc chỉ có trong snapshot local bị Git ignore
(`workspace/25600292/probe/source/localisation/translations.csv`).

## Quy trình mỗi đợt

1. Chọn key của đợt trong `localization/phaseN.keys` (mỗi dòng một key).
2. Điền `translation_vi` trong `localization/translations.vi.csv`. Không sửa cột
   `key` và `source_sha256`.
3. Đặt `reviewed` trong `localization/status.csv` sau khi tự rà câu chữ,
   thuật ngữ và ký hiệu đặc biệt. Chỉ dùng `in_game` sau khi đã thấy trong game.
4. Key chưa đủ ngữ cảnh để dịch chắc chắn: đặt `blocked` và ghi lý do ngắn ở cột
   `note`. Không đưa key đó vào `phaseN.keys`.
5. Key ngoài đợt hiện tại để `translation_vi` trống. Game sẽ tự dùng tiếng Anh
   cho các key này (fallback `en`).
6. Chạy kiểm tra:

```powershell
uv run hnh-vi validate --required-keys localization/phase1.keys
uv run hnh-vi coverage --selected-keys localization/phase1.keys
```

`validate` phải không có lỗi chặn. Cảnh báo `duplicate_source_key` là bình
thường (tám nhóm key trùng đã biết). Cảnh báo `glossary_mismatch` cần được xem
lại trước khi đổi sang `reviewed`.

## Văn phong

- Tự nhiên, ngắn gọn, dễ chơi. Dịch ý, không dịch từng chữ.
- Nút bấm và nhãn menu càng ngắn càng tốt để không tràn nút. Ví dụ dùng
  "Tiếp tục game", không dùng câu dài.
- Dùng "game" cho thuật ngữ chung ("Thoát game", "Tải game"). Không trộn với
  "trò chơi" trong cùng một menu.
- Gọi người chơi là "bạn". Thông báo hệ thống nói gọn, không thêm chủ ngữ thừa.
- Bối cảnh trung cổ: ưu tiên từ quen thuộc như "dân", "binh lính", "quân địch",
  "thị trấn"; tránh từ quá hiện đại hoặc quá hàn lâm.
- Tên riêng giữ nguyên (tên game, tên quốc gia/thành phố như Ashenholt).

## Giữ nguyên ký hiệu đặc biệt

Validator chặn build khi thay đổi những thứ sau, nên kiểm tra kỹ:

- Placeholder `%s`, `%d`, `%%`, `{ten_bien}`: giữ đúng số lượng và tên. Với
  `%s`/`%d` không đánh số, giữ đúng thứ tự xuất hiện; đổi ngữ pháp cho khớp
  thứ tự đó thay vì đảo placeholder.
- BBCode như `[b]...[/b]`: giữ đủ cặp thẻ, không đổi tên thẻ.
- Xuống dòng: số lần xuống dòng thật (và ký tự `\n` nếu có) phải bằng bản gốc.
- Không dùng ký tự điều khiển. Dấu tiếng Việt không bắt buộc NFC trong file
  commit; bản build tự chuẩn hóa NFC.

## Thuật ngữ chuẩn

Danh sách đầy đủ nằm ở `localization/glossary.csv`. Checker chỉ cảnh báo, không
tự sửa. Một số quyết định đáng chú ý:

| Nhóm | Dùng | Ghi chú |
| --- | --- | --- |
| Tài nguyên | Vàng, Gỗ, Đá, Sắt, Lương thực, Phép thuật | Không dùng "thức ăn" cho Food |
| Nhân lực | nhân công, dân số | "dân" dùng khi nói chung chung |
| Quân sự | binh lính, quân địch, chi phí duy trì | |
| Lưu/tải | bản lưu, ô lưu, tải, lưu | "Ô lưu" chỉ dành cho slot save |
| Độ khó | Nhẹ nhàng, Ổn định, Thử thách, Khốc liệt | Tên bốn mức độ khó, theo scope key |
| Nạn đói | nạn đói | Dùng cho cả ba thông báo đói kém |

Khi thêm thuật ngữ mới, thêm một dòng vào `glossary.csv`. Để cột `scope` trống
nếu quy tắc áp dụng cho mọi key, hoặc ghi đúng tên key nếu chỉ áp dụng riêng.
Thuật ngữ được so khớp theo từ nguyên vẹn, không phân biệt hoa/thường; dạng số
nhiều như "enemies" không khớp "Enemy", nên cần nhớ tự giữ nhất quán.

## Phạm vi Đợt 1

Đợt 1 gồm menu chính, menu trong game, cài đặt, nút chung, tên tài nguyên cơ
bản, nhãn trạng thái chung, thông báo hệ thống, độ khó, credits và màn hình thất
bại. Công trình, nâng cấp, giao thương, nhiệm vụ, hướng dẫn và cốt truyện thuộc
các đợt sau; không dịch chúng trong đợt này.
