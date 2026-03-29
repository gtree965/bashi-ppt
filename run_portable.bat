@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

REM =========================================================
REM SlideForge v0.1.0 - Windows Portable Launcher
REM Uses embedded Python — no system Python or npm required.
REM =========================================================

cd /d "%~dp0"

set "LOGFILE=%~dp0launch_log.txt"
echo [%date% %time%] Launcher started > "%LOGFILE%"
echo Working directory: %CD% >> "%LOGFILE%"

set "EMBED_DIR=python-3.12.10-embed-amd64"
set "PYTHON_EXE=%EMBED_DIR%\python.exe"

echo.
echo  ========================================
echo   SlideForge v0.1.0 (Windows Portable)
echo   Local AI PPT Generator
echo  ========================================
echo.

REM 1. Check embedded Python
echo [CHECK] Looking for: %PYTHON_EXE% >> "%LOGFILE%"
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Portable Python environment not found!
    echo         Embedded Python not found at %EMBED_DIR%\
    echo Please make sure the folder "%EMBED_DIR%" is in the same directory as this script.
    echo [ERROR] Python not found at %PYTHON_EXE% >> "%LOGFILE%"
    pause
    exit /b 1
)
echo [OK] Python found >> "%LOGFILE%"

REM 2. Ensure import site is enabled in ._pth (required for pip packages)
powershell -NoProfile -Command "$pth='%EMBED_DIR%\python312._pth'; if (Test-Path $pth) { $text=(Get-Content $pth) -replace '^#import site', 'import site'; Set-Content $pth -Value $text }"

REM 3. Bootstrap pip if not working
"%PYTHON_EXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [SETUP] First-time setup: downloading pip...
    echo.
    powershell -NoProfile -Command "$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing -ErrorAction Stop"
    if errorlevel 1 (
        echo [ERROR] Failed to download get-pip.py. Please check your internet connection.
        echo [ERROR] get-pip download failed >> "%LOGFILE%"
        pause
        exit /b 1
    )

    "%PYTHON_EXE%" get-pip.py --no-warn-script-location
    if errorlevel 1 (
        echo [ERROR] Failed to install pip.
        echo [ERROR] pip install failed >> "%LOGFILE%"
        pause
        exit /b 1
    )
    del get-pip.py 2>nul
)

REM 4. Install dependencies
echo [SETUP] Checking dependencies...
echo [STEP] Installing dependencies... >> "%LOGFILE%"
"%PYTHON_EXE%" -m pip install -r backend\requirements.txt --no-warn-script-location -q 2>> "%LOGFILE%"
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies from requirements.txt.
    echo         Please check your internet connection.
    echo [ERROR] pip install failed >> "%LOGFILE%"
    pause
    exit /b 1
)
echo [OK] Dependencies ready >> "%LOGFILE%"

echo [SETUP] Checking OpenCC...
"%PYTHON_EXE%" "%~dp0scripts\ensure_opencc.py" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to install OpenCC dependency.
    echo [ERROR] OpenCC setup failed >> "%LOGFILE%"
    pause
    exit /b 1
)

REM 5. Check frontend dist
if not exist "%~dp0frontend\dist\index.html" (
    echo [ERROR] Frontend build not found. Expected frontend\dist\index.html
    echo [ERROR] dist missing >> "%LOGFILE%"
    pause
    exit /b 1
)

REM 6. Check LM Studio (optional — Hymn Studio works without it)
echo [CHECK] Checking LM Studio connection...
curl -s http://localhost:1234/v1/models >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] LM Studio not detected.
    echo [INFO] Presentation mode requires LM Studio with a loaded model.
    echo [INFO] Hymn Studio works without LM Studio.
    echo [INFO] Press any key to continue...
    pause >nul
)

REM 7. Start Flask
echo.
echo [START] Starting SlideForge server...
echo [URL]   Open browser: http://localhost:5100
echo.
echo Press Ctrl+C to stop the server.
echo.

echo [STEP] Starting app.py >> "%LOGFILE%"
set "BACKEND_DIR=%~dp0backend"
"%PYTHON_EXE%" -c "import runpy, sys; sys.path.insert(0, r'%BACKEND_DIR%'); runpy.run_path(r'%BACKEND_DIR%\app.py', run_name='__main__')" 2>> "%LOGFILE%"
set "EXIT_CODE=!ERRORLEVEL!"
echo [DONE] app.py exited with code !EXIT_CODE! >> "%LOGFILE%"

echo.
echo App exited. (Exit code: !EXIT_CODE!)
echo If the app crashed, check launch_log.txt for details.
pause
