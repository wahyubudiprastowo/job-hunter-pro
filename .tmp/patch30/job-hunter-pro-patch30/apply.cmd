@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 30
echo   Premium Glassmorphism UI + Real-Time Progress
echo =====================================================
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p30_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\apps\web\static" 2>nul
mkdir "%BACKUP_DIR%\apps\web\templates" 2>nul

if exist "%PROJECT_ROOT%\apps\web\static\styles.css" (
    copy /Y "%PROJECT_ROOT%\apps\web\static\styles.css" "%BACKUP_DIR%\apps\web\static\styles.css" >nul
    echo   [OK] Backed up styles.css
)
if exist "%PROJECT_ROOT%\apps\web\templates\dashboard.html" (
    copy /Y "%PROJECT_ROOT%\apps\web\templates\dashboard.html" "%BACKUP_DIR%\apps\web\templates\dashboard.html" >nul
    echo   [OK] Backed up dashboard.html
)
echo.

echo [INFO] Installing Premium UI...
mkdir "%PROJECT_ROOT%\apps\web\static" 2>nul

copy /Y "%PATCH_ROOT%\apps\web\static\styles.css" "%PROJECT_ROOT%\apps\web\static\styles.css" >nul && echo   [OK] styles.css (Premium Glassmorphism)
copy /Y "%PATCH_ROOT%\apps\web\static\realtime.js" "%PROJECT_ROOT%\apps\web\static\realtime.js" >nul && echo   [OK] realtime.js (Live updates)
copy /Y "%PATCH_ROOT%\apps\web\realtime_tracker.py" "%PROJECT_ROOT%\apps\web\realtime_tracker.py" >nul && echo   [OK] realtime_tracker.py (Backend)
copy /Y "%PATCH_ROOT%\apps\web\templates\dashboard.html" "%PROJECT_ROOT%\apps\web\templates\dashboard.html" >nul && echo   [OK] dashboard.html (Premium template)

echo.
echo =====================================================
echo   [SUCCESS] Premium UI installed!
echo =====================================================
echo.
echo NEXT STEPS (REQUIRED for real-time):
echo.
echo 1. Update apps\web\app.py:
echo    Add /api/realtime/progress route
echo    See: INTEGRATION_SNIPPETS.md Step 2
echo.
echo 2. Update apps\worker\runner.py:
echo    Add tracker hook calls at events
echo    See: INTEGRATION_SNIPPETS.md Step 3
echo.
echo 3. Restart bot:
echo    python run_web.py
echo.
echo 4. Open: http://localhost:5050
echo.
echo Enjoy your PREMIUM dashboard! :)
echo.
endlocal
