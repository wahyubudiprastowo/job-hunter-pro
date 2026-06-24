# Quick start for Windows native run.
$ErrorActionPreference = "Stop"

if (-Not (Test-Path ".venv")) {
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
} else {
    .\.venv\Scripts\Activate.ps1
}

if (-Not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Edit .env with your credentials, then re-run." -ForegroundColor Yellow
    exit 1
}

python run_web.py
