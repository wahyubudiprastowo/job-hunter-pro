@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 21
echo   UI Modernization (Sidebar + KPI + ApexCharts)
echo =====================================================
echo [INFO] Project: %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\apps\web\templates.bak_v21_%TS%"

echo [INFO] Backing up existing templates to: %BACKUP_DIR%
mkdir "%BACKUP_DIR%" 2>nul

if exist "%PROJECT_ROOT%\apps\web\templates\*.html" (
    copy /Y "%PROJECT_ROOT%\apps\web\templates\*.html" "%BACKUP_DIR%\" >nul
    echo   [OK] Templates backed up
)

echo [INFO] Installing Patch 21 files...

REM Ensure static folder exists
mkdir "%PROJECT_ROOT%\apps\web\static" 2>nul

REM Copy CSS
copy /Y "%PATCH_ROOT%\apps\web\static\styles.css" "%PROJECT_ROOT%\apps\web\static\styles.css" >nul && echo   [OK] styles.css

REM Copy all template files
copy /Y "%PATCH_ROOT%\apps\web\templates\base.html" "%PROJECT_ROOT%\apps\web\templates\base.html" >nul && echo   [OK] base.html (sidebar layout)
copy /Y "%PATCH_ROOT%\apps\web\templates\dashboard.html" "%PROJECT_ROOT%\apps\web\templates\dashboard.html" >nul && echo   [OK] dashboard.html (KPI + charts)
copy /Y "%PATCH_ROOT%\apps\web\templates\applications.html" "%PROJECT_ROOT%\apps\web\templates\applications.html" >nul && echo   [OK] applications.html (modern table)
copy /Y "%PATCH_ROOT%\apps\web\templates\application_detail.html" "%PROJECT_ROOT%\apps\web\templates\application_detail.html" >nul && echo   [OK] application_detail.html (fit score visual)
copy /Y "%PATCH_ROOT%\apps\web\templates\questions.html" "%PROJECT_ROOT%\apps\web\templates\questions.html" >nul && echo   [OK] questions.html (inline forms)

echo.
echo =====================================================
echo   [SUCCESS] Patch 21 installed!
echo =====================================================
echo.
echo IMPORTANT - Manual step required:
echo.
echo   Update apps\web\app.py with snippets from:
echo   %PATCH_ROOT%\INTEGRATION_SNIPPETS.md (Step 3)
echo   
echo   Without these snippets:
echo   - KPI cards (Applied Today, etc.) will show 0
echo   - Charts will be empty
echo   - Avg Fit Score won't display
echo   - Rate Limit banner won't show (needs Patch 19)
echo.
echo Restart bot:
echo   python run_web.py
echo.
echo Open dashboard:
echo   http://localhost:5050
echo.
echo Rollback if needed:
echo   Copy *.html from %BACKUP_DIR% back to apps\web\templates\
echo.
endlocal
