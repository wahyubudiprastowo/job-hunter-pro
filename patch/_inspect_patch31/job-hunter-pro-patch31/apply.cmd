@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 31
echo   Indeed 2026 Fixes (URL + Selectors + Cloudflare)
echo =====================================================
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p31_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\extractors" 2>nul

if exist "%PROJECT_ROOT%\packages\extractors\indeed_2026_fixes.py" (
    copy /Y "%PROJECT_ROOT%\packages\extractors\indeed_2026_fixes.py" "%BACKUP_DIR%\packages\extractors\indeed_2026_fixes.py" >nul
    echo   [OK] Backed up existing helper
)
echo.

echo [INFO] Installing Patch 31 helper module...
copy /Y "%PATCH_ROOT%\packages\extractors\indeed_2026_fixes.py" "%PROJECT_ROOT%\packages\extractors\indeed_2026_fixes.py" >nul && echo   [OK] indeed_2026_fixes.py installed

echo.
echo =====================================================
echo   [SUCCESS] Helper installed!
echo =====================================================
echo.
echo CRITICAL NEXT STEPS:
echo.
echo 1. Read INTEGRATION_SNIPPETS.md
echo.
echo 2. Edit packages\extractors\indeed.py:
echo    a. Add imports from indeed_2026_fixes
echo    b. Replace _build_search_url function body
echo    c. Replace collect_job_cards function body  
echo    d. Add Cloudflare check di search() + login()
echo    e. Update SELECTORS dict
echo.
echo 3. Edit packages\stealth\browser.py:
echo    Add get_stealth_chrome_options() + apply_stealth_javascript()
echo.
echo 4. Restart bot:
echo    python run_web.py
echo    Click INDEED only
echo.
echo 5. Watch log for "Collected N > 0" and Cloudflare bypass.
echo.
endlocal
