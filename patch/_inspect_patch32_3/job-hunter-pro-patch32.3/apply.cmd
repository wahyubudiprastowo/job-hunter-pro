@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 32.3
echo   Browser Profile Reset Button
echo =====================================================
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p323_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\stealth" 2>nul

if exist "%PROJECT_ROOT%\packages\stealth\profile_manager.py" (
    copy /Y "%PROJECT_ROOT%\packages\stealth\profile_manager.py" "%BACKUP_DIR%\packages\stealth\profile_manager.py" >nul
    echo   [OK] Backed up existing profile_manager.py
)
echo.

echo [INFO] Installing Patch 32.3 helper...
copy /Y "%PATCH_ROOT%\packages\stealth\profile_manager.py" "%PROJECT_ROOT%\packages\stealth\profile_manager.py" >nul && echo   [OK] profile_manager.py installed

echo.
echo =====================================================
echo   [SUCCESS] Helper installed!
echo =====================================================
echo.
echo NEXT STEPS:
echo.
echo 1. Read INTEGRATION_SNIPPETS.md
echo.
echo 2. Update apps\web\app.py:
echo    Add 3 routes for profile management
echo    See: INTEGRATION_SNIPPETS.md Step 2
echo.
echo 3. Update apps\web\templates\settings.html:
echo    Add Profiles section with cards + buttons
echo    See: INTEGRATION_SNIPPETS.md Step 3
echo.
echo 4. Restart bot:
echo    python run_web.py
echo.
echo 5. Visit: http://localhost:5050/settings?section=profiles
echo.
echo 6. Click "Reset Profile" on Indeed to test!
echo    Chrome will launch automatically with fresh profile.
echo.
endlocal
