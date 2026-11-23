@echo off
title School POS Backend
cd /d %~dp0

echo Starting School POS Backend...
echo.

gunicorn school_pos.wsgi --bind 0.0.0.0:8000 --workers 3 --reload

pause
