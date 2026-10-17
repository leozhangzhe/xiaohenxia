param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousLocation = Get-Location

try {
    if ([string]::IsNullOrWhiteSpace($env:SF_AUTH_MYSQL_USER)) {
        throw 'Set SF_AUTH_MYSQL_USER explicitly before startup.'
    }
    if ([string]::IsNullOrEmpty($env:SF_AUTH_MYSQL_PASSWORD)) {
        throw 'Set SF_AUTH_MYSQL_PASSWORD in the current process environment before startup.'
    }

    $pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        throw 'Project .venv is missing. Install requirements into a project virtual environment first.'
    }

    foreach ($item in @(
        @('SPIDERFOOT_DATA', '.runtime-profile\.spiderfoot'),
        @('SPIDERFOOT_LOGS', '.runtime-profile\.spiderfoot\logs'),
        @('SPIDERFOOT_CACHE', '.runtime-profile\.spiderfoot\cache')
    )) {
        $runtimePath = [Environment]::GetEnvironmentVariable($item[0], 'Process')
        if ([string]::IsNullOrEmpty($runtimePath)) {
            $runtimePath = Join-Path $projectRoot $item[1]
        }
        $resolved = [IO.Path]::GetFullPath($runtimePath)
        if (-not $resolved.StartsWith($projectRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw ($item[0] + ' must point inside this project when using the local launcher.')
        }
        [Environment]::SetEnvironmentVariable($item[0], $resolved, 'Process')
    }

    Set-Location -LiteralPath $projectRoot
    & $pythonExe -B (Join-Path $PSScriptRoot 'auth_admin.py') --check
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if ($CheckOnly) {
        Write-Host 'Authentication preflight passed. No Web server was started.'
        exit 0
    }

    $frontend = Join-Path $projectRoot 'spiderfoot\static\node_modules\jquery\dist\jquery.min.js'
    if (-not (Test-Path -LiteralPath $frontend)) {
        throw 'Frontend dependencies are missing. Install them before starting the application.'
    }
    Write-Host 'Starting the application at http://127.0.0.1:5001/login ...'
    & $pythonExe -B (Join-Path $projectRoot 'sf.py') -l 127.0.0.1:5001
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
} finally {
    Set-Location -LiteralPath $previousLocation.Path
}
