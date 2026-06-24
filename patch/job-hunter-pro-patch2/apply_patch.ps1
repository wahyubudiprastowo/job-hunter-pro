param([string]$ProjectPath = "C:\Users\WP2300419\Documents\VContainer\job-hunter-pro")
$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$patchRoot = $PSScriptRoot

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Job-Hunter Pro - PATCH 2 Auto-Apply" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

if (-Not (Test-Path $ProjectPath)) {
    Write-Host "[ERROR] Project not found: $ProjectPath" -ForegroundColor Red
    exit 1
}

$files = @("packages\extractors\linkedin.py","data\answers.json")
$backupDir = Join-Path $ProjectPath ".backup_p2_$ts"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
Write-Host "[INFO] Backups to: $backupDir" -ForegroundColor Yellow

foreach ($f in $files) {
    $src = Join-Path $ProjectPath $f
    if (Test-Path $src) {
        $dest = Join-Path $backupDir $f
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        Copy-Item $src $dest -Force
        Write-Host "  [OK] Backed up: $f" -ForegroundColor Gray
    }
}

Write-Host "[INFO] Applying patches..." -ForegroundColor Yellow
foreach ($f in $files) {
    $src = Join-Path $patchRoot $f
    $dest = Join-Path $ProjectPath $f
    if (Test-Path $src) {
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        Copy-Item $src $dest -Force
        Write-Host "  [OK] Patched: $f" -ForegroundColor Green
    }
}

Write-Host "[SUCCESS] Done! Restart with: python run_web.py" -ForegroundColor Green