param(
    [Parameter(Mandatory = $true)][string]$GameDir,
    [string]$Backup,
    [switch]$Apply,
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $RepoRoot) { $RepoRoot = $projectRoot }
if (-not $env:LOCALAPPDATA) {
    Write-Error 'LOCALAPPDATA is not set, so the backup folder cannot be chosen.'
    exit 1
}
$backupRoot = Join-Path $env:LOCALAPPDATA 'HearthAndHamletVietnamese\backups'

$uninstallArgs = @(
    'run', '--project', $projectRoot, 'python', '-m', 'hnh_vi.install', 'uninstall',
    '--repo-root', $RepoRoot, '--game-dir', $GameDir, '--backup-root', $backupRoot
)
if ($Backup) { $uninstallArgs += @('--backup', $Backup) }

# Always plan first: this only reads files and refuses to restore over a Steam update.
$planLines = & uv @uninstallArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$planLines | Out-Host
if (-not $Apply) {
    Write-Host 'Dry run only. Nothing was changed. Run again with -Apply to restore the backup.'
    exit 0
}

$plan = ($planLines -join "`n") | ConvertFrom-Json
# -LiteralPath keeps brackets, spaces and Unicode in the game path from being read as wildcards.
if (-not (Test-Path -LiteralPath $plan.game_exe -PathType Leaf)) {
    Write-Error "missing_file: $($plan.game_exe)"
    exit 1
}
$exeLock = $null
try {
    # See install.ps1: the EXE is locked, the PCK is re-verified by Python before the swap.
    $exeLock = [System.IO.File]::Open(
        $plan.game_exe, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    & uv @uninstallArgs '--apply'
    exit $LASTEXITCODE
}
finally {
    if ($exeLock) { $exeLock.Dispose() }
}
