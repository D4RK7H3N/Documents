@echo off
title School POS Backend Installer
color 0a
setlocal enabledelayedexpansion

echo ========================================
echo   School POS Backend Auto-Installer
echo ========================================
echo.

echo [1/7] Installing Python dependencies...
pip install gunicorn
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo [2/7] Running migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Failed to run migrations!
    pause
    exit /b 1
)

echo.
echo [3/7] Collecting static files...
python manage.py collectstatic --noinput

echo.
echo [4/7] Creating superuser (optional)...
echo Press Ctrl+C to skip
python manage.py createsuperuser

echo.
echo [5/7] Configuring environment...
echo Please enter your server IP address (e.g., 192.168.1.100)
set /p SERVER_IP="Server IP: "

echo DB_NAME=SMSS > .env
echo DB_USER=postgres >> .env
echo DB_PASSWORD=postgres >> .env
echo DB_HOST=localhost >> .env
echo DB_PORT=5432 >> .env
echo SERVER_IP=%SERVER_IP% >> .env

echo.
echo [6/7] Creating startup script...
echo @echo off > start.bat
echo title School POS Backend>> start.bat
echo cd /d %%~dp0>> start.bat
echo gunicorn school_pos.wsgi --bind %SERVER_IP%:8000 --workers 3>> start.bat

echo.
echo [7/7] Creating Windows Service (optional)...
echo Install as Windows Service? (Y/N)
set /p INSTALL_SERVICE=">> "

if /i "%INSTALL_SERVICE%"=="Y" (
    pip install pywin32
    python -c "import win32serviceutil; win32serviceutil.HandleCommandLine('SchoolPOSBackend')"
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Starting server on http://%SERVER_IP%:8000
echo.
echo To start manually, run: start.bat
echo.
start.bat
