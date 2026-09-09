param(
  [string]$Target = "$HOME\Downloads\ONE_CLICK_CONTEXT_CHROME_READY"
)

$ErrorActionPreference = 'Stop'
$repo = 'BobIvans/scaling-chrome-extensions'
$commit = '92311c5e6a116bae1af93df8f8cd9c9105ccdd72'
$base = "https://raw.githubusercontent.com/$repo/$commit/one-click-context"
$expectedVersion = '0.8.4'

$files = @(
  'manifest.json',
  'background.js',
  'artifact-inventory.js',
  'capture-regions.js',
  'content.js',
  'offscreen.html',
  'offscreen.js',
  'viewer.html',
  'viewer.js',
  'viewer.css',
  'library.html',
  'library/agent.mjs',
  'library/convert.mjs',
  'library/library.mjs',
  'library/workspace.mjs',
  'library/idb-store.mjs',
  'library/library.css',
  'library/README_RU.md',
  'vendor/fflate.mjs',
  'vendor/pdf.mjs',
  'vendor/pdf.worker.mjs',
  'vendor/FFLATE_LICENSE.txt',
  'vendor/PDFJS_LICENSE.txt',
  'INSTALL_RU.txt',
  'README.md'
)

function Fail([string]$Message) {
  Write-Host "ERROR: $Message" -ForegroundColor Red
  exit 1
}

Write-Host "One Click Context renewal" -ForegroundColor Cyan
Write-Host "Source commit: $commit"
Write-Host "Target: $Target"
Write-Host ""

if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
  Fail "Target folder does not exist. Open chrome://extensions -> One Click Context -> Details and pass the exact 'Loaded from' folder with -Target."
}

$oldManifestPath = Join-Path $Target 'manifest.json'
if (-not (Test-Path -LiteralPath $oldManifestPath -PathType Leaf)) {
  Fail "manifest.json is not directly inside the target folder. Refusing to update the wrong directory."
}

try {
  $oldManifest = Get-Content -LiteralPath $oldManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
  Write-Host "Current installed-folder version: $($oldManifest.version)"
} catch {
  Fail "Current manifest.json is unreadable: $($_.Exception.Message)"
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$parent = Split-Path -Parent $Target
$leaf = Split-Path -Leaf $Target
$backup = Join-Path $parent ("$leaf.backup-$stamp")
$temp = Join-Path $env:TEMP ("occ-renew-$stamp")

Write-Host "Backup will be created at: $backup"
$answer = Read-Host "Type YES to back up the current folder and renew it to $expectedVersion"
if ($answer -ne 'YES') {
  Write-Host 'Cancelled. No files changed.' -ForegroundColor Yellow
  exit 0
}

Copy-Item -LiteralPath $Target -Destination $backup -Recurse -Force
New-Item -ItemType Directory -Path $temp -Force | Out-Null

try {
  foreach ($relative in $files) {
    $uri = "$base/$relative"
    $tmpPath = Join-Path $temp ($relative -replace '/', [IO.Path]::DirectorySeparatorChar)
    $tmpDir = Split-Path -Parent $tmpPath
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
    Write-Host "Downloading $relative"
    Invoke-WebRequest -Uri $uri -OutFile $tmpPath -UseBasicParsing
    if (-not (Test-Path -LiteralPath $tmpPath -PathType Leaf)) {
      throw "Missing downloaded file: $relative"
    }
  }

  $newManifestPath = Join-Path $temp 'manifest.json'
  $newManifest = Get-Content -LiteralPath $newManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($newManifest.manifest_version -ne 3) {
    throw "Downloaded manifest is not Manifest V3."
  }
  if ($newManifest.version -ne $expectedVersion) {
    throw "Downloaded version is $($newManifest.version), expected $expectedVersion."
  }

  foreach ($relative in $files) {
    $src = Join-Path $temp ($relative -replace '/', [IO.Path]::DirectorySeparatorChar)
    $dst = Join-Path $Target ($relative -replace '/', [IO.Path]::DirectorySeparatorChar)
    $dstDir = Split-Path -Parent $dst
    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    Copy-Item -LiteralPath $src -Destination $dst -Force
  }

  $installedManifest = Get-Content -LiteralPath (Join-Path $Target 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($installedManifest.version -ne $expectedVersion) {
    throw "Post-copy manifest verification failed."
  }

  Write-Host ""
  Write-Host "Renewal files copied successfully: One Click Context $expectedVersion" -ForegroundColor Green
  Write-Host "Backup: $backup"
  Write-Host ""
  Write-Host "NEXT:" -ForegroundColor Cyan
  Write-Host "1. Open chrome://extensions"
  Write-Host "2. On the EXISTING One Click Context card press Reload (circular arrow). Do NOT remove the extension."
  Write-Host "3. Confirm version $expectedVersion."
  Write-Host "4. Reload the ChatGPT/DeepSeek/web page tabs you want to capture."
  Write-Host "5. Right-click the OCC icon to test Chat / Document / Chat + Document modes."
  Write-Host "6. On ChatGPT inspect a chat with repeated messages, known time elements and a file card; inventory must not click anything."
  Write-Host "7. On DeepSeek inspect a visible conversation; missing IDs/dates must remain explicitly unknown rather than invented."
  Write-Host "8. Confirm signed file-link query/hash data is not present in the source inventory."
  Write-Host "9. Recheck IndexedDB original Blob dedup/GC/tombstone behavior from 0.8.3."
  Write-Host ""
  Write-Host "If anything breaks, close Chrome, restore the backup folder contents to $Target, then reload the extension." -ForegroundColor Yellow
} catch {
  Write-Host "Renewal failed: $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "Restoring folder from backup..." -ForegroundColor Yellow
  Remove-Item -LiteralPath $Target -Recurse -Force
  Copy-Item -LiteralPath $backup -Destination $Target -Recurse -Force
  Fail "Original extension folder was restored from backup."
} finally {
  if (Test-Path -LiteralPath $temp) {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
  }
}
