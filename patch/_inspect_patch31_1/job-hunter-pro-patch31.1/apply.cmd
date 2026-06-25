@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 31.1
echo   Critical Bug Fixes (Selector + URL + Title + Crash)
echo =====================================================
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p311_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\extractors" 2>nul

if exist "%PROJECT_ROOT%\packages\extractors\indeed_v2_fixes.py" (
    copy /Y "%PROJECT_ROOT%\packages\extractors\indeed_v2_fixes.py" "%BACKUP_DIR%\packages\extractors\indeed_v2_fixes.py" >nul
    echo   [OK] Backed up existing helper
)
echo.

echo [INFO] Installing Patch 31.1 helper...
copy /Y "%PATCH_ROOT%\packages\extractors\indeed_v2_fixes.py" "%PROJECT_ROOT%\packages\extractors\indeed_v2_fixes.py" >nul && echo   [OK] indeed_v2_fixes.py installed

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
echo    a. Add imports from indeed_v2_fixes
echo    b. Replace _build_search_url body
echo    c. Replace collect_job_cards body
echo.
echo 3. Edit apps\worker\runner.py around line 821:
echo    Change "NotificationCategory.SUMMARY" to "NotificationCategory.DAILY_SUMMARY"
echo.
echo 4. Restart bot:
echo    python run_web.py
echo    Click INDEED only
echo.
echo 5. Watch log for:
echo    - "scoped to results" (Fix A working)
echo    - URL with sc=DSQF7 only, no PAXZC (Fix B)
echo    - SKIP with non-empty title (Fix C)
echo    - Clean Run done (Fix D - no crash)
echo.
endlocal
