param(
    [switch]$StopDocker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
$CandidatePorts = @(8000, 8010, 8011, 8012, 3002, 3003, 3004, 3010)

function Get-PortProcess {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    $pids = @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($processId in $pids) {
        if (-not $processId) {
            continue
        }
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if ($proc) {
            [PSCustomObject]@{
                Port = $Port
                PID = $processId
                ProcessName = $proc.ProcessName
                CommandLine = if ($cim) { $cim.CommandLine } else { "" }
            }
        }
    }
}

function Test-ProjectDevProcess {
    param(
        [Parameter(Mandatory = $true)]$ProcessInfo,
        [Parameter(Mandatory = $true)][string]$Root
    )
    $name = [string]$ProcessInfo.ProcessName
    $cmd = [string]$ProcessInfo.CommandLine
    $rootNeedle = $Root.ToLowerInvariant()
    $cmdLower = $cmd.ToLowerInvariant()
    $isPython = $name -in @("python", "python3")
    $isNode = $name -in @("node", "npm", "npm.cmd")
    $hasProjectRoot = $cmdLower.Contains($rootNeedle)
    $isBackendDev =
        $cmdLower.Contains("backend.app.main") -or
        $cmdLower.Contains("scripts/run_backend.py") -or
        $cmdLower.Contains("scripts\run_backend.py") -or
        $cmdLower.Contains("dev_backend.ps1")
    $isFrontendDev =
        $cmdLower.Contains("dev_frontend.ps1") -or
        ($hasProjectRoot -and (
            $cmdLower.Contains("npm.cmd run dev") -or
            $cmdLower.Contains("next") -or
            $cmdLower.Contains("\frontend")
        ))
    return (($isPython -and ($hasProjectRoot -or $isBackendDev)) -or ($isNode -and $isFrontendDev))
}

function Stop-ProjectProcess {
    param($ProcessInfo)
    if ($ProcessInfo.PID -eq $PID) {
        return
    }
    Write-Host "Stopping PID $($ProcessInfo.PID) $($ProcessInfo.ProcessName)" -ForegroundColor Yellow
    if ($ProcessInfo.CommandLine) {
        Write-Host "  $($ProcessInfo.CommandLine)" -ForegroundColor DarkGray
    }
    Stop-Process -Id $ProcessInfo.PID -Force -ErrorAction SilentlyContinue
}

Set-Location $ProjectRoot
Write-Host "Stopping OmniAssistant dev servers for $ProjectRoot" -ForegroundColor Cyan

$seen = @{}
foreach ($port in $CandidatePorts) {
    foreach ($owner in @(Get-PortProcess -Port $port)) {
        if ($seen.ContainsKey([string]$owner.PID)) {
            continue
        }
        $seen[[string]$owner.PID] = $true
        if (Test-ProjectDevProcess -ProcessInfo $owner -Root $ProjectRoot) {
            Stop-ProjectProcess -ProcessInfo $owner
        } else {
            Write-Host "Leaving non-project process on port ${port}: PID $($owner.PID) $($owner.ProcessName)" -ForegroundColor Yellow
        }
    }
}

$rootNeedle = $ProjectRoot.ToLowerInvariant()
$projectProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessId -ne $PID -and
    $_.CommandLine -and
    $_.CommandLine.ToLowerInvariant().Contains($rootNeedle) -and
    (
        $_.CommandLine.ToLowerInvariant().Contains("backend.app.main") -or
        $_.CommandLine.ToLowerInvariant().Contains("dev_backend.ps1") -or
        $_.CommandLine.ToLowerInvariant().Contains("dev_frontend.ps1") -or
        $_.CommandLine.ToLowerInvariant().Contains("npm.cmd run dev") -or
        $_.CommandLine.ToLowerInvariant().Contains("next")
    )
}

foreach ($processInfo in $projectProcesses) {
    if ($seen.ContainsKey([string]$processInfo.ProcessId)) {
        continue
    }
    $proc = Get-Process -Id $processInfo.ProcessId -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-ProjectProcess -ProcessInfo ([PSCustomObject]@{
            PID = $processInfo.ProcessId
            ProcessName = $proc.ProcessName
            CommandLine = $processInfo.CommandLine
        })
    }
}

if ($StopDocker) {
    Write-Host "Stopping Docker infra: db redis qdrant" -ForegroundColor Yellow
    docker compose stop db redis qdrant
} else {
    Write-Host "Docker infra left running. Use .\scripts\stop_dev.ps1 -StopDocker to stop it." -ForegroundColor Green
}

Write-Host "Dev server stop complete." -ForegroundColor Green
