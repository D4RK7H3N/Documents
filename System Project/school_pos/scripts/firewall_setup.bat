@echo off
REM Firewall setup script for School POS Backend (Windows)
REM Run as Administrator

echo Setting up firewall rules for School POS...

REM Allow port 8000 for Gunicorn
netsh advfirewall firewall add rule name="School POS Backend" dir=in action=allow protocol=tcp localport=8000

REM Allow port 5432 for PostgreSQL (if using)
REM netsh advfirewall firewall add rule name="PostgreSQL" dir=in action=allow protocol=tcp localport=5432

echo Firewall rules applied successfully!
pause
