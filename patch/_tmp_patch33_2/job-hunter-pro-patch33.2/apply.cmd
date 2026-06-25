@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 33.2
echo   Indeed Discovery Mode Critical Fixes
echo =====================================================
echo.

echo [INFO] Installing helper module...
mkdir "%PROJECT_ROOT%\packages\core" 2>nul

copy /Y "%PATCH_ROOT%\packages\core\discovery_filter_helper.py" "%PROJECT_ROOT%\packages\core\discovery_filter_helper.py" >nul && echo   [OK] discovery_filter_helper.py installed

echo.
echo =====================================================
echo   [SUCCESS] Helper installed!
echo =====================================================
echo.
echo CRITICAL NEXT STEPS:
echo.
echo Read INTEGRATION_SNIPPETS.md and apply 4 manual fixes:
echo.
echo 1. Edit apps\worker\runner.py
echo    Add "and not discovery_mode" to filter checks
echo.
echo 2. Edit packages\extractors\indeed.py
echo    Add region auto-detect logic
echo    Add throttling between searches
echo.
echo 3. Edit packages\extractors\indeed_v2_fixes.py
echo    Add more title extraction strategies
echo.
echo 4. Restart bot:
echo    python run_web.py
echo.
echo 5. Test "Scrape Indeed" at /discovered
echo    Expected: discovered=80+, skipped=0 (in discovery mode)
echo.
endlocal
