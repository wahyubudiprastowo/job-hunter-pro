@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Job-Hunter Pro - PATCH 3 (AI Question Fallback)
REM Always runs from .\patch\job-hunter-pro-patch3
REM Target: parent project folder (two levels up)
REM ============================================================

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

REM Resolve absolute path
pushd "%PROJECT_ROOT%" || (
    echo [ERROR] Cannot reach project root: %PROJECT_ROOT%
    exit /b 1
)
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 3 Auto-Apply
echo =====================================================
echo [INFO] Patch source : %PATCH_ROOT%
echo [INFO] Project root : %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p3_%TS%"

echo [INFO] Creating backups in: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\extractors" 2>nul
mkdir "%BACKUP_DIR%\packages\ai" 2>nul
mkdir "%BACKUP_DIR%\apps\worker" 2>nul
mkdir "%BACKUP_DIR%" 2>nul

REM Backup existing files (skip if not present)
if exist "%PROJECT_ROOT%\packages\extractors\linkedin.py" (
    copy /Y "%PROJECT_ROOT%\packages\extractors\linkedin.py" "%BACKUP_DIR%\packages\extractors\linkedin.py" >nul
    echo   [OK] Backed up linkedin.py
)
if exist "%PROJECT_ROOT%\apps\worker\runner.py" (
    copy /Y "%PROJECT_ROOT%\apps\worker\runner.py" "%BACKUP_DIR%\apps\worker\runner.py" >nul
    echo   [OK] Backed up runner.py
)
if exist "%PROJECT_ROOT%\config.yaml" (
    copy /Y "%PROJECT_ROOT%\config.yaml" "%BACKUP_DIR%\config.yaml" >nul
    echo   [OK] Backed up config.yaml
)
echo.

REM Apply patches
echo [INFO] Applying patches...

if not exist "%PROJECT_ROOT%\packages\ai" mkdir "%PROJECT_ROOT%\packages\ai"

copy /Y "%PATCH_ROOT%\packages\ai\__init__.py"      "%PROJECT_ROOT%\packages\ai\__init__.py"      >nul && echo   [OK] packages/ai/__init__.py
copy /Y "%PATCH_ROOT%\packages\ai\provider.py"      "%PROJECT_ROOT%\packages\ai\provider.py"      >nul && echo   [OK] packages/ai/provider.py
copy /Y "%PATCH_ROOT%\packages\ai\question_bot.py"  "%PROJECT_ROOT%\packages\ai\question_bot.py"  >nul && echo   [OK] packages/ai/question_bot.py
copy /Y "%PATCH_ROOT%\packages\extractors\linkedin.py" "%PROJECT_ROOT%\packages\extractors\linkedin.py" >nul && echo   [OK] packages/extractors/linkedin.py
copy /Y "%PATCH_ROOT%\apps\worker\runner.py"        "%PROJECT_ROOT%\apps\worker\runner.py"        >nul && echo   [OK] apps/worker/runner.py
copy /Y "%PATCH_ROOT%\config.yaml"                    "%PROJECT_ROOT%\config.yaml"                    >nul && echo   [OK] config.yaml

echo.
echo [SUCCESS] Patch 3 applied!
echo.
echo Next steps:
echo   1. cd %PROJECT_ROOT%
echo   2. Edit .env: add AI_API_KEY=sk-your-key
echo   3. (Optional) edit config.yaml ai.system_prompt to customize
echo   4. .\.venv\Scripts\Activate.ps1
echo   5. pip install --upgrade openai
echo   6. python run_web.py
echo   7. Open http://localhost:5050 and click Start
echo.
endlocal
