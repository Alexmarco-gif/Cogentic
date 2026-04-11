[CmdletBinding()]
param(
    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $repoRoot "frontend"
Set-Location $frontendRoot

Write-Host "Starting frontend with frontend/.env.local..." -ForegroundColor Cyan
Write-Host "Frontend root: $frontendRoot" -ForegroundColor DarkGray
Write-Host "Port: $Port" -ForegroundColor DarkGray

node node_modules\next\dist\bin\next dev -p $Port
