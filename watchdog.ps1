<#
CloudLap watchdog
Keeps the MCP server and the ngrok tunnel running. Relaunches either one if it stops.
Safe to start more than once: only one copy runs at a time.

Run hidden at login, for example from the Startup folder:
  powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "<path>\watchdog.ps1"

Reads `port` and `ngrok_domain` from config.json. If ngrok_domain is empty the tunnel is not managed.
Writes a short rolling log to watchdog.log next to this script.
#>
param([int]$IntervalSeconds = 10)

$ErrorActionPreference = "Continue"
$dir = $PSScriptRoot
$log = Join-Path $dir "watchdog.log"

# Single instance guard
$created = $false
$mutex = New-Object System.Threading.Mutex($true, "Global\CloudLapWatchdog", [ref]$created)
if (-not $created) { exit 0 }

function Say([string]$m) {
    try {
        Add-Content -Path $log -Value ("{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m)
        $lines = Get-Content -Path $log
        if ($lines.Count -gt 500) { $lines | Select-Object -Last 300 | Set-Content -Path $log }
    } catch {}
}

function Read-Config {
    try { return Get-Content -Path (Join-Path $dir "config.json") -Raw | ConvertFrom-Json } catch { return $null }
}

function Find-Python {
    $c = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($c) { return $c.FullName }
    $g = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($g -and $g.Source -notlike "*WindowsApps*") { return $g.Source }
    return $null
}

function Find-Ngrok {
    $candidates = @("$env:LOCALAPPDATA\ngrok\ngrok.exe")
    $candidates += Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Ngrok*\ngrok.exe" -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName }
    foreach ($x in $candidates) { if (Test-Path $x) { return $x } }
    $g = Get-Command ngrok.exe -ErrorAction SilentlyContinue
    if ($g) { return $g.Source }
    return $null
}

function Port-Up([int]$p) {
    [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
}

function Start-Server {
    $py = Find-Python
    if (-not $py) { Say "ERROR: python not found, cannot start server"; return }
    Start-Process -FilePath $py -ArgumentList "server.py" -WorkingDirectory $dir -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $dir "server_stdout.log") -RedirectStandardError (Join-Path $dir "server_stderr.log")
    Say "started server"
}

function Start-Tunnel([string]$domain, [int]$p) {
    $ng = Find-Ngrok
    if (-not $ng) { Say "ERROR: ngrok not found, cannot start tunnel"; return }
    Start-Process -FilePath $ng -ArgumentList @("http", "--url=$domain", "127.0.0.1:$p") -WindowStyle Hidden
    Say "started ngrok tunnel"
}

Say "watchdog started (interval ${IntervalSeconds}s)"
$lastServerOk = $true
$lastTunnelOk = $true

while ($true) {
    $cfg = Read-Config
    $port = 8787
    if ($cfg -and $cfg.port) { $port = [int]$cfg.port }
    $domain = ""
    if ($cfg -and $cfg.ngrok_domain) { $domain = [string]$cfg.ngrok_domain }

    $serverOk = Port-Up $port
    if (-not $serverOk) {
        if ($lastServerOk) { Say "server is down on port $port" }
        Start-Server
        Start-Sleep -Seconds 12
        $serverOk = Port-Up $port
        Say ("server up after restart: " + $serverOk)
    }
    $lastServerOk = $serverOk

    if ($domain) {
        $tunnelOk = [bool](Get-Process -Name ngrok -ErrorAction SilentlyContinue)
        if (-not $tunnelOk) {
            if ($lastTunnelOk) { Say "tunnel is down" }
            Start-Tunnel $domain $port
            Start-Sleep -Seconds 8
            $tunnelOk = [bool](Get-Process -Name ngrok -ErrorAction SilentlyContinue)
            Say ("tunnel up after restart: " + $tunnelOk)
        }
        $lastTunnelOk = $tunnelOk
    }

    Start-Sleep -Seconds $IntervalSeconds
}
