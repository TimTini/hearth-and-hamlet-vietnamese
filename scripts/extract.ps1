param(
    [Parameter(Mandatory = $true)][string]$GameDir,
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $RepoRoot) { $RepoRoot = $projectRoot }
$contextArgs = @(
    'run', '--project', $projectRoot, 'python', '-m', 'hnh_vi.workspace',
    'prepare', '--repo-root', $RepoRoot, '--game-dir', $GameDir
)
$contextJson = & uv @contextArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$context = $contextJson | ConvertFrom-Json
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
