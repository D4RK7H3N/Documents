@echo off
REM ========================================
REM School POS - Quick Setup for Server
REM ========================================

echo ========================================
echo School POS - Server Setup
echo ========================================

REM Activate Virtual Environment
cd /d "%~dp0school_pos"
call venv\Scripts\activate.bat 2>nul

if errorlevel 1 (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)

REM Run Migrations
echo Running migrations...
python manage.py migrate --noinput

REM Collect Static Files
echo Collecting static files...
python manage.py collectstatic --noinput --clear 2>nul

REM Open Firewall
echo Opening firewall...
netsh advfirewall firewall add rule name="School POS Backend" dir=in action=allow protocol=tcp localport=8000 2>nul

REM Start Gunicorn
echo Starting backend...
start /b gunicorn school_pos.wsgi:application --bind 0.0.0.0:8000 --workers 5

echo.
echo ========================================
echo Backend running at:
echo   - http://localhost:8000
echo   - http://192.168.1.180:8000
echo ========================================
echo.
echo Press any key to exit...
pause >nul
