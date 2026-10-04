# Downloads PUBLIC Git data only when you explicitly run this script.
# No checkout, tests, package installation, model, browser or trading execution.
param(
  [Parameter(Mandatory=$true)][string]$RepoRoot,
  [Parameter(Mandatory=$true)][string]$ArchiveRoot,
  [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
$tool = Join-Path $PSScriptRoot "..\tools\archive_tool.py"
New-Item -ItemType Directory -Force -Path $RepoRoot,$ArchiveRoot | Out-Null
$env:GIT_TERMINAL_PROMPT = "0"
$repos = @(
  @{Name="scaling-chrome-extensions"; Sha="da6abf4c006e4e7d26fe45ef30fa9d07a356f396"},
  @{Name="studious-pancake"; Sha="67d3852cbc4cb1b24582df45adbf6a42d4da2af0"}
)
foreach ($repo in $repos) {
  $checkout = Join-Path $RepoRoot $repo.Name
  if (!(Test-Path $checkout)) {
    & git clone --no-checkout --no-recurse-submodules --config core.longpaths=true "https://github.com/BobIvans/$($repo.Name).git" $checkout
    if ($LASTEXITCODE -ne 0) { throw "Clone failed; nothing has been qualified." }
  }
  # Existing directories are not reset, cleaned, updated or executed.
  & git -C $checkout cat-file -e "$($repo.Sha)^{commit}"
  if ($LASTEXITCODE -ne 0) { throw "Pinned commit unavailable. Fetch/review the repository separately; this script will not reset it." }
  $archive = Join-Path $ArchiveRoot "$($repo.Name)-$($repo.Sha.Substring(0,12))"
  & $Python $tool git --source $checkout --ref $repo.Sha --out $archive
  if ($LASTEXITCODE -ne 0) { throw "Archive incomplete; inspect receipt/manifest." }
  & $Python $tool verify --archive $archive
  if ($LASTEXITCODE -ne 0) { throw "Archive verification failed." }
}
Write-Output "Private raw archives collected. Review secrets and sharing scope before uploading."
