@echo off
set "ROOT=%~dp0"
echo Starting MetraCheck Development Environment...

start "MetraCheck Backend" powershell -NoExit -Command "cd '%ROOT%'; Write-Host '=== MetraCheck Backend (Port 8000) ===' -ForegroundColor Green; & '.\ocr test\.venv\Scripts\python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

start "MetraCheck Frontend" powershell -NoExit -Command "cd '%ROOT%frontend'; Write-Host '=== MetraCheck Frontend (Port 5173) ===' -ForegroundColor Green; npm run dev -- --host 127.0.0.1 --port 5173"

echo MetraCheck servers launched in persistent windows.
echo   Backend API: http://127.0.0.1:8000
echo   Frontend UI: http://127.0.0.1:5173
