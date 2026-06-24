@echo off
setlocal enabledelayedexpansion

set "PATCH_ROOT=%~dp0"
set "PATCH_ROOT=%PATCH_ROOT:~0,-1%"
set "PROJECT_ROOT=%PATCH_ROOT%\..\.."

pushd "%PROJECT_ROOT%" || exit /b 1
set "PROJECT_ROOT=%CD%"
popd

echo =====================================================
echo   Job-Hunter Pro - PATCH 28
echo   Phase 3d Telegram Notifications
echo =====================================================
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p28_%TS%"

echo [INFO] Backups: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\notifications" 2>nul

if exist "%PROJECT_ROOT%\packages\notifications" (
    xcopy /Y /Q /E "%PROJECT_ROOT%\packages\notifications" "%BACKUP_DIR%\packages\notifications\" >nul
    echo   [OK] Backed up existing notifications package
)
echo.

echo [INFO] Installing Patch 28...
mkdir "%PROJECT_ROOT%\packages\notifications" 2>nul

copy /Y "%PATCH_ROOT%\packages\notifications\base.py" "%PROJECT_ROOT%\packages\notifications\base.py" >nul && echo   [OK] base.py
copy /Y "%PATCH_ROOT%\packages\notifications\telegram.py" "%PROJECT_ROOT%\packages\notifications\telegram.py" >nul && echo   [OK] telegram.py
copy /Y "%PATCH_ROOT%\packages\notifications\manager.py" "%PROJECT_ROOT%\packages\notifications\manager.py" >nul && echo   [OK] manager.py
copy /Y "%PATCH_ROOT%\packages\notifications\__init__.py" "%PROJECT_ROOT%\packages\notifications\__init__.py" >nul && echo   [OK] __init__.py

echo.
echo =====================================================
echo   [SUCCESS] Notifications package installed!
echo =====================================================
echo.
echo NEXT STEPS:
echo.
echo 1. Setup Telegram bot (5 min):
echo    - Talk to @BotFather on Telegram
echo    - /newbot, get TOKEN
echo    - Start chat with your bot, send /start
echo    - Open: https://api.telegram.org/bot^<TOKEN^>/getUpdates
echo    - Find chat.id
echo.
echo 2. Add credentials to .env:
echo    TELEGRAM_BOT_TOKEN=your-token
echo    TELEGRAM_CHAT_ID=your-chat-id
echo.
echo 3. Add config to config.yaml:
echo    notifications:
echo      enabled: true
echo      channels:
echo        telegram:
echo          enabled: true
echo.
echo 4. Update runner.py with notify() calls
echo    See: %PATCH_ROOT%\INTEGRATION_SNIPPETS.md Step 5
echo.
echo 5. Test manually then run bot
echo.
endlocal
