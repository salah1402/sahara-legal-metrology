# MetraCheck Development Server Launcher (Persistent Windows)
$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting MetraCheck Backend (FastAPI + RapidOCR)..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "cd '$rootDir'; Write-Host '=== MetraCheck Backend (FastAPI on Port 8000) ===' -ForegroundColor Green; & '.\ocr test\.venv\Scripts\python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "Starting MetraCheck Frontend (Vite React)..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "cd '$rootDir\frontend'; Write-Host '=== MetraCheck Frontend (Vite on Port 5173) ===' -ForegroundColor Green; npm run dev -- --host 127.0.0.1 --port 5173"

Write-Host "`nMetraCheck development servers launched in independent persistent terminals:" -ForegroundColor Green
Write-Host "  Backend API: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "  Frontend UI: http://127.0.0.1:5173`n" -ForegroundColor Yellow
