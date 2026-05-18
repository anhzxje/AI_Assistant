Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
$BackendPreferredPort = 8000
$FrontendPreferredPort = 3002
$BackendCandidates = @($BackendPreferredPort, 8010, 8011, 8012) | Select-Object -Unique
$FrontendCandidates = @($FrontendPreferredPort, 3003, 3004, 3010) | Select-Object -Unique

function Resolve-PowerShellExe {
    $localCandidates = @(
        (Join-Path $PSHOME "powershell.exe"),
        (Join-Path $PSHOME "pwsh.exe")
    )
    foreach ($candidate in $localCandidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    foreach ($name in @("pwsh.exe", "powershell.exe")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }
    throw "Cannot find a PowerShell executable. Current PSHOME=$PSHOME"
}

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
        [Parameter(Mandatory = $true)]$PortProcess,
        [Parameter(Mandatory = $true)][string]$Root
    )
    $name = [string]$PortProcess.ProcessName
    $cmd = [string]$PortProcess.CommandLine
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

function Stop-ProjectProcessOnPort {
    param(
        [int]$Port,
        [string]$Root
    )
    $owners = @(Get-PortProcess -Port $Port)
    foreach ($owner in $owners) {
        Write-Host "Port $Port is used by PID $($owner.PID) $($owner.ProcessName)" -ForegroundColor Yellow
        if ($owner.CommandLine) {
            Write-Host "  $($owner.CommandLine)" -ForegroundColor DarkGray
        }
        if (Test-ProjectDevProcess -PortProcess $owner -Root $Root) {
            Write-Host "Stopping old project dev process on port $Port..." -ForegroundColor Yellow
            Stop-Process -Id $owner.PID -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 700
        } else {
            Write-Host "Process does not look project-owned; leaving it running." -ForegroundColor Yellow
        }
    }
}

function Find-FreePort {
    param(
        [int[]]$Candidates,
        [string]$Root
    )
    foreach ($port in $Candidates) {
        Stop-ProjectProcessOnPort -Port $port -Root $Root
        if (-not @(Get-PortProcess -Port $port)) {
            return $port
        }
        Write-Host "Port $port remains occupied; trying fallback." -ForegroundColor Yellow
    }
    throw "No free port found in candidates: $($Candidates -join ', ')"
}

function Wait-BackendHealth {
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 30
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $url = "http://127.0.0.1:$Port/health"
    while ((Get-Date) -lt $deadline) {
        try {
            $body = Invoke-RestMethod -Uri $url -TimeoutSec 3
            if ($body.status -eq "ok") {
                return $body
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $null
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Head -TimeoutSec 5 -UseBasicParsing
            if ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Start-NewTerminal {
    param(
        [string]$ScriptPath,
        [string[]]$Arguments
    )
    $psExe = Resolve-PowerShellExe
    $argumentList = @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) + $Arguments
    Start-Process -FilePath $psExe -ArgumentList $argumentList
}

function Write-FrontendEnv {
    param([int]$BackendPort)
    $envPath = Join-Path $ProjectRoot "frontend\.env.local"
    "NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:$BackendPort" | Set-Content -Path $envPath -Encoding UTF8
    Write-Host "Updated frontend/.env.local -> NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:$BackendPort" -ForegroundColor Green
}

function Start-BackendWithFallback {
    foreach ($port in $BackendCandidates) {
        Stop-ProjectProcessOnPort -Port $port -Root $ProjectRoot
        if (@(Get-PortProcess -Port $port)) {
            Write-Host "Port $port remains occupied by a non-project process; trying fallback." -ForegroundColor Yellow
            continue
        }
        $candidate = $port
        Write-Host "Starting backend candidate port $candidate..." -ForegroundColor Cyan
        Start-NewTerminal -ScriptPath (Join-Path $ScriptRoot "dev_backend.ps1") -Arguments @("-Port", "$candidate")
        $health = Wait-BackendHealth -Port $candidate -TimeoutSeconds 30
        if ($health) {
            return @{ Port = $candidate; Health = $health }
        }
        Write-Host "Backend did not become healthy on port $candidate; trying fallback." -ForegroundColor Yellow
        Stop-ProjectProcessOnPort -Port $candidate -Root $ProjectRoot
    }
    throw "Backend failed to start on all candidate ports: $($BackendCandidates -join ', ')"
}

function Start-FrontendWithFallback {
    param([int]$BackendPort)
    foreach ($port in $FrontendCandidates) {
        Stop-ProjectProcessOnPort -Port $port -Root $ProjectRoot
        if (@(Get-PortProcess -Port $port)) {
            Write-Host "Port $port remains occupied by a non-project process; trying fallback." -ForegroundColor Yellow
            continue
        }
        $candidate = $port
        Write-Host "Starting frontend candidate port $candidate..." -ForegroundColor Cyan
        Start-NewTerminal -ScriptPath (Join-Path $ScriptRoot "dev_frontend.ps1") -Arguments @("-Port", "$candidate", "-BackendPort", "$BackendPort")
        $ok = Wait-HttpOk -Url "http://127.0.0.1:$candidate/login" -TimeoutSeconds 60
        if ($ok) {
            return $candidate
        }
        Write-Host "Frontend did not respond on port $candidate; trying fallback." -ForegroundColor Yellow
        Stop-ProjectProcessOnPort -Port $candidate -Root $ProjectRoot
    }
    throw "Frontend failed to start on all candidate ports: $($FrontendCandidates -join ', ')"
}

Set-Location $ProjectRoot
Write-Host "Project root: $ProjectRoot" -ForegroundColor Cyan
Write-Host "Starting Docker infra..." -ForegroundColor Cyan
docker compose up -d db redis qdrant

$backend = Start-BackendWithFallback
Write-FrontendEnv -BackendPort $backend.Port
$frontendPort = Start-FrontendWithFallback -BackendPort $backend.Port

$loginUrl = "http://127.0.0.1:$frontendPort/login"
Start-Process $loginUrl

$dockerStatus = docker ps --filter "name=project-root-db-1" --filter "name=project-root-redis-1" --filter "name=project-root-qdrant-1" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host ""
Write-Host "=== Lumi Dev Runtime ===" -ForegroundColor Green
Write-Host "Docker:" -ForegroundColor Green
$dockerStatus | ForEach-Object { Write-Host $_ }
Write-Host "Backend:  http://127.0.0.1:$($backend.Port)  health=$($backend.Health.status) qdrant=$($backend.Health.qdrant) llm=$($backend.Health.llm)" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:$frontendPort" -ForegroundColor Green
Write-Host "Login:    $loginUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Useful accounts:" -ForegroundColor Cyan
Write-Host "  admin@omni.local / admin123456"
Write-Host "  user@omni.local / user123456"
Write-Host "  user2@omni.local / user2123456"
Write-Host ""
Write-Host "Keep the backend and frontend PowerShell windows open while developing." -ForegroundColor Yellow
