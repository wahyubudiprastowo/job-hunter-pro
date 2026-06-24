@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Job-Hunter Pro - PATCH 7 (CV multi-format + OCR fallback)
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
echo   Job-Hunter Pro - PATCH 7 (CV Multi-format + OCR)
echo =====================================================
echo [INFO] Patch source : %PATCH_ROOT%
echo [INFO] Project root : %PROJECT_ROOT%
echo.

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%PROJECT_ROOT%\.backup_p7_%TS%"

echo [INFO] Creating backups in: %BACKUP_DIR%
mkdir "%BACKUP_DIR%\packages\ai" 2>nul

if exist "%PROJECT_ROOT%\packages\ai\cv_extractor.py" (
    copy /Y "%PROJECT_ROOT%\packages\ai\cv_extractor.py" "%BACKUP_DIR%\packages\ai\cv_extractor.py" >nul
    echo   [OK] Backed up cv_extractor.py
)
echo.

echo [INFO] Applying patches...
copy /Y "%PATCH_ROOT%\packages\ai\cv_extractor.py" "%PROJECT_ROOT%\packages\ai\cv_extractor.py" >nul && echo   [OK] packages/ai/cv_extractor.py
copy /Y "%PATCH_ROOT%\convert_cv_to_text.py" "%PROJECT_ROOT%\convert_cv_to_text.py" >nul && echo   [OK] convert_cv_to_text.py (helper)

echo.
echo [SUCCESS] Patch 7 applied!
echo.
echo Next steps - PICK ONE:
echo.
echo OPTION A (RECOMMENDED - 1 minute):
echo   1. Open your CV in Word/Google Docs
echo   2. Save As / Export → PDF (text-based, NOT image)
echo   3. Replace: resumes\base_resume.pdf
echo   4. Restart bot
echo.
echo OPTION B (OCR - if you only have scan PDF):
echo   pip install pdf2image pytesseract Pillow
echo   Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
echo   python convert_cv_to_text.py
echo.
echo OPTION C (FASTEST - manual text):
echo   1. Open base_resume.txt.SAMPLE in this folder
echo   2. Edit with your real CV content
echo   3. Save as: resumes\base_resume.txt
echo   Bot will use TXT automatically when PDF fails.
echo.
endlocal
