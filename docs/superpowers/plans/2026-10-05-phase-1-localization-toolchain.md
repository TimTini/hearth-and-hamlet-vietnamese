# Phase 1 Localization Toolchain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tạo toolchain đã kiểm thử và bản Việt hóa thử Đợt 1 cho Hearth and Hamlet 1.1.0, gồm giao diện cơ bản, build PCK ứng viên, cài/gỡ có backup và bằng chứng smoke test.

**Architecture:** Python thuần chạy bằng `uv` sở hữu schema, fingerprint, validator và CLI; các script PowerShell mỏng điều phối đường dẫn Windows và thao tác cài/gỡ. GDRE Tools 2.7.0 và Godot 4.6.3 là dependency portable được ghim URL/SHA-256 trong manifest; dữ liệu game trích xuất, PCK và backup luôn nằm ngoài Git.

**Tech Stack:** Python 3.12+, `uv`, `pytest`, `ruff`, Windows PowerShell 5.1+, GDRE Tools 2.7.0, Godot 4.6.3-stable, Git.

**Spec:** `docs/superpowers/specs/2026-10-05-hearth-and-hamlet-vietnamese-design.md`

## Global Constraints

- Chỉ hỗ trợ ban đầu EXE 1.1.0.0, Steam build `25600292`, EXE SHA-256 `7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A`, PCK SHA-256 `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`.
- Không commit hoặc phát hành EXE, DLL, PCK, asset, source English đầy đủ hay output đã trích xuất từ game.
- `translations.vi.csv` chỉ commit `key`, `source_sha256`, `translation_vi`; source English đầy đủ chỉ ở `workspace/` bị ignore.
- Mọi script ghi vào thư mục game mặc định dry-run; ghi thật cần `-Apply`.
- Không sửa save game, không chạy dịch vụ mạng ngoài tải dependency đã ghim, không cài dependency toàn hệ thống.
- Mọi logic mới đi theo RED → GREEN → REFACTOR; mỗi task kết thúc bằng suite xanh và một commit riêng với staging hẹp.
- PowerShell phải chạy được với đường dẫn chứa khoảng trắng và dùng `-LiteralPath` cho thao tác file.
- Nếu probe cho thấy danh sách ngôn ngữ bị hardcode hoặc GDRE không tạo resource tương thích, dừng trước khi patch game thật, cập nhật spec/plan và xin duyệt lại.

## Review Focus

- CSV UTF-8 BOM, dấu phẩy/dấu nháy và newline nằm trong ô phải được đọc/ghi không làm đổi key hoặc nội dung.
- Placeholder gồm `%s`, `%d`, positional printf, `%%`, `{name}` và BBCode lồng nhau phải được bảo toàn chính xác.
- Đường dẫn game/tool có khoảng trắng hoặc ký tự Unicode phải được resolve và quote đúng, không tách argument.
- Steam update hoặc install bị ngắt giữa replace phải không làm mất PCK dùng được và không được khôi phục nhầm backup cũ.
- Key trùng, source hash drift và row status không tồn tại phải tạo lỗi có vị trí, không bị bỏ qua hoặc tự sửa ngầm.

---

### Task 1: Project Core and Supported-Build Fingerprint

**Files:**
- Create: `pyproject.toml`
- Create: `src/hnh_vi/__init__.py`
- Create: `src/hnh_vi/builds.py`
- Create: `manifests/game-builds.json`
- Create: `tests/python/test_builds.py`
- Modify: `.gitignore`
- Modify: `README.md`

**Interfaces:**
- Produces: `BuildSpec`, `load_build_specs(path: Path) -> tuple[BuildSpec, ...]`, `sha256_file(path: Path) -> str`, `verify_game_dir(game_dir: Path, spec: BuildSpec, appmanifest: Path | None = None) -> VerificationResult`.
- `VerificationResult` exposes `ok: bool` and ordered `issues: tuple[str, ...]` without printing paths or file contents beyond names/hash evidence.

- [ ] **Step 1: Write failing manifest and path tests**

Add tests named `test_loads_supported_build_25600292`, `test_verifies_matching_fixture_hashes`, `test_rejects_hash_mismatch_without_mutation`, `test_rejects_missing_files`, and `test_accepts_game_path_with_spaces_and_unicode`. Use only synthetic temporary files; assert exact issue codes `missing_file`, `hash_mismatch`, and `steam_build_mismatch`.

- [ ] **Step 2: Run tests and verify RED**

Run: `uv run pytest tests/python/test_builds.py -q`

Expected: FAIL because `hnh_vi.builds` and the manifest do not exist.

- [ ] **Step 3: Implement the minimal project core**

Set `requires-python = ">=3.12"`; use only stdlib at runtime and add `pytest` plus `ruff` as development dependencies. Implement the interfaces above and add the exact supported-build fingerprints from Global Constraints to `manifests/game-builds.json`.

- [ ] **Step 4: Verify GREEN and lint**

Run: `uv run pytest tests/python/test_builds.py -q`

Expected: all Task 1 tests PASS.

Run: `uv run ruff check src tests/python/test_builds.py`

Expected: exit 0.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- pyproject.toml uv.lock src/hnh_vi/__init__.py src/hnh_vi/builds.py manifests/game-builds.json tests/python/test_builds.py .gitignore README.md
git commit -m "feat: verify supported game builds"
```

### Task 2: Pinned Portable Tool Bootstrap

**Files:**
- Create: `src/hnh_vi/tools.py`
- Create: `manifests/tools.json`
- Create: `scripts/bootstrap.ps1`
- Create: `tests/python/test_tools.py`
- Create: `tests/python/test_bootstrap_script.py`

**Interfaces:**
- Consumes: repository root and `.tools/` ignore rule from Task 1.
- Produces: `ToolSpec`, `load_tool_specs(path: Path) -> tuple[ToolSpec, ...]`, `ensure_tool(spec: ToolSpec, tools_dir: Path) -> Path`.
- `scripts/bootstrap.ps1 [-RepoRoot <path>] [-Offline]` calls the Python interface through `uv run`; `-Offline` never performs a network request.

Tool manifest values:

- `gdre-tools` version `2.7.0`, asset `GDRE_tools-v2.7.0-windows.zip`, URL `https://github.com/GDRETools/gdsdecomp/releases/download/v2.7.0/GDRE_tools-v2.7.0-windows.zip`, SHA-256 `92a8d5d3d5c0cca159fc6cc34ebdda2cf7e1b448035cdabe1a67f0981cbd0a2c`.
- `godot` version `4.6.3-stable`, asset `Godot_v4.6.3-stable_win64.exe.zip`, URL `https://github.com/godotengine/godot-builds/releases/download/4.6.3-stable/Godot_v4.6.3-stable_win64.exe.zip`, SHA-256 `e39986a178d585ce7ac198fb8de6ea436366dc0cc00e594810c2e3e104c04b90`.

- [ ] **Step 1: Write failing bootstrap tests**

Use a real local ZIP addressed by `Path.as_uri()` to test download/extract without mocking. Add tests for matching digest, mismatched digest removing the partial archive, offline reuse, offline missing tool, path with spaces/Unicode, and archive path traversal rejection. The script test invokes `powershell.exe -NoProfile -File scripts/bootstrap.ps1 -Offline` against a temporary repo root and asserts a nonzero exit with `tool_missing_offline`.

- [ ] **Step 2: Run tests and verify RED**

Run: `uv run pytest tests/python/test_tools.py tests/python/test_bootstrap_script.py -q`

Expected: FAIL because tool bootstrap does not exist.

- [ ] **Step 3: Implement verified download and extraction**

Use `urllib.request` and `zipfile`; download to a temporary sibling, verify SHA-256 before extraction, reject absolute/parent-traversal members, extract to a temporary directory, then rename to `.tools/<id>/<version>`. Do not alter PATH or install globally. Make the PowerShell wrapper contain orchestration only.

- [ ] **Step 4: Verify GREEN and tool manifest syntax**

Run: `uv run pytest tests/python/test_tools.py tests/python/test_bootstrap_script.py -q`

Expected: all Task 2 tests PASS.

Run: `uv run ruff check src tests/python`

Expected: exit 0.

- [ ] **Step 5: Commit Task 2**

```powershell
git add -- src/hnh_vi/tools.py manifests/tools.json scripts/bootstrap.ps1 tests/python/test_tools.py tests/python/test_bootstrap_script.py
git commit -m "feat: bootstrap pinned localization tools"
```

### Task 3: Read-Only Extraction and Compatibility Probe

**Files:**
- Create: `src/hnh_vi/workspace.py`
- Create: `scripts/extract.ps1`
- Create: `scripts/probe.ps1`
- Create: `tests/fixtures/godot_project/project.godot`
- Create: `tests/fixtures/godot_project/make_fixture.gd`
- Create: `tests/fixtures/godot_project/localisation/translations.csv`
- Create: `tests/python/test_workspace.py`
- Create: `tests/python/test_extract_integration.py`
- Modify: `work/hearth-and-hamlet-vietnamese-progress.md`

**Interfaces:**
- Consumes: `verify_game_dir`, pinned GDRE/Godot executable paths.
- Produces: `WorkspaceSnapshot(build_id: str, pck_sha256: str, source_csv_sha256: str, extracted_at_utc: str)`, `write_snapshot(path: Path, snapshot: WorkspaceSnapshot) -> None`, `verify_snapshot(snapshot_path: Path, source_csv: Path, source_pck: Path, expected_build_id: str) -> VerificationResult`.
- `scripts/extract.ps1 -GameDir <path> [-RepoRoot <path>]` verifies the build before running GDRE and writes only under `workspace/<build-id>/`.
- `scripts/probe.ps1` records GDRE/Godot versions, PCK file listing, CSV headers/locales and whether language selection is dynamic or hardcoded; it never writes to the game directory.

- [ ] **Step 1: Write failing workspace tests**

Test deterministic snapshot JSON, source CSV drift, PCK drift, missing workspace files, and a repo/game path containing spaces. Integration setup uses the real portable Godot `PCKPacker` fixture script to create a synthetic PCK, then the real GDRE CLI to extract `res://localisation/translations.csv`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest tests/python/test_workspace.py -q`

Expected: FAIL because `hnh_vi.workspace` is absent.

- [ ] **Step 3: Implement snapshot and extraction orchestration**

Keep Python responsible for snapshot validation and PowerShell responsible for invoking GDRE with an argument array. `extract.ps1` must fail before invoking GDRE when fingerprint verification fails.

- [ ] **Step 4: Bootstrap real tools and run synthetic integration**

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap.ps1`

Expected: pinned tools installed under `.tools/` with matching checksums.

Run: `uv run pytest tests/python/test_workspace.py tests/python/test_extract_integration.py -q -m integration`

Expected: PASS; synthetic PCK remains unchanged and extracted CSV matches the fixture hash.

- [ ] **Step 5: Probe the owned 1.1.0 source read-only**

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/extract.ps1 -GameDir "<GameDir>"`

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/probe.ps1 -GameDir "<GameDir>"`

Expected: source fingerprint matches build `25600292`; probe confirms actual CSV schema and determines how `Scenes/language.gdc`/`globals/language_manager.gdc` populate locales. Do not continue if locale selection is hardcoded or the probe cannot explain it.

- [ ] **Step 6: Update evidence and commit Task 3**

Record only schema names, counts, hashes, tool versions and compatibility conclusions in the progress log; do not commit extracted sentences or scripts.

```powershell
git add -- src/hnh_vi/workspace.py scripts/extract.ps1 scripts/probe.ps1 tests/fixtures/godot_project tests/python/test_workspace.py tests/python/test_extract_integration.py work/hearth-and-hamlet-vietnamese-progress.md
git commit -m "feat: extract localization data safely"
```

### Task 4: Translation Dataset and Contract Validator

**Files:**
- Create: `src/hnh_vi/dataset.py`
- Create: `src/hnh_vi/contracts.py`
- Create: `src/hnh_vi/coverage.py`
- Create: `localization/glossary.csv`
- Create: `localization/translations.vi.csv`
- Create: `localization/status.csv`
- Create: `tests/fixtures/localization/source.csv`
- Create: `tests/fixtures/localization/translations.vi.csv`
- Create: `tests/fixtures/localization/status.csv`
- Create: `tests/python/test_dataset.py`
- Create: `tests/python/test_contracts.py`
- Create: `tests/python/test_coverage.py`

**Interfaces:**
- Consumes: actual source schema conclusion from Task 3.
- Produces: `SourceRow`, `TranslationRow`, `StatusRow`, `GlossaryTerm`, `load_source_csv(path: Path) -> tuple[SourceRow, ...]`, `load_translation_csv(path: Path) -> tuple[TranslationRow, ...]`, `validate_dataset(source: tuple[SourceRow, ...], translations: tuple[TranslationRow, ...], statuses: tuple[StatusRow, ...], glossary: tuple[GlossaryTerm, ...], required_keys: frozenset[str] | None = None) -> ValidationReport`, `calculate_coverage(translations: tuple[TranslationRow, ...], statuses: tuple[StatusRow, ...], selected_keys: frozenset[str] | None = None) -> CoverageReport`.
- `ValidationReport.errors` and `.warnings` are ordered issue objects containing `code`, `key`, and safe metadata; they never copy the complete English source into committed reports.

- [ ] **Step 1: Write failing CSV and contract tests**

Cover UTF-8 with BOM, quoted comma/newline, duplicate key, missing/extra key, `source_sha256` drift, missing status, empty translation in `required_keys`, empty translation outside `required_keys` remaining a coverage gap rather than a build error, Vietnamese Unicode normalization, `%s`, `%2$d`, `%%`, `{name}`, escaped `\n`, balanced/nested BBCode, glossary warning, and deterministic coverage counts by all four statuses.

- [ ] **Step 2: Run tests and verify RED**

Run: `uv run pytest tests/python/test_dataset.py tests/python/test_contracts.py tests/python/test_coverage.py -q`

Expected: FAIL because dataset/validator modules do not exist.

- [ ] **Step 3: Implement minimal parsing, validation and coverage**

Use `csv`, `hashlib`, `re`, `unicodedata` and dataclasses only. Preserve source row order; never silently normalize keys or placeholders. Normalize `translation_vi` to NFC only when writing a generated build workspace, not while loading committed input.

- [ ] **Step 4: Verify GREEN and full Python suite**

Run: `uv run pytest tests/python -q`

Expected: all tests through Task 4 PASS.

Run: `uv run ruff check src tests/python`

Expected: exit 0.

- [ ] **Step 5: Commit Task 4**

```powershell
git add -- src/hnh_vi/dataset.py src/hnh_vi/contracts.py src/hnh_vi/coverage.py localization tests/fixtures/localization tests/python/test_dataset.py tests/python/test_contracts.py tests/python/test_coverage.py
git commit -m "feat: validate Vietnamese translation contracts"
```

### Task 5: CLI, Skeleton Generation, and Safe Reports

**Files:**
- Create: `src/hnh_vi/cli.py`
- Create: `src/hnh_vi/__main__.py`
- Create: `tests/python/test_cli.py`
- Modify: `pyproject.toml`
- Modify: `README.md`

**Interfaces:**
- Consumes: dataset, validator, coverage and workspace interfaces.
- Produces console command `hnh-vi` with subcommands:
  - `verify-game --game-dir <path> [--appmanifest <path>]`
  - `skeleton --source <ignored-source.csv> --translations <path> --statuses <path>`
  - `validate --source <ignored-source.csv> --translations <path> --statuses <path> --glossary <path> [--required-keys <path>] [--json <path>]`
  - `coverage` with the same dataset inputs and optional `--selected-keys <path>`.
- Exit codes: `0` success, `2` invalid user input, `3` unsupported/drifted build, `4` translation contract failure, `5` tool/build failure.

- [ ] **Step 1: Write failing CLI tests**

Invoke the installed console script through `uv run hnh-vi`. Assert deterministic JSON, exact exit codes, no full English source in report output, skeleton rows contain only `key,source_sha256,translation_vi`, and rerunning skeleton preserves existing Vietnamese/status data while adding new keys explicitly.

- [ ] **Step 2: Run tests and verify RED**

Run: `uv run pytest tests/python/test_cli.py -q`

Expected: FAIL because the CLI entry point is absent.

- [ ] **Step 3: Implement the argparse CLI**

Use stdlib `argparse`; keep output encoding UTF-8 and machine-readable issue codes. Skeleton generation must never delete or rewrite an existing translation without an explicit source match.

- [ ] **Step 4: Verify GREEN and package entry point**

Run: `uv run pytest tests/python -q`

Expected: full Python suite PASS.

Run: `uv run hnh-vi --help`

Expected: exit 0 and four subcommands listed.

- [ ] **Step 5: Commit Task 5**

```powershell
git add -- src/hnh_vi/cli.py src/hnh_vi/__main__.py tests/python/test_cli.py pyproject.toml uv.lock README.md
git commit -m "feat: add localization workflow CLI"
```

### Task 6: Deterministic Translation Patch Build

**Files:**
- Create: `src/hnh_vi/build.py`
- Create: `scripts/build.ps1`
- Create: `tests/python/test_build.py`
- Create: `tests/python/test_build_integration.py`
- Modify: `tests/fixtures/godot_project/localisation/translations.csv`

**Interfaces:**
- Consumes: verified workspace snapshot, valid Vietnamese dataset, pinned GDRE executable.
- Produces: `merge_translation_csv(source_path: Path, translations_path: Path, output_path: Path, locale: str = "vi") -> BuildInput`; `BuildArtifact(path: Path, sha256: str, source_pck_sha256: str, locale: str, patched_paths: tuple[str, ...])`.
- `scripts/build.ps1 -GameDir <path> [-RepoRoot <path>]` writes only to `dist/<build-id>/` and temporary workspace. For build `25600292`, the final files are `dist/25600292/Hearth-and-Hamlet-vi-1.1.0.pck` and `dist/25600292/Hearth-and-Hamlet-vi-1.1.0.json`.
- GDRE invocation uses `--headless --pck-patch=<source.pck> --patch-translations=<merged.csv>=res://localisation/translations.csv --locales=vi --output=<candidate.pck>`.

- [ ] **Step 1: Write failing merge and build tests**

Test output column order, UTF-8/NFC Vietnamese, refusal on any validator error, source snapshot drift, deterministic artifact metadata, and no mutation of source PCK. Integration test patches the synthetic PCK, lists it again with GDRE, and asserts `translations.vi.translation` plus the original locales exist.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest tests/python/test_build.py -q`

Expected: FAIL because `hnh_vi.build` is absent.

- [ ] **Step 3: Implement merge/build orchestration**

Build to a temporary sibling under `dist/<build-id>/`, verify GDRE exit code and expected paths by reopening/listing the candidate, then rename the artifact and write JSON metadata/checksum. Never build in or write to the game directory.

- [ ] **Step 4: Verify synthetic PCK GREEN**

Run: `uv run pytest tests/python/test_build.py tests/python/test_build_integration.py -q -m integration`

Expected: PASS; source fixture PCK hash unchanged, candidate contains all original locale resources and `vi`.

- [ ] **Step 5: Commit Task 6**

```powershell
git add -- src/hnh_vi/build.py scripts/build.ps1 tests/python/test_build.py tests/python/test_build_integration.py tests/fixtures/godot_project/localisation/translations.csv
git commit -m "feat: build deterministic Vietnamese PCK patches"
```

### Task 7: Phase 1 Vietnamese Content and Real Candidate

**Files:**
- Create: `localization/phase1.keys`
- Modify: `localization/glossary.csv`
- Modify: `localization/translations.vi.csv`
- Modify: `localization/status.csv`
- Modify: `work/hearth-and-hamlet-vietnamese-progress.md`

**Interfaces:**
- Consumes: ignored English source snapshot, skeleton/validate/coverage CLI and build script.
- Produces: all Phase 1 keys translated with status at least `reviewed`; a real candidate PCK under ignored `dist/25600292/`.

- [ ] **Step 1: Generate the real skeleton without committing source English**

Run `uv run hnh-vi skeleton` against `workspace/25600292/localisation/translations.csv`. Confirm `git diff` contains keys, hashes and empty Vietnamese cells only; verify no full source CSV appears in Git status.

- [ ] **Step 2: Define and translate the Phase 1 key set**

Select menu, settings, common buttons, resource names, state labels and system notifications from the actual source. Add their keys to `phase1.keys`, translate in natural/easy Vietnamese, add glossary decisions and mark reviewed rows. Preserve names/placeholders/tags exactly.

- [ ] **Step 3: Validate and inspect coverage**

Run: `uv run hnh-vi validate --source workspace/25600292/localisation/translations.csv --translations localization/translations.vi.csv --statuses localization/status.csv --glossary localization/glossary.csv --required-keys localization/phase1.keys`

Expected: exit 0, zero blocking errors.

Run: `uv run hnh-vi coverage --source workspace/25600292/localisation/translations.csv --translations localization/translations.vi.csv --statuses localization/status.csv --glossary localization/glossary.csv --selected-keys localization/phase1.keys`

Expected: every key in `phase1.keys` has a nonempty translation and status `reviewed`; non-Phase-1 rows may remain `draft`/empty and are reported separately.

- [ ] **Step 4: Build the real candidate without installing it**

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1 -GameDir "<GameDir>"`

Expected: artifact and metadata created under ignored `dist/25600292/`; original game PCK hash remains exactly `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`.

- [ ] **Step 5: Commit Task 7**

```powershell
git add -- localization/phase1.keys localization/glossary.csv localization/translations.vi.csv localization/status.csv work/hearth-and-hamlet-vietnamese-progress.md
git commit -m "feat: translate phase 1 interface text"
```

### Task 8: Dry-Run Installer, Atomic Apply, Rollback, and Uninstall

**Files:**
- Create: `src/hnh_vi/install.py`
- Create: `scripts/install.ps1`
- Create: `scripts/uninstall.ps1`
- Create: `tests/python/test_install.py`
- Create: `tests/python/test_install_scripts.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: verified `BuildArtifact` metadata and supported `BuildSpec`.
- Produces: `InstallPlan`, `BackupRecord`, `plan_install(game_dir: Path, artifact_path: Path, artifact_metadata_path: Path, backup_root: Path) -> InstallPlan`, `apply_install(plan: InstallPlan) -> BackupRecord`, `plan_uninstall(game_dir: Path, backup_record_path: Path) -> InstallPlan`, `apply_uninstall(plan: InstallPlan) -> None`.
- Backups live under `%LOCALAPPDATA%\HearthAndHamletVietnamese\backups\<build-id>\<UTC timestamp>\` with JSON metadata and verified PCK copy.
- `install.ps1 -GameDir <path> -Artifact <path> [-Apply]`; `uninstall.ps1 -GameDir <path> [-Backup <path>] [-Apply]`.

- [ ] **Step 1: Write failing install-state tests**

Use only synthetic game directories. Test default dry-run, unsupported hash, artifact mismatch, existing verified backup reuse rules, timestamped non-overwrite, path with spaces/Unicode, candidate staged on the game volume, failed pre-replace leaving original unchanged, simulated failed post-replace verification rolling back, Steam-updated PCK refusing old uninstall, and successful uninstall restoring the exact original hash.

- [ ] **Step 2: Run tests and verify RED**

Run: `uv run pytest tests/python/test_install.py tests/python/test_install_scripts.py -q`

Expected: FAIL because installer interfaces/scripts do not exist.

- [ ] **Step 3: Implement fail-closed install state machine**

Use `shutil.copy2`, fsync/close, SHA-256 verification and same-directory `os.replace` for the final swap. On any post-swap verification error, restore the just-created verified backup before returning failure. Do not catch and downgrade configuration/hash errors.

- [ ] **Step 4: Verify GREEN and full suite**

Run: `uv run pytest -q`

Expected: all unit and synthetic integration tests PASS.

Run: `uv run ruff check src tests`

Expected: exit 0.

- [ ] **Step 5: Verify real dry-run only**

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install.ps1 -GameDir "<GameDir>" -Artifact "dist/25600292/Hearth-and-Hamlet-vi-1.1.0.pck"`

Expected: reports the exact source/artifact hashes, planned backup location and replacement; original PCK hash remains unchanged.

- [ ] **Step 6: Commit Task 8**

```powershell
git add -- src/hnh_vi/install.py scripts/install.ps1 scripts/uninstall.ps1 tests/python/test_install.py tests/python/test_install_scripts.py README.md
git commit -m "feat: install and restore localization safely"
```

### Task 9: Independent Review, Real Apply, Runtime Smoke, and Phase 1 Handoff

**Files:**
- Create: `docs/phase-1-smoke-checklist.md`
- Create: `docs/translation-guide.md`
- Modify: `README.md`
- Modify: `localization/status.csv`
- Modify: `work/hearth-and-hamlet-vietnamese-progress.md`

**Interfaces:**
- Consumes: complete Phase 1 implementation and real build artifact.
- Produces: independent review findings resolved, clean verification run, runtime evidence by screen, and exact install/uninstall commands for the user.

- [ ] **Step 1: Request independent read-only review**

Dispatch a fresh reviewer with the spec, this plan, base SHA before Task 1 and current HEAD. Require findings with file/line/risk for correctness, data loss, path safety, copyright boundary, translation contract and missing tests. Resolve every Critical/Important finding with a new failing test before code changes.

- [ ] **Step 2: Run the complete verification chain fresh**

Run: `uv sync --locked`

Run: `uv run pytest -q`

Run: `uv run ruff check src tests`

Run: `git diff --check`

Run both synthetic extraction and build integration tests explicitly. Expected: every command exits 0; report exact test counts and any skipped markers.

- [ ] **Step 3: Apply the real candidate with backup**

Re-run build verification and the Task 8 dry-run command immediately before apply. Then run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install.ps1 -GameDir "<GameDir>" -Artifact "dist/25600292/Hearth-and-Hamlet-vi-1.1.0.pck" -Apply`. Expected: backup metadata/hash valid and installed PCK hash equals artifact metadata. If any check differs, stop without launching the game.

- [ ] **Step 4: Perform runtime smoke test**

Launch the owned game and check: Vietnamese appears in language selection; switching locale works; relaunch preserves locale; diacritics render; Phase 1 menus/settings/buttons/resources/status/notifications display; placeholders and BBCode render; representative long labels do not clip materially. Use a new/test save. Record observed screens and mark only observed keys `in_game`.

- [ ] **Step 5: Prove uninstall and restore**

Close the game, run uninstall dry-run then `-Apply`, and verify the restored PCK hash equals the original supported-build hash. Launch once in English to confirm the original build starts. Reinstall only if the user wants to continue playing the Phase 1 build.

- [ ] **Step 6: Update docs and progress evidence**

Document commands actually run, exit codes, test counts, tool versions, runtime observations, untranslated/blocked keys and next task for Phase 2. Do not claim full-game coverage.

- [ ] **Step 7: Commit Task 9**

```powershell
git add -- docs/phase-1-smoke-checklist.md docs/translation-guide.md README.md localization/status.csv work/hearth-and-hamlet-vietnamese-progress.md
git commit -m "docs: hand off phase 1 localization"
```

## Plan Self-Review Result

- Spec coverage: Phase 1 covers bootstrap, extraction, source drift, dataset, validator, coverage, build, dry-run/apply/rollback/uninstall, review and runtime smoke. Phases 2–4 intentionally require later content-focused plans after Phase 1 runtime evidence.
- Step scan: every production-code task begins with named failing tests; content/docs steps use the validator and runtime checklist rather than pretending prose has a RED test.
- Type consistency: `BuildSpec`, `VerificationResult`, `WorkspaceSnapshot`, `ValidationReport`, `CoverageReport`, `BuildArtifact`, `InstallPlan` and `BackupRecord` have one owner task and downstream consumers named explicitly.
- Review Focus coverage: CSV edge cases are in Task 4; placeholders/tags in Task 4; spaced/Unicode paths in Tasks 1–3 and 8; interrupted install/Steam update in Task 8; duplicate keys/source drift/status gaps in Task 4.
- Proportion: the plan specifies interfaces, observable assertions and commands; implementation bodies are left to the worker except where safety semantics require an exact operation.
