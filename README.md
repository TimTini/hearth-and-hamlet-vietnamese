# Hearth and Hamlet Vietnamese

Dự án Việt hóa **Hearth and Hamlet** theo văn phong tự nhiên, dễ chơi.

Trạng thái hiện tại: Phase 1 preview (111 key giao diện) đã dịch, build candidate và dry-run cài/gỡ đã chạy trên build Steam `25600292`. **Chưa** apply vào game trong biên plan tự động — xem
[`docs/phase-1-smoke-checklist.md`](docs/phase-1-smoke-checklist.md). Theo dõi checkpoint tại
[`work/hearth-and-hamlet-vietnamese-progress.md`](work/hearth-and-hamlet-vietnamese-progress.md).

Repo này chỉ lưu script, kiểm thử và nội dung dịch do dự án tạo ra. Không
commit file thực thi, PCK, asset hoặc dữ liệu đã trích xuất từ game.

## Phát triển toolchain

Cần Python 3.12+ và `uv`. Từ thư mục repo, chạy:

```powershell
uv sync --locked
uv run pytest
uv run ruff check src tests/python
```

## CLI Việt hóa

`hnh-vi` xuất JSON UTF-8 ổn định. Bốn lệnh là:

```powershell
uv run hnh-vi verify-game --game-dir "<thư mục game>"
uv run hnh-vi skeleton
uv run hnh-vi validate
uv run hnh-vi coverage
```

`verify-game` chỉ đọc và đối chiếu EXE/PCK với `manifests/game-builds.json`; có
thể thêm `--appmanifest <file .acf>` để kiểm tra Steam build ID. Ba lệnh dataset
đọc CSV nguồn đã phục hồi trong `workspace/<build-id>/` và bắt buộc đối chiếu
`localization/source-completeness.json`; khi dùng đường dẫn khác, truyền
`--source-csv <file>` và `--completeness <file>`. `skeleton` thêm key đã xác minh
vào `localization/translations.vi.csv` và `localization/status.csv`, giữ nguyên
bản dịch/trạng thái/ghi chú đang có, và không ghi cột tiếng Anh hay marker chưa
phục hồi. `validate` nhận tùy chọn `--required-keys <file>` (mỗi key một dòng);
`coverage` nhận `--selected-keys <file>` theo cùng định dạng.

Mã thoát: `0` thành công, `2` đầu vào không hợp lệ, `3` build hoặc completeness
không được hỗ trợ/không khớp, `4` lỗi contract bản dịch, `5` lỗi ghi skeleton
hoặc kiểm tra build.

Task 1 có API Python xác minh build chỉ đọc tại `src/hnh_vi/builds.py`:
`load_build_specs`, `sha256_file` và `verify_game_dir`. Manifest
`manifests/game-builds.json` hỗ trợ EXE 1.1.0.0, Steam build `25600292`;
hash EXE/PCK phải khớp để xác minh thành công. `exe_version` là metadata của
build được duyệt; verifier dùng hash để xác định đúng binary.

`verify_game_dir` trả `VerificationResult(ok, issues)` với issue code theo
thứ tự EXE, PCK rồi Steam: `missing_file`, `hash_mismatch`,
`steam_build_mismatch`. Khi truyền `appmanifest`, build ID Steam cũng phải
khớp. Không truyền file này thì chỉ xác minh fingerprint EXE/PCK.
Hàm không ghi file hoặc in dữ liệu; lỗi đọc file/JSON được báo cho caller.
Tên EXE/PCK trong manifest phải là tên file, không chứa đường dẫn.

Kiểm thử CLI dùng game giả lập trong thư mục tạm; contract skeleton có thể đối
chiếu CSV phục hồi trong workspace bị ignore. Không test nào mở hoặc chạy game
đã cài.

## Extraction và probe chỉ đọc

`scripts/extract.ps1 -GameDir <path>` và `scripts/probe.ps1 -GameDir <path>` xác minh
build/tool trước khi chạy. Trong suốt quá trình, PowerShell giữ handle EXE/PCK với
`FileShare.Read`: GDRE/Python vẫn đọc được, nhưng Windows từ chối mở để ghi hoặc
xóa hai file nguồn, kể cả qua hard link tạo sau bước kiểm tra. Handle được release
trong `finally` khi script kết thúc. Snapshot/report JSON dùng file tạm rồi atomic
replace, không truncate output cũ.

Output chỉ nằm dưới `workspace/<build-id>/` bị ignore. Extraction từ chối source
không rỗng với `workspace_source_not_empty`; không tự xóa hoặc dùng lại CSV cũ.
Build thật hiện chưa phục hồi đủ: còn 27/1.849 key chưa xác minh. Preview, nếu
được tạo ở các bước sau, phải giữ fallback tiếng Anh và báo rõ giới hạn nguồn.

## Cài và gỡ bản preview

```powershell
scripts/install.ps1   -GameDir "<thư mục game>" -Artifact "dist/<build-id>/Hearth-and-Hamlet-vi-preview-1.1.0.pck" [-Apply]
scripts/uninstall.ps1 -GameDir "<thư mục game>" [-Backup "<thư mục backup>"] [-Apply]
```

Cả hai script mặc định là dry-run: chỉ kiểm tra và in kế hoạch, không ghi gì. Chỉ
`-Apply` mới ghi thật. Metadata của artifact được đọc từ file `.json` cùng tên.

- Install từ chối build không hỗ trợ (hash EXE/PCK không khớp
  `manifests/game-builds.json`), artifact không khớp metadata hoặc build nguồn,
  artifact diagnostic (thư mục `diagnostic`, metadata diagnostic), và mọi file/thư
  mục là symlink, junction hoặc hard link ở PCK game hay đường dẫn backup.
- Trước khi thay PCK, script tạo backup mới (không bao giờ ghi đè backup cũ) tại
  `%LOCALAPPDATA%\HearthAndHamletVietnamese\backups\<build-id>\<UTC timestamp>\`
  gồm bản PCK gốc và `backup.json` có hash; backup được đọc lại và kiểm tra hash.
- PCK mới được copy sang file tạm cùng thư mục game (cùng volume), kiểm tra
  SHA-256, rồi `os.replace`. Lỗi trước replace thì PCK game không đổi; lỗi xác minh
  sau replace thì PCK được phục hồi ngay từ backup vừa tạo.
- Uninstall chỉ chấp nhận backup có metadata hợp lệ và hash khớp bản gốc của
  build được hỗ trợ. Không có `-Backup` thì dùng backup mới nhất khớp PCK đang cài.
  Nếu Steam đã cập nhật game sau khi cài (EXE/PCK khác bản đã cài), script từ chối
  ghi đè và nhắc dùng Steam "Verify integrity of game files" hoặc backup phù hợp.
- Khi `-Apply`, PowerShell giữ handle `FileShare.Read` trên EXE game trong lúc
  Python chạy. PCK game không thể khóa kiểu này vì nó phải được thay; Python kiểm
  tra lại hash EXE/PCK ngay trước và sau khi replace, và replace thất bại nếu game
  đang mở PCK (khi đó PCK giữ nguyên, backup vừa tạo bị xóa).
- Backup cho một lần cài chỉ được giữ khi PCK game thực sự đã bị thay. Lỗi
  `rollback_failed` in rõ đường dẫn backup để copy tay vào thư mục game.

Test cài/gỡ chỉ dùng thư mục game giả lập trong thư mục tạm; không test nào ghi vào
game Steam thật.

## Checkpoint apply / smoke (ngoài biên tự động)

Checklist xác minh dry-run và các bước cần ủy quyền tường minh (`-Apply`,
launch game, smoke UI, gỡ) nằm tại
[`docs/phase-1-smoke-checklist.md`](docs/phase-1-smoke-checklist.md).
