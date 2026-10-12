@echo off
setlocal
cd /d "%~dp0"
title CloudLap

rem ---- find Python (windowed) ----
call :find_python
if not defined PYW (
    echo Installing Python, please wait about a minute...
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements --silent
    call :find_python
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

rem ---- first time: setup window. After that: the CloudLap window ----
set "NEXT=launcher.pyw"
findstr /c:"totp_secret" config.json >nul 2>&1 || set "NEXT=setup_gui.pyw"
findstr /c:"ngrok_domain" config.json >nul 2>&1 || set "NEXT=setup_gui.pyw"
if not exist config.json set "NEXT=setup_gui.pyw"

start "" %PYW% %NEXT%
exit /b 0

:find_python
set "PYW="
where pythonw >nul 2>&1 && set "PYW=pythonw"
if defined PYW goto :eof
where pyw >nul 2>&1 && set "PYW=pyw -3"
if defined PYW goto :eof
for %%V in (313 312 311 310) do if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe" if not defined PYW set PYW="%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe"
goto :eof
