# Thiết kế trình cài bản Việt hóa một lần bấm

## Mục tiêu

Phát hành `Hearth-and-Hamlet-Tieng-Viet-Setup.exe` trên GitHub Releases để người
dùng Windows 10/11 có thể cài hoặc khôi phục bản Việt hóa mà không cần Python,
uv, Git, Godot hay GDRE. Trình cài chỉ hỗ trợ Steam build `25600292`, game
`1.1.0.0`, và phải từ chối mọi file game không khớp fingerprint đã biết.

## Phạm vi phát hành

- GitHub Release chứa một EXE tự chứa và file SHA-256 tương ứng.
- Không commit hoặc phát hành PCK hoàn chỉnh, file game gốc, dữ liệu trích xuất,
  đường dẫn máy cá nhân, credential hay cookie.
- EXE nhúng một delta tạo từ PCK gốc hợp pháp sang PCK Việt hóa, cùng bản Windows
  x64 của Zstandard đã ghim phiên bản và kiểm tra hash. Zstandard giữ nguyên giấy
  phép BSD đi kèm trong repo.
- Source, test và script tái tạo installer được commit; payload và binary build
  vẫn nằm trong thư mục bị Git bỏ qua.

## Trải nghiệm người dùng

1. Người dùng tải rồi mở EXE.
2. Trình cài tìm game theo thứ tự: thư mục chứa EXE, thư mục làm việc hiện tại,
   Steam mặc định và các thư viện trong `libraryfolders.vdf`.
3. Nếu không tìm thấy, chương trình yêu cầu người dùng dán đường dẫn thư mục
   `Hearth and Hamlet`.
4. Chương trình hiển thị hành động phù hợp: cài nếu PCK là bản gốc; khôi phục nếu
   PCK là bản Việt hóa. Chế độ dòng lệnh cho test dùng `--install`, `--restore`,
   `--game-dir`, `--yes` và `--no-pause`.
5. Trước khi ghi, chương trình hiển thị thư mục và yêu cầu xác nhận, trừ khi có
   `--yes`.
6. Khi cài, chương trình tạo backup trong
   `%LOCALAPPDATA%\HearthAndHamletVietnamese\backups\25600292\<UTC timestamp>`,
   tạo PCK mới trong thư mục game, kiểm tra SHA-256 rồi mới thay thế file đích.
7. Khi khôi phục, chương trình chỉ dùng backup có metadata và hash hợp lệ, đồng
   thời từ chối ghi đè nếu Steam đã cập nhật hoặc file hiện tại không đúng bản
   Việt hóa đã biết.

## Kiến trúc

- `Installer.Core`: phát hiện Steam/game, kiểm tra fingerprint, quản lý backup,
  điều phối cài/khôi phục và thay file có rollback. Logic không phụ thuộc UI để
  có thể unit test bằng thư mục tổng hợp.
- `Installer.App`: giao diện console tiếng Việt, parser tham số và exit code rõ
  ràng. Payload Zstandard và delta được đọc từ embedded resources, chỉ giải nén
  vào thư mục tạm riêng rồi xóa khi hoàn tất.
- `Installer.Tests`: kiểm tra phát hiện đường dẫn, từ chối build sai, backup,
  cài, khôi phục, rollback và đường dẫn Unicode/khoảng trắng.
- `scripts/build-installer.ps1`: xác minh hash hai PCK đầu vào, tải Zstandard từ
  release chính thức bằng URL/hash đã ghim, tạo delta, build .NET 8
  `win-x64` self-contained single-file và sinh file `.sha256`.

## Toàn vẹn và an toàn

- Hash PCK gốc:
  `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`.
- Hash PCK Việt hóa:
  `BEDB9B0A788AB5547A166197FB44648F92D09E550928D769B12F919A362A7227`.
- Hash EXE game:
  `7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A`.
- Không yêu cầu quyền quản trị. Nếu Steam Library không cho ghi, báo lỗi rõ và
  không tự nâng quyền.
- Giữ read-lock trên EXE game trong lúc thao tác; việc thay PCK dùng file tạm cùng
  volume và rollback khi kiểm tra sau thay thất bại.
- Mọi đường dẫn filesystem dùng API literal, không ghép thành shell command.
- Installer không kết nối mạng lúc chạy và không thu thập telemetry.
- Binary chưa ký số; README và release notes nói rõ Windows SmartScreen có thể
  cảnh báo và cung cấp SHA-256 để đối chiếu.

## Kiểm chứng và tiêu chí phát hành

- Unit test .NET chạy xanh; test Python/ruff hiện có không hồi quy.
- Build self-contained single-file thành đúng tên yêu cầu.
- E2E trên bản sao PCK gốc: cài tạo đúng hash PCK Việt hóa và backup đúng hash
  PCK gốc; khôi phục trả lại đúng hash gốc.
- E2E build sai chứng minh không thay file và không tạo backup.
- Quét repo, lịch sử commit mới và binary strings để không có secret, đường dẫn
  cá nhân hoặc PCK đầy đủ; xác nhận asset không phải archive chứa PCK.
- Review độc lập không còn finding Critical/Important.
- Chỉ nhánh `main`; commit được push trước khi tạo tag/release. Release asset và
  checksum tải lại được và khớp hash local.

## Ngoài phạm vi

- Không hỗ trợ Steam Workshop vì build hiện tại không công bố Workshop.
- Không tự động hỗ trợ build game khác; mỗi build mới cần fingerprint và delta
  mới, rồi phát hành installer mới.
- Không ký Authenticode khi chưa có chứng thư ký mã.
