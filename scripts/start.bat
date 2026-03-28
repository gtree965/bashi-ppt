@echo off
chcp 65001 >nul
echo.
echo  ========================================
echo     SlideForge v0.1.0
echo     Local AI PPT Generator
echo  ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check/create venv
if not exist "%~dp0..\venv" (
    echo [SETUP] First run: creating virtual environment...
    python -m venv "%~dp0..\venv"
    call "%~dp0..\venv\Scripts\activate"
    echo [SETUP] Installing Python dependencies...
    pip install -r "%~dp0..\backend\requirements.txt"
) else (
    call "%~dp0..\venv\Scripts\activate"
)

REM Build frontend if needed
if not exist "%~dp0..\frontend\dist\index.html" (
    echo [BUILD] Building frontend...
    cd /d "%~dp0..\frontend"
    call npm install
    call npm run build
    cd /d "%~dp0"
)

REM Check LM Studio
echo [CHECK] Checking LM Studio connection...
curl -s http://localhost:1234/v1/models >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] LM Studio not detected. Start LM Studio and load a model first.
    echo [INFO] The app will still start - press any key to continue...
    pause >nul
)

REM Start Flask
echo [START] Starting SlideForge server...
echo [URL] Open browser: http://localhost:5000
echo.
cd /d "%~dp0..\backend"
python app.py
