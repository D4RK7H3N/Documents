@echo off
REM Migration and Start script for School POS Backend
REM Run this as Administrator or with proper permissions

echo ========================================
echo School POS - Migration & Start Script
echo ========================================

REM Set working directory
cd /d "%~dp0.."

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run migrations
echo Running migrations...
python manage.py migrate --noinput

REM Collect static files
echo Collecting static files...
python manage.py collectstatic --noinput --clear

REM Start Gunicorn on all interfaces
echo Starting Gunicorn on 0.0.0.0:8000...
start /b gunicorn school_pos.wsgi:application --bind 0.0.0.0:8000 --workers 5

echo ========================================
echo Backend started!
echo Access at: http://localhost:8000
echo ========================================
pause
