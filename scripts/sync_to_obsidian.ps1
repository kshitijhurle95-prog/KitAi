# ==============================================================================
# KitAi -> Obsidian Automated Synchronization Script
# Synchronizes repository telemetry, test results, and live health into Obsidian.
# ==============================================================================

$ErrorActionPreference = "SilentlyContinue"

$VaultPath = "C:\Users\HP\Documents\Obsidian Vault\KitAi - Autonomous AI Study Agent"
$OverviewFile = Join-Path $VaultPath "00 - KitAi Project Overview.md"
$RepoRoot = "c:\Users\HP\Documents\antigravity\calm-oppenheimer"

Write-Host "Syncing KitAi documentation to Obsidian Vault..." -ForegroundColor Cyan

# 1. Verify Obsidian Vault Directory
if (-not (Test-Path $VaultPath)) {
    Write-Host "Error: Obsidian Vault path not found at $VaultPath" -ForegroundColor Red
    exit 1
}

# 2. Check Backend Server Health
$ServerStatus = "Offline"
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
    if ($health.status -eq "healthy") {
        $ServerStatus = "Online (Port 8000, Model: $($health.default_llm))"
    }
} catch {
    $ServerStatus = "Offline / Standby"
}

# 3. Check Automated Pytest Status
Write-Host "Running pytest verification..." -ForegroundColor DarkGray
$TestStatus = "Tests passing"
try {
    Push-Location "$RepoRoot\backend"
    $pytestOutput = & ".\.venv\Scripts\python.exe" -m pytest -q
    $exitCode = $LASTEXITCODE
    Pop-Location
    if ($exitCode -eq 0) {
        $lastLine = ($pytestOutput | Select-Object -Last 1)
        $TestStatus = "Passing ($lastLine)"
    } else {
        $TestStatus = "Failed (exit code $exitCode)"
    }
} catch {
    $TestStatus = "Not verified"
}

# 4. Get Current Timestamp
$Timestamp = (Get-Date).ToString("dd-MM-yyyy HH:mm:ss 'IST'")

# 5. Update Telemetry Header in 00 - KitAi Project Overview.md
if (Test-Path $OverviewFile) {
    $content = [System.IO.File]::ReadAllText($OverviewFile, [System.Text.Encoding]::UTF8)
    
    # Replace Last Updated timestamp
    $content = $content -replace "(?m)^\> \*\*Last Updated:\*\* .*$", "> **Last Updated:** $Timestamp"
    
    # Add or update Live Health Telemetry
    if ($content -match "(?m)^\> \*\*Server Status:\*\* .*$") {
        $content = $content -replace "(?m)^\> \*\*Server Status:\*\* .*$", "> **Server Status:** $ServerStatus | **Tests:** $TestStatus"
    } else {
        $content = $content -replace "(?m)(\> \*\*Status:\*\* .*$)", "`$1`r`n> **Server Status:** $ServerStatus | **Tests:** $TestStatus"
    }

    [System.IO.File]::WriteAllText($OverviewFile, $content, [System.Text.Encoding]::UTF8)
    Write-Host "KitAi Overview telemetry updated in Obsidian!" -ForegroundColor Green
} else {
    Write-Host "Warning: Overview file not found at $OverviewFile" -ForegroundColor Yellow
}

Write-Host "Sync complete! Obsidian is up to date." -ForegroundColor Cyan
Write-Host "   - Vault: $VaultPath" -ForegroundColor DarkGray
Write-Host "   - Server Status: $ServerStatus" -ForegroundColor DarkGray
Write-Host "   - Test Results: $TestStatus" -ForegroundColor DarkGray
Write-Host "   - Timestamp: $Timestamp" -ForegroundColor DarkGray
