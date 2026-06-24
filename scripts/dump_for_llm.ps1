param([string[]]$Files)

if (-not $Files) {
    # Default critical files
    $Files = @(
        "packages/ai/resume_tailor.py",
        "packages/ai/cv_extractor.py",
        "packages/ai/provider.py",
        "packages/ai/question_bot.py",
        "apps/worker/runner.py",
        "apps/worker/control.py",
        "apps/web/app.py",
        "packages/extractors/linkedin.py",
        "packages/stealth/browser.py",
        "config.yaml"
    )
}

foreach ($f in $Files) {
    if (Test-Path $f) {
        Write-Output "=== FILE: $f ==="
        Get-Content $f -Raw
        Write-Output ""
        Write-Output ""
    } else {
        Write-Output "=== MISSING: $f ==="
    }
}