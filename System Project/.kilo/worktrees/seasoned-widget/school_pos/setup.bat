@echo off
title School POS Backend - Auto Setup
color 0a

echo ========================================
echo   School POS Backend Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/5] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/5] Running migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Migration failed
    pause
    exit /b 1
)

echo.
echo [3/5] Collecting static files...
python manage.py collectstatic --noinput

echo.
echo [4/5] Creating superuser...
echo Press Ctrl+C to skip this step
python manage.py createsuperuser

echo.
echo [5/5] Getting IP address...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set "IP=%%a"
    set "IP=!IP: =!"
)

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Your Server IP: %IP%
echo.
echo To start server, run: start.bat
echo.
echo Clients should connect to: http://%IP%:8000
echo.
pause

REM Start the server
start.bat
