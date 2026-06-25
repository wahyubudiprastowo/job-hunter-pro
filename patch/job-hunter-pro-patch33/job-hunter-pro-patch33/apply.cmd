@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 33
echo   Glassdoor Extractor (Phase 4b)
echo =====================================================
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p33_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\extractors" 2>nul
mkdir "%BACKUP_DIR%\scripts" 2>nul

if exist "%PROJECT_ROOT%\packages\extractors\glassdoor.py" (
    copy /Y "%PROJECT_ROOT%\packages\extractors\glassdoor.py" "%BACKUP_DIR%\packages\extractors\glassdoor.py" >nul
    echo   [OK] Backed up existing glassdoor.py
)

if exist "%PROJECT_ROOT%\scripts\prewarm_glassdoor.py" (
    copy /Y "%PROJECT_ROOT%\scripts\prewarm_glassdoor.py" "%BACKUP_DIR%\scripts\prewarm_glassdoor.py" >nul
    echo   [OK] Backed up existing prewarm_glassdoor.py
)
echo.

echo [INFO] Installing Patch 33...
mkdir "%PROJECT_ROOT%\scripts" 2>nul

copy /Y "%PATCH_ROOT%\packages\extractors\glassdoor.py" "%PROJECT_ROOT%\packages\extractors\glassdoor.py" >nul && echo   [OK] glassdoor.py installed
copy /Y "%PATCH_ROOT%\scripts\prewarm_glassdoor.py" "%PROJECT_ROOT%\scripts\prewarm_glassdoor.py" >nul && echo   [OK] prewarm_glassdoor.py installed

echo.
echo =====================================================
echo   [SUCCESS] Glassdoor extractor installed!
echo =====================================================
echo.
echo CRITICAL NEXT STEPS:
echo.
echo 1. Read INTEGRATION_SNIPPETS.md
echo.
echo 2. Add to config.yaml:
echo    platforms:
echo      glassdoor:
echo        enabled: false (start disabled)
echo        region: "auto"
echo        login_method: "auto"
echo.
echo 3. Add to .env:
echo    GLASSDOOR_EMAIL=your-email@gmail.com
echo    GLASSDOOR_PASSWORD=your-password
echo.
echo 4. Register in apps\worker\runner.py:
echo    Add GlassdoorExtractor to EXTRACTOR_REGISTRY
echo.
echo 5. CRITICAL: Pre-warm Glassdoor profile:
echo    python scripts\prewarm_glassdoor.py
echo    (Browser opens, sign in, browse, close)
echo.
echo 6. Enable in config.yaml:
echo    glassdoor.enabled: true
echo.
echo 7. Restart bot:
echo    python run_web.py
echo.
echo 8. Test discovery or apply!
echo.
endlocal
