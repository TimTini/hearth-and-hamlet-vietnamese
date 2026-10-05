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
- [ ] Người dùng duyệt file design spec đã lưu.
- [ ] Viết và duyệt implementation plan.
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
- Tool Godot/PCK sẽ là bản portable ghim phiên bản/checksum trong `.tools/`;
  chưa chọn release cụ thể trước khi lập plan và làm probe tương thích.
- Không thay đổi thư mục game trong giai đoạn thiết kế.

## Việc chưa xác minh

- Chưa trích xuất CSV thật bằng toolchain đã chọn.
- Chưa xác nhận Godot tool version chính xác cần để import resource cho game.
- Chưa patch/build PCK thử.
- Chưa mở game với locale tiếng Việt; font, layout và save locale chưa được
  xác minh runtime.
- Chưa tạo remote; checkpoint chỉ lưu local.

## Bước kế tiếp

1. Người dùng duyệt design spec đã lưu.
2. Dùng skill writing-plans để tạo implementation plan chi tiết.
3. Sau khi người dùng duyệt plan và cách thực thi, bắt đầu bằng probe/toolchain
   có test fixture, rồi triển khai Đợt 1 theo TDD.
