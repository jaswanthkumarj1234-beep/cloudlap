@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo     Claude Laptop Remote MCP Server Setup
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
        echo Please install Python 3.10+ from https://www.python.org/ or Microsoft Store.
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

:: 3. Download cloudflared if not present
echo.
echo [3/4] Checking Cloudflare Tunnel binary (cloudflared.exe)...
if not exist "cloudflared.exe" (
    echo Downloading cloudflared.exe...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe', 'cloudflared.exe')"
    if not exist "cloudflared.exe" (
        echo [ERROR] Failed to download cloudflared.exe.
        echo You can manually download it from:
        echo https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
        echo Place cloudflared.exe in this folder.
    ) else (
        echo Downloaded cloudflared.exe successfully.
    )
) else (
    echo cloudflared.exe already exists.
)

:: 4. Instructions and launch prompt
echo.
echo ===================================================
echo [4/4] Setup complete!
echo.
echo Next Steps:
echo 1. Check config.json to customize settings or auth tokens.
echo 2. Run 'start.bat' to launch the server and Cloudflare tunnel.
echo 3. In Claude, go to Settings -^> Connectors -^> Add Custom Connector,
echo    and paste the public HTTPS URL printed by start.bat.
echo ===================================================
echo.

set /p STARTNOW="Would you like to start the server now? (Y/N): "
if /i "%STARTNOW%"=="Y" (
    echo Starting server...
    call "%~dp0start.bat"
) else (
    echo You can start the server anytime by running start.bat.
    pause
)
