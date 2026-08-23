param([switch]$Browser)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.env')) {
        throw 'Create .env from .env.example and set the required passwords first.'
    }
    $configArgs = @('compose')
    if ($Browser) { $configArgs += @('--profile', 'browser') }
    $configArgs += @('config', '--quiet')
    & docker @configArgs
    if ($LASTEXITCODE -ne 0) { throw 'docker compose configuration is invalid' }
    docker compose ps --format json
    if ($LASTEXITCODE -ne 0) { throw 'docker compose status failed' }
    Invoke-RestMethod -Uri 'http://127.0.0.1:8420/health' -TimeoutSec 5 | Out-Null
}
finally {
    Pop-Location
}
