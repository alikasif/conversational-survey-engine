param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet("start", "stop", "status")]
    [string]$Action
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root ".venv\Scripts\Activate.ps1"
$Creds = Join-Path $Root "gen-lang-client-0575690477-7f0434f5aa44.json"

function Test-ServerHealth {
    Write-Host ""
    Write-Host "=== Server Status ===" -ForegroundColor Cyan

    # Port check
    $backendPort = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    $frontendPort = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

    Write-Host "Backend  (port 8000): $(if ($backendPort) { 'LISTENING' } else { 'DOWN' })" -ForegroundColor $(if ($backendPort) { 'Green' } else { 'Red' })
    Write-Host "Frontend (port 5173): $(if ($frontendPort) { 'LISTENING' } else { 'DOWN' })" -ForegroundColor $(if ($frontendPort) { 'Green' } else { 'Red' })

    # Backend health endpoint
    if ($backendPort) {
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "Backend  /api/health: OK ($($health.status))" -ForegroundColor Green
        } catch {
            try {
                $code = $_.Exception.Response.StatusCode.value__
                Write-Host "Backend  /api/health: HTTP $code" -ForegroundColor Yellow
            } catch {
                Write-Host "Backend  /api/health: UNREACHABLE" -ForegroundColor Red
            }
        }

        # Verify routes are loaded (not stale)
        try {
            $openapi = Invoke-RestMethod -Uri "http://localhost:8000/openapi.json" -TimeoutSec 5 -ErrorAction Stop
            $routes = ($openapi.paths.PSObject.Properties | Measure-Object).Count
            Write-Host "Backend  routes:      $routes endpoints loaded" -ForegroundColor Green
        } catch {
            Write-Host "Backend  routes:      FAILED to fetch openapi.json" -ForegroundColor Red
        }
    }

    # Frontend check
    if ($frontendPort) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 5 -ErrorAction Stop -UseBasicParsing
            Write-Host "Frontend http://localhost:5173: OK ($($resp.StatusCode))" -ForegroundColor Green
        } catch {
            Write-Host "Frontend http://localhost:5173: UNREACHABLE" -ForegroundColor Red
        }
    }

    Write-Host "=======================" -ForegroundColor Cyan
}

function Start-Servers {
    Write-Host "Starting backend server..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:GOOGLE_APPLICATION_CREDENTIALS = '$Creds'; & '$Venv'; Push-Location '$Root\backend'; python -m uvicorn app.main:app --port 8000 --host 0.0.0.0" -WindowStyle Normal

    Write-Host "Starting frontend server..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Push-Location '$Root\frontend'; npm run dev" -WindowStyle Normal

    Start-Sleep -Seconds 3
    $backendUp = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    $frontendUp = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

    Write-Host ""
    Write-Host "Backend  (port 8000): $(if ($backendUp) { 'UP' } else { 'STARTING...' })" -ForegroundColor $(if ($backendUp) { 'Green' } else { 'Yellow' })
    Write-Host "Frontend (port 5173): $(if ($frontendUp) { 'UP' } else { 'STARTING...' })" -ForegroundColor $(if ($frontendUp) { 'Green' } else { 'Yellow' })

    # Wait a bit more and run full health check
    if (-not $backendUp -or -not $frontendUp) {
        Write-Host "Waiting for servers to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
    Test-ServerHealth
}

function Stop-Servers {
    Write-Host "Stopping servers..." -ForegroundColor Cyan

    Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

    Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

    Start-Sleep -Seconds 1

    $backendUp = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    $frontendUp = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

    if (-not $backendUp -and -not $frontendUp) {
        Write-Host "All servers stopped." -ForegroundColor Green
    } else {
        if ($backendUp) { Write-Host "WARNING: Backend still running on port 8000" -ForegroundColor Red }
        if ($frontendUp) { Write-Host "WARNING: Frontend still running on port 5173" -ForegroundColor Red }
    }
}

switch ($Action) {
    "start"  { Start-Servers }
    "stop"   { Stop-Servers }
    "status" { Test-ServerHealth }
}
