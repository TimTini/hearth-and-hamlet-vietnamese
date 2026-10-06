# Thiết kế phát hành sớm từ nguồn phục hồi chưa đầy đủ

Ngày: 2026-10-06

Trạng thái: Chờ người dùng duyệt bản spec đã lưu

Repo: `<RepoRoot>`

Thiết kế gốc: `docs/superpowers/specs/2026-10-05-hearth-and-hamlet-vietnamese-design.md`

Thiết kế liên quan: `docs/superpowers/specs/2026-10-06-runtime-key-recovery-design.md`

## 1. Bối cảnh và mục tiêu

Steam build `25600292` chứa `1.849` dòng translation nhưng không chứa CSV
nguồn. GDRE 2.7.0 phục hồi đủ schema và số dòng, nhưng `27` dòng vẫn mang
marker `MissingKey`; `1.822` dòng còn lại có định danh đã phục hồi. Số dòng
không được coi là số unique key. Audit read-only xác nhận có `1.810` unique
key đã biết: chín nhóm key trùng tạo thêm 12 dòng. Cả chín nhóm có cùng nguồn
English cho một key; khác biệt chỉ nằm ở locale khác.

Mục tiêu của thiết kế này là cho phép Việt hóa và phát hành bản thử theo từng
đợt mà không phải chờ phục hồi đủ 27 key, đồng thời không che giấu giới hạn
nguồn hoặc tuyên bố sai độ phủ toàn game.

## 2. Phạm vi

Trong phạm vi:

- Manifest an toàn mô tả độ đầy đủ của snapshot nguồn bằng count và hash.
- Dataset, validator và coverage phân biệt key đã biết với dòng chưa phục hồi.
- Build preview có fallback tiếng Anh rõ ràng và metadata trung thực.
- Bốn đợt dịch đã duyệt tiếp tục dùng văn phong tự nhiên, dễ chơi.

Ngoài phạm vi:

- Khôi phục 27 key tại runtime; việc đó thuộc spec runtime recovery riêng.
- Cam kết mọi nội dung đã được dịch trong bản preview đầu tiên.
- Commit CSV tiếng Anh trích xuất, marker có câu nguồn, asset hoặc script game.

## 3. Nguồn sự thật và manifest completeness

CSV phục hồi đầy đủ vẫn nằm trong `workspace/<build-id>/` và bị Git ignore.
Git chỉ chứa `localization/source-completeness.json` với schema xác định:

- `schema_version`: `1`.
- `build_id`: `"25600292"`.
- `pck_sha256`: hash PCK được hỗ trợ.
- `recovered_csv_sha256`: hash CSV phục hồi local.
- `total_rows`: `1849`.
- `recovered_rows`: `1822`.
- `unique_recovered_keys`: `1810`.
- `duplicate_key_groups`: `9`.
- `duplicate_extra_rows`: `12`.
- `unrecovered_rows`: `27`.
- `fallback_locale`: `"en"`.
- `policy`: `"partial_with_english_fallback"`.
- `source_complete`: `false` cho đến khi không còn marker chưa phục hồi.

Manifest không chứa câu tiếng Anh hoặc marker đầy đủ. Mọi thay đổi build ID,
PCK hash, CSV hash, schema hoặc count phải làm validation/build dừng; không tự
động cập nhật manifest để hợp thức hóa source drift.

## 4. Dataset và trạng thái

`translations.vi.csv` tiếp tục dùng đúng ba cột:

- `key`
- `source_sha256`
- `translation_vi`

Chỉ dòng có key nguồn thật mới được đưa vào dataset đã commit. Không tạo key
giả từ index, marker hoặc nội dung tiếng Anh đoán được.

`status.csv` tiếp tục dùng `draft`, `reviewed`, `in_game`, `blocked` cho các
key đã biết. Hai mươi bảy dòng chưa biết được theo dõi ở cấp completeness
manifest, không được tạo 27 status row giả. Khi recovery xác minh được một key,
key đó đi qua skeleton/source-hash bình thường rồi mới xuất hiện trong dataset.

Validator phải audit duplicate key trước khi tính unique-key coverage. Các row
có cùng key và cùng English source hash được canonicalize thành một translation
row, nhưng vẫn sinh warning kèm occurrence count; không âm thầm chọn dòng cuối.
Nếu cùng key nhưng English source hash khác nhau, validation dừng vì một locale
vi không thể biểu diễn hai source khác nhau cho cùng lookup key.

## 5. Validation và coverage

Build bị chặn khi:

- Fingerprint build/PCK/CSV hoặc các count không khớp completeness manifest.
- Marker chưa phục hồi lọt vào translation dataset hoặc `phaseN.keys`.
- Required key của đợt hiện tại thiếu bản dịch, còn `draft`/`blocked`, hoặc vi
  phạm placeholder, tag, newline, Unicode hay source hash.
- Fallback locale không còn là `en` hoặc bản dịch `en` gốc không còn trong PCK.

Key đã biết nhưng ngoài phạm vi đợt hiện tại có thể để `translation_vi` trống;
đó là coverage gap, không phải contract error.

Coverage report bắt buộc tách:

- `total_source_rows`, `recovered_rows`, `unrecovered_rows`.
- `unique_recovered_keys` sau duplicate audit.
- Số key có bản dịch, `reviewed`, `in_game`, `blocked` trên toàn dataset.
- Số key và tỷ lệ riêng của đợt được chọn.
- `source_complete` và `maximum_known_source_ratio`.

Không trường nào được làm tròn thành hoặc trình bày như `100% toàn game` khi
`source_complete=false`.

## 6. Build và fallback

Build preview chỉ tạo locale `vi` từ các row có `translation_vi` hợp lệ. Các
key vi không có message sẽ dùng luồng fallback của Godot. Project hiện không
ghi đè `locale/fallback`, nên fallback mặc định là `en`; build vẫn phải xác
minh resource `en` gốc tồn tại trước khi phát hành.

Metadata artifact phải ghi:

- `release_quality`: `"preview"`.
- `source_complete`: `false`.
- `fallback_locale`: `"en"`.
- Các count completeness và coverage của đợt.
- Hash PCK nguồn, artifact và các path được patch.

Artifact preview không được chứa diagnostic script hoặc log runtime.

## 7. Trình tự giao bản dịch

Giữ bốn đợt đã duyệt:

1. Pipeline và giao diện cơ bản.
2. Vòng chơi chính.
3. Nội dung tiến trình.
4. Cốt truyện và hoàn thiện.

Mỗi đợt chỉ yêu cầu 100% `reviewed` trong `phaseN.keys`; các key đã biết ngoài
đợt và 27 dòng chưa biết vẫn được báo riêng. Sau khi recovery bổ sung key mới,
chúng được phân loại vào đợt phù hợp và không làm mất bản dịch đã có.

## 8. Kiểm thử và tiêu chí chấp nhận

Fixture phải bao phủ:

- CSV có marker chưa phục hồi, duplicate giống nhau và duplicate xung đột.
- Manifest count/hash đúng và mọi dạng drift.
- Required key không được dùng marker hoặc key giả.
- Locale vi thiếu key thực sự fallback sang en trong fixture Godot.
- Metadata preview không tuyên bố source hoàn chỉnh.
- Skeleton chạy lại giữ nguyên bản dịch/status hiện có khi key mới được phục hồi.

Spec hoàn tất khi pipeline có thể tạo preview cho một phase đã dịch đầy đủ,
validator không có lỗi chặn, coverage công bố đúng giới hạn nguồn, PCK gốc
không đổi và artifact không chứa dữ liệu chẩn đoán.

## 9. Ranh giới kế hoạch

Spec này có implementation plan riêng, tiếp tục từ Task 4 của Phase 1 và
không bao gồm runtime instrumentation. Việc thực thi dùng phương thức
subagent-driven đã được người dùng chọn.
