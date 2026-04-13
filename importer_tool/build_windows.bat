@echo off
setlocal
cd /d "%~dp0"

python -m pip install --upgrade pip
if errorlevel 1 goto :fail

python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

python build_windows.py
if errorlevel 1 goto :fail

exit /b 0

:fail
echo.
echo Build failed.
exit /b 1
