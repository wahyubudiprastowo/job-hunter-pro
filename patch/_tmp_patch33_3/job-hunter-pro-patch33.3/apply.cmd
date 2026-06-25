@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 33.3
echo   Indeed + Glassdoor Production Fixes
echo =====================================================
echo.

echo [INFO] Installing helper modules + verification script...
mkdir "%PROJECT_ROOT%\packages\extractors" 2>nul
mkdir "%PROJECT_ROOT%\scripts" 2>nul

copy /Y "%PATCH_ROOT%\packages\extractors\robust_click.py" "%PROJECT_ROOT%\packages\extractors\robust_click.py" >nul && echo   [OK] robust_click.py installed
copy /Y "%PATCH_ROOT%\scripts\check_glassdoor_ready.py" "%PROJECT_ROOT%\scripts\check_glassdoor_ready.py" >nul && echo   [OK] check_glassdoor_ready.py installed

echo.
echo =====================================================
echo   [SUCCESS] Helper files installed!
echo =====================================================
echo.
echo CRITICAL NEXT STEPS:
echo.
echo 1. READ RECOMMENDATIONS.md
echo    Contains daily workflow + best practices
echo.
echo 2. APPLY MANUAL FIXES (see INTEGRATION_SNIPPETS.md):
echo    - Edit packages\extractors\indeed.py line ~561
echo      Replace ActionChains click with robust_click
echo    - Reduce queries in config.yaml (5 instead of 10)
echo.
echo 3. VERIFY GLASSDOOR:
echo    python scripts\check_glassdoor_ready.py
echo.
echo 4. APPLY REAL JOBS:
echo    python run_web.py
echo    Visit /discovered
echo    Find BCG Platinion (fit 78)
echo    Click Apply Now!
echo.
echo Your next job is statistically 60 applies away.
echo Let's start tonight.
echo.
endlocal
