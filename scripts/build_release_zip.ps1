param(
    [string]$Version = "",
    [string]$OutputDirectory = "release"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$versionFile = Join-Path $repoRoot "VERSION"

if (-not $Version) {
    $Version = (Get-Content -LiteralPath $versionFile -Raw).Trim()
}
if ($Version -notmatch '^\d+\.\d+\.\d+([-.][0-9A-Za-z.-]+)?$') {
    throw "Invalid release version: $Version"
}

$outputRoot = Join-Path $repoRoot $OutputDirectory
$packageName = "Bashi-PPT-v$Version-Windows-Portable"
$stagingRoot = Join-Path $outputRoot $packageName
$zipPath = Join-Path $outputRoot "$packageName.zip"
$checksumPath = "$zipPath.sha256"

New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$resolvedOutput = (Resolve-Path -LiteralPath $outputRoot).Path

function Assert-InOutputRoot([string]$Path) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith(
        $resolvedOutput + [IO.Path]::DirectorySeparatorChar,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Refusing to modify path outside release directory: $fullPath"
    }
}

foreach ($path in @($stagingRoot, $zipPath, $checksumPath)) {
    Assert-InOutputRoot $path
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null

function Copy-ReleaseItem([string]$RelativePath) {
    $source = Join-Path $repoRoot $RelativePath
    $destination = Join-Path $stagingRoot $RelativePath
    $parent = Split-Path -Parent $destination
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
}

$rootFiles = @(
    "README.md",
    "README_CN.md",
    "CHANGELOG.md",
    "LICENSE",
    "VERSION",
    ".env.example",
    "run_portable.bat",
    "安装说明.txt",
    "CONTRIBUTING.md",
    "SECURITY.md"
)
foreach ($file in $rootFiles) {
    Copy-ReleaseItem $file
}

$backendFiles = @(
    "backend\app.py",
    "backend\article_export.py",
    "backend\config.py",
    "backend\grounding_audit.py",
    "backend\image_search.py",
    "backend\requirements.txt",
    "backend\schema.py",
    "backend\slide_recommendation.py",
    "backend\text_constraints.py",
    "backend\llm",
    "backend\lyrics",
    "backend\renderer",
    "backend\templates"
)
foreach ($item in $backendFiles) {
    Copy-ReleaseItem $item
}

Copy-ReleaseItem "frontend\dist"
Copy-ReleaseItem "python-3.12.10-embed-amd64"
Copy-ReleaseItem "scripts\ensure_opencc.py"

$publicDocs = @(
    "docs\USER_GUIDE.md",
    "docs\USER_GUIDE_CN.md",
    "docs\PRIVACY.md",
    "docs\PRIVACY_CN.md",
    "docs\RELEASE_NOTES_v$Version.md"
)
foreach ($doc in $publicDocs) {
    Copy-ReleaseItem $doc
}

Get-ChildItem -LiteralPath $stagingRoot -Recurse -Directory |
    Where-Object { $_.Name -eq "__pycache__" } |
    Sort-Object FullName -Descending |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $stagingRoot -Recurse -File -Include *.pyc,*.pyo |
    Remove-Item -Force

if (Test-Path -LiteralPath (Join-Path $stagingRoot ".env")) {
    throw "Release package must not contain .env"
}

Compress-Archive -LiteralPath $stagingRoot -DestinationPath $zipPath -CompressionLevel Optimal
$hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $([IO.Path]::GetFileName($zipPath))" |
    Set-Content -LiteralPath $checksumPath -Encoding ascii

$zip = Get-Item -LiteralPath $zipPath
Remove-Item -LiteralPath $stagingRoot -Recurse -Force
Write-Host "Created: $($zip.FullName)"
Write-Host "Size: $([math]::Round($zip.Length / 1MB, 2)) MB"
Write-Host "SHA256: $hash"
