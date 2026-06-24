@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Job-Hunter Pro PATCH 10 — Phase 2c Cover Letter Generator
REM ============================================================

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
echo   Job-Hunter Pro - PATCH 10
echo   Phase 2c: Cover Letter Generator
echo =====================================================
echo [INFO] Patch source : %PATCH_ROOT%
echo [INFO] Project root : %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p10_%TS%"

echo [INFO] Backups → %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\ai" 2>nul

REM No file overwrites (all NEW files), just install:
echo [INFO] Installing Patch 10 files...
copy /Y "%PATCH_ROOT%\packages\ai\cover_letter.py" "%PROJECT_ROOT%\packages\ai\cover_letter.py" >nul && echo   [OK] NEW: packages/ai/cover_letter.py
copy /Y "%PATCH_ROOT%\packages\ai\cover_letter_validator.py" "%PROJECT_ROOT%\packages\ai\cover_letter_validator.py" >nul && echo   [OK] NEW: packages/ai/cover_letter_validator.py

if not exist "%PROJECT_ROOT%\cover_letters\generated" mkdir "%PROJECT_ROOT%\cover_letters\generated" 2>nul
echo   [OK] Created cover_letters/generated/

echo.
echo =====================================================
echo   [SUCCESS] Files installed!
echo =====================================================
echo.
echo IMPORTANT — 2 manual steps:
echo.
echo   1. EDIT apps\worker\runner.py — see:
echo      %PATCH_ROOT%\RUNNER_EDIT_INSTRUCTIONS.txt
echo      (6 edits, mostly additive)
echo.
echo   2. EDIT config.yaml — add to ai: section:
echo      cover_letter: true
echo      cover_letter_strict: true
echo      cover_letter_output_dir: "cover_letters/generated"
echo.
echo OPTIONAL — verify validator works:
echo   python %PATCH_ROOT%\test_cover_letter.py
echo.
echo Then restart bot: python run_web.py
echo.
echo NOTE: Cover letters are generated + saved to disk but NOT yet
echo uploaded to LinkedIn forms. That comes in Patch 10b (extractor).
echo.
endlocal
