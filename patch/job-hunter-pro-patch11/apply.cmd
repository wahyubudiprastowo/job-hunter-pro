@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 11
echo   Comprehensive Fix (6 bugs)
echo =====================================================
echo [INFO] Project: %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p11_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\ai" 2>nul

if exist "%PROJECT_ROOT%\packages\ai\provider.py" (
    copy /Y "%PROJECT_ROOT%\packages\ai\provider.py" "%BACKUP_DIR%\packages\ai\provider.py" >nul
    echo   [OK] Backed up provider.py
)
if exist "%PROJECT_ROOT%\packages\ai\resume_validator.py" (
    copy /Y "%PROJECT_ROOT%\packages\ai\resume_validator.py" "%BACKUP_DIR%\packages\ai\resume_validator.py" >nul
    echo   [OK] Backed up resume_validator.py
)
if exist "%PROJECT_ROOT%\config.yaml" (
    copy /Y "%PROJECT_ROOT%\config.yaml" "%BACKUP_DIR%\config.yaml" >nul
    echo   [OK] Backed up config.yaml
)
echo.

echo [INFO] Installing Patch 11...
copy /Y "%PATCH_ROOT%\packages\ai\provider.py" "%PROJECT_ROOT%\packages\ai\provider.py" >nul && echo   [OK] provider.py (log fix + better masking)
copy /Y "%PATCH_ROOT%\packages\ai\resume_validator.py" "%PROJECT_ROOT%\packages\ai\resume_validator.py" >nul && echo   [OK] resume_validator.py (COMMON_KNOWLEDGE_TERMS)
copy /Y "%PATCH_ROOT%\config.yaml" "%PROJECT_ROOT%\config.yaml" >nul && echo   [OK] config.yaml (improved queries/keywords)

echo.
echo =====================================================
echo   [SUCCESS] Files installed!
echo =====================================================
echo.
echo CRITICAL POST-INSTALL STEPS:
echo.
echo   1. UPDATE CV: Read CV_EXTRACTION_GUIDE.md
echo      Your CV is only 1161 chars — must be 3000-6000
echo      Edit: resumes\base_resume.txt
echo.
echo   2. MERGE answer bank additions:
echo      python -c "import json; ..."  (see PATCH_NOTES.md Step 2)
echo.
echo   3. Verify .env has new AI_API_KEY (after security rotation)
echo.
echo   4. Restart bot: python run_web.py
echo.
endlocal
