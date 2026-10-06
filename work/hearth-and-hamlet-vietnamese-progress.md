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

### Task 3 — fix round 1

- Gate output chặn hard link ngoài symlink/junction trước các writer Python,
  PowerShell và GDRE. Snapshot ghi file tạm rồi atomic replace.
- Extraction yêu cầu `source/` rỗng và trả `workspace_source_not_empty` khi có
  dữ liệu; không tái sử dụng CSV cũ hoặc tự xóa output. Probe vẫn chạy chỉ đọc.
- Regression fixture: hard link tới cả EXE/PCK ở 10 output writer, snapshot atomic,
  và PCK chỉ chứa TSV với CSV cũ trong workspace. Tất cả đã RED → GREEN.
- Kiểm chứng mới: focused 22 passed, integration 3 passed/19 deselected, full
  71 passed; Ruff và diff check sạch.
- Probe thật sau sửa vẫn trả exit 2, locale dynamic, 27/1.849 key không phục hồi,
  hash CSV/script/EXE/PCK không đổi. Task 3 tiếp tục BLOCKED; không bắt đầu Task 4.

### Task 3 — fix round 2, 2026-10-06

- EXE/PCK được giữ bằng handle `FileShare.Read` từ trước writer GDRE/PowerShell
  đến sau snapshot/report Python; xác minh lại build khi handle còn sống và release
  trong `finally`. Alias tạo sau gate không thể mở hai file nguồn để ghi/xóa.
- Snapshot/report JSON cùng dùng writer atomic; không truncate inode output cũ.
- Watcher thực trên fixture đã RED → GREEN ở cả probe Out-File, GDRE extraction
  và Python report. Đổi share mode sang cho phép write/delete tái hiện lỗi GDRE;
  khôi phục read-only làm test xanh. Reader vẫn hoạt động; handle release đã test.
- Focused 27 passed; integration 8 passed/19 deselected. Full cuối 76 passed;
  Ruff/diff check sạch. Watcher test đồng bộ theo lifecycle process, tránh deadline
  khởi động tùy ý khi verification chậm.
- Probe F: → H: vẫn trả exit 2, dynamic locale, thiếu 27/1.849 key; các hash nguồn
  và CSV/script đã nêu không đổi. Task 3 vẫn BLOCKED; Task 4 chưa bắt đầu.

## Quyết định thiết kế bổ sung — 2026-10-06

Người dùng chọn đồng thời hai hướng: tiếp tục Việt hóa phần nguồn đã phục hồi
với fallback tiếng Anh, và mở luồng phục hồi 27 key còn thiếu. Thiết kế được
tách thành hai spec để có kế hoạch và review độc lập:

- `docs/superpowers/specs/2026-10-06-partial-source-release-design.md`
- `docs/superpowers/specs/2026-10-06-runtime-key-recovery-design.md`

Audit read-only cho snapshot hiện tại: `1.849` row tổng, `27` row
`MissingKey`, `1.822` row có key, `1.811` unique key; tám nhóm duplicate tạo
11 row dư và đều có cùng English source trong từng nhóm. Count này đã sửa theo
ruling Task 1 bên dưới; audit trước gộp key khác case. Chưa sửa code Task 4
hoặc tạo diagnostic artifact tại checkpoint này. Sau đó người dùng đã duyệt
hai spec, giao agent tự quyết chi tiết kế hoạch và yêu cầu bắt đầu dịch bằng
phương thức subagent-driven.

Hai implementation plan mới đã được viết theo thứ tự agent tự chốt:

1. `docs/superpowers/plans/2026-10-06-partial-source-preview.md` — hoàn thiện
   pipeline và dịch Phase 1 trước, dừng ở real install dry-run.
2. `docs/superpowers/plans/2026-10-06-runtime-key-recovery.md` — offline hints,
   synthetic diagnostic và real diagnostic dry-run sau khi preview pipeline ổn.

Tasks 4–9 của plan ngày 2026-10-05 được đánh dấu superseded để không bị chạy
nhầm. Chưa có `-Apply` hoặc game launch nào được thực hiện.

## Partial preview — Task 1, 2026-10-06

- Phạm vi: completeness manifest và canonical dataset; không build/install/launch.
- Base: `3078526efb0d186cd7893553bf5bdcef13286482`.
- RED: `uv run pytest tests/python/test_completeness.py tests/python/test_dataset.py -q`
  → exit 1, hai collection error vì `hnh_vi.completeness` chưa tồn tại.
- Test synthetic cho schema/hash/count, marker GDRE anchored, prefix sai grammar,
  key thường có chữ MissingKey, duplicate và thứ tự; không copy câu game.
- Implementation đang kiểm chứng; source thật chỉ đọc để audit count/hash.
- Focused GREEN: 45 passed; full `uv run pytest -q`: 121 passed, không skip;
  `uv run ruff check src tests/python`: exit 0.
- Real audit: hash CSV giữ nguyên, 1.849 total / 1.822 recovered / 27 unrecovered,
  nhưng exact-key identity cho 1.811 unique / 8 duplicate groups / 11 extra rows.
  Trước ruling, manifest giữ values cũ (1.810 / 9 / 12) và count gate đã chặn đúng.
- Root cause metadata-only: hai row 1353/1771 có key khác case, length đều 9,
  cùng English hash; Group-Object mặc định case-insensitive giải thích audit cũ.
  Không strip/casefold key. Controller ruling cho phép sửa approved count thành
  1.811 unique / 8 groups / 11 extras trong manifest, spec và plan.
- RED ruling: focused test → exit 1, 1 failed / 47 passed do manifest còn count cũ.
  Regression same-English/case-variant key đã chứng minh RED bằng temporary
  casefold mutation tại grouping (1 failed / 2 passed / 21 deselected); mutation
  đã gỡ.
- Verification sau ruling: focused 48 passed, full 124 passed (không skip), Ruff
  exit 0. Real audit exit 0: 1.811 canonical keys, tám duplicate warning,
  không blocking issue; hash CSV trước/sau vẫn `D7ADF32E…003F7E`.
- Source-leak check: không real marker hoặc full English sentence trong các file
  Task 1; writer/gate Task 3 không đổi. Không ghi game, tạo snapshot thật hoặc
  build artifact. Tiếp theo controller review Task 1 trước Task 2.

## Partial preview — Task 3 fix round 3, 2026-10-06

- Thread Codex `01a10c6a-5b55-7392-a969-1388d25c346c` dừng giữa chừng vì usage
  limit trong lúc worker đang sửa pair-consistency cho skeleton dual-write.
- Tasks 1–2 đã complete trên nhánh `codex/phase-1-localization`; Task 3 CLI
  skeleton đã có commit `77083e6` nhưng review Important còn mở:
  thay translations trước khi status replace thất bại.
- Fix round 3 (chưa commit): `_write_texts_atomic` backup atomic rồi rollback
  mọi file đã replace nếu replace sau lỗi; vẫn chặn destination không phải file
  thường. Test: directory status, read-only status, synthetic mid-replace fail.
- Verification local: focused CLI 10 passed; full `uv run pytest -q` xanh;
  Ruff sạch trên `cli.py` / `test_cli.py`. Chưa commit — chờ review độc lập.

## Partial preview ? Task 5 Phase 1 n?i dung, 2026-10-06

- Ph?m vi: d?ch ??t 1 (menu, t?y ch?n, ng?n ng?, ?? kh?, credits, game over,
  th?ng b?o h? th?ng, t?n t?i nguy?n c? b?n, nh?n tr?ng th?i chung). Base:
  `f07cd1b28658925025ab8ce85901d13febeae6fc`.
- Ch?n ch?nh x?c 111 key trong `localization/phase1.keys`, tr?n t?ng 1.811 key
  duy nh?t ?? ph?c h?i. 111 key c? b?n d?ch v? `reviewed`; kh?ng c? `in_game`.
- Nh?m ?? ch?n: MAIN_MENU, GAME_MENU, l?u/t?i, ng?n ng?, OPTIONS/OPT, UI_SCALE,
  DIFFICULTY v? x?c nh?n ??i ?? kh?, CREDITS, GAME_OVER, NOTIFICATION h? th?ng,
  t?i nguy?n v? nh?n tr?ng th?i chung.
- Lo?i kh?i ??t: BU_*, UPG_*, *_IMPROVEMENT_*, POLICY_*, TRADE_*, QUEST_*,
  TUTORIAL_*, ACH_*, ITEM_*, END_* v? c?c key giao th??ng/qu?n s?/c?t truy?n.
- `blocked` (7 key, kh?ng n?m trong `phase1.keys`): n?m key thang ?? kh? DIF_*,
  `HAPPINESS_A` (gi? tr? ngu?n gi?ng placeholder) v?
  `NOTIFICATION_CARAVAN_RETURNED` (kh?ng r? `{type}` l? lo?i hay quy m?).
- Key ngo?i `phase1.keys` gi? `translation_vi` tr?ng theo ruling Task 4; kh?ng
  ?i?n b?n d?ch nh?p.
- Glossary: 28 d?ng thu?t ng? (t?i nguy?n, qu?n s?, l?u/t?i, b?n t?n ?? kh?).
  `docs/translation-guide.md` ghi quy tr?nh, v?n phong v? quy t?c k? hi?u.
- Validate: `uv run hnh-vi validate --required-keys localization/phase1.keys`
  ? exit 0, 0 l?i, 8 c?nh b?o `duplicate_source_key` ?? bi?t, 0 c?nh b?o glossary.
- Coverage: selected 111/111 translated v? reviewed (ratio 1.0); to?n dataset
  111 reviewed, 7 blocked, 1.693 draft; `source_complete=false`,
  `maximum_known_source_ratio?0.9854`, 27 d?ng ch?a ph?c h?i.
- Build: `scripts/build.ps1 -GameDir <game>` exit 0, kh?ng `-Apply`. Preview PCK v?
  metadata JSON n?m trong `dist/25600292/` (ignored); metadata: `release_quality=preview`,
  `source_complete=false`, `fallback_locale=en`, 111 translated, 1.700 omitted empty.
  Patched paths: `translations.vi.translation` v? `project.binary`.
  PCK preview SHA-256 `63285783?B41A3` (byte c? th? kh?c khi build l?i).
- EXE/PCK g?c tr??c v? sau build ??u l? `7D37BBF3?F9A2A` / `7D5A2113?E0201`,
  kh?ng ??i. Ch?a install, ch?a launch game; Phase 1 v?n c?n smoke test th?c t?
  (ch?n Ti?ng Vi?t, font/d?u, l?u l?a ch?n ng?n ng?, k?ch th??c n?t).
- L?u ? runtime: danh s?ch ng?n ng? trong game l? `native_names` ? script
  `language.gd`; ch?a x?c minh b?n vi hi?n ?? c? m?c ch?n "Ti?ng Vi?t" hay ch?a,
  c?n ki?m tra khi smoke.
