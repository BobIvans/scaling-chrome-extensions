param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot 'connection.json'),
    [string]$PythonPath
)
$ErrorActionPreference = 'Stop'
try {
    $ShellRoot = $PSScriptRoot
    $ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
    if (Test-Path -LiteralPath $ConfigPath -PathType Leaf) {
        $Connection = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $PythonPath) { $PythonPath = $Connection.python_path }
    }
    if (-not $PythonPath -or -not [System.IO.Path]::IsPathRooted($PythonPath) -or
        -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        throw 'Choose an installed Python 3.11+ with Tk: Launch_Windows.ps1 -PythonPath C:\Path\python.exe'
    }
    $PackageArgs = @('-I', '-X', 'utf8', (Join-Path $ShellRoot 'package.py'), 'verify', '--shell', $ShellRoot)
    & $PythonPath @PackageArgs
    if ($LASTEXITCODE -ne 0) { throw 'Desktop shell manifest verification failed.' }
    if (Test-Path -LiteralPath $ConfigPath -PathType Leaf) {
        $PreflightArgs = @('-I', '-X', 'utf8', (Join-Path $ShellRoot 'preflight.py'), '--config', $ConfigPath)
        & $PythonPath @PreflightArgs
        # The window still opens on a failed preflight so settings can be repaired.
    }
    $AppArgs = @('-I', '-X', 'utf8', (Join-Path $ShellRoot 'app.py'), '--config', $ConfigPath)
    & $PythonPath @AppArgs
    exit $LASTEXITCODE
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
