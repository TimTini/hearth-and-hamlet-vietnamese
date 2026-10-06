# Việt hóa Hearth and Hamlet

Bản Việt hóa **Hearth and Hamlet** theo hướng tự nhiên, rõ nghĩa và dễ chơi.

Hiện tại dự án đã dịch **1.811/1.811 key phục hồi được** của Steam build
`25600292` (game `1.1.0.0`). Còn 27 dòng nguồn chưa thể phục hồi chắc chắn từ
PCK; game sẽ dùng tiếng Anh cho các dòng đó thay vì dự án tự đoán nội dung.

Repo chỉ chứa nội dung dịch, mã nguồn công cụ, manifest hỗ trợ, tài liệu và kiểm
thử. Repo không chứa file EXE, PCK, asset hoặc dữ liệu trích xuất từ game. Vì
vậy người dùng tự tạo bản vá từ bản game hợp pháp đang cài trên máy, sau đó mới
cài bản vá vào game.

## Yêu cầu

- Windows 10/11 và PowerShell.
- Hearth and Hamlet bản Steam build `25600292`, game version `1.1.0.0`.
- [Python 3.12+](https://www.python.org/downloads/) và
  [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Đóng game trước khi build, cài hoặc gỡ bản dịch.

Các lệnh dưới đây chạy từ thư mục repo. Ví dụ đường dẫn game mặc định:

```powershell
$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\Hearth and Hamlet"
$AppManifest = Join-Path (Split-Path (Split-Path $GameDir -Parent) -Parent) "appmanifest_4315040.acf"
```

Nếu Steam Library của bạn nằm ở ổ khác, thay `$GameDir` bằng đường dẫn thực tế.

## Cài bản Việt hóa

### 1. Tải repo và cài môi trường

```powershell
git clone https://github.com/TimTini/hearth-and-hamlet-vietnamese.git
Set-Location .\hearth-and-hamlet-vietnamese
uv sync --locked
```

### 2. Kiểm tra đúng phiên bản game

```powershell
uv run hnh-vi verify-game --game-dir $GameDir --appmanifest $AppManifest
```

Lệnh phải trả JSON có `"ok": true`. Tham số `--appmanifest` giúp kiểm tra cả
Steam build ID; bỏ tham số này thì công cụ chỉ xác minh fingerprint EXE/PCK. Nếu
báo `hash_mismatch` hoặc `steam_build_mismatch`, không tiếp tục cài: bản game
hiện tại chưa được dự án hỗ trợ hoặc Steam đã cập nhật game.

### 3. Chuẩn bị công cụ và nguồn cục bộ

```powershell
.\scripts\bootstrap.ps1
.\scripts\probe.ps1 -GameDir $GameDir
```

`bootstrap.ps1` tải đúng phiên bản Godot/GDRE đã ghim và kiểm tra SHA-256.
`probe.ps1` chỉ đọc PCK của game, phục hồi phần dữ liệu cần cho quá trình build
vào `workspace/` trên máy bạn. `workspace/` bị Git bỏ qua và không được upload.

### 4. Kiểm tra nội dung dịch và tạo bản vá

```powershell
uv run hnh-vi validate --required-keys .\localization\phase1.keys
uv run hnh-vi coverage --selected-keys .\localization\phase1.keys
.\scripts\build.ps1 -GameDir $GameDir
```

Artifact được tạo tại:

```text
dist\25600292\Hearth-and-Hamlet-vi-preview-1.1.0.pck
```

File JSON cùng tên chứa metadata và hash để script cài đặt xác minh lại.

### 5. Dry-run rồi cài thật

```powershell
$Artifact = ".\dist\25600292\Hearth-and-Hamlet-vi-preview-1.1.0.pck"

# Chỉ kiểm tra và in kế hoạch, chưa thay đổi game
.\scripts\install.ps1 -GameDir $GameDir -Artifact $Artifact

# Chỉ chạy sau khi dry-run thành công
.\scripts\install.ps1 -GameDir $GameDir -Artifact $Artifact -Apply
```

Khi `-Apply`, script tạo backup PCK gốc tại:

```text
%LOCALAPPDATA%\HearthAndHamletVietnamese\backups\25600292\<UTC timestamp>\
```

Sau khi cài, mở game bằng Steam, vào phần chọn ngôn ngữ, chọn **Tiếng Việt**.
Nếu giao diện chưa đổi ngay, thoát game rồi mở lại.

## Cập nhật lên bản dịch mới

Đóng game, gỡ bản vá hiện tại về PCK gốc, cập nhật repo rồi build/cài lại:

```powershell
.\scripts\uninstall.ps1 -GameDir $GameDir
.\scripts\uninstall.ps1 -GameDir $GameDir -Apply

git pull --ff-only
uv sync --locked
.\scripts\bootstrap.ps1
.\scripts\build.ps1 -GameDir $GameDir

$Artifact = ".\dist\25600292\Hearth-and-Hamlet-vi-preview-1.1.0.pck"
.\scripts\install.ps1 -GameDir $GameDir -Artifact $Artifact
.\scripts\install.ps1 -GameDir $GameDir -Artifact $Artifact -Apply
```

Lệnh build dùng lại dữ liệu trong `workspace/` đã tạo ở lần cài đầu. Nếu bạn đã
xóa `workspace/`, chạy lại `probe.ps1` trước `build.ps1`.

## Gỡ bản Việt hóa

Luôn chạy dry-run trước:

```powershell
# Kiểm tra backup phù hợp, không thay đổi game
.\scripts\uninstall.ps1 -GameDir $GameDir

# Phục hồi PCK gốc từ backup đã xác minh
.\scripts\uninstall.ps1 -GameDir $GameDir -Apply
```

Muốn chọn một backup cụ thể:

```powershell
.\scripts\uninstall.ps1 -GameDir $GameDir -Backup "<đường dẫn thư mục backup>"
.\scripts\uninstall.ps1 -GameDir $GameDir -Backup "<đường dẫn thư mục backup>" -Apply
```

Nếu Steam đã cập nhật game sau khi cài bản dịch, script sẽ từ chối ghi đè. Khi
đó dùng Steam **Verify integrity of game files**, rồi chờ dự án hỗ trợ build mới.

## Các script và lệnh chính

| Lệnh | Chức năng | Có ghi vào game? |
|---|---|---|
| `scripts/bootstrap.ps1` | Tải/kiểm tra công cụ Godot và GDRE đã ghim | Không |
| `scripts/probe.ps1 -GameDir ...` | Phục hồi dữ liệu build tối thiểu vào `workspace/` | Không |
| `scripts/extract.ps1 -GameDir ...` | Tạo snapshot trích xuất cục bộ phục vụ phát triển | Không |
| `scripts/build.ps1 -GameDir ...` | Tạo PCK Việt hóa trong `dist/` | Không |
| `scripts/install.ps1 ...` | Dry-run kế hoạch cài | Không, trừ khi có `-Apply` |
| `scripts/uninstall.ps1 ...` | Dry-run kế hoạch gỡ | Không, trừ khi có `-Apply` |
| `uv run hnh-vi verify-game` | Xác minh fingerprint EXE/PCK/build Steam | Không |
| `uv run hnh-vi validate` | Kiểm tra key, hash, placeholder, BBCode và trạng thái dịch | Không |
| `uv run hnh-vi coverage` | Báo cáo độ phủ bản dịch | Không |
| `uv run hnh-vi skeleton` | Đồng bộ khung CSV từ nguồn đã phục hồi | Chỉ ghi file CSV trong repo |

Các thao tác có thể thay game đều mặc định là dry-run. Chỉ `-Apply` mới ghi
thật. Install kiểm tra lại build, artifact, metadata và SHA-256; tạo backup trước
khi thay PCK; nếu kiểm tra sau khi thay thất bại, công cụ cố gắng khôi phục ngay
từ backup vừa tạo.

## Phát triển và đóng góp bản dịch

Quy tắc văn phong và thuật ngữ nằm trong
[`docs/translation-guide.md`](docs/translation-guide.md). Dữ liệu chính:

- `localization/translations.vi.csv`: key, hash nguồn và bản dịch tiếng Việt.
- `localization/status.csv`: trạng thái review của từng key.
- `localization/glossary.csv`: thuật ngữ thống nhất.
- `localization/phase1.keys`: toàn bộ key phục hồi được dùng cho bản build hiện tại.

Kiểm chứng trước khi gửi thay đổi:

```powershell
uv sync --locked
uv run hnh-vi validate --required-keys .\localization\phase1.keys
uv run hnh-vi coverage --selected-keys .\localization\phase1.keys
uv run pytest -q
uv run ruff check src tests/python
git diff --check
```

Kiểm thử cài/gỡ dùng game tổng hợp trong thư mục tạm, không ghi vào bản game
Steam thật. `.gitignore` loại khỏi repo dữ liệu game phục hồi, artifact build,
backup, log, bản nháp nội bộ và các mẫu credential/cookie phổ biến.

## Giấy phép và quyền sở hữu

- Mã nguồn công cụ và script do dự án tạo được phát hành theo
  [MIT License](LICENSE).
- Nội dung tiếng Việt trong `localization/` được phát hành theo
  [CC BY-NC-SA 4.0](TRANSLATION-LICENSE.md), trong phạm vi người đóng góp có
  quyền cấp phép.
- Tên game, nội dung gốc và mọi tài sản của Hearth and Hamlet thuộc chủ sở hữu
  tương ứng. Repo không cấp lại quyền đối với tài sản hoặc nội dung gốc của game.

## Giới hạn hiện tại

- Chỉ hỗ trợ Steam build `25600292` / game `1.1.0.0`.
- 1.811 key phục hồi được đã có bản dịch; 27 dòng chưa phục hồi dùng fallback
  tiếng Anh.
- Một số câu tiếng Việt dài hơn tiếng Anh; nếu gặp chữ tràn khung hoặc ngữ cảnh
  chưa tự nhiên, hãy mở issue kèm key hoặc ảnh chụp màn hình.

Đây là dự án cộng đồng, không liên kết hoặc được nhà phát triển game bảo trợ.
