param(
    [Parameter(Mandatory = $true)][string]$GameDir,
    [Parameter(Mandatory = $true)][string]$Artifact,
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

$installArgs = @(
    'run', '--project', $projectRoot, 'python', '-m', 'hnh_vi.install', 'install',
    '--repo-root', $RepoRoot, '--game-dir', $GameDir, '--artifact', $Artifact,
    '--backup-root', $backupRoot
)

# Always plan first: this only reads files and stops on any unsupported or unsafe input.
$planLines = & uv @installArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$planLines | Out-Host
if (-not $Apply) {
    Write-Host 'Dry run only. Nothing was changed. Run again with -Apply to install.'
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
    # While this handle lives Windows denies write/delete opens of the EXE through any alias.
    # The PCK cannot be locked this way because it must be replaced; Python re-verifies it
    # right before the swap and the swap itself fails if the game has the PCK open.
    $exeLock = [System.IO.File]::Open(
        $plan.game_exe, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    & uv @installArgs '--apply'
    exit $LASTEXITCODE
}
finally {
    if ($exeLock) { $exeLock.Dispose() }
}
