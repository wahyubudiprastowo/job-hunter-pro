@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Job-Hunter Pro Docs Bundle v2 ULTIMATE
REM Installs comprehensive documentation into project's docs/ folder
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
echo   Job-Hunter Pro - Docs Bundle v2 ULTIMATE
echo =====================================================
echo [INFO] Source : %PATCH_ROOT%
echo [INFO] Target : %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"

if exist "%PROJECT_ROOT%\docs" (
    set "BACKUP_DIR=%PROJECT_ROOT%\docs.bak_v2_%TS%"
    echo [INFO] Backing up existing docs/ to: !BACKUP_DIR!
    move "%PROJECT_ROOT%\docs" "!BACKUP_DIR!" >nul
    echo   [OK] Backup created
)

echo [INFO] Installing v2 ULTIMATE documentation...
mkdir "%PROJECT_ROOT%\docs" 2>nul
mkdir "%PROJECT_ROOT%\docs\PRDs" 2>nul
xcopy /Y /Q /E "%PATCH_ROOT%\docs\*.*" "%PROJECT_ROOT%\docs\" >nul

echo.
echo [SUCCESS] Documentation installed!
echo.
echo Total docs: 21 (Tier 0-4) + 17 PRDs + Template
echo Index: %PROJECT_ROOT%\docs\00_INDEX.md
echo Master: %PROJECT_ROOT%\docs\00_MASTER_CONTINUITY.md
echo.
echo Next: Read docs\00_MASTER_CONTINUITY.md
echo.
endlocal
