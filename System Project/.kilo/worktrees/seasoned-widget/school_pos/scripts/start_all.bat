@echo off
REM ========================================
REM School POS - Complete Setup Script
REM Run as Administrator
REM ========================================

echo ========================================
echo School POS - Setup & Start
echo ========================================

REM ========================================
REM Firewall Setup
REM ========================================
echo.
echo [1/4] Setting up firewall rules...
netsh advfirewall firewall add rule name="School POS Backend" dir=in action=allow protocol=tcp localport=8000 2>nul
echo Firewall: Port 8000 allowed

REM ========================================
REM Activate Virtual Environment
REM ========================================
echo.
echo [2/4] Activating virtual environment...
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM ========================================
REM Run Migrations
REM ========================================
echo.
echo [3/4] Running migrations...
python manage.py migrate --noinput
if errorlevel 1 (
    echo WARNING: Migration had issues, continuing...
)

REM ========================================
REM Collect Static Files
REM ========================================
echo.
echo [4/4] Collecting static files...
python manage.py collectstatic --noinput --clear 2>nul

REM ========================================
REM Start Gunicorn
REM ========================================
echo.
echo Starting Gunicorn on 0.0.0.0:8000...
start /b gunicorn school_pos.wsgi:application --bind 0.0.0.0:8000 --workers 5

echo.
echo ========================================
echo Setup complete!
echo Backend running at: http://localhost:8000
echo LAN Access: http://192.168.1.180:8000
echo ========================================
pause
