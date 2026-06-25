@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 31.2
echo   Cloudflare Pragmatic Workaround
echo =====================================================
echo.

echo [INFO] Installing helper + prewarm script...

mkdir "%PROJECT_ROOT%\scripts" 2>nul

copy /Y "%PATCH_ROOT%\packages\extractors\cloudflare_helper.py" "%PROJECT_ROOT%\packages\extractors\cloudflare_helper.py" >nul && echo   [OK] cloudflare_helper.py
copy /Y "%PATCH_ROOT%\scripts\prewarm_indeed.py" "%PROJECT_ROOT%\scripts\prewarm_indeed.py" >nul && echo   [OK] prewarm_indeed.py

echo.
echo =====================================================
echo   [SUCCESS] Files installed!
echo =====================================================
echo.
echo CRITICAL NEXT STEPS:
echo.
echo 1. STOP bot first (Ctrl+C in run_web.py terminal)
echo.
echo 2. Run pre-warm script ONCE:
echo    python scripts\prewarm_indeed.py
echo.
echo    Browser will open. You MUST:
echo    - Complete Cloudflare verification
echo    - Sign in to Indeed
echo    - Browse 5-10 jobs (humanize behavior)
echo    - Close browser when done
echo.
echo 3. Update indeed.py:
echo    See INTEGRATION_SNIPPETS.md Step 2
echo.
echo 4. Restart bot:
echo    python run_web.py
echo.
echo 5. Bot should now SKIP Cloudflare (cookies saved)
echo.
echo Re-run prewarm monthly to maintain cookies.
echo.
endlocal
