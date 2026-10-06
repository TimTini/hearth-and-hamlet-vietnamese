# Phase 1 preview — checklist smoke và checkpoint cài đặt

Ngày xác minh: 2026-10-06, nhánh `codex/phase-1-localization`, HEAD kiểm chứng
`4c90333cdcddf57102a80b7f1e47ca42c7867efd`.

Game: Hearth and Hamlet EXE 1.1.0.0, Steam build `25600292`.
GameDir: `<GameDir>`.

## 1. Bằng chứng đã có (không ghi vào game)

| Hạng mục | Kết quả |
| --- | --- |
| `uv sync --locked` | OK, 8 package |
| `uv run pytest -q -rs` | **415 passed, 2 skipped** (2 test symlink cần quyền đặc biệt trên máy này) |
| `uv run ruff check src tests/python` | All checks passed |
| `git diff --check` | exit 0 |
| `hnh-vi verify-game` | `ok: true`, build `25600292`, EXE 1.1.0.0 |
| `hnh-vi validate --required-keys localization/phase1.keys` | exit 0, 0 lỗi, 8 cảnh báo `duplicate_source_key` đã biết |
| `hnh-vi coverage --selected-keys localization/phase1.keys` | selected 111/111 translated + reviewed; `source_complete=false`; 27 key chưa phục hồi |
| `scripts/build.ps1 -GameDir <game>` | exit 0, không `-Apply` |
| File tracked | Không có PCK/EXE/DLL/asset; `workspace/`, `dist/`, `.tools/` bị ignore |

Artifact preview (nằm trong `dist/`, bị ignore, không commit):

- `dist/25600292/Hearth-and-Hamlet-vi-preview-1.1.0.pck`, 857.730.692 byte.
- SHA-256 lần build cuối: `B04247D059A8B4CEC654211179CBEB42A27FDF7CD7B5B548A29C47A6EDB593D8`.
- Metadata: `release_quality=preview`, `source_complete=false`, `fallback_locale=en`,
  `translated_keys=111`, `omitted_empty_keys=1700`, `locale=vi`.
- `patched_paths`: `res://localisation/translations.vi.translation`, `res://project.binary`.
- Hash PCK nguồn trong metadata: `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`.

### Hash artifact không ổn định giữa các lần build

Godot sinh id sub-resource ngẫu nhiên nên byte PCK khác nhau sau mỗi lần build.
Lần build trước cho `59A0EB03…03431`, lần build cuối cho `B04247D0…593D8`.
Mọi trường metadata khác (hash CSV nguồn, hash selected keys, hash merged CSV,
coverage, patched paths, kích thước) giống hệt giữa hai lần. Vì vậy phải dùng hash
trong file `.json` đi kèm đúng artifact đang cài, không so với hash cũ.

### Dry-run cài/gỡ trên game thật (không `-Apply`)

Install dry-run — exit 0:

- `mode`: `dry-run`, `action`: `install`, `build_id`: `25600292`
- `current_pck_sha256`: `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`
- `new_pck_sha256`: `B04247D059A8B4CEC654211179CBEB42A27FDF7CD7B5B548A29C47A6EDB593D8`
- `backup_dir` dự kiến:
  `%LOCALAPPDATA%\HearthAndHamletVietnamese\backups\25600292\<UTC timestamp>`
- Script in "Dry run only. Nothing was changed."

Uninstall dry-run — exit 1 với `already_original: the game already has its original PCK`.
Đây là từ chối đúng: chưa cài nên không có gì để gỡ.

Sau cả hai lệnh:

- EXE `7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A` — không đổi.
- PCK `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201` — không đổi.
- Danh sách file, kích thước, thời gian sửa trong thư mục game — không đổi.
- Thư mục `%LOCALAPPDATA%\HearthAndHamletVietnamese` chưa được tạo.
- Game chưa được mở.

### Review độc lập

Review whole-branch cuối do controller thực hiện sau commit Task 7 (SDD final
review). Task này không tự tạo reviewer thứ hai.

## 2. Checkpoint cần ủy quyền tường minh

Các bước dưới đây ghi vào thư mục game Steam hoặc mở game, nằm ngoài biên tự động.
**Chỉ chạy sau khi người dùng đồng ý rõ ràng cho từng bước.** Đóng game và Steam
overlay trước khi bắt đầu.

1. Cài thật:

   ```powershell
   scripts/install.ps1 -GameDir "<GameDir>" -Artifact "dist/25600292/Hearth-and-Hamlet-vi-preview-1.1.0.pck" -Apply
   ```

   Kỳ vọng: backup mới dưới `%LOCALAPPDATA%\HearthAndHamletVietnamese\backups\25600292\`
   gồm PCK gốc và `backup.json`; PCK game có hash bằng `artifact_sha256` trong
   file `.json` đi kèm; EXE không đổi.
2. Mở game và chạy smoke bên dưới.
3. Gỡ: `scripts/uninstall.ps1 -GameDir "..." -Apply`; kiểm tra PCK về lại
   `7D5A2113…E0201`. Nếu có sự cố, dùng Steam "Verify integrity of game files".
4. Tùy chọn: cài lại preview sau khi gỡ.

## 3. Checklist smoke trong game (chưa chạy)

- [ ] Game khởi động, không crash, không treo ở màn hình tải.
- [ ] Chọn được ngôn ngữ tiếng Việt trong Options. Có thể hiển thị **"VI"** thay vì
  "Tiếng Việt" vì `language.gd` (`native_names`) chưa có tên bản địa cho `vi` — ghi lại.
- [ ] Lựa chọn ngôn ngữ được lưu sau khi thoát và mở lại game.
- [ ] Dấu tiếng Việt (ă â ê ô ơ ư đ và dấu thanh) hiển thị đúng, không ô vuông.
- [ ] Menu chính, menu game, Options, lưu/tải: chữ không bị cắt, nút đủ rộng.
- [ ] Độ khó, tín dụng, game over, thông báo hệ thống đọc tự nhiên.
- [ ] Key chưa dịch / chưa phục hồi vẫn hiện tiếng Anh (fallback), không hiện tên key.
- [ ] Đổi kích thước UI (UI scale) không làm vỡ bố cục.
- [ ] Sau khi gỡ, game quay lại bản gốc.

## 4. Mục mở

- Tên "Tiếng Việt" trong danh sách ngôn ngữ chưa được xác minh (có thể là "VI").
- Font, dấu và độ rộng nút chưa thử trong game.
- 27 key nguồn chưa phục hồi → fallback tiếng Anh (kế hoạch runtime-key-recovery riêng).
- Ngoài 111 key Phase 1, 1.693 key còn draft và 7 key `blocked`.
- Phase 1 chỉ là preview, không phải bản Việt hóa đầy đủ.
