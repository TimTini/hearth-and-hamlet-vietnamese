# Runtime Localization-Key Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover missing localization keys offline where possible and prepare a separately identifiable, reversible runtime diagnostic artifact for keys that remain unknown.

**Architecture:** Recovery first derives deterministic local hint inputs and accepts only a strictly improved, reproducible source snapshot. A synthetic Godot fixture must then prove a custom `Translation` probe before any diagnostic artifact is built; release and diagnostic metadata, paths and installer entry points remain disjoint, and real apply/launch is a later explicit checkpoint.

**Tech Stack:** Python 3.12 standard library via `uv`, pytest, Ruff, GDScript fixture code, PowerShell 5.1, pinned Godot 4.6.3 and GDRE 2.7.0.

**Spec:** `docs/superpowers/specs/2026-10-06-runtime-key-recovery-design.md`

## Global Constraints

- This plan consumes the reviewed interfaces and installer from `docs/superpowers/plans/2026-10-06-partial-source-preview.md`; do not duplicate its dataset/build/install implementations.
- Never commit recovered English CSV, missing-marker contents, hint files, raw runtime keys/logs, recovered scripts, game assets, saves or user configuration.
- Offline recovery may update completeness metadata only after the same PCK and hint hash reproduce the same improved result twice.
- An observed runtime key is not integrated until GDRE/hint produces a stable source row and the normal source-hash validator accepts it.
- Diagnostic artifacts live only under ignored `dist/<build-id>/diagnostic/`, declare `artifact_kind=diagnostic`, and are rejected by release install mode.
- Diagnostic code, project settings and logs must be absent from every release artifact.
- Every game write and launch is dry-run or synthetic by default. This plan stops after a real diagnostic dry-run; apply/launch requires explicit later authorization.
- If the custom Translation hook is unstable, changes the executable, cannot preserve English fallback or cannot be cleanly removed, stop runtime instrumentation while leaving preview releases usable.
- Use new/test saves only in any later authorized runtime session; never read or modify an important save.
- Stage only task-owned files, commit each reviewed task and do not push.

## Review Focus

- A hint run that changes key identities without reducing missing rows must be rejected; Task 1 owns this regression.
- Two runs with the same PCK/hints but different recovered output must not update completeness; Task 1 owns this regression.
- Translation probe ordering must not log known vi keys or swallow English fallback; Task 2 owns this regression.
- Release tooling must reject diagnostic metadata even when filenames are disguised; Tasks 3–4 own this regression.
- Failed diagnostic apply/uninstall and Steam source drift must preserve the original PCK and backup chain; Task 4 owns this regression.

---

### Task 1: Deterministic Offline Hint Recovery

**Files:**
- Create: `src/hnh_vi/recovery.py`
- Create: `scripts/recover-hints.ps1`
- Create: `tests/fixtures/recovery/recovery.log`
- Create: `tests/fixtures/recovery/source-partial.csv`
- Create: `tests/python/test_recovery.py`
- Create: `tests/python/test_recovery_integration.py`
- Modify: `.gitignore`
- Modify: `work/hearth-and-hamlet-vietnamese-progress.md`

**Interfaces:**
- Consumes: pinned GDRE, source PCK, current `SourceCompleteness`, ignored recovery CSV/log and verified runtime keys when available.
- Produces: `RecoveryState`, `RecoveryCandidate`, `collect_hint_candidates(source_csv: Path, recovered_project: Path, observed_keys: Path | None) -> RecoveryCandidate`, `compare_recovery(before: SourceCompleteness, after_csv: Path) -> RecoveryState`, `verify_recovery_reproducible(first_csv: Path, second_csv: Path) -> VerificationResult`.
- `scripts/recover-hints.ps1 -GameDir <path> [-ObservedKeys <ignored-path>] [-RepoRoot <path>]` writes only under ignored `workspace/<build-id>/recovery/`.

- [ ] **Step 1: Write failing parser/comparison tests**

Cover marker parsing without emitting marker content, candidate deduplication, hint hashing, no-improvement rejection, row-count/locale drift, key-identity replacement, reproducible improvement, non-deterministic output and safe JSON summaries containing counts/hashes only.

- [ ] **Step 2: Run unit tests and verify RED**

Run: `uv run pytest tests/python/test_recovery.py -q`

Expected: FAIL because `hnh_vi.recovery` does not exist.

- [ ] **Step 3: Implement offline recovery orchestration**

Generate hint files only in ignored workspace. Invoke GDRE `--translation-hint` twice into fresh directories under the existing EXE/PCK read-handle guard. Accept a candidate only when both outputs match and the missing count strictly decreases without other source drift.

- [ ] **Step 4: Run synthetic GDRE integration and real read-only recovery attempt**

Use a synthetic optimized translation fixture to prove hint improvement and rejection paths. Then run against the owned game read-only; record only before/after counts and hashes. Do not update committed completeness metadata in this task unless the result is reproducible and independently reviewed.

- [ ] **Step 5: Verify and commit**

Run: `uv run pytest tests/python/test_recovery.py tests/python/test_recovery_integration.py -q -m integration`

Run: `uv run pytest -q`

Run: `uv run ruff check src tests/python`

Expected: all commands exit 0.

```powershell
git add -- src/hnh_vi/recovery.py scripts/recover-hints.ps1 tests/fixtures/recovery tests/python/test_recovery.py tests/python/test_recovery_integration.py .gitignore work/hearth-and-hamlet-vietnamese-progress.md
git commit -m "feat: recover localization keys from verified hints"
```

### Task 2: Synthetic Translation-Probe Feasibility

**Files:**
- Create: `diagnostic/translation_probe.gd`
- Create: `tests/fixtures/diagnostic_project/project.godot`
- Create: `tests/fixtures/diagnostic_project/main.gd`
- Create: `tests/fixtures/diagnostic_project/localisation/translations.csv`
- Create: `tests/python/test_diagnostic_fixture.py`
- Modify: `work/hearth-and-hamlet-vietnamese-progress.md`

**Interfaces:**
- Consumes: Godot `Translation`, `TranslationServer` and generated known-vi mapping.
- Produces: a diagnostic `TranslationProbe` fixture that delegates known vi lookups, records missing `src_message` once, returns no diagnostic translation for misses and leaves English fallback observable.

- [ ] **Step 1: Write the failing Godot fixture test**

Run real Godot headless and assert a known vi key returns Vietnamese without logging, an unknown vi key returns English and logs exactly once, repeated lookup is deduplicated, contextual/plural paths are explicit, and the log path remains outside the project/repo fixture.

- [ ] **Step 2: Run and verify RED**

Run: `uv run pytest tests/python/test_diagnostic_fixture.py -q -m integration`

Expected: FAIL because the diagnostic project/probe does not exist.

- [ ] **Step 3: Implement the minimum probe**

Use a `Translation` subclass and a separate logger object so `_get_message()` does not own mutable output state. Register/unregister the probe explicitly in the fixture; do not assume translation insertion order without asserting it.

- [ ] **Step 4: Verify feasibility and failure boundaries**

Test locale switching, probe removal, unwritable log path, empty/corrupt known mapping and process restart. If known-key delegation or fallback is unstable, mark runtime instrumentation blocked and do not proceed to Task 3.

- [ ] **Step 5: Commit Task 2**

Run full pytest and Ruff; expected exit 0.

```powershell
git add -- diagnostic/translation_probe.gd tests/fixtures/diagnostic_project tests/python/test_diagnostic_fixture.py work/hearth-and-hamlet-vietnamese-progress.md
git commit -m "test: prove runtime translation key capture"
```

### Task 3: Diagnostic Artifact Builder and Separation Contract

**Files:**
- Create: `src/hnh_vi/diagnostic.py`
- Create: `scripts/build-diagnostic.ps1`
- Create: `tests/python/test_diagnostic.py`
- Create: `tests/python/test_diagnostic_integration.py`
- Modify: `src/hnh_vi/build.py`
- Modify: `src/hnh_vi/install.py`

**Interfaces:**
- Consumes: verified preview dataset/artifact, proven `TranslationProbe`, pinned GDRE and supported source snapshot.
- Produces: `DiagnosticArtifact`, `build_diagnostic_artifact(...) -> DiagnosticArtifact`, `verify_diagnostic_artifact(path: Path, metadata_path: Path) -> DiagnosticArtifact`.
- Metadata has `artifact_kind="diagnostic"`, source/artifact hashes, probe paths and no raw keys. Release `verify_build_artifact` and `plan_install` reject this kind.
- `scripts/build-diagnostic.ps1` writes only under ignored `dist/25600292/diagnostic/`.

- [ ] **Step 1: Write failing separation/build tests**

Cover metadata kind, path allowlist, disguised filename, diagnostic path in release PCK, raw-key/log leakage, source drift, deterministic hash, original PCK unchanged and release installer rejection.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest tests/python/test_diagnostic.py -q`

Expected: FAIL because diagnostic builder does not exist.

- [ ] **Step 3: Implement diagnostic artifact build**

Generate probe configuration in temporary ignored workspace, patch only the files proven by Task 2, reopen/list the artifact and publish metadata atomically. Never modify executable or release output.

- [ ] **Step 4: Verify with real synthetic PCK**

Run Godot/GDRE integration to assert the diagnostic probe works, release artifact remains probe-free, source hash remains unchanged and the release installer rejects diagnostic metadata.

- [ ] **Step 5: Commit Task 3**

Run focused/full tests and Ruff; expected exit 0.

```powershell
git add -- src/hnh_vi/diagnostic.py scripts/build-diagnostic.ps1 tests/python/test_diagnostic.py tests/python/test_diagnostic_integration.py src/hnh_vi/build.py src/hnh_vi/install.py
git commit -m "feat: build isolated diagnostic translation patches"
```

### Task 4: Reversible Diagnostic Dry-Run Workflow

**Files:**
- Create: `scripts/install-diagnostic.ps1`
- Create: `scripts/uninstall-diagnostic.ps1`
- Create: `tests/python/test_diagnostic_install.py`
- Modify: `src/hnh_vi/diagnostic.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: verified `DiagnosticArtifact` and the release install primitives without weakening release-mode rejection.
- Produces: `DiagnosticInstallPlan`, `plan_diagnostic_install(...) -> DiagnosticInstallPlan`, `apply_diagnostic_install(plan: DiagnosticInstallPlan) -> BackupRecord`, `plan_diagnostic_uninstall(...) -> DiagnosticInstallPlan`.
- Diagnostic backups and logs use distinct metadata under `%LOCALAPPDATA%\HearthAndHamletVietnamese\diagnostic\<build-id>\`.

- [ ] **Step 1: Write failing diagnostic install tests**

Use synthetic directories. Cover default dry-run, release/diagnostic kind confusion, wrong source, existing preview, verified backup, interrupted apply rollback, uninstall restore, stale Steam PCK, log path outside game/repo, hard links and repeated dry-runs.

- [ ] **Step 2: Run tests and verify RED**

Run: `uv run pytest tests/python/test_diagnostic_install.py -q`

Expected: FAIL because diagnostic install workflow does not exist.

- [ ] **Step 3: Implement the separate diagnostic state machine**

Reuse low-level verified copy/replace/rollback helpers, not release policy decisions. Require `artifact_kind=diagnostic`; release scripts must continue to reject it.

- [ ] **Step 4: Verify and commit**

Run focused/full tests, Ruff and PowerShell wrapper tests; expected exit 0.

```powershell
git add -- scripts/install-diagnostic.ps1 scripts/uninstall-diagnostic.ps1 tests/python/test_diagnostic_install.py src/hnh_vi/diagnostic.py README.md
git commit -m "feat: plan reversible diagnostic installs"
```

### Task 5: Real Diagnostic Dry-Run and Runtime Handoff

**Files:**
- Create: `docs/runtime-recovery-checklist.md`
- Modify: `README.md`
- Modify: `work/hearth-and-hamlet-vietnamese-progress.md`

**Interfaces:**
- Consumes: reviewed diagnostic artifact and install/uninstall workflow.
- Produces: verified real dry-run evidence and exact later commands/checklist for authorized apply, observation, uninstall and key integration.

- [ ] **Step 1: Run the complete diagnostic verification chain**

Run locked sync, full pytest, Ruff, diff check and explicit recovery/diagnostic integrations. Record exact versions, counts and skipped tests.

- [ ] **Step 2: Build the real diagnostic artifact without installing**

Verify source build/hashes immediately before build. Expected diagnostic artifact only under ignored diagnostic dist path and source game unchanged.

- [ ] **Step 3: Run real diagnostic install/uninstall dry-runs only**

Expected output names the exact source/artifact/backup/log hashes and paths; no game file or user data is written and the game is not launched.

- [ ] **Step 4: Write the authorized runtime checklist**

Define apply, test-save launch, screen/state traversal, log close, uninstall, original-hash verification, offline hint rerun and `observed -> verified -> integrated` transitions. State that an unvisited flow remains blocked.

- [ ] **Step 5: Perform final independent review and commit**

Review security/data-loss boundaries, artifact separation, fallback, log privacy and recovery evidence. Resolve Critical/Important findings before commit.

```powershell
git add -- docs/runtime-recovery-checklist.md README.md work/hearth-and-hamlet-vietnamese-progress.md
git commit -m "docs: prepare runtime key recovery handoff"
```

## Plan Self-Review Result

- Spec coverage: Task 1 owns offline hints and reproducibility; Task 2 proves the hook/fallback; Tasks 3–4 isolate and safely stage diagnostic artifacts; Task 5 stops at the required external apply checkpoint.
- Step scan: every task ends with a testable deliverable; real game mutation and launch are intentionally not bundled with implementation.
- Type consistency: `RecoveryCandidate/RecoveryState` feed completeness updates; `DiagnosticArtifact` is distinct from release `BuildArtifact`; diagnostic install uses a separate policy type while sharing verified low-level operations.
- Review Focus coverage: ineffective/nondeterministic hints are Task 1; probe ordering/fallback is Task 2; disguised diagnostic artifacts are Tasks 3–4; source drift/rollback is Task 4.
- Proportion: five tasks cover one recovery subsystem and depend on the preview plan rather than duplicating it.
