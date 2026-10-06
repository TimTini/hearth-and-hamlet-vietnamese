param(
    [Parameter(Mandatory = $true)][string]$GameDir,
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $RepoRoot) { $RepoRoot = $projectRoot }
$contextArgs = @(
    'run', '--project', $projectRoot, 'python', '-m', 'hnh_vi.build',
    'context', '--repo-root', $RepoRoot, '--game-dir', $GameDir
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
    # The build command verifies the game again, then runs GDRE against the locked PCK.
    # It writes only to workspace/<build-id>/build-* (removed afterwards) and dist/<build-id>/.
    $buildArgs = @(
        'run', '--project', $projectRoot, 'python', '-m', 'hnh_vi.build',
        'build', '--repo-root', $RepoRoot, '--game-dir', $GameDir
    )
    & uv @buildArgs
    exit $LASTEXITCODE
}
finally {
    foreach ($sourceLock in $sourceLocks) { $sourceLock.Dispose() }
}
