@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 13
echo   Easy Apply Detection Fix (Multi-Strategy)
echo =====================================================
echo [INFO] Project: %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p13_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\extractors" 2>nul

if exist "%PROJECT_ROOT%\packages\extractors\linkedin.py" (
    copy /Y "%PROJECT_ROOT%\packages\extractors\linkedin.py" "%BACKUP_DIR%\packages\extractors\linkedin.py" >nul
    echo   [OK] Backed up linkedin.py
)
echo.

echo [INFO] Installing Patch 13...
copy /Y "%PATCH_ROOT%\packages\extractors\linkedin.py" "%PROJECT_ROOT%\packages\extractors\linkedin.py" >nul && echo   [OK] linkedin.py (multi-strategy Easy Apply detection)

echo.
echo =====================================================
echo   [SUCCESS] Patch 13 installed!
echo =====================================================
echo.
echo NEXT: Restart bot
echo   python run_web.py
echo.
echo MONITOR: Check log for new patterns:
echo   ✅ Easy Apply detected via: main_selector
echo   ✅ Easy Apply detected via: text_search (sofortbewerbung)
echo   ❌ Easy Apply NOT detected: all_strategies_failed
echo.
endlocal
