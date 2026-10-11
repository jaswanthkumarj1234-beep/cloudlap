@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ===================================================
echo     Starting Claude Laptop Remote MCP Server
echo ===================================================
echo.

:: 1. Verify cloudflared.exe exists
if not exist "cloudflared.exe" (
    echo [ERROR] cloudflared.exe not found!
    echo Running setup.bat first to configure environment...
    call setup.bat
    if not exist "cloudflared.exe" (
        echo [ERROR] cloudflared.exe is still missing. Exiting.
        pause
        exit /b 1
    )
)

:: 2. Start Python server in background
set PYTHON_CMD=python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    py --version >nul 2>&1
    if %ERRORLEVEL% equ 0 set PYTHON_CMD=py
)

echo [1/2] Starting Python Remote MCP server on http://localhost:8787 using '%PYTHON_CMD%' ...
start "Claude MCP Python Server" /MIN %PYTHON_CMD% server.py

:: Give server 2 seconds to initialize
timeout /t 2 /nobreak >nul

:: 3. Start cloudflared tunnel
echo [2/2] Starting Cloudflare Tunnel...
echo.
echo =====================================================================
echo  LOOK BELOW for the trycloudflare.com URL!
echo  Copy the URL: https://[random-subdomain].trycloudflare.com
echo  In Claude: Settings -^> Connectors -^> Add -^> Paste the URL
echo =====================================================================
echo.

:: Run cloudflared attached to this console so user sees the live URL and incoming requests
cloudflared.exe tunnel --url http://localhost:8787

echo.
echo Tunnel closed. Terminating background Python server if running...
taskkill /FI "WINDOWTITLE eq Claude MCP Python Server*" /T /F >nul 2>&1
echo Done.
