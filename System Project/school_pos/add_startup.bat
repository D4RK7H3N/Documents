@echo off
title Add to Windows Startup
echo.
echo This will add School POS to Windows startup...
echo.

REM Get startup folder path
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

REM Create shortcut
echo Set WshShell = CreateObject("WScript.Shell") > "%TEMP%\create_shortcut.vbs"
echo Set shortcut = WshShell.CreateShortcut("%STARTUP_FOLDER%\School POS Backend.lnk") >> "%TEMP%\create_shortcut.vbs"
echo shortcut.TargetPath = "%CD%\start.bat" >> "%TEMP%\create_shortcut.vbs"
echo shortcut.WorkingDirectory = "%CD%" >> "%TEMP%\create_shortcut.vbs"
echo shortcut.Description = "School POS Backend Server" >> "%TEMP%\create_shortcut.vbs"
echo shortcut.Save >> "%TEMP%\create_shortcut.vbs"

cscript //nologo "%TEMP%\create_shortcut.vbs"
del "%TEMP%\create_shortcut.vbs"

echo Done!
echo School POS will now start automatically on Windows boot.
echo.
pause
