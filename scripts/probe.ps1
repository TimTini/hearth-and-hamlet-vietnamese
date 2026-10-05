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
$sourceLocks = @()
try {
    # Locks protect the source file objects, including aliases created after the gate.
    foreach ($path in @($context.exe, $context.pck)) {
        $sourceLocks += [System.IO.File]::Open(
            $path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read
        )
    }
    & uv @contextArgs | Out-Null
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $probeDir = Join-Path $context.workspace 'probe'
    [void][System.IO.Directory]::CreateDirectory($probeDir)
    $versionArgs = @('--headless', '--version')
    $gdreVersion = & $context.gdre @versionArgs | Out-String
    # GDRE 2.7.0 returns 1 for --version; require its verified version output.
    if (($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) -or $gdreVersion.Trim() -ne 'Godot RE Tools v2.7.0') {
        throw 'gdre_version_probe_failed'
    }
    $gdreVersion | Out-File -LiteralPath (Join-Path $probeDir 'gdre-version.txt') -Encoding utf8
    & $context.godot '--version' | Out-File -LiteralPath (Join-Path $probeDir 'godot-version.txt') -Encoding utf8
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $listArgs = @('--headless', "--list-files=$($context.pck)")
    & $context.gdre @listArgs | Out-File -LiteralPath (Join-Path $probeDir 'pck-files.txt') -Encoding utf8
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $recoverArgs = @(
        '--headless', "--recover=$($context.pck)", "--output=$probeDir/source",
        '--include=res://localisation/*', '--include=res://Scenes/language.gdc',
        '--include=res://globals/language_manager.gdc', '--include=res://project.binary'
    )
    & $context.gdre @recoverArgs | Out-File -LiteralPath (Join-Path $probeDir 'recovery.log') -Encoding utf8
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $reportArgs = @(
        'run', '--project', $projectRoot, 'python', '-m', 'hnh_vi.workspace',
        'probe-report', '--repo-root', $RepoRoot, '--game-dir', $GameDir
    )
    & uv @reportArgs
    exit $LASTEXITCODE
}
finally {
    foreach ($sourceLock in $sourceLocks) { $sourceLock.Dispose() }
}
