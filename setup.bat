@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo     CloudLap Remote MCP Server Setup
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Check Python installation
echo [1/4] Checking Python installation...
set PYTHON_CMD=python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    py --version >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo [ERROR] Python is not found in your PATH!
        echo Please install Python 3.10+ from https://www.python.org/
        echo Ensure 'Add Python to PATH' is checked during installation.
        pause
        exit /b 1
    )
)
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version') do echo Found %%i using '%PYTHON_CMD%'.

:: 2. Install dependencies
echo.
echo [2/4] Installing Python requirements...
%PYTHON_CMD% -m pip install --upgrade pip >nul 2>&1
%PYTHON_CMD% -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install requirements. Please check your internet connection or pip setup.
    pause
    exit /b 1
)
echo Python packages installed successfully.

:: 3. Check ngrok
echo.
echo [3/4] Checking ngrok installation...
ngrok version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing ngrok via winget...
    winget install ngrok.ngrok --accept-package-agreements --accept-source-agreements --silent >nul 2>&1
    ngrok version >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [NOTE] Please install ngrok from https://ngrok.com/download or run: winget install ngrok.ngrok
    ) else (
        echo ngrok installed successfully.
    )
) else (
    echo ngrok is installed.
)

:: 4. Config check
echo.
echo [4/4] Checking configuration...
if not exist "config.json" (
    if exist "config.example.json" (
        copy config.example.json config.json >nul
        echo Created config.json from template.
    )
)

echo.
echo ===================================================
echo Setup complete!
echo.
echo Next Steps:
echo 1. Edit config.json and set your 'ngrok_domain'
echo 2. Run 'CloudLap.exe' (GUI) or 'start.bat' (Console)
echo 3. In Claude: Settings -^> Connectors -^> Add Custom Connector
echo    Paste URL: https://[your-ngrok-domain]/mcp
echo ===================================================
echo.

set /p STARTNOW="Would you like to start CloudLap now? (Y/N): "
if /i "%STARTNOW%"=="Y" (
    start "" "%~dp0CloudLap.exe"
) else (
    pause
)
