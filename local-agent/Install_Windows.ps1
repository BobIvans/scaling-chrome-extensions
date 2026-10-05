param(
 [string]$Destination=(Join-Path $env:LOCALAPPDATA 'VoiceAgentOSMini'),
 [string]$PythonPath='python'
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Path $root -Force | Out-Null
$files=@('mini_controller.py','core_client.py','control_bridge.py','github_merge_watch.py','folder_watch.py','laya_client.py','self_renew.py','laya_questions.json','Run_Windows.ps1','README_RU.md')
foreach($f in $files){Copy-Item -LiteralPath (Join-Path $PSScriptRoot $f) -Destination (Join-Path $root $f) -Force}
if(!(Test-Path -LiteralPath (Join-Path $root 'settings.json'))){Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'settings.example.json') -Destination (Join-Path $root 'settings.json')}
$shortcut=Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\Voice AgentOS Mini.lnk'
$shell=New-Object -ComObject WScript.Shell
$link=$shell.CreateShortcut($shortcut)
$link.TargetPath=(Get-Command powershell.exe).Source
$link.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $root 'Run_Windows.ps1')+'" -PythonPath "'+$PythonPath+'"'
$link.WorkingDirectory=$root
$link.Save()
Write-Output ('Installed local mini controller: '+$root)
Write-Output 'Edit settings.json once, then launch Voice AgentOS Mini from Start Menu.'
