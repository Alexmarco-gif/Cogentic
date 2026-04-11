[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Prefer the repo .env Redis setting over any stale shell override.
Remove-Item Env:REDIS_URL -ErrorAction SilentlyContinue

Write-Host "Starting backend with repo-local environment..." -ForegroundColor Cyan
Write-Host "Repo root: $repoRoot" -ForegroundColor DarkGray
Write-Host "Host: $HostAddress  Port: $Port" -ForegroundColor DarkGray

& ".\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host $HostAddress --port $Port
