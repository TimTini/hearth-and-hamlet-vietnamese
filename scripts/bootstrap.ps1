param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Offline
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$uvArgs = @('run', '--project', $projectRoot)
if ($Offline) {
    $uvArgs += '--offline'
}
$uvArgs += @(
    'python', '-m', 'hnh_vi.tools', 'ensure',
    '--manifest', (Join-Path $RepoRoot 'manifests/tools.json'),
    '--tools-dir', (Join-Path $RepoRoot '.tools')
)
if ($Offline) {
    $uvArgs += '--offline'
}

& uv @uvArgs
exit $LASTEXITCODE
