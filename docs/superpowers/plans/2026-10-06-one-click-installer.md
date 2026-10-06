# One-click Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish `Hearth-and-Hamlet-Tieng-Viet-Setup.exe`, a self-contained Windows installer that safely installs or restores the Vietnamese patch without Python, uv, Git, Godot, or GDRE.

**Architecture:** A trim-friendly .NET 8 console application owns game discovery, fingerprint checks, backup/restore, and atomic replacement. The release build embeds a Zstandard executable and a `--patch-from` delta generated locally from the verified original and translated PCK files; neither complete PCK is committed or released.

**Tech Stack:** C#/.NET 8, PowerShell build script, Zstandard 1.5.7, xUnit, existing Python/pytest/ruff checks, GitHub CLI.

**Spec:** `docs/superpowers/specs/2026-10-06-one-click-installer-design.md`

## Global Constraints

- Output asset name is exactly `Hearth-and-Hamlet-Tieng-Viet-Setup.exe`.
- Runtime target is Windows 10/11 x64 and must not require an installed .NET runtime or development tool.
- Supported Steam build is exactly `25600292`, game version `1.1.0.0`.
- Original PCK SHA-256 is `7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201`.
- Vietnamese PCK SHA-256 is `BEDB9B0A788AB5547A166197FB44648F92D09E550928D769B12F919A362A7227`.
- Game EXE SHA-256 is `7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A`.
- No complete PCK, extracted game asset, credential, cookie, personal path, or private snapshot may be committed or released.
- Runtime performs no network request or telemetry and does not request elevation.
- Existing user changes and the existing Python development workflow remain intact.

## Review Focus

- A Steam update or tampered PCK must fail closed before backup or replacement.
- Paths containing spaces, Unicode, brackets, or quotes must be passed as process arguments, never shell-concatenated.
- Interrupted or failed patch generation/replacement must leave the original PCK recoverable.
- Restore must reject stale or malformed backups and refuse to overwrite a changed game.
- The single-file bundle must not expose private build paths or contain either complete PCK.

---

### Task 1: Installer core and console flow

**Files:**
- Create: `installer/src/HearthAndHamlet.Vietnamese.Setup/HearthAndHamlet.Vietnamese.Setup.csproj`
- Create: `installer/src/HearthAndHamlet.Vietnamese.Setup/Program.cs`
- Create: `installer/src/HearthAndHamlet.Vietnamese.Setup/InstallerOptions.cs`
- Create: `installer/src/HearthAndHamlet.Vietnamese.Setup/GameLocator.cs`
- Create: `installer/src/HearthAndHamlet.Vietnamese.Setup/InstallEngine.cs`
- Create: `installer/src/HearthAndHamlet.Vietnamese.Setup/PayloadPatcher.cs`
- Create: `installer/src/HearthAndHamlet.Vietnamese.Setup/ReleaseConstants.cs`
- Create: `installer/src/HearthAndHamlet.Vietnamese.Setup/Properties/AssemblyInfo.cs`
- Create: `installer/tests/HearthAndHamlet.Vietnamese.Setup.Tests/HearthAndHamlet.Vietnamese.Setup.Tests.csproj`
- Create: `installer/tests/HearthAndHamlet.Vietnamese.Setup.Tests/GameLocatorTests.cs`
- Create: `installer/tests/HearthAndHamlet.Vietnamese.Setup.Tests/InstallEngineTests.cs`
- Create: `installer/tests/HearthAndHamlet.Vietnamese.Setup.Tests/InstallerOptionsTests.cs`

**Interfaces:**
- Produces: `IEnumerable<string> GameLocator.FindCandidates(string executableDirectory, string currentDirectory, IEnumerable<string> steamRoots)`, `Task<InstallResult> InstallEngine.InstallAsync(GamePaths game, string backupRoot, IPayloadPatcher patcher, CancellationToken cancellationToken)`, `Task<InstallResult> InstallEngine.RestoreAsync(GamePaths game, string backupRoot, CancellationToken cancellationToken)`, `InstallerOptions.Parse(string[] args)`, and CLI exit codes usable by packaging/E2E tests.

- [ ] **Step 1: Write failing tests for options and discovery**

  Cover explicit `--game-dir`, `--install`, `--restore`, `--yes`, `--no-pause`; discovery from the installer directory and Steam `libraryfolders.vdf`; Unicode/space paths; malformed VDF ignored without accepting an invalid game directory.

- [ ] **Step 2: Run the focused tests and confirm RED**

  Run: `dotnet test installer/tests/HearthAndHamlet.Vietnamese.Setup.Tests/HearthAndHamlet.Vietnamese.Setup.Tests.csproj --filter "FullyQualifiedName~InstallerOptionsTests|FullyQualifiedName~GameLocatorTests"`
  Expected: build/test failure because the production types do not exist.

- [ ] **Step 3: Implement the minimum parser and game discovery**

  Candidate directories are accepted only when both `Hearth and Hamlet.exe` and `Hearth and Hamlet.pck` exist. Registry reads and VDF parsing are isolated so tests can supply roots/files without changing the machine registry.

- [ ] **Step 4: Run focused tests and confirm GREEN**

  Run the command from Step 2. Expected: all selected tests pass.

- [ ] **Step 5: Write failing engine tests**

  Use synthetic files and an injected patcher. Cover: valid install backup and target hash; unsupported EXE/PCK; already installed; valid restore; stale/malformed backup; changed current game; patch failure; post-replace hash failure with rollback; and read-only/unwritable destination.

- [ ] **Step 6: Run engine tests and confirm RED**

  Run: `dotnet test installer/tests/HearthAndHamlet.Vietnamese.Setup.Tests/HearthAndHamlet.Vietnamese.Setup.Tests.csproj --filter FullyQualifiedName~InstallEngineTests`
  Expected: failures because install/restore behavior is missing.

- [ ] **Step 7: Implement safe install, restore, and console orchestration**

  Hash with streaming SHA-256; store backup metadata without personal paths; stage output in the game directory; verify before replace; retain a rollback file until post-replace verification succeeds; hold the game EXE open with restrictive sharing; use `ProcessStartInfo.ArgumentList` for Zstandard; clean only the installer-owned temporary directory.

- [ ] **Step 8: Run the complete .NET test project**

  Run: `dotnet test installer/tests/HearthAndHamlet.Vietnamese.Setup.Tests/HearthAndHamlet.Vietnamese.Setup.Tests.csproj --configuration Release`
  Expected: zero failed tests and zero warnings.

- [ ] **Step 9: Commit the task**

  Stage only the installer source/test files and commit `Add safe one-click installer core`.

### Task 2: Reproducible payload and single-file release build

**Files:**
- Create: `manifests/installer-tools.json`
- Create: `scripts/build-installer.ps1`
- Create: `installer/third_party/zstd-LICENSE`
- Create: `tests/python/test_build_installer_script.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: the Task 1 app project and exact hashes in `ReleaseConstants`.
- Produces: `scripts/build-installer.ps1 -OriginalPck <path> -TranslatedPck <path>`, `dist/installer/Hearth-and-Hamlet-Tieng-Viet-Setup.exe`, and adjacent `.sha256`.

- [ ] **Step 1: Write failing static/build-script tests**

  Assert pinned HTTPS URL/version/hash, hash verification before extraction, literal path handling, ignored payload/build outputs, exact output filename, self-contained `win-x64` single-file publish properties, and bundled Zstandard license.

- [ ] **Step 2: Run the focused Python test and confirm RED**

  Run: `uv run pytest -q tests/python/test_build_installer_script.py`
  Expected: failures because the manifest/script/license do not exist.

- [ ] **Step 3: Add the pinned tool manifest, license, ignores, and build script**

  The script downloads only when the verified tool is absent, refuses wrong input hashes, creates a Zstandard level-19 delta, embeds the delta and pinned `zstd.exe` through MSBuild properties, publishes .NET 8 self-contained/single-file/trimmed, then writes the EXE SHA-256.

- [ ] **Step 4: Run focused tests and confirm GREEN**

  Run the command from Step 2. Expected: all tests pass.

- [ ] **Step 5: Build the real release payload**

  Use the verified original backup and latest translated artifact. Record download hash, delta size, output size, elapsed time and exit code in `work/one-click-release-progress.md`.

- [ ] **Step 6: Run real copied-game E2E**

  In a uniquely named temporary directory, copy the supported game EXE/PCK, run the built installer with `--install --yes --no-pause`, verify installed SHA and backup SHA, then run `--restore --yes --no-pause` and verify original SHA. Repeat with a deliberately changed PCK and verify nonzero exit plus no mutation/backup.

- [ ] **Step 7: Run full local regression checks**

  Run: `dotnet test installer/tests/HearthAndHamlet.Vietnamese.Setup.Tests/HearthAndHamlet.Vietnamese.Setup.Tests.csproj --configuration Release`, `uv run pytest -q`, `uv run ruff check src tests/python`, `uv run hnh-vi validate --required-keys .\localization\phase1.keys`, `uv run hnh-vi coverage --selected-keys .\localization\phase1.keys`, and `git diff --check`.

- [ ] **Step 8: Commit the task**

  Stage only source, test, manifest, license and ignore changes; never stage `dist/`, `.tools/`, payloads or PCK files. Commit `Build self-contained Vietnamese installer`.

### Task 3: Public documentation and GitHub Release

**Files:**
- Modify: `README.md`
- Create: `docs/release-checklist.md`

**Interfaces:**
- Consumes: verified EXE and checksum from Task 2.
- Produces: public installation/manual recovery documentation, tag `v1.1.0-vi.1`, and a GitHub Release with exactly the EXE plus checksum asset.

- [ ] **Step 1: Write/update documentation**

  Put one-click download/install first; explain auto-detection and paste fallback, backup/restore, supported build, SmartScreen/unsigned warning and checksum verification. Retain the source-build/manual PowerShell path for advanced users and clearly distinguish it from the no-runtime installer.

- [ ] **Step 2: Run documentation/security scans**

  Search tracked files and the new commit range for credentials, email/home paths, private snapshot names, PCK/EXE/DLL artifacts and oversized blobs. Inspect binary strings/resources for local paths or secret-like values. Confirm only `main` exists locally/remotely.

- [ ] **Step 3: Obtain independent whole-change review**

  Reviewer checks the spec, plan, full diff, tests, packaging inputs, licensing, backup/rollback behavior and public-release contents. Fix every Critical/Important finding and re-review the fix diff.

- [ ] **Step 4: Perform fresh final verification**

  Re-run full regression checks and real copied-game install/restore E2E against the exact release EXE. Recompute SHA-256 after all checks.

- [ ] **Step 5: Commit and push `main`**

  Commit only documentation/release checklist changes, verify clean status, push `main`, and verify local `HEAD` equals `origin/main`.

- [ ] **Step 6: Create and verify GitHub Release**

  Create annotated tag/release `v1.1.0-vi.1`, upload exactly `Hearth-and-Hamlet-Tieng-Viet-Setup.exe` and `Hearth-and-Hamlet-Tieng-Viet-Setup.exe.sha256`, then download both to a new temporary directory and verify the checksum, file name, asset count and public release URL.
