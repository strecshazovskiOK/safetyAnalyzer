@echo off
echo Installing Safety Report Analyzer...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Creating virtual environment...
python -m venv .venv

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Installation complete!
echo.
echo To run the Safety Analyzer:
echo 1. Double-click run.bat
echo 2. Or run: .venv\Scripts\activate.bat && python gui.py
echo.
pause
