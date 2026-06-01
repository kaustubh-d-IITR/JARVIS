@echo off
title JARVIS — Local Setup
echo.
echo ================================================
echo   JARVIS — Automated Local Setup (Windows)
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo       Virtual environment created.
) else (
    echo       Virtual environment already exists.
)

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/5] Installing dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

echo [4/5] Verifying key files...
if not exist "vision\gemini_vision.py" (
    echo.
    echo [ERROR] vision\gemini_vision.py NOT FOUND!
    echo         Core vision component is missing.
    echo.
)
if not exist ".env" (
    echo.
    echo [WARNING] .env file NOT FOUND!
    echo          Create .env with your API keys.
    echo.
)

echo [5/5] Running startup validation...
python startup_check.py

echo.
echo ================================================
echo   Setup complete. Run: run_jarvis.bat
echo ================================================
pause
