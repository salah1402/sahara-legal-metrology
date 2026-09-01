# Start MetraCheck Frontend Server
$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$rootDir\frontend"
Write-Host "Starting MetraCheck Frontend on http://127.0.0.1:5173..." -ForegroundColor Cyan
npm run dev -- --host 127.0.0.1 --port 5173
