# Phase 1 preview — smoke checklist và checkpoint cài đặt

Ngày xác minh dry-run: 2026-10-06 (worktree codex/phase-1-localization).

## Đã xác minh trong repo (không ghi game)

- uv sync --locked: OK
- Full pytest: **415 passed, 2 skipped** (symlink privilege thiếu trên máy này)
- 
uff check src tests/python: sạch
- git diff --check: sạch
- hnh-vi validate --required-keys localization/phase1.keys: exit 0 (chỉ warning duplicate_source_key đã biết)
- hnh-vi coverage --selected-keys localization/phase1.keys: selected 111/111 translated + reviewed; source_complete=false
- scripts/build.ps1 tạo preview dưới dist/25600292/ (gitignored)
- Metadata preview: 
elease_quality=preview, allback_locale=en, 	ranslated_keys=111
- Hash PCK/EXE gốc sau build + dry-run: **không đổi**

## Dry-run cài/gỡ trên game thật (không -Apply)

GameDir:

<GameDir>

Artifact:

dist/25600292/Hearth-and-Hamlet-vi-preview-1.1.0.pck

Install dry-run (exit 0): mode=dry-run, backup dự kiến dưới
%LOCALAPPDATA%\HearthAndHamletVietnamese\backups\25600292\<UTC>/.

Uninstall dry-run khi chưa apply: báo lready_original (đúng — PCK vẫn là bản gốc).

## Checkpoint cần ủy quyền tường minh (ngoài biên tự động của plan)

Các bước sau **ghi hoặc mở** bên ngoài worktree; chỉ chạy khi người dùng xác nhận rõ:

1. scripts/install.ps1 -GameDir "..." -Artifact "..." -Apply
2. Khởi động game và chọn locale tiếng Việt (có thể hiện **VI** thay vì "Tiếng Việt" vì language.gd chưa có tên bản địa i)
3. Smoke UI: font/dấu, nút menu/options, lưu lựa chọn ngôn ngữ, fallback tiếng Anh cho key chưa dịch
4. scripts/uninstall.ps1 -GameDir "..." -Apply (hoặc Steam Verify nếu cần)
5. Tùy chọn: cài lại preview sau khi gỡ

## Mục mở

- 27 key chưa phục hồi → fallback en (runtime recovery là plan riêng)
- ~1700 key known còn draft/trống ngoài Phase 1
- 7 key locked (ngữ cảnh chưa rõ)
- PCK artifact hash không ổn định giữa các lần build (Godot random sub-resource id); metadata/path list vẫn deterministic
