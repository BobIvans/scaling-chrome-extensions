param(
 [Parameter(Mandatory=$true)][string]$PythonPath,
 [Parameter(Mandatory=$true)][string]$ProfilePath,
 [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'ContextLibrary\versions\0.2.0')
)
$ErrorActionPreference = 'Stop'
$SourceRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = [System.IO.Path]::GetFullPath($PythonPath)
$ProfilePath = [System.IO.Path]::GetFullPath($ProfilePath)
$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
& $PythonPath -I -X utf8 (Join-Path $PSScriptRoot 'install.py') install --source $SourceRoot --output $InstallRoot --python $PythonPath --profile $ProfilePath
if ($LASTEXITCODE -ne 0) { throw 'Installation verification failed.' }
$ShortcutRoot = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$Shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $ShortcutRoot 'Context Library.lnk'))
$Shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$LaunchPath = Join-Path $InstallRoot 'desktop\Launch_Windows.ps1'
$Shortcut.Arguments = '-NoProfile -File "' + $LaunchPath + '"'
$Shortcut.WorkingDirectory = $InstallRoot
$Shortcut.Save()
Write-Output 'Installed. Initialize and qualify the trusted profile before enabling context writes; see README_RU.md.'
