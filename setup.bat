@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo     CloudLap setup
echo ===================================================
echo.

set PYTHON_CMD=python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    py --version >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo [ERROR] Python was not found.
        echo Install Python 3.10 or newer from https://www.python.org/downloads/
        echo and tick "Add Python to PATH", then double-click setup.bat again.
        pause
        exit /b 1
    )
)

%PYTHON_CMD% setup_wizard.py
if %ERRORLEVEL% neq 0 pause
