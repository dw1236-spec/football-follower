@echo off
REM One-click launcher for Windows: creates a virtual environment (first run
REM only), installs dependencies, and starts the app. Just double-click this
REM file, or run it from a terminal with: run_windows.bat
setlocal
cd /d %~dp0

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies (first run only, this may take a minute)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo.
echo Launching NFL Fantasy Draft Analyzer...
python main.py

echo.
pause
