# run_all.ps1
# Script to run all AskHR services in separate PowerShell windows
# Save Path: P:\____AI____\HSAGroup\AskHRPro\run\run_all.ps1
# Run all
# & "P:\____AI____\HSAGroup\AskHRPro\run\run_all.ps1"
# Stop all 
# taskkill /F /IM python.exe


# cloudeflare 
# C:\cloudflared.exe tunnel --url http://127.0.0.1:8082

Clear-Host
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "      AskHR Enterprise AI System Launcher         " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Determine project root directory
# Since this script resides in the run/ directory, the parent is the project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item $ScriptDir).Parent.FullName

if (-not $ProjectRoot) {
    $ProjectRoot = Get-Location
}

Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray
Write-Host ""

# =====================================================================
# [Part 1]: LLM Inference Service (Port 8000)
# Manual Command:
# python services/llm_inference_service/server.py
# =====================================================================
Write-Host "[1/3] Starting LLM Inference Service on Port 8000..." -ForegroundColor Green

$LLMCommand = "`$host.ui.RawUI.WindowTitle='AskHR - LLM Inference Service'; `$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; cd '$ProjectRoot'; python services/llm_inference_service/server.py"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $LLMCommand


# Wait 5 seconds for the LLM model to load before starting the orchestrator
Write-Host "Waiting 5 seconds for the LLM model to load..." -ForegroundColor Yellow
Start-Sleep -Seconds 5


# =====================================================================
# [Part 2]: Orchestrator Service (Port 8081)
# Manual Command:
# python -m uvicorn services.orchestrator_service.main:app --host 127.0.0.1 --port 8081 --reload
# =====================================================================
Write-Host "[2/3] Starting Orchestrator Service on Port 8081..." -ForegroundColor Green

$OrchCommand = "`$host.ui.RawUI.WindowTitle='AskHR - Orchestrator Service'; `$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; cd '$ProjectRoot'; python -m uvicorn services.orchestrator_service.main:app --host 127.0.0.1 --port 8081 --reload"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $OrchCommand


# =====================================================================
# [Part 3]: Frontend Service (Port 8082)
# Manual Command:
# python services/frontend_service/server.py
# =====================================================================
Write-Host "[3/3] Starting Frontend Service on Port 8082..." -ForegroundColor Green

$FrontendCommand = "`$host.ui.RawUI.WindowTitle='AskHR - Frontend Service'; `$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; cd '$ProjectRoot'; python services/frontend_service/server.py"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCommand


Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "         All services launched successfully!       " -ForegroundColor Cyan
Write-Host "  - LLM API:          http://127.0.0.1:8000/health" -ForegroundColor Gray
Write-Host "  - Orchestrator API: http://127.0.0.1:8081/health" -ForegroundColor Gray
Write-Host "  - Frontend Portal:  http://127.0.0.1:8082"        -ForegroundColor Gray
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "You can close this main window. Services will run in their own windows." -ForegroundColor Yellow
Start-Sleep -Seconds 3
