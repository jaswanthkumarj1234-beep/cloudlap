@echo off
cd /d "%~dp0"
title CloudLap
set "PYW="

where pythonw >nul 2>&1 && set "PYW=pythonw"
if not defined PYW where pyw >nul 2>&1 && set "PYW=pyw -3"
for %%V in (313 312 311 310) do if not defined PYW if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe" set PYW="%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe"

if not defined PYW (
    echo Installing Python, please wait about a minute...
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements --silent
    for %%V in (313 312 311 310) do if not defined PYW if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe" set PYW="%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe"
)

if not defined PYW (
    echo.
    echo Python could not be installed automatically.
    echo Opening the download page. Install it, tick "Add Python to PATH",
    echo then double-click this file again.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

set "NEXT=launcher.pyw"
if not exist config.json set "NEXT=setup_gui.pyw"
if exist config.json findstr /c:"totp_secret" config.json >nul 2>&1 || set "NEXT=setup_gui.pyw"
if exist config.json findstr /c:"ngrok_domain" config.json >nul 2>&1 || set "NEXT=setup_gui.pyw"

start "" %PYW% %NEXT%
exit /b 0
