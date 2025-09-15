@echo off
echo Starting Safety Report Analyzer...
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found. Running installer...
    call install.bat
    if errorlevel 1 exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Starting application...
python gui.py

pause
