# Thiết kế phục hồi localization key còn thiếu

Ngày: 2026-10-06

Trạng thái: Đã được người dùng duyệt ngày 2026-10-06; người dùng giao agent tự
quyết chi tiết kế hoạch và yêu cầu bắt đầu dịch.

Repo: `<RepoRoot>`

Thiết kế liên quan: `docs/superpowers/specs/2026-10-06-partial-source-release-design.md`

## 1. Mục tiêu

Phục hồi chính xác tối đa 27 localization key mà GDRE 2.7.0 chưa tìm được,
không chặn việc Việt hóa các key đã biết và không đưa diagnostic code vào
artifact phát hành.

Ưu tiên phục hồi offline. Runtime instrumentation chỉ được dùng sau khi
fixture tổng hợp chứng minh được cơ chế và chỉ trong artifact chẩn đoán tạm.

## 2. Cơ sở kỹ thuật

`OptimizedTranslation` giữ bảng băm phục vụ lookup nhưng không giữ danh sách
key nguồn có thể liệt kê ngược. `Translation` có virtual `_get_message()` có
thể quan sát `src_message`, nhưng dùng hook đó để ghi log là kỹ thuật chẩn
đoán cần được chứng minh trên fixture và đúng build, không phải logging contract
được Godot bảo đảm.

Nguồn chính thức dùng để khóa thiết kế:

- `https://docs.godotengine.org/en/4.5/classes/class_translation.html`
- `https://docs.godotengine.org/en/4.5/classes/class_optimizedtranslation.html`
- `https://docs.godotengine.org/en/4.5/classes/class_translationserver.html`
- `https://github.com/GDRETools/gdsdecomp/blob/master/standalone/gdre_main.gd`

## 3. Hai tầng phục hồi

### Tầng A — offline hints

Tạo hint input local, bị Git ignore, từ các nguồn đã có quyền đọc:

- Key/string trong resource, scene và script đã phục hồi.
- Candidate do marker recovery cung cấp.
- Key đã quan sát và xác minh từ diagnostic log trước đó.

Chạy GDRE với `--translation-hint`, rồi chỉ chấp nhận kết quả khi:

- Số marker chưa phục hồi giảm.
- Tổng row, locale và source resource vẫn đúng.
- Key mới không trùng/xung đột với key đã biết.
- Kết quả lặp lại deterministically từ cùng PCK và hint input.

Hint hoặc câu tiếng Anh đầy đủ không được commit. Git chỉ ghi count/hash và
mapping key đã được xác minh qua dataset bình thường.

### Tầng B — runtime diagnostic

Chỉ bắt đầu nếu tầng A vẫn còn marker và fixture feasibility đã đạt.

Diagnostic resource kế thừa `Translation`, nhận lookup cho locale `vi`, giữ
delegate tới dữ liệu vi đã biết và ghi lại key mà delegate không có. Nó không
tự dịch, không sửa save và không gửi dữ liệu qua mạng. Lookup thiếu tiếp tục
đi theo fallback `en`.

Việc gắn resource vào main translation domain phải được chứng minh bằng
fixture; không giả định thứ tự `add_translation()` hoặc wrapper delegation.
Nếu không thể gắn ổn định mà không sửa executable, tầng runtime dừng và các
key còn lại tiếp tục `blocked`.

## 4. Diagnostic artifact và log

Diagnostic artifact có tên/path riêng dưới `dist/<build-id>/diagnostic/`, bị
Git ignore và không thể được installer release chấp nhận nhầm.

Log nằm dưới workspace hoặc user-data path dành riêng, bị Git ignore. Log có
thể chứa key nguồn để phục hồi, nhưng báo cáo đã commit chỉ chứa:

- Build ID và PCK hash.
- Diagnostic artifact hash.
- Số key quan sát, số key mới xác minh và số key còn blocked.
- Runtime checklist đã đi qua.

Không commit câu tiếng Anh, save, cấu hình người dùng hoặc log thô.

## 5. Vòng đời an toàn

Mọi command diagnostic mặc định dry-run. Trước real apply phải:

1. Xác minh đúng build/PCK.
2. Xác minh fixture và synthetic diagnostic tests đang xanh.
3. Tạo backup nhất quán và metadata/hash phục hồi.
4. Dùng new game hoặc save thử.
5. Nhận chấp thuận riêng cho thao tác apply/launch ngoài worktree.

Sau phiên quan sát:

1. Đóng game.
2. Gỡ diagnostic artifact và phục hồi hash PCK gốc.
3. Xác minh game khởi động lại ở bản gốc hoặc preview không diagnostic.
4. Import key mới qua offline hint/snapshot/validator; không nhập thẳng log
   vào release dataset.

Diagnostic artifact không bao giờ được đóng gói trong release ZIP.

## 6. Coverage recovery

Runtime chỉ tìm được key thuộc màn hình/trạng thái đã đi qua. Checklist phải
ghi rõ nhóm UI, gameplay state và flow đã quan sát; một lượt chơi ngắn không
được coi là phục hồi đủ.

Mỗi key mới có trạng thái recovery riêng trong workspace local:

- `observed`: thấy trong log nhưng chưa tái xác minh offline.
- `verified`: GDRE/hint tái tạo được snapshot ổn định.
- `integrated`: đã vào dataset và qua validator.

Chỉ `integrated` mới làm giảm `unrecovered_rows` trong completeness manifest.

## 7. Kiểm thử

Fixture Godot phải chứng minh:

- Custom `Translation` nhận đúng key thiếu, không log key đã có và không phá
  fallback tiếng Anh.
- Duplicate lookup được deduplicate deterministically.
- Log không được ghi vào repo hoặc game directory.
- Artifact diagnostic và release có path/metadata khác nhau; installer từ
  chối diagnostic artifact trong release mode.
- Apply lỗi giữa chừng rollback được; uninstall phục hồi hash gốc.
- Key quan sát nhưng chưa verify không được nhập vào dataset.

Runtime trên game thật chỉ là bằng chứng bổ sung sau fixture; không thay thế
unit/integration test.

## 8. Tiêu chí chấp nhận và lối thoát

Tầng offline hoàn tất khi chạy lặp lại cho cùng kết quả và mọi key mới qua
duplicate/source validation.

Tầng runtime feasibility hoàn tất khi fixture chứng minh hook, fallback,
logging, apply và uninstall. Real runtime recovery có thể tiến dần theo các
phiên chơi; nó không chặn preview release.

Nếu hook không hoạt động ổn định hoặc cần sửa executable, runtime recovery
dừng với bằng chứng rõ. Project vẫn phát hành preview từ key đã biết và giữ
count còn thiếu trung thực.

## 9. Ranh giới kế hoạch

Spec này có implementation plan riêng, bắt đầu bằng offline-hint recovery và
synthetic runtime feasibility. Real apply/launch là checkpoint cần chấp thuận
riêng; phương thức thực thi code là subagent-driven.
