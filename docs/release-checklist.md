# Release checklist — one-click installer

Use this before creating or replacing GitHub Release `v1.1.0-vi.1`.

## Build inputs

- [ ] Original PCK SHA-256 is `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`
- [ ] Translated PCK SHA-256 is `BEDB9B0A788AB5547A166197FB44648F92D09E550928D769B12F919A362A7227`
- [ ] Game EXE SHA-256 is `7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A`
- [ ] `scripts/build-installer.ps1 -OriginalPck ... -TranslatedPck ...` exits 0
- [ ] Output name is exactly `dist/installer/Hearth-and-Hamlet-Tieng-Viet-Setup.exe`
- [ ] Adjacent `.sha256` matches `Get-FileHash -Algorithm SHA256`

## Verification

- [ ] `dotnet test installer/tests/... --configuration Release`
- [ ] `uv run pytest -q`
- [ ] `uv run ruff check src tests/python`
- [ ] `uv run hnh-vi validate --required-keys .\localization\phase1.keys`
- [ ] `uv run hnh-vi coverage --selected-keys .\localization\phase1.keys`
- [ ] Copied-game E2E: install → translated hash; backup → original hash; restore → original hash
- [ ] Copied-game E2E: wrong PCK exits nonzero and leaves files unchanged

## Security / privacy

- [ ] No complete PCK committed or uploaded
- [ ] No credentials, cookies, emails, or personal machine paths in tracked files
- [ ] Only branch `main` exists locally and on `origin`
- [ ] Release assets are exactly the EXE plus `.sha256`

## Publish

- [ ] Documentation commit pushed to `main`
- [ ] Annotated tag `v1.1.0-vi.1` points at the pushed commit
- [ ] GitHub Release contains the two assets; re-download verifies checksum
