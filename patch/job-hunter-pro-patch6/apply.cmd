@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Job-Hunter Pro - PATCH 6 (CV-Powered AI Answers)
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
echo   Job-Hunter Pro - PATCH 6 (CV-Powered AI Answers)
echo =====================================================
echo [INFO] Patch source : %PATCH_ROOT%
echo [INFO] Project root : %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p6_%TS%"

echo [INFO] Creating backups in: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\ai" 2>nul
mkdir "%BACKUP_DIR%\packages\extractors" 2>nul
mkdir "%BACKUP_DIR%\apps\worker" 2>nul

if exist "%PROJECT_ROOT%\packages\ai\question_bot.py" (
    copy /Y "%PROJECT_ROOT%\packages\ai\question_bot.py" "%BACKUP_DIR%\packages\ai\question_bot.py" >nul
    echo   [OK] Backed up question_bot.py
)
if exist "%PROJECT_ROOT%\apps\worker\runner.py" (
    copy /Y "%PROJECT_ROOT%\apps\worker\runner.py" "%BACKUP_DIR%\apps\worker\runner.py" >nul
    echo   [OK] Backed up runner.py
)
if exist "%PROJECT_ROOT%\packages\extractors\linkedin.py" (
    copy /Y "%PROJECT_ROOT%\packages\extractors\linkedin.py" "%BACKUP_DIR%\packages\extractors\linkedin.py" >nul
    echo   [OK] Backed up linkedin.py
)
echo.

echo [INFO] Applying patches...
if not exist "%PROJECT_ROOT%\packages\ai" mkdir "%PROJECT_ROOT%\packages\ai"
copy /Y "%PATCH_ROOT%\packages\ai\cv_extractor.py" "%PROJECT_ROOT%\packages\ai\cv_extractor.py" >nul && echo   [OK] packages/ai/cv_extractor.py
copy /Y "%PATCH_ROOT%\packages\ai\question_bot.py" "%PROJECT_ROOT%\packages\ai\question_bot.py" >nul && echo   [OK] packages/ai/question_bot.py
copy /Y "%PATCH_ROOT%\apps\worker\runner.py" "%PROJECT_ROOT%\apps\worker\runner.py" >nul && echo   [OK] apps/worker/runner.py

REM Run linkedin.py inline patcher
echo.
echo [INFO] Patching linkedin.py to accept cv_text...
copy /Y "%PATCH_ROOT%\patch_linkedin.py" "%PROJECT_ROOT%\patch_linkedin.py" >nul
pushd "%PROJECT_ROOT%"
python patch_linkedin.py
del /Q patch_linkedin.py 2>nul
popd

echo.
echo [INFO] Installing pypdf...
pushd "%PROJECT_ROOT%"
call .venv\Scripts\python.exe -m pip install --quiet pypdf
popd

echo.
echo [SUCCESS] Patch 6 applied!
echo.
echo CRITICAL — Fix your .env first:
echo   Open .env in notepad and ensure AI lines look EXACTLY like this:
echo.
echo   AI_API_KEY=
echo   AI_BASE_URL=https://openwebui.tail443aaa.ts.net/api/v1/vscode/sk-3d39a725ffa5e05f-539a83-9e66c5a9
echo.
echo   ^(No leading spaces, no quotes, URL starts with https://^)
echo.
echo Next steps:
echo   1. Verify .env is correct
echo   2. Place your real CV at: resumes\base_resume.pdf
echo   3. python run_web.py
echo   4. Click "Test AI" in dashboard
echo   5. Click "Start"
echo.
endlocal
