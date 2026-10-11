@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ===================================================
echo     Starting CloudLap Remote MCP Server
echo ===================================================
echo.

:: 1. Verify python
set PYTHON_CMD=python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    py --version >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo [ERROR] Python is not installed or not in PATH!
        pause
        exit /b 1
    )
)

:: 2. Read ngrok domain from config.json
set NGROK_DOMAIN=
for /f "tokens=2 delims=:, " %%a in ('findstr "ngrok_domain" config.json 2^>nul') do (
    set NGROK_DOMAIN=%%~a
)

if "%NGROK_DOMAIN%"=="" (
    echo [ERROR] ngrok_domain is not configured in config.json!
    echo Please edit config.json and set your domain first.
    pause
    exit /b 1
)

:: 3. Clean up any stale instances on port 8787 or ngrok
echo [1/3] Preparing ports and processes...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8787 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1

:: 4. Start Python server
echo [2/3] Starting CloudLap server on http://127.0.0.1:8787 ...
start "CloudLap Server" /MIN %PYTHON_CMD% server.py
timeout /t 3 /nobreak >nul

:: 5. Start ngrok tunnel
echo [3/3] Starting ngrok tunnel to %NGROK_DOMAIN% ...
echo.
echo =====================================================================
echo  CloudLap is LIVE!
echo  URL: https://%NGROK_DOMAIN%/mcp
echo  Paste this in Claude: Settings -^> Connectors -^> Add Custom Connector
echo =====================================================================
echo.

ngrok http --url=%NGROK_DOMAIN% 127.0.0.1:8787

echo.
echo Tunnel closed. Stopping server...
taskkill /FI "WINDOWTITLE eq CloudLap Server*" /T /F >nul 2>&1
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8787 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
echo Done.
