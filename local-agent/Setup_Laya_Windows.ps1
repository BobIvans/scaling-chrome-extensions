param(
 [string]$Destination=(Join-Path $env:LOCALAPPDATA 'VoiceAgentOSMini\laya-v0.3.23'),
 [string]$BootstrapPython='python'
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($Destination)
$venv=Join-Path $root 'venv'
New-Item -ItemType Directory -Path $root -Force | Out-Null
& $BootstrapPython -m venv $venv
$python=Join-Path $venv 'Scripts\python.exe'
& $python -m pip install --disable-pip-version-check --upgrade pip
& $python -m pip install --disable-pip-version-check 'laya[serve]==0.3.23'
$version=& $python -c "import importlib.metadata;print(importlib.metadata.version('laya'))"
if($LASTEXITCODE -ne 0 -or $version.Trim() -ne '0.3.23'){throw "Pinned Laya version mismatch: $version"}
$receipt=@{
 schema='voice-agentos.laya-install.v1'
 state='PINNED_PACKAGE_INSTALLED'
 version='0.3.23'
 release_commit='d8a2e59'
 python=$python
 installed_at=(Get-Date).ToUniversalTime().ToString('o')
}
$receipt|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $root 'INSTALL_RECEIPT.json') -Encoding UTF8
Write-Output $python
