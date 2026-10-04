$ErrorActionPreference = "Stop"
Push-Location (Join-Path $PSScriptRoot "..")
try {
  python -m unittest discover -s tests -v
  if ($LASTEXITCODE -ne 0) { throw "Toolkit tests failed." }
} finally { Pop-Location }
