# Hearth and Hamlet Vietnamese

Dự án Việt hóa **Hearth and Hamlet** theo văn phong tự nhiên, dễ chơi.

Trạng thái hiện tại: thiết kế đã được chốt cho game phiên bản 1.1.0; chưa có
gói cài thử. Theo dõi checkpoint tại
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

Kiểm thử chỉ dùng file tổng hợp trong thư mục tạm, không truy cập game thật.
CLI và script cài/gỡ chưa được triển khai.

## Extraction và probe chỉ đọc

`scripts/extract.ps1 -GameDir <path>` và `scripts/probe.ps1 -GameDir <path>` xác minh
build/tool trước khi chạy. Trong suốt quá trình, PowerShell giữ handle EXE/PCK với
`FileShare.Read`: GDRE/Python vẫn đọc được, nhưng Windows từ chối mở để ghi hoặc
xóa hai file nguồn, kể cả qua hard link tạo sau bước kiểm tra. Handle được release
trong `finally` khi script kết thúc. Snapshot/report JSON dùng file tạm rồi atomic
replace, không truncate output cũ.

Output chỉ nằm dưới `workspace/<build-id>/` bị ignore. Extraction từ chối source
không rỗng với `workspace_source_not_empty`; không tự xóa hoặc dùng lại CSV cũ.
Build thật hiện chưa có snapshot hợp lệ: probe báo `translation_recovery_incomplete`
với 27/1.849 key chưa phục hồi. Xem checkpoint Task 3 trước khi tiếp tục pipeline.
