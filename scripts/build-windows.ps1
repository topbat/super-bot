Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'docker compose configuration is invalid' }
    uv sync --frozen
    uv run pytest
    pnpm install --frozen-lockfile
    pnpm --filter '@superbot/desktop' test --run
    pnpm --filter '@superbot/desktop' build
    docker compose build --pull
}
finally {
    Pop-Location
}
