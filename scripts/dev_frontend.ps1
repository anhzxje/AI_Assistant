param(
    [int]$Port = 3002,
    [int]$BackendPort = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$EnvPath = Join-Path $FrontendRoot ".env.local"

"NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:$BackendPort" | Set-Content -Path $EnvPath -Encoding UTF8

Set-Location $FrontendRoot
Write-Host "Starting frontend dev server on http://127.0.0.1:$Port" -ForegroundColor Cyan
Write-Host "Using backend http://127.0.0.1:$BackendPort" -ForegroundColor Cyan
npm.cmd run dev -- --hostname 127.0.0.1 --port $Port
