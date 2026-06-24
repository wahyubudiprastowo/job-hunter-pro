@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Job-Hunter Pro PATCH 9 — Anti-Hallucination Validator
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
echo   Job-Hunter Pro - PATCH 9
echo   Anti-Hallucination Validator for Resume Tailoring
echo =====================================================
echo [INFO] Patch source : %PATCH_ROOT%
echo [INFO] Project root : %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p9_%TS%"

echo [INFO] Creating backups in: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\ai" 2>nul

if exist "%PROJECT_ROOT%\packages\ai\resume_tailor.py" (
    copy /Y "%PROJECT_ROOT%\packages\ai\resume_tailor.py" "%BACKUP_DIR%\packages\ai\resume_tailor.py" >nul
    echo   [OK] Backed up: resume_tailor.py
)
echo.

echo [INFO] Installing Patch 9 files...
copy /Y "%PATCH_ROOT%\packages\ai\resume_validator.py" "%PROJECT_ROOT%\packages\ai\resume_validator.py" >nul && echo   [OK] NEW: packages/ai/resume_validator.py
copy /Y "%PATCH_ROOT%\packages\ai\resume_tailor.py"    "%PROJECT_ROOT%\packages\ai\resume_tailor.py"    >nul && echo   [OK] REPLACED: packages/ai/resume_tailor.py

echo.
echo =====================================================
echo   [SUCCESS] Files installed!
echo =====================================================
echo.
echo IMPORTANT — 2 manual steps required:
echo.
echo   1. EDIT apps\worker\runner.py — see:
echo      %PATCH_ROOT%\RUNNER_EDIT_INSTRUCTIONS.txt
echo.
echo   2. EDIT config.yaml — add to ai: section:
echo      validator_strict: true
echo.
echo OPTIONAL — run self-test to verify:
echo      python %PATCH_ROOT%\test_validator.py
echo.
echo Then restart bot: python run_web.py
echo.
endlocal
