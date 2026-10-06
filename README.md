# Việt hóa Hearth and Hamlet

Bản Việt hóa **Hearth and Hamlet** theo hướng tự nhiên, rõ nghĩa và dễ chơi.

Hiện tại dự án đã dịch **1.811/1.811 key phục hồi được** của Steam build
`25600292` (game `1.1.0.0`). Còn 27 dòng nguồn chưa thể phục hồi chắc chắn từ
PCK; game sẽ dùng tiếng Anh cho các dòng đó thay vì dự án tự đoán nội dung.

## Cài nhanh (không cần Python)

Cách dùng dành cho người chơi Windows thông thường: tải một file EXE, mở lên, rồi
để trình cài tự tìm game / dán đường dẫn nếu cần.

1. Tải từ [GitHub Releases](https://github.com/TimTini/hearth-and-hamlet-vietnamese/releases):
   - `Hearth-and-Hamlet-Tieng-Viet-Setup.exe`
   - `Hearth-and-Hamlet-Tieng-Viet-Setup.exe.sha256` (để đối chiếu checksum)
2. (Khuyến nghị) Kiểm tra SHA-256 của EXE trùng với file `.sha256`.
3. Đóng game nếu đang mở.
4. Chạy EXE. Trình cài sẽ:
   - tự tìm Steam Library / thư mục chứa EXE;
   - nếu không thấy, yêu cầu bạn dán đường dẫn thư mục `Hearth and Hamlet`;
   - xác minh đúng build `25600292` / version `1.1.0.0` và SHA-256 EXE/PCK;
   - tạo backup rồi cài bản Việt hóa, hoặc khôi phục bản gốc nếu đã cài trước đó.
5. Mở game bằng Steam, chọn ngôn ngữ **Tiếng Việt**.

Khôi phục bản gốc: chạy lại cùng EXE và chọn phục hồi, hoặc dùng:

```powershell
.\Hearth-and-Hamlet-Tieng-Viet-Setup.exe --restore --yes --no-pause
```

Backup nằm tại:

```text
%LOCALAPPDATA%\HearthAndHamletVietnamese\backups\25600292\<UTC timestamp>\
```

### Lưu ý Windows SmartScreen

EXE hiện **chưa ký Authenticode**. Windows có thể hiện cảnh báo SmartScreen.
Hãy đối chiếu SHA-256 trong release trước khi chạy. Nếu cảnh báo hiện lên, chọn
xem thêm chi tiết / Run anyway sau khi đã xác minh checksum.

### Copy thủ công (nếu không muốn chạy EXE)

Nếu bạn đã có PCK Việt hóa đã xác minh hash
`BEDB9B0A788AB5547A166197FB44648F92D09E550928D769B12F919A362A7227`:

1. Đóng game.
2. Sao lưu `Hearth and Hamlet.pck` gốc ra chỗ khác.
3. Thay file PCK trong thư mục game bằng bản Việt hóa.
4. Mở game và chọn **Tiếng Việt**.

Không phát hành nguyên PCK trên GitHub (chứa phần lớn dữ liệu game gốc). EXE
release chỉ nhúng delta Zstandard và tái tạo PCK từ bản game hợp pháp trên máy bạn.

## Yêu cầu

- Windows 10/11 x64.
- Hearth and Hamlet bản Steam build `25600292`, game version `1.1.0.0`.
- Đóng game trước khi cài hoặc phục hồi.

Repo chỉ chứa nội dung dịch, mã nguồn công cụ, manifest hỗ trợ, tài liệu và kiểm
thử. Repo không chứa file EXE/PCK/asset game. Bản phát hành GitHub chỉ có trình
cài và checksum.

## Cài bằng nguồn (nâng cao)

Dành cho người đóng góp hoặc khi muốn build lại từ source. Cần
[Python 3.12+](https://www.python.org/downloads/) và
[uv](https://docs.astral.sh/uv/getting-started/installation/).

Ví dụ đường dẫn game:

```powershell
$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\Hearth and Hamlet"
$AppManifest = Join-Path (Split-Path (Split-Path $GameDir -Parent) -Parent) "appmanifest_4315040.acf"
```

```powershell
git clone https://github.com/TimTini/hearth-and-hamlet-vietnamese.git
Set-Location .\hearth-and-hamlet-vietnamese
uv sync --locked
uv run hnh-vi verify-game --game-dir $GameDir --appmanifest $AppManifest
.\scripts\bootstrap.ps1
.\scripts\probe.ps1 -GameDir $GameDir
uv run hnh-vi validate --required-keys .\localization\phase1.keys
uv run hnh-vi coverage --selected-keys .\localization\phase1.keys
.\scripts\build.ps1 -GameDir $GameDir
$Artifact = ".\dist\25600292\Hearth-and-Hamlet-vi-preview-1.1.0.pck"
.\scripts\install.ps1 -GameDir $GameDir -Artifact $Artifact
.\scripts\install.ps1 -GameDir $GameDir -Artifact $Artifact -Apply
```

Gỡ / phục hồi bằng script:

```powershell
.\scripts\uninstall.ps1 -GameDir $GameDir
.\scripts\uninstall.ps1 -GameDir $GameDir -Apply
```

### Build lại trình cài một lần bấm

Cần PCK gốc và PCK Việt hóa đã đúng SHA-256 đã ghim:

```powershell
.\scripts\build-installer.ps1 `
  -OriginalPck "<đường dẫn PCK gốc>" `
  -TranslatedPck "<đường dẫn PCK Việt hóa>"
```

Output:

```text
dist\installer\Hearth-and-Hamlet-Tieng-Viet-Setup.exe
dist\installer\Hearth-and-Hamlet-Tieng-Viet-Setup.exe.sha256
```

## Các script và lệnh chính

| Lệnh | Chức năng | Có ghi vào game? |
|---|---|---|
| `Hearth-and-Hamlet-Tieng-Viet-Setup.exe` | Cài/khôi phục bản Việt hóa (không cần Python) | Có, sau xác nhận hoặc `--yes` |
| `scripts/build-installer.ps1` | Tạo EXE self-contained + checksum | Không |
| `scripts/bootstrap.ps1` | Tải/kiểm tra công cụ Godot và GDRE đã ghim | Không |
| `scripts/probe.ps1 -GameDir ...` | Phục hồi dữ liệu build tối thiểu vào `workspace/` | Không |
| `scripts/build.ps1 -GameDir ...` | Tạo PCK Việt hóa trong `dist/` | Không |
| `scripts/install.ps1 ...` | Dry-run kế hoạch cài | Không, trừ khi có `-Apply` |
| `scripts/uninstall.ps1 ...` | Dry-run kế hoạch gỡ | Không, trừ khi có `-Apply` |
| `uv run hnh-vi verify-game` | Xác minh fingerprint EXE/PCK/build Steam | Không |
| `uv run hnh-vi validate` | Kiểm tra key, hash, placeholder, BBCode và trạng thái dịch | Không |
| `uv run hnh-vi coverage` | Báo cáo độ phủ bản dịch | Không |

## Phát triển và đóng góp bản dịch

Quy tắc văn phong và thuật ngữ nằm trong
[`docs/translation-guide.md`](docs/translation-guide.md). Dữ liệu chính:

- `localization/translations.vi.csv`: key, hash nguồn và bản dịch tiếng Việt.
- `localization/status.csv`: trạng thái review của từng key.
- `localization/glossary.csv`: thuật ngữ thống nhất.
- `localization/phase1.keys`: toàn bộ key phục hồi được dùng cho bản build hiện tại.

```powershell
uv sync --locked
uv run hnh-vi validate --required-keys .\localization\phase1.keys
uv run hnh-vi coverage --selected-keys .\localization\phase1.keys
uv run pytest -q
uv run ruff check src tests/python
git diff --check
```

Checklist phát hành: [`docs/release-checklist.md`](docs/release-checklist.md).

## Giấy phép và quyền sở hữu

- Mã nguồn công cụ và script do dự án tạo được phát hành theo
  [MIT License](LICENSE).
- Nội dung tiếng Việt trong `localization/` được phát hành theo
  [CC BY-NC-SA 4.0](TRANSLATION-LICENSE.md), trong phạm vi người đóng góp có
  quyền cấp phép.
- Zstandard đi kèm trình cài theo BSD license tại
  `installer/third_party/zstd-LICENSE`.
- Tên game, nội dung gốc và mọi tài sản của Hearth and Hamlet thuộc chủ sở hữu
  tương ứng. Repo không cấp lại quyền đối với tài sản hoặc nội dung gốc của game.

## Giới hạn hiện tại

- Chỉ hỗ trợ Steam build `25600292` / game `1.1.0.0`.
- 1.811 key phục hồi được đã có bản dịch; 27 dòng chưa phục hồi dùng fallback
  tiếng Anh.
- Steam hiện chưa công bố Workshop cho game này; cài đặt dùng trình cài độc lập.
- EXE chưa ký số; SmartScreen có thể cảnh báo.
- Một số câu tiếng Việt dài hơn tiếng Anh; nếu gặp chữ tràn khung hoặc ngữ cảnh
  chưa tự nhiên, hãy mở issue kèm key hoặc ảnh chụp màn hình.

Đây là dự án cộng đồng, không liên kết hoặc được nhà phát triển game bảo trợ.
