# Tiến độ Việt hóa Hearth and Hamlet

Cập nhật: 2026-10-05

## Mục tiêu và phạm vi

Tạo toolchain và bản dịch tiếng Việt tự nhiên, dễ chơi cho Hearth and Hamlet
1.1.0. Không commit hoặc phân phối file game/asset gốc. Phát hành theo bốn
đợt; cài đặt phải có dry-run, backup, rollback và uninstall.

## Trạng thái

- [x] Xác định game dùng Godot và localization nằm trong PCK.
- [x] Xác định nguồn hiện tại là EXE 1.1.0.0, Steam build 25600292.
- [x] Chốt văn phong tự nhiên, dễ chơi.
- [x] Chốt phát hành theo từng đợt.
- [x] Chốt hướng patch cục bộ chỉ thay tài nguyên localization.
- [x] Người dùng duyệt thiết kế trong trao đổi.
- [x] Khởi tạo repo Git local trên nhánh `main`.
- [x] Viết design spec.
- [x] Người dùng duyệt file design spec đã lưu.
- [x] Viết implementation plan Đợt 1.
- [ ] Người dùng duyệt implementation plan và cách thực thi.
- [ ] Triển khai Đợt 1 theo TDD.
- [ ] Review độc lập và verification Đợt 1.
- [ ] Dịch và kiểm chứng các đợt 2–4.

## Bằng chứng nguồn đã đọc

- `<GameDir>\Hearth and Hamlet.exe`
  có `FileVersion` và `ProductVersion` là `1.1.0.0`.
- `<SteamLibrary>\steamapps\appmanifest_4315040.acf` ghi build `25600292`.
- PCK chứa `localisation/translations.csv` và các resource
  `translations.<locale>.translation`.
- PCK chứa NotoSans và các font ngôn ngữ khác; khả năng hiển thị tiếng Việt
  vẫn cần smoke test trong game.

## Fingerprint nguồn

- EXE SHA-256:
  `7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A`
- PCK SHA-256:
  `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`

## Quyết định

- Repo đề xuất và đã tạo:
  `<RepoRoot>`.
- Dùng PowerShell cho orchestration Windows và Python chạy bằng `uv` cho
  pipeline dữ liệu.
- Implementation plan chọn GDRE Tools 2.7.0 và Godot 4.6.3-stable dạng
  portable, ghim URL/SHA-256 trong manifest; tương thích thực tế vẫn phải qua
  probe read-only và PCK fixture trước khi patch game thật.
- Không thay đổi thư mục game trong giai đoạn thiết kế.
- Không commit toàn bộ câu tiếng Anh trích từ game; bảng dịch dùng
  `source_sha256`, còn source đầy đủ chỉ nằm trong workspace local bị ignore.

## Việc chưa xác minh

- Chưa trích xuất CSV thật bằng toolchain đã chọn.
- Chưa xác nhận Godot tool version chính xác cần để import resource cho game.
- Chưa patch/build PCK thử.
- Chưa mở game với locale tiếng Việt; font, layout và save locale chưa được
  xác minh runtime.
- Chưa tạo remote; checkpoint chỉ lưu local.

## Bước kế tiếp

1. Người dùng duyệt design spec đã lưu.
2. Người dùng duyệt implementation plan và chọn cách thực thi.
3. Bắt đầu bằng toolchain có test fixture và probe read-only, rồi triển khai
   Đợt 1 theo TDD.

## Checkpoint Task 3 — 2026-10-05

Trạng thái: **BLOCKED** ở source snapshot thật; chưa bắt đầu Task 4 và chưa
build/patch/install game. Extraction và probe chỉ ghi vào `workspace/<build-id>/`
bị Git ignore. Không commit nội dung CSV hoặc script được phục hồi từ game.

- Toolchain đã kiểm chứng: GDRE Tools `2.7.0`; Godot
  `4.6.3.stable.official.7d41c59c4`. PCK thật báo engine `4.6.3`, bytecode
  `4.5.0-stable (ebc36a7)`.
- Kiểm thử: `uv run pytest -q` → 66 passed; focused workspace/extraction/probe
  → 17 passed; Ruff sạch. Fixture sử dụng Godot PCKPacker và GDRE thật; bytes
  EXE/PCK fixture không thay đổi sau extract/probe.
- Build `25600292`: 8.130 path trong PCK. Localization gồm 7 resource locale
  và CSV import metadata; PCK không chứa CSV gốc.
- GDRE recovery tạo CSV 1.849 row, schema
  `key,en,de,zh_CN,zht_CN,ru,ja,ko`, nhưng không phục hồi được 27/1.849 key.
  CSV này chưa phải nguồn hợp lệ để tạo snapshot hoặc bản dịch.
- Probe trả exit `2`, issue `translation_recovery_incomplete`,
  `compatible=false`. Locale selection được tạo động từ các locale đã nạp;
  manager xác thực locale theo tập đã nạp và lưu lựa chọn. Đây là bằng chứng
  source đã đọc, chưa phải runtime/E2E.
- SHA-256 CSV recovery chưa đầy đủ:
  `D7ADF32E2453BEAE6D716319D703C1BC5715A31143C7DB91D299FA7619003F7E`.
- SHA-256 script selector:
  `EFCA9D1AEEDA5A96662977719C58367B0607A200E20C82FDF6DB6D95925325D5`;
  manager:
  `E7CCD833154D1439711A6BA1111794C6CF041DDC51FA269F95A53A5A7E7BB172`.
- EXE/PCK thật vẫn khớp fingerprint đã duyệt sau probe. Không có snapshot thật
  hợp lệ. Dừng pipeline tại đây cho tới khi có cách phục hồi đầy đủ key được
  đánh giá và duyệt; không đổi schema hoặc kiến trúc để vượt gate.
