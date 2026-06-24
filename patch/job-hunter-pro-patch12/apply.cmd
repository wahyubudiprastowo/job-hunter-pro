@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 12
echo   Stability + Validator Tuning
echo =====================================================
echo [INFO] Project: %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p12_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\ai" 2>nul

if exist "%PROJECT_ROOT%\packages\ai\resume_validator.py" (
    copy /Y "%PROJECT_ROOT%\packages\ai\resume_validator.py" "%BACKUP_DIR%\packages\ai\resume_validator.py" >nul
    echo   [OK] Backed up resume_validator.py
)
echo.

echo [INFO] Installing Patch 12...
copy /Y "%PATCH_ROOT%\packages\ai\resume_validator.py" "%PROJECT_ROOT%\packages\ai\resume_validator.py" >nul && echo   [OK] resume_validator.py (expanded COMMON_KNOWLEDGE_TERMS)

echo.
echo =====================================================
echo   [SUCCESS] resume_validator.py installed!
echo =====================================================
echo.
echo NEXT STEPS:
echo.
echo   1. RUN CV DIAGNOSTIC:
echo      python patch\job-hunter-pro-patch12\cv_diagnostic.py
echo.
echo   2. UPDATE CV (Critical): resumes\base_resume.txt
echo      Should be 3000-6000 chars with all your real tech listed
echo.
echo   3. APPLY runner.py edits manually:
echo      See: %PATCH_ROOT%\RUNNER_PATCH_SNIPPET.txt
echo      (Stale element retry + better cleanup + final summary)
echo.
echo   4. APPLY timezone fix:
echo      See: %PATCH_ROOT%\TEMPLATE_TIMEZONE_FIX.txt
echo      (Choose Option A JS or Option B Python)
echo.
echo   5. Restart bot: python run_web.py
echo.
endlocal
