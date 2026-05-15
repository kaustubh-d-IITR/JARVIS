@echo off
title JARVIS AI Assistant
echo.
echo ================================================
echo   JARVIS — Launching...
echo ================================================
echo.

:: Activate venv if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Run startup check
echo [1/2] Running pre-flight checks...
python startup_check.py
if errorlevel 1 (
    echo.
    echo [ERROR] Startup checks failed. Fix errors above first.
    echo         Run setup_local.bat to install dependencies.
    pause
    exit /b 1
)

:: Launch Streamlit
echo.
echo [2/2] Starting JARVIS...
echo.
echo   Opening browser at http://127.0.0.1:8501
echo   Press Ctrl+C to stop.
echo.
start http://127.0.0.1:8501
streamlit run app.py --server.port 8501 --server.headless true
