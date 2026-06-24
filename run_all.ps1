# run_all.ps1
# Script to run all AskHR services in separate PowerShell windows

Clear-Host
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "      AskHR Enterprise AI System Launcher         " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Determine project root directory
$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = Get-Location
}

Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray
Write-Host ""

# 1. Start LLM Inference Service (Port 8000)
Write-Host "[1/3] Starting LLM Inference Service on Port 8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; cd '$ProjectRoot'; python services/llm_inference_service/server.py" -Title "AskHR - LLM Inference Service"

# Wait a few seconds for the LLM service to load its model before starting the orchestrator
Write-Host "Waiting 5 seconds for the LLM model to load..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 2. Start Orchestrator Service (Port 8081)
Write-Host "[2/3] Starting Orchestrator Service on Port 8081..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; cd '$ProjectRoot'; python -m uvicorn services.orchestrator_service.main:app --host 127.0.0.1 --port 8081 --reload" -Title "AskHR - Orchestrator Service"

# 3. Start Frontend Service (Port 8082)
Write-Host "[3/3] Starting Frontend Service on Port 8082..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; cd '$ProjectRoot'; python services/frontend_service/server.py" -Title "AskHR - Frontend Service"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  All services have been launched successfully!   " -ForegroundColor Cyan
Write-Host "  - LLM API:          http://127.0.0.1:8000/health" -ForegroundColor Gray
Write-Host "  - Orchestrator API: http://127.0.0.1:8081/health" -ForegroundColor Gray
Write-Host "  - Frontend Portal:  http://127.0.0.1:8082"        -ForegroundColor Gray
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "You can close this main window. The services will continue running in their own windows." -ForegroundColor Yellow
Start-Sleep -Seconds 2
