@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM Job-Hunter Pro - PATCH 8 (Phase 2b: AI Resume Tailoring + Speed)
REM ============================================================
set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."
pushd "%PROJECT_ROOT%" || (echo [ERROR] Cannot reach %PROJECT_ROOT% & exit /b 1)
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Patch 8 - AI Resume Tailoring (Phase 2b)
echo =====================================================
echo [INFO] Patch source : %PATCH_ROOT%
echo [INFO] Project root : %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p8_%TS%"
mkdir "%BACKUP_DIR%\packages\ai" 2>nul
mkdir "%BACKUP_DIR%\packages\stealth" 2>nul
mkdir "%BACKUP_DIR%\apps\worker" 2>nul

REM Backup
if exist "%PROJECT_ROOT%\apps\worker\runner.py" copy /Y "%PROJECT_ROOT%\apps\worker\runner.py" "%BACKUP_DIR%\apps\worker\" >nul
if exist "%PROJECT_ROOT%\packages\stealth\browser.py" copy /Y "%PROJECT_ROOT%\packages\stealth\browser.py" "%BACKUP_DIR%\packages\stealth\" >nul
if exist "%PROJECT_ROOT%\config.yaml" copy /Y "%PROJECT_ROOT%\config.yaml" "%BACKUP_DIR%\" >nul
echo [OK] Backup at %BACKUP_DIR%
echo.

echo [INFO] Applying...
copy /Y "%PATCH_ROOT%\packages\ai\resume_tailor.py" "%PROJECT_ROOT%\packages\ai\" >nul && echo   [OK] packages/ai/resume_tailor.py (NEW)
copy /Y "%PATCH_ROOT%\packages\stealth\browser.py" "%PROJECT_ROOT%\packages\stealth\" >nul && echo   [OK] packages/stealth/browser.py
copy /Y "%PATCH_ROOT%\apps\worker\runner.py" "%PROJECT_ROOT%\apps\worker\" >nul && echo   [OK] apps/worker/runner.py

echo.
echo [INFO] Installing reportlab (for PDF generation)...
pushd "%PROJECT_ROOT%"
call .venv\Scripts\python.exe -m pip install --quiet reportlab
popd

echo.
echo [SUCCESS] Patch 8 applied!
echo.
echo NEXT STEPS:
echo   1. Open config.yaml in notepad
echo   2. Replace the `ai:` block with content from config.snippet.yaml
echo      (key change: resume_tailoring: true)
echo   3. python run_web.py
echo   4. Click Start
echo.
echo Each apply will now generate a custom resume PDF saved to:
echo   resumes\generated\Company_Title_JobID.pdf
echo.
endlocal
