param(
    [Parameter(Mandatory = $true)]
    [string]$OriginalPck,
    [Parameter(Mandatory = $true)]
    [string]$TranslatedPck,
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $RepoRoot = Split-Path -Parent $PSScriptRoot
    }
    else {
        $RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
        $RepoRoot = Split-Path -Parent $RepoRoot
    }
}

function Get-Sha256Hex([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Assert-Sha256([string]$Path, [string]$Expected, [string]$Label) {
    $actual = Get-Sha256Hex -Path $Path
    if ($actual -ne $Expected.ToUpperInvariant()) {
        throw "hash_mismatch: $Label expected $Expected but got $actual"
    }
}

$repoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$originalPck = [System.IO.Path]::GetFullPath($OriginalPck)
$translatedPck = [System.IO.Path]::GetFullPath($TranslatedPck)

$expectedOriginal = '7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201'
$expectedTranslated = 'BEDB9B0A788AB5547A166197FB44648F92D09E550928D769B12F919A362A7227'
$outputName = 'Hearth-and-Hamlet-Tieng-Viet-Setup.exe'

Assert-Sha256 -Path $originalPck -Expected $expectedOriginal -Label 'OriginalPck'
Assert-Sha256 -Path $translatedPck -Expected $expectedTranslated -Label 'TranslatedPck'

$manifestPath = Join-Path $repoRoot 'manifests\installer-tools.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$zstd = $manifest.tools | Where-Object { $_.id -eq 'zstd' } | Select-Object -First 1
if ($null -eq $zstd) {
    throw 'zstd tool entry missing from installer-tools.json'
}

$toolsRoot = Join-Path $repoRoot '.tools\zstd'
$versionRoot = Join-Path $toolsRoot $zstd.version
$archivePath = Join-Path $versionRoot $zstd.asset
$extractRoot = Join-Path $versionRoot 'extract'
$zstdExe = Join-Path $extractRoot 'zstd-v1.5.7-win64\zstd.exe'

New-Item -ItemType Directory -Force -Path $versionRoot | Out-Null

if (-not (Test-Path -LiteralPath $zstdExe)) {
    if (-not (Test-Path -LiteralPath $archivePath)) {
        Write-Host "Downloading $($zstd.url)"
        Invoke-WebRequest -Uri $zstd.url -OutFile $archivePath
    }
    Assert-Sha256 -Path $archivePath -Expected $zstd.sha256 -Label 'zstd archive'
    if (Test-Path -LiteralPath $extractRoot) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force
    }
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractRoot -Force
}

if (-not (Test-Path -LiteralPath $zstdExe)) {
    throw "zstd.exe not found after extraction: $zstdExe"
}
Assert-Sha256 -Path $archivePath -Expected $zstd.sha256 -Label 'zstd archive'

$payloadDir = Join-Path $repoRoot 'installer\payload'
New-Item -ItemType Directory -Force -Path $payloadDir | Out-Null
$deltaPath = Join-Path $payloadDir 'payload.patch.zst'
if (Test-Path -LiteralPath $deltaPath) {
    Remove-Item -LiteralPath $deltaPath -Force
}

Write-Host "Creating Zstandard --patch-from delta at level 19"
$previousErrorAction = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $zstdExe --patch-from=$originalPck --long=30 $translatedPck -o $deltaPath -19 2>&1 | ForEach-Object { Write-Host $_ }
$deltaExit = $LASTEXITCODE
$ErrorActionPreference = $previousErrorAction
if ($deltaExit -ne 0) {
    throw "zstd delta creation failed with exit code $deltaExit"
}
if (-not (Test-Path -LiteralPath $deltaPath)) {
    throw "delta was not created: $deltaPath"
}

$project = Join-Path $repoRoot 'installer\src\HearthAndHamlet.Vietnamese.Setup\HearthAndHamlet.Vietnamese.Setup.csproj'
$publishDir = Join-Path $repoRoot 'dist\installer'
New-Item -ItemType Directory -Force -Path $publishDir | Out-Null

Write-Host "Publishing self-contained single-file installer"
& dotnet publish $project `
    -c Release `
    -r win-x64 `
    --self-contained true `
    -p:SelfContained=true `
    -p:PublishSingleFile=true `
    -p:PublishTrimmed=true `
    "-p:InstallerZstdPath=$zstdExe" `
    "-p:InstallerDeltaPath=$deltaPath" `
    -o $publishDir
if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed with exit code $LASTEXITCODE"
}

$publishedExe = Join-Path $publishDir 'HearthAndHamlet.Vietnamese.Setup.exe'
$finalExe = Join-Path $publishDir $outputName
if (-not (Test-Path -LiteralPath $publishedExe)) {
    throw "publish output missing: $publishedExe"
}
if (Test-Path -LiteralPath $finalExe) {
    Remove-Item -LiteralPath $finalExe -Force
}
Move-Item -LiteralPath $publishedExe -Destination $finalExe

$shaPath = "$finalExe.sha256"
$hash = Get-Sha256Hex -Path $finalExe
Set-Content -LiteralPath $shaPath -Value "$hash  $outputName" -Encoding ascii
Write-Host "Built $finalExe"
Write-Host "SHA-256 $hash"
Write-Host "Delta bytes $((Get-Item -LiteralPath $deltaPath).Length)"
