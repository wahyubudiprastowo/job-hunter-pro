@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 9.1
echo   Validator Variant Handling Fix
echo =====================================================
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p9_1_%TS%"

echo [INFO] Backing up to: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\ai" 2>nul

if exist "%PROJECT_ROOT%\packages\ai\resume_validator.py" (
    copy /Y "%PROJECT_ROOT%\packages\ai\resume_validator.py" "%BACKUP_DIR%\packages\ai\resume_validator.py" >nul
    echo   [OK] Backed up resume_validator.py
)

echo [INFO] Installing Patch 9.1...
copy /Y "%PATCH_ROOT%\packages\ai\resume_validator.py" "%PROJECT_ROOT%\packages\ai\resume_validator.py" >nul && echo   [OK] resume_validator.py (with variant handling)

echo.
echo [SUCCESS] Patch 9.1 installed!
echo.
echo Run self-test to verify:
echo   python %PATCH_ROOT%\test_validator.py
echo.
echo Expected: 7/7 tests passed
echo.
endlocal
