# StudyBrain Local Development Server Launch Script
Write-Host "🧠 Launching StudyBrain AI Study Agent..." -ForegroundColor Cyan

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Set-Location "c:\Users\HP\Documents\antigravity\calm-oppenheimer\backend"

if (-not (Test-Path ".venv\Scripts\uvicorn.exe")) {
    Write-Host "Virtual environment uvicorn binary not found. Please verify setup." -ForegroundColor Red
    exit 1
}

Write-Host "Starting FastAPI server on http://localhost:8000..." -ForegroundColor Green
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
