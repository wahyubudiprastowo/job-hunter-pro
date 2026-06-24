@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || (
    echo [ERROR] Cannot reach project root
    exit /b 1
)
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - Docs Bundle v3.1
echo   (incremental update — adds Patches 14 + 15 + checklist)
echo =====================================================
echo [INFO] Target: %PROJECT_ROOT%\docs\
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"

if exist "%PROJECT_ROOT%\docs" (
    set "BACKUP_DIR=%PROJECT_ROOT%\docs.bak_v31_%TS%"
    echo [INFO] Backing up existing docs/ to: !BACKUP_DIR!
    xcopy /Y /Q /E /I "%PROJECT_ROOT%\docs" "!BACKUP_DIR!" >nul
    echo   [OK] Backup created
)

echo [INFO] Installing v3.1 updates...
xcopy /Y /Q /E /I "%PATCH_ROOT%\docs\*.*" "%PROJECT_ROOT%\docs\" >nul

echo.
echo [SUCCESS] v3.1 docs installed!
echo.
echo Updated/new files:
echo   - 00_MASTER_CONTINUITY.md (v3.1)
echo   - CURRENT_STATE_SNAPSHOT.md (post Patch 15)
echo   - PATCH_HISTORY_LEDGER.md (P14+P15 added)
echo   - 17_CHANGELOG.md (P14+P15 details)
echo   - FEATURE_CHECKLIST.md (NEW - comprehensive)
echo   - NEXT_STEPS_ROADMAP.md (NEW - prioritized)
echo.
echo See docs/00_MASTER_CONTINUITY.md for entry point.
endlocal
