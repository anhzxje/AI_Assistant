param(
    [int]$Port = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot

Set-Location $ProjectRoot
Write-Host "Starting backend dev server on http://127.0.0.1:$Port" -ForegroundColor Cyan
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port $Port
