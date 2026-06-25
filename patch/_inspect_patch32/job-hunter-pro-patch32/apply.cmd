@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 32
echo   Discovery and Curation Mode
echo =====================================================
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p32_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\storage" 2>nul
mkdir "%BACKUP_DIR%\apps\web\templates" 2>nul

if exist "%PROJECT_ROOT%\packages\storage\discovered_jobs.py" (
    copy /Y "%PROJECT_ROOT%\packages\storage\discovered_jobs.py" "%BACKUP_DIR%\packages\storage\discovered_jobs.py" >nul
    echo   [OK] Backed up discovered_jobs.py
)

if exist "%PROJECT_ROOT%\apps\web\templates\discovered.html" (
    copy /Y "%PROJECT_ROOT%\apps\web\templates\discovered.html" "%BACKUP_DIR%\apps\web\templates\discovered.html" >nul
    echo   [OK] Backed up discovered.html
)
echo.

echo [INFO] Installing Patch 32...
copy /Y "%PATCH_ROOT%\packages\storage\discovered_jobs.py" "%PROJECT_ROOT%\packages\storage\discovered_jobs.py" >nul && echo   [OK] discovered_jobs.py installed
copy /Y "%PATCH_ROOT%\apps\web\templates\discovered.html" "%PROJECT_ROOT%\apps\web\templates\discovered.html" >nul && echo   [OK] discovered.html installed

echo.
echo =====================================================
echo   [SUCCESS] Patch 32 files installed!
echo =====================================================
echo.
echo NEXT STEPS (REQUIRED):
echo.
echo 1. Read INTEGRATION_SNIPPETS.md
echo.
echo 2. Edit config.yaml:
echo    Add discovery: section (enabled: false default)
echo.
echo 3. Edit apps/web/app.py:
echo    Add 5 routes (discovered_page, action, bulk-action,
echo                   apply-selected, schedule)
echo.
echo 4. Edit apps/worker/runner.py:
echo    Add discovery_mode branch in per-card loop
echo.
echo 5. Edit apps/web/templates/base.html:
echo    Add nav item for "Discovered"
echo.
echo 6. Restart bot:
echo    python run_web.py
echo.
echo 7. Enable discovery mode:
echo    config.yaml: discovery.enabled: true
echo.
echo 8. Click Start, then visit:
echo    http://localhost:5050/discovered
echo.
endlocal
