@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 28.1
echo   Real Settings Integration (Config + Env)
echo =====================================================
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p281_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\apps\web\templates" 2>nul

if exist "%PROJECT_ROOT%\apps\web\settings_api.py" (
    copy /Y "%PROJECT_ROOT%\apps\web\settings_api.py" "%BACKUP_DIR%\apps\web\settings_api.py" >nul
    echo   [OK] Backed up existing settings_api.py
)
if exist "%PROJECT_ROOT%\apps\web\templates\settings.html" (
    copy /Y "%PROJECT_ROOT%\apps\web\templates\settings.html" "%BACKUP_DIR%\apps\web\templates\settings.html" >nul
    echo   [OK] Backed up existing settings.html
)
echo.

echo [INFO] Installing Patch 28.1...
copy /Y "%PATCH_ROOT%\apps\web\settings_api.py" "%PROJECT_ROOT%\apps\web\settings_api.py" >nul && echo   [OK] settings_api.py installed
copy /Y "%PATCH_ROOT%\apps\web\templates\settings.html" "%PROJECT_ROOT%\apps\web\templates\settings.html" >nul && echo   [OK] settings.html installed

echo.
echo =====================================================
echo   [SUCCESS] Patch 28.1 installed!
echo =====================================================
echo.
echo NEXT STEPS:
echo.
echo 1. Update apps\web\app.py:
echo    Add 2 routes (GET /settings + POST /settings/save/^<section^>)
echo    See: %PATCH_ROOT%\INTEGRATION_SNIPPETS.md Step 2
echo.
echo 2. Restart bot:
echo    python run_web.py
echo.
echo 3. Open: http://localhost:5050/settings
echo.
echo 4. Try editing settings in each tab + save
echo    Backups will appear in data\.settings_backups\
echo.
endlocal
