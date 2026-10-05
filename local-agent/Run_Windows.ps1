param([string]$Settings=(Join-Path $PSScriptRoot 'settings.json'),[string]$PythonPath='python')
$ErrorActionPreference='Stop'
& $PythonPath -I -X utf8 (Join-Path $PSScriptRoot 'mini_controller.py') --settings $Settings
exit $LASTEXITCODE
