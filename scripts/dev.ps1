param(
    [switch]$Browser,
    [switch]$NoDesktop
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.env')) {
        throw 'Create .env from .env.example and set the required passwords first.'
    }
    $composeArgs = @('compose')
    if ($Browser) { $composeArgs += @('--profile', 'browser') }
    $composeArgs += @('up', '-d', '--build', '--wait')
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) { throw 'docker compose failed' }
    if (-not $NoDesktop) { pnpm --filter '@superbot/desktop' dev }
}
finally {
    Pop-Location
}
