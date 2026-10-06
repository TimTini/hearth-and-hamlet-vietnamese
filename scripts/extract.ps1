param(
    [Parameter(Mandatory = $true)][string]$GameDir,
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $RepoRoot) { $RepoRoot = $projectRoot }
$contextArgs = @(
    'run', '--project', $projectRoot, 'python', '-m', 'hnh_vi.workspace',
    'prepare-extract', '--repo-root', $RepoRoot, '--game-dir', $GameDir
)
$contextJson = & uv @contextArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$context = $contextJson | ConvertFrom-Json
$sourceLocks = @()
try {
    # Windows denies write/delete opens through every alias while these handles live.
    foreach ($path in @($context.exe, $context.pck)) {
        $sourceLocks += [System.IO.File]::Open(
            $path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read
        )
    }
    # Verify again while the source handles exclude any concurrent mutation.
    & uv @contextArgs | Out-Null
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $gdreArgs = @(
        '--headless', "--extract=$($context.pck)",
        "--output=$($context.workspace)/source", '--include=res://localisation/*'
    )
    & $context.gdre @gdreArgs | Out-Host
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $snapshotArgs = @(
        'run', '--project', $projectRoot, 'python', '-m', 'hnh_vi.workspace',
        'snapshot', '--repo-root', $RepoRoot, '--game-dir', $GameDir
    )
    & uv @snapshotArgs
    exit $LASTEXITCODE
}
finally {
    foreach ($sourceLock in $sourceLocks) { $sourceLock.Dispose() }
}
