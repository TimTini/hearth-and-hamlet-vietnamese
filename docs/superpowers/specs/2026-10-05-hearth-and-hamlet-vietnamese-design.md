# Thiết kế Việt hóa Hearth and Hamlet

Ngày: 2026-10-05

Trạng thái: Đã được người dùng duyệt ngày 2026-10-05

Repo: `<RepoRoot>`

## 1. Mục tiêu

Tạo bộ công cụ có thể lặp lại và một bản dịch tiếng Việt tự nhiên, dễ chơi
cho **Hearth and Hamlet 1.1.0**, Steam build `25600292`. Dự án phải cho phép
trích xuất dữ liệu ngôn ngữ từ bản game hợp pháp đã cài trên máy người dùng,
kiểm tra chất lượng bản dịch, tạo gói cài thử theo từng đợt, cài có backup và
gỡ về đúng trạng thái ban đầu.

Bản dịch ưu tiên câu tiếng Việt rõ ràng, tự nhiên và nhất quán với bối cảnh
trung cổ. Tên riêng được giữ nguyên. Thuật ngữ chỉ giữ tiếng Anh khi dịch ra
tiếng Việt làm mất nghĩa hoặc gây khó hiểu; các trường hợp đó phải được ghi
trong glossary.

## 2. Phạm vi và ranh giới

### Trong phạm vi

- Công cụ Windows để chuẩn bị dependency, trích xuất localization, build,
  dry-run, cài đặt và gỡ cài đặt.
- Pipeline Python chạy bằng `uv` để đọc bảng dịch, kiểm tra contract và tạo
  báo cáo độ phủ.
- Bảng dịch tiếng Việt, glossary và metadata trạng thái rà soát.
- Tạo resource `vi.translation` tương thích với bản Godot của game và patch
  cục bộ các tài nguyên localization cần thiết.
- Bản cài thử theo bốn đợt và smoke test tương ứng.
- Tài liệu cho cộng tác viên tiếp tục dịch hoặc cập nhật khi game đổi phiên
  bản.

### Ngoài phạm vi

- Phát tán EXE, PCK, asset, script đã decompile hoặc dữ liệu game nguyên bản.
- Né DRM, sửa gameplay, cheat hoặc can thiệp save game.
- Tự động vá một Steam build chưa được xác nhận tương thích.
- Cài dependency vào phạm vi toàn hệ thống nếu có thể dùng bản portable đã
  ghim phiên bản trong thư mục `.tools/` bị Git ignore.
- Coi bản dịch máy/bản nháp là đã được kiểm chứng trong game.

## 3. Nguồn game được hỗ trợ ban đầu

Nguồn đã khảo sát:

- Thư mục: `<GameDir>`
- EXE version: `1.1.0.0`
- Steam build: `25600292`
- SHA-256 EXE:
  `7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A`
- SHA-256 PCK:
  `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`
- Engine/resource evidence: Godot; PCK chứa
  `localisation/translations.csv` và các resource
  `translations.<locale>.translation`.

Các hash trên là fingerprint của build đầu tiên, không phải bí mật. Manifest
tương thích phải lưu version, Steam build, hash và ngày xác nhận. Mọi build
khác bị từ chối cho tới khi được phân tích và thêm manifest riêng.

## 4. Kiến trúc repo

```text
hearth-and-hamlet-vietnamese/
├── docs/
│   └── superpowers/
│       ├── plans/
│       └── specs/
├── localization/
│   ├── glossary.csv
│   ├── translations.vi.csv
│   └── status.csv
├── manifests/
│   └── game-builds.json
├── scripts/
│   ├── bootstrap.ps1
│   ├── build.ps1
│   ├── extract.ps1
│   ├── install.ps1
│   └── uninstall.ps1
├── src/
│   └── hnh_vi/
├── tests/
│   ├── fixtures/
│   ├── powershell/
│   └── python/
├── work/
│   └── hearth-and-hamlet-vietnamese-progress.md
├── pyproject.toml
├── uv.lock
└── README.md
```

Trách nhiệm được tách như sau:

- PowerShell điều phối hành vi đặc thù Windows và thao tác cài/gỡ.
- Python xử lý dữ liệu dịch và các kiểm tra có tính quyết định, không gọi game
  hoặc dịch vụ mạng.
- Công cụ Godot/PCK portable thực hiện thao tác archive/resource; script chỉ
  gọi phiên bản đã ghim và xác minh checksum.
- `work/`, `dist/`, `.tools/`, dữ liệu trích xuất và backup game thật không
  được commit. Riêng progress log có tên cố định nêu trên được commit.

## 5. Luồng dữ liệu

```text
PCK gốc 1.1.0
   │  extract read-only
   ▼
CSV tiếng Anh ──► translations.vi.csv + glossary.csv + status.csv
                         │
                         ├── validate keys/placeholders/tags/coverage
                         ▼
                  vi.translation + language metadata
                         │
                         ▼
                  PCK đã patch cục bộ
                         │
                  install có backup
                         ▼
                    game smoke test
```

Extraction tạo snapshot nguồn có fingerprint và không ghi vào thư mục game.
Translation rows phải có khóa ổn định hoặc source fingerprint đủ để phát hiện
khi upstream thay đổi. Build chỉ dùng các row hợp lệ của đúng source snapshot.

## 6. Mô hình dữ liệu dịch

`translations.vi.csv` phải chứa tối thiểu:

- `key`: khóa localization hoặc định danh ổn định lấy từ CSV nguồn.
- `source_sha256`: fingerprint của câu tiếng Anh tại build nguồn, dùng để phát
  hiện source drift mà không commit toàn bộ văn bản gốc của game.
- `translation_vi`: bản dịch tiếng Việt.

Câu tiếng Anh đầy đủ chỉ tồn tại trong source snapshot local bị Git ignore.
CLI hiển thị source local cạnh bản dịch khi cần rà soát; release và lịch sử Git
không chứa bảng tiếng Anh trích xuất nguyên vẹn.

`status.csv` tách metadata quy trình khỏi payload được game import:

- `key`
- `status`: một trong `draft`, `reviewed`, `in_game`, `blocked`
- `note`: ghi chú ngữ cảnh ngắn, không chứa dữ liệu cá nhân.

Ý nghĩa trạng thái:

- `draft`: đã có bản dịch ban đầu nhưng chưa rà đầy đủ.
- `reviewed`: đã rà câu chữ, thuật ngữ và contract text.
- `in_game`: đã quan sát trong game và kiểm tra hiển thị/ngữ cảnh.
- `blocked`: chưa đủ ngữ cảnh hoặc chưa mở được nội dung.

`glossary.csv` định nghĩa thuật ngữ nguồn, bản dịch chuẩn, loại từ/phạm vi và
ghi chú. Checker báo vi phạm có độ tin cậy cao; không tự sửa câu dịch.

## 7. Contract và kiểm tra chất lượng

Validator phải phát hiện và dừng build khi có:

- Khóa bắt buộc bị thiếu hoặc trùng.
- Source English không còn khớp snapshot của manifest.
- Bản dịch trống ngoài allowlist có lý do rõ ràng.
- Thay đổi số lượng hoặc tên placeholder như `%s`, `%d`, `{name}`.
- Mất cân bằng hoặc thay đổi cấu trúc BBCode/tag đã được hỗ trợ.
- Escape sequence bắt buộc như `\n` bị biến đổi sai.
- Locale hoặc cột CSV không đúng schema.

Validator cảnh báo nhưng không nhất thiết dừng build khi có:

- Thuật ngữ lệch glossary cần người dịch xem lại.
- Câu dài vượt ngưỡng heuristic.
- Trạng thái còn `draft` hoặc `blocked`.

Báo cáo độ phủ phải tách ít nhất: tổng số chuỗi, có bản dịch, `reviewed`,
`in_game`, `blocked`, lỗi chặn build và cảnh báo. Không dùng một phần trăm duy
nhất để che sự khác biệt giữa “đã dịch” và “đã kiểm chứng trong game”.

## 8. Build và đóng gói

`bootstrap.ps1` tải hoặc kiểm tra công cụ portable đã ghim phiên bản trong
`.tools/`, xác minh SHA-256 trước khi dùng và không sửa PATH toàn hệ thống.
Nguồn tải, license, phiên bản và checksum phải được ghi trong manifest công
cụ.

`extract.ps1`:

1. Xác minh đường dẫn game và manifest build.
2. Trích xuất read-only các file localization/config cần thiết vào workspace
   bị ignore.
3. Ghi fingerprint snapshot để các bước sau phát hiện dữ liệu lẫn build.

`build.ps1`:

1. Chạy validator.
2. Tạo CSV/resource đầu vào sạch trong thư mục tạm.
3. Dùng toolchain khớp phiên bản để tạo `vi.translation` và metadata lựa chọn
   “Tiếng Việt”.
4. Tạo PCK ứng viên từ PCK gốc trong thư mục tạm, chỉ thay các path đã cho
   phép.
5. Mở lại PCK ứng viên, kiểm tra danh sách path và tạo manifest/checksum đầu
   ra trong `dist/`.

Không commit PCK đầu vào, PCK đầu ra hoặc tài nguyên đã trích xuất.

## 9. Cài đặt và gỡ cài đặt

`install.ps1` mặc định là dry-run. Ghi thật chỉ khi người dùng truyền `-Apply`.
Trước khi ghi, script phải:

1. Resolve đường dẫn tuyệt đối và xác nhận nó nằm đúng thư mục game được chỉ
   định.
2. Xác minh EXE version, Steam build khi có và SHA-256 PCK.
3. Xác minh checksum cùng manifest của artifact build.
4. Tạo backup timestamped kèm metadata hash; không ghi đè backup cũ.
5. Chuẩn bị file thay thế trên cùng volume và chỉ thay sau khi mọi kiểm tra
   hoàn tất.

Nếu có lỗi trước replace, PCK đang dùng không thay đổi. Nếu replace thành
công nhưng bước xác minh sau đó thất bại, script phải phục hồi ngay từ backup
vừa tạo và báo lỗi rõ. Không thêm retry/timeout để che nguyên nhân.

`uninstall.ps1` chỉ khôi phục backup có metadata hợp lệ và hash khớp; mặc định
cũng dry-run và chỉ ghi với `-Apply`. Nếu Steam đã cập nhật game sau khi cài
bản dịch, script không ghi đè build mới bằng backup cũ mà báo hướng phục hồi
qua Steam hoặc backup phù hợp.

## 10. Các đợt giao bản dịch

### Đợt 1 — Khung kỹ thuật và giao diện cơ bản

- Pipeline, manifest, backup/install/uninstall và báo cáo độ phủ.
- Menu, cài đặt, nút chung, tài nguyên, trạng thái, thông báo hệ thống.
- Xác minh chọn “Tiếng Việt”, font/dấu, save/load lựa chọn, kích thước nút và
  phục hồi bản gốc.

### Đợt 2 — Vòng chơi chính

- Công trình, nâng cấp, sản xuất, lao động, dân số, nghiên cứu, chính sách,
  thuế và tooltip.
- Rà glossary trên toàn bộ phạm vi đã dịch.

### Đợt 3 — Nội dung tiến trình

- Nhiệm vụ, hướng dẫn, giao thương, viễn chinh, chiến đấu, báo cáo và sự kiện.
- Kiểm tra đặc biệt các placeholder và nội dung biến thiên.

### Đợt 4 — Cốt truyện và hoàn thiện

- Lời dẫn và nội dung truyện còn lại.
- Rà ngữ cảnh, tràn chữ, độ tự nhiên và độ phủ 100% payload.
- Release ZIP chỉ gồm script, translation payload, checksum và hướng dẫn; nó
  không được chứa tài sản game gốc.

## 11. Kiểm thử và bằng chứng

### Tự động

- Unit test parser CSV, mapping key, glossary và coverage.
- Regression test placeholder, tag, escaped newline và Unicode tiếng Việt.
- Test lỗi cho key thiếu/dư/trùng, source drift và translation trống.
- Test PowerShell trên game fixture tổng hợp: dry-run, version mismatch,
  backup, lỗi giữa chừng, rollback và uninstall.
- Test archive ứng viên bằng cách mở lại và so path allowlist/checksum.
- Toàn bộ test dùng fixture do dự án tạo, không dùng asset game thật.

### Thủ công/runtime

- Build với bản game thật được cấp bởi người sở hữu.
- Lần smoke đầu dùng save thử hoặc new game, không dùng save quan trọng.
- Ghi riêng bằng chứng source, unit/build, smoke và nội dung đã quan sát trong
  game.
- Mỗi màn hình thuộc phạm vi đợt phải có checklist; nội dung chưa mở được giữ
  trạng thái `blocked` hoặc chưa xác minh.

### Review và checkpoint

- Logic mới thực hiện theo TDD: test đỏ đúng nguyên nhân, code tối thiểu, test
  xanh và chạy lại suite.
- Thay đổi đáng kể có review độc lập read-only trước khi kết luận.
- Sau mỗi checkpoint đã kiểm chứng, stage đúng file liên quan và tạo một commit
  riêng. Không dùng `git add -A` mù.
- Chỉ push khi sau này repo có remote được phép ghi; tạo repo local không đồng
  nghĩa được phép tạo remote hoặc PR.

## 12. Tiêu chí hoàn tất

Dự án hoàn tất đợt cuối khi:

- Validator báo không có lỗi chặn build và payload có độ phủ 100%.
- Mọi chuỗi không bị `blocked` đạt ít nhất `reviewed`; phạm vi quan trọng đã
  đạt `in_game` theo checklist.
- Build artifact được kiểm tra lại bằng tool đọc PCK và checksum khớp manifest.
- Cài/gỡ và rollback đã qua fixture test lẫn smoke trên bản 1.1.0.
- Font/dấu tiếng Việt, placeholder, tag và các màn hình chính đã được quan sát
  trong game.
- Release không chứa file game hoặc tài sản có bản quyền.
- README/runbook ghi đúng lệnh đã được chạy thực tế và giới hạn còn lại.

## 13. Quyết định đã chốt

- Văn phong: tự nhiên, dễ chơi.
- Phát hành theo bốn đợt có bản thử sớm.
- Cách tích hợp: patcher cục bộ chỉ thay tài nguyên localization, có backup và
  uninstall; không phát tán PCK hoàn chỉnh.
- Hệ công cụ: PowerShell cho Windows orchestration, Python qua `uv` cho xử lý
  dữ liệu, tool Godot/PCK portable được ghim và xác minh.
- Mặc định mọi thao tác ghi vào game là dry-run.
