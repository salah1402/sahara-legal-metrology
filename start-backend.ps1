# Start MetraCheck Backend Server
$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rootDir
Write-Host "Starting MetraCheck Backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
& ".\ocr test\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
