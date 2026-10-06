# Partial-Source Vietnamese Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, validate and translate a safe Phase 1 Vietnamese preview from the 1,811 known localization keys while reporting 27 unrecovered source rows and retaining English fallback.

**Architecture:** The ignored recovered CSV remains the source of truth, while a committed completeness manifest pins its hashes and counts. Dataset/contract/coverage code canonicalizes same-source duplicates, excludes missing-key markers, and permits preview builds only for fully reviewed phase keys; build and install remain deterministic, fail-closed and dry-run by default.

**Tech Stack:** Python 3.12 standard library via `uv`, pytest, Ruff, PowerShell 5.1, pinned Godot 4.6.3 and GDRE 2.7.0.

**Spec:** `docs/superpowers/specs/2026-10-06-partial-source-release-design.md`

## Global Constraints

- Only Steam build `25600292` is supported: EXE SHA-256 `7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A`, PCK SHA-256 `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`.
- Completeness is pinned to 1,849 total rows, 1,822 recovered rows, 1,811 unique recovered keys, eight duplicate-key groups, 11 duplicate extra rows and 27 unrecovered rows.
- Ruling 2026-10-06: preserve exact, case-sensitive key identity without stripping, normalization or casefolding. The previous 1,810/9/12 audit used PowerShell Group-Object's case-insensitive grouping; source fingerprints are unchanged.
- Never commit the recovered English CSV, raw missing-key markers, recovered game scripts, binaries, tools, logs, saves or user configuration.
- `translations.vi.csv` has exactly `key,source_sha256,translation_vi`; translation prose is natural, easy to play and NFC-normalized only in generated build workspaces.
- A same-key/same-English-hash duplicate is canonicalized with a warning; a same-key/different-English-hash duplicate blocks validation.
- Preview builds must retain the original English translation and declare `release_quality=preview`, `source_complete=false`, and `fallback_locale=en`.
- Every operation that could write the game is dry-run by default. This plan stops after the real install dry-run; `-Apply` and launching the game require a later explicit checkpoint.
- EXE/PCK read handles and the hard-link/symlink/junction protections established in Task 3 remain mandatory for every real-game command.
- Use only stdlib and existing pinned tools; no new runtime dependency.
- Stage only task-owned files and commit each reviewed task separately; no push because the repo has no remote.

## Review Focus

- A recovered CSV with unchanged row count but changed marker/duplicate distribution must fail completeness verification; Task 1 owns this regression.
- Duplicate keys with identical English source but conflicting non-English columns must canonicalize safely for vi without hiding the duplicate warning; Task 1 owns this regression.
- Empty translations outside the selected phase must fall back, while an empty selected key must block the build; Tasks 2 and 4 own this regression.
- Candidate metadata must not report full coverage or accept a diagnostic artifact; Task 4 owns this regression.
- Installer interruption, Steam-updated source and hard-link aliases must preserve or restore the exact original PCK; Task 6 owns this regression.

---

### Task 1: Source Completeness and Canonical Dataset

**Files:**
- Create: `src/hnh_vi/completeness.py`
- Create: `src/hnh_vi/dataset.py`
- Create: `localization/source-completeness.json`
- Create: `tests/fixtures/localization/source-partial.csv`
- Create: `tests/fixtures/localization/source-completeness.json`
- Create: `tests/python/test_completeness.py`
- Create: `tests/python/test_dataset.py`
- Modify: `work/hearth-and-hamlet-vietnamese-progress.md`

**Interfaces:**
- Consumes: ignored recovered CSV and Task 3 `WorkspaceSnapshot`/supported-build fingerprint.
- Produces: `SourceCompleteness`, `SourceRow`, `CanonicalSource`, `load_source_completeness(path: Path) -> SourceCompleteness`, `audit_source_csv(path: Path, expected: SourceCompleteness) -> CanonicalSource`.
- `CanonicalSource.rows` contains one row per real localization key in source order; `.issues` contains deterministic safe metadata without full English text.

- [ ] **Step 1: Write failing completeness and dataset tests**

Test exact manifest values, UTF-8 BOM/quoted newline, all missing-key marker positions, a marker text change with unchanged count, nine synthetic same-English duplicate groups, same-key/different-English conflict, distinct case/whitespace variant keys with the same English hash, stable first-occurrence order, source hash drift, count drift, missing columns and paths containing spaces/Unicode. Assert the fixture audit yields its expected canonical key count and that issue metadata contains no complete source sentence.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest tests/python/test_completeness.py tests/python/test_dataset.py -q`

Expected: FAIL because `hnh_vi.completeness` and `hnh_vi.dataset` do not exist.

- [ ] **Step 3: Implement parsing and canonicalization**

Use `csv`, `dataclasses`, `hashlib`, `json` and `pathlib`. Missing-key rows are counted but never exposed as buildable keys. Canonicalize duplicates only when their English source hashes match; retain occurrence count in a warning and block conflicting hashes.

- [ ] **Step 4: Verify the real ignored source read-only**

Run the audit against `workspace/25600292/probe/source/localisation/translations.csv` and `localization/source-completeness.json`.

Expected: 1,849 total rows, 1,822 recovered rows, 1,811 canonical keys, eight duplicate groups, 11 duplicate extra rows, 27 unrecovered rows, no blocking issue; no game write and no English source in Git diff.

- [ ] **Step 5: Run GREEN, Ruff and commit**

Run: `uv run pytest tests/python/test_completeness.py tests/python/test_dataset.py -q`

Run: `uv run ruff check src tests/python`

Expected: both exit 0.

```powershell
git add -- src/hnh_vi/completeness.py src/hnh_vi/dataset.py localization/source-completeness.json tests/fixtures/localization/source-partial.csv tests/fixtures/localization/source-completeness.json tests/python/test_completeness.py tests/python/test_dataset.py work/hearth-and-hamlet-vietnamese-progress.md
git commit -m "feat: audit partial localization sources"
```

### Task 2: Translation Contracts and Coverage

**Files:**
- Create: `src/hnh_vi/contracts.py`
- Create: `src/hnh_vi/coverage.py`
- Create: `localization/glossary.csv`
- Create: `localization/translations.vi.csv`
- Create: `localization/status.csv`
- Create: `tests/fixtures/localization/translations.vi.csv`
- Create: `tests/fixtures/localization/status.csv`
- Create: `tests/fixtures/localization/glossary.csv`
- Create: `tests/python/test_contracts.py`
- Create: `tests/python/test_coverage.py`

**Interfaces:**
- Consumes: `CanonicalSource` and `SourceCompleteness` from Task 1.
- Produces: `TranslationRow`, `StatusRow`, `GlossaryTerm`, `ValidationIssue`, `ValidationReport`, `CoverageReport`, `load_translation_csv(path: Path) -> tuple[TranslationRow, ...]`, `load_status_csv(path: Path) -> tuple[StatusRow, ...]`, `load_glossary_csv(path: Path) -> tuple[GlossaryTerm, ...]`, `validate_dataset(source: CanonicalSource, translations: tuple[TranslationRow, ...], statuses: tuple[StatusRow, ...], glossary: tuple[GlossaryTerm, ...], required_keys: frozenset[str] | None = None) -> ValidationReport`, `calculate_coverage(source: CanonicalSource, translations: tuple[TranslationRow, ...], statuses: tuple[StatusRow, ...], selected_keys: frozenset[str] | None = None) -> CoverageReport`.

- [ ] **Step 1: Write failing contract and coverage tests**

Cover duplicate/missing/extra translation keys, source-hash drift, missing status, invalid status, empty required translation, allowed empty non-required translation, missing-key marker in dataset/phase selection, NFC, `%s`, `%2$d`, `%%`, `{name}`, escaped `\n`, balanced/nested BBCode, glossary warning, deterministic issue ordering and the full/known/selected coverage fields from the spec.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest tests/python/test_contracts.py tests/python/test_coverage.py -q`

Expected: FAIL because contract and coverage modules do not exist.

- [ ] **Step 3: Implement minimal validation and coverage**

Use stdlib only. Never include full English source in `ValidationIssue` or reports. Preserve input data on load; NFC normalization happens only when a build workspace is generated.

- [ ] **Step 4: Verify GREEN and full suite**

Run: `uv run pytest tests/python/test_contracts.py tests/python/test_coverage.py -q`

Run: `uv run pytest -q`

Run: `uv run ruff check src tests/python`

Expected: all commands exit 0.

- [ ] **Step 5: Commit Task 2**

```powershell
git add -- src/hnh_vi/contracts.py src/hnh_vi/coverage.py localization/glossary.csv localization/translations.vi.csv localization/status.csv tests/fixtures/localization/translations.vi.csv tests/fixtures/localization/status.csv tests/fixtures/localization/glossary.csv tests/python/test_contracts.py tests/python/test_coverage.py
git commit -m "feat: validate partial Vietnamese translations"
```

### Task 3: Workflow CLI and Safe Skeleton Updates

**Files:**
- Create: `src/hnh_vi/cli.py`
- Create: `src/hnh_vi/__main__.py`
- Create: `tests/python/test_cli.py`
- Modify: `pyproject.toml`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1–2 dataset, completeness, validation and coverage interfaces plus existing `verify_game_dir`.
- Produces console command `hnh-vi` with `verify-game`, `skeleton`, `validate`, and `coverage` subcommands.
- Exit codes: `0` success, `2` invalid input, `3` unsupported/drifted build or completeness mismatch, `4` translation contract failure, `5` tool/build failure.

- [ ] **Step 1: Write failing CLI tests**

Invoke `uv run hnh-vi`. Assert deterministic UTF-8 JSON, exact exit codes, no full English source in stdout/report, skeleton columns exactly `key,source_sha256,translation_vi`, exclusion of missing-key markers, canonical duplicate handling, and rerun preservation of existing translation/status while adding newly verified keys.

- [ ] **Step 2: Run tests and verify RED**

Run: `uv run pytest tests/python/test_cli.py -q`

Expected: FAIL because the entry point is absent.

- [ ] **Step 3: Implement the argparse CLI**

Use stdlib `argparse`. Require the completeness manifest for skeleton/validate/coverage; no command may silently regenerate or approve changed counts/hashes.

- [ ] **Step 4: Generate the real safe skeleton**

Run `skeleton` against the ignored recovered source. Inspect `git diff` and assert it contains only keys, source hashes, empty Vietnamese values and status metadata; the full recovered CSV remains ignored.

- [ ] **Step 5: Verify and commit**

Run: `uv run pytest tests/python/test_cli.py -q`

Run: `uv run pytest -q`

Run: `uv run hnh-vi --help`

Run: `uv run ruff check src tests/python`

Expected: all commands exit 0 and help lists four subcommands.

```powershell
git add -- src/hnh_vi/cli.py src/hnh_vi/__main__.py tests/python/test_cli.py pyproject.toml uv.lock README.md localization/translations.vi.csv localization/status.csv
git commit -m "feat: add partial localization workflow CLI"
```

### Task 4: Deterministic Preview Patch Build

**Files:**
- Create: `src/hnh_vi/build.py`
- Create: `scripts/build.ps1`
- Create: `tests/python/test_build.py`
- Create: `tests/python/test_build_integration.py`
- Modify: `tests/fixtures/godot_project/localisation/translations.csv`

**Interfaces:**
- Consumes: verified `WorkspaceSnapshot`, `SourceCompleteness`, valid Vietnamese dataset and pinned GDRE.
- Produces: `BuildInput`, `BuildArtifact`, `merge_translation_csv(source_path: Path, canonical_source: CanonicalSource, translations_path: Path, output_path: Path, locale: str = "vi") -> BuildInput`, `verify_build_artifact(path: Path, metadata_path: Path) -> BuildArtifact`.
- `scripts/build.ps1 -GameDir <path> [-RepoRoot <path>]` writes only to temporary workspace and `dist/<build-id>/`.
- Real output names: `dist/25600292/Hearth-and-Hamlet-vi-preview-1.1.0.pck` and matching `.json`.

- [ ] **Step 1: Write failing merge/build tests**

Test canonical key order, empty non-selected vi cells omitted from the vi resource, required empty key rejection, NFC output, source/completeness drift, English resource retention, exact preview metadata fields, diagnostic metadata rejection and no source PCK mutation.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest tests/python/test_build.py -q`

Expected: FAIL because `hnh_vi.build` is absent.

- [ ] **Step 3: Implement merge and build orchestration**

Invoke GDRE with `--pck-patch`, `--patch-translations=<merged.csv>=res://localisation/translations.csv`, `--locales=vi` and a temporary output. Reopen/list the candidate before atomic publish. Metadata must include source/artifact hashes, patched paths, completeness and selected-phase coverage.

- [ ] **Step 4: Prove fallback and artifact contents with real synthetic tools**

Use Godot/GDRE fixture integration to assert original locales plus `vi` exist, a vi key translates, a vi-missing key returns English, diagnostic paths are absent and source PCK hash is unchanged.

- [ ] **Step 5: Verify and commit**

Run: `uv run pytest tests/python/test_build.py tests/python/test_build_integration.py -q -m integration`

Run: `uv run pytest -q`

Run: `uv run ruff check src tests/python`

Expected: all commands exit 0.

```powershell
git add -- src/hnh_vi/build.py scripts/build.ps1 tests/python/test_build.py tests/python/test_build_integration.py tests/fixtures/godot_project/localisation/translations.csv
git commit -m "feat: build partial Vietnamese preview patches"
```

### Task 5: Phase 1 Natural Vietnamese Content

**Files:**
- Create: `localization/phase1.keys`
- Create: `docs/translation-guide.md`
- Modify: `localization/glossary.csv`
- Modify: `localization/translations.vi.csv`
- Modify: `localization/status.csv`
- Modify: `work/hearth-and-hamlet-vietnamese-progress.md`

**Interfaces:**
- Consumes: ignored source alongside CLI skeleton/validate/coverage and the approved natural/easy Vietnamese style.
- Produces: every recovered Phase 1 menu, settings, common button, resource, state and system-notification key translated and at least `reviewed`; an ignored real preview candidate.

- [ ] **Step 1: Define the Phase 1 key list from the real source**

Select only recovered keys for menus, settings, common actions, resource names, state labels and system notifications. Exclude missing markers and content whose context cannot be established. Record scope counts, not the English source table, in the progress log.

- [ ] **Step 2: Translate and establish the glossary**

Translate `phase1.keys` in natural, concise Vietnamese. Preserve names, placeholders, BBCode and required newlines exactly; prefer consistent gameplay terminology over literal wording. Mark uncertain context `blocked` rather than guessing.

- [ ] **Step 3: Validate and revise until clean**

Run `hnh-vi validate` with `--required-keys localization/phase1.keys` and fix every blocking issue. Run coverage for the selected keys; expected selected keys are 100% nonempty and `reviewed`, while global/source completeness remains explicitly partial.

- [ ] **Step 4: Build the real candidate without installing**

Run `scripts/build.ps1` against the owned game. Expected: preview PCK/metadata under ignored `dist/25600292/`, original EXE/PCK hashes unchanged and metadata reports the exact partial-source ceiling.

- [ ] **Step 5: Review content and commit**

Perform an independent language/contract review of the selected rows. Resolve unnatural phrasing, glossary drift and placeholder/tag findings before commit.

```powershell
git add -- localization/phase1.keys localization/glossary.csv localization/translations.vi.csv localization/status.csv docs/translation-guide.md work/hearth-and-hamlet-vietnamese-progress.md
git commit -m "feat: translate phase 1 interface text"
```

### Task 6: Dry-Run Installer, Atomic Apply and Uninstall

**Files:**
- Create: `src/hnh_vi/install.py`
- Create: `scripts/install.ps1`
- Create: `scripts/uninstall.ps1`
- Create: `tests/python/test_install.py`
- Create: `tests/python/test_install_scripts.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: verified preview `BuildArtifact` and supported `BuildSpec`.
- Produces: `InstallPlan`, `BackupRecord`, `plan_install(game_dir: Path, artifact_path: Path, artifact_metadata_path: Path, backup_root: Path) -> InstallPlan`, `apply_install(plan: InstallPlan) -> BackupRecord`, `plan_uninstall(game_dir: Path, backup_record_path: Path) -> InstallPlan`, `apply_uninstall(plan: InstallPlan) -> None`.
- Backups live under `%LOCALAPPDATA%\HearthAndHamletVietnamese\backups\<build-id>\<UTC timestamp>\` with verified JSON metadata and PCK copy.
- `install.ps1 -GameDir <path> -Artifact <path> [-Apply]`; `uninstall.ps1 -GameDir <path> [-Backup <path>] [-Apply]`.

- [ ] **Step 1: Write failing install-state tests**

Use synthetic game directories only. Cover default dry-run, unsupported/source drift, artifact mismatch, diagnostic artifact rejection, verified non-overwriting backup, spaces/Unicode, same-volume staging, pre-replace failure, post-replace rollback, Steam-updated source, hard-link/symlink/junction outputs and exact uninstall restore.

- [ ] **Step 2: Run tests and verify RED**

Run: `uv run pytest tests/python/test_install.py tests/python/test_install_scripts.py -q`

Expected: FAIL because install interfaces/scripts do not exist.

- [ ] **Step 3: Implement fail-closed install state machine**

Use `shutil.copy2`, fsync/close, SHA-256 verification and same-directory `os.replace`. Restore the verified backup on any post-swap error. Never downgrade configuration/hash failures.

- [ ] **Step 4: Verify GREEN and full suite**

Run: `uv run pytest tests/python/test_install.py tests/python/test_install_scripts.py -q`

Run: `uv run pytest -q`

Run: `uv run ruff check src tests/python`

Expected: all commands exit 0.

- [ ] **Step 5: Commit Task 6**

```powershell
git add -- src/hnh_vi/install.py scripts/install.ps1 scripts/uninstall.ps1 tests/python/test_install.py tests/python/test_install_scripts.py README.md
git commit -m "feat: install and restore preview patches safely"
```

### Task 7: Final Preview Verification and Real Dry-Run Handoff

**Files:**
- Create: `docs/phase-1-smoke-checklist.md`
- Modify: `README.md`
- Modify: `work/hearth-and-hamlet-vietnamese-progress.md`

**Interfaces:**
- Consumes: reviewed Phase 1 data, real preview artifact and installer.
- Produces: clean whole-branch evidence, exact real dry-run output and an explicit apply/runtime checklist for a later user-authorized checkpoint.

- [ ] **Step 1: Run the complete verification chain fresh**

Run `uv sync --locked`, full pytest, Ruff, `git diff --check`, synthetic extraction/build/install integration and source-leak scans. Record exact counts, versions and skipped tests.

- [ ] **Step 2: Rebuild and verify the real preview candidate**

Run source verification, validation, selected coverage and build from clean temporary output. Expected original EXE/PCK hashes unchanged and artifact metadata/hash reproducible.

- [ ] **Step 3: Run the real install and uninstall dry-runs only**

Run `install.ps1` without `-Apply`, then `uninstall.ps1` without `-Apply` where applicable. Expected: exact planned paths/hashes/backup location; game files unchanged. Do not launch the game.

- [ ] **Step 4: Perform final independent whole-branch review**

Review correctness, path/data-loss safety, copyright boundary, translation contract, fallback behavior, Phase 1 wording and missing tests. Resolve every Critical/Important finding through the plan's fix loop.

- [ ] **Step 5: Document the external apply checkpoint and commit**

Document that `install -Apply`, game launch, runtime smoke, uninstall `-Apply` and optional reinstall require explicit authorization because they write/launch outside the worktree.

```powershell
git add -- docs/phase-1-smoke-checklist.md README.md work/hearth-and-hamlet-vietnamese-progress.md
git commit -m "docs: prepare phase 1 preview handoff"
```

## Plan Self-Review Result

- Spec coverage: Tasks 1–4 implement completeness, canonicalization, contracts, coverage, CLI, fallback and preview metadata; Task 5 supplies reviewed Phase 1 content; Tasks 6–7 provide safe installation tooling and a dry-run handoff.
- Step scan: each step has one checkable outcome; real game writes and launches are deliberately outside this plan's automatic execution boundary.
- Type consistency: `SourceCompleteness` and `CanonicalSource` flow from Task 1 through contracts, CLI and build; `BuildArtifact` flows into installer without a second metadata model.
- Review Focus coverage: completeness-distribution drift and duplicates are in Task 1; selected/non-selected empties in Tasks 2/4; misleading metadata in Task 4; install interruption/update/link attacks in Task 6.
- Proportion: seven independently reviewable tasks replace the superseded Tasks 4–9 without repeating completed bootstrap/extraction work.
