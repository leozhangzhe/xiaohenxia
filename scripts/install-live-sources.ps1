param([string]$PythonExe = '', [switch]$IncludeApp, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $PythonExe) {
    $PythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $PythonExe)) { $PythonExe = (Get-Command python.exe -ErrorAction Stop).Source }
}
$arguments = @((Join-Path $PSScriptRoot 'setup_live_sources.py'))
if ($IncludeApp) { $arguments += '--include-app' }
if ($CheckOnly) { $arguments += '--check' }
& $PythonExe @arguments
exit $LASTEXITCODE
