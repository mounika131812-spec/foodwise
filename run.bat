@echo off
REM Smart Food Waste Management Platform - Launcher
cd /d "%~dp0"

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import flask, jwt, bcrypt" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting server on http://localhost:3000
echo Press Ctrl+C to stop.
echo.
start "" http://localhost:3000
python app.py
pause