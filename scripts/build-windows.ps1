param([switch]$WithContainers)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    uv sync --frozen
    uv run pytest
    pnpm install --frozen-lockfile
    pnpm --filter '@superbot/desktop' test --run
    pnpm --filter '@superbot/desktop' package:win
    if ($WithContainers) {
        if (-not (Test-Path -LiteralPath '.env')) {
            throw 'Create .env from .env.example before building containers.'
        }
        docker compose config --quiet
        if ($LASTEXITCODE -ne 0) { throw 'docker compose configuration is invalid' }
        docker compose build --pull api worker scheduler
        if ($LASTEXITCODE -ne 0) { throw 'container build failed' }
    }
}
finally {
    Pop-Location
}
