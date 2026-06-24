@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Job-Hunter Pro - PATCH 5
REM - Zombie state detection + auto-recovery
REM - Reset State button in dashboard
REM - AI Test button + URL-embedded token support
REM - Heartbeat-based health monitoring
REM ============================================================

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || (
    echo [ERROR] Cannot reach project root: %PROJECT_ROOT%
    exit /b 1
)
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 5 Auto-Apply
echo =====================================================
echo [INFO] Patch source : %PATCH_ROOT%
echo [INFO] Project root : %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p5_%TS%"

echo [INFO] Creating backups in: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\ai" 2>nul
mkdir "%BACKUP_DIR%\apps\worker" 2>nul
mkdir "%BACKUP_DIR%\apps\web\templates" 2>nul

if exist "%PROJECT_ROOT%\packages\ai\provider.py" (
    copy /Y "%PROJECT_ROOT%\packages\ai\provider.py" "%BACKUP_DIR%\packages\ai\provider.py" >nul
    echo   [OK] Backed up provider.py
)
if exist "%PROJECT_ROOT%\apps\worker\control.py" (
    copy /Y "%PROJECT_ROOT%\apps\worker\control.py" "%BACKUP_DIR%\apps\worker\control.py" >nul
    echo   [OK] Backed up control.py
)
if exist "%PROJECT_ROOT%\apps\worker\runner.py" (
    copy /Y "%PROJECT_ROOT%\apps\worker\runner.py" "%BACKUP_DIR%\apps\worker\runner.py" >nul
    echo   [OK] Backed up runner.py
)
if exist "%PROJECT_ROOT%\apps\web\app.py" (
    copy /Y "%PROJECT_ROOT%\apps\web\app.py" "%BACKUP_DIR%\apps\web\app.py" >nul
    echo   [OK] Backed up app.py
)
if exist "%PROJECT_ROOT%\apps\web\templates\dashboard.html" (
    copy /Y "%PROJECT_ROOT%\apps\web\templates\dashboard.html" "%BACKUP_DIR%\apps\web\templates\dashboard.html" >nul
    echo   [OK] Backed up dashboard.html
)
echo.

REM Clear stale state files before applying
if exist "%PROJECT_ROOT%\data\.control" (
    del /Q "%PROJECT_ROOT%\data\.control\*.txt" 2>nul
    echo [INFO] Cleared stale state files in data\.control\
)
echo.

echo [INFO] Applying patches...
copy /Y "%PATCH_ROOT%\packages\ai\provider.py" "%PROJECT_ROOT%\packages\ai\provider.py" >nul && echo   [OK] packages/ai/provider.py
copy /Y "%PATCH_ROOT%\apps\worker\control.py" "%PROJECT_ROOT%\apps\worker\control.py" >nul && echo   [OK] apps/worker/control.py
copy /Y "%PATCH_ROOT%\apps\worker\runner.py" "%PROJECT_ROOT%\apps\worker\runner.py" >nul && echo   [OK] apps/worker/runner.py
copy /Y "%PATCH_ROOT%\apps\web\app.py" "%PROJECT_ROOT%\apps\web\app.py" >nul && echo   [OK] apps/web/app.py
copy /Y "%PATCH_ROOT%\apps\web\templates\dashboard.html" "%PROJECT_ROOT%\apps\web\templates\dashboard.html" >nul && echo   [OK] apps/web/templates/dashboard.html

echo.
echo [SUCCESS] Patch 5 applied!
echo.
echo IMPORTANT next steps:
echo   1. Open .env and SET your AI URL:
echo      AI_API_KEY=
echo      AI_BASE_URL=https://openwebui.tail443aaa.ts.net/api/v1/vscode/sk-3d39a725ffa5e05f-539a83-9e66c5a9
echo   2. (or copy from env.append.txt in this folder)
echo   3. Open config.yaml and replace ai: block (see config.snippet.yaml)
echo   4. Restart: python run_web.py
echo   5. Click "Test AI" button in dashboard to validate
echo   6. Click "Start" to run bot
echo.
echo NEW dashboard buttons:
echo   - Reset State : force-clear stuck state files
echo   - Test AI     : validate AI endpoint without running bot
echo   - Diagnostics : expand to see heartbeat + zombie status
echo.
endlocal
