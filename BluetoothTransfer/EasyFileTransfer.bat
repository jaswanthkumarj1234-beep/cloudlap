@echo off & powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$t=[IO.File]::ReadAllText('%~f0'); iex $t.Substring($t.IndexOf('#PSBEGIN'+'#'))" & exit /b
#PSBEGIN#
# Easy File Transfer (Bluetooth)
# A simple step-by-step helper for sending files between two Windows computers
# with Bluetooth. It uses the Bluetooth file-transfer tool that is already built
# into Windows, so no internet and no extra software are needed.

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

function New-Font($size, $bold) {
    $style = [System.Drawing.FontStyle]::Regular
    if ($bold) { $style = [System.Drawing.FontStyle]::Bold }
    return New-Object System.Drawing.Font('Segoe UI', $size, $style)
}

function New-Lbl($text, $x, $y, $w, $h, $size, $bold) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $text
    $l.Location = New-Object System.Drawing.Point($x, $y)
    $l.Size = New-Object System.Drawing.Size($w, $h)
    $l.Font = New-Font $size $bold
    return $l
}

function New-Btn($text, $x, $y, $w, $h, $color) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $text
    $b.Location = New-Object System.Drawing.Point($x, $y)
    $b.Size = New-Object System.Drawing.Size($w, $h)
    $b.FlatStyle = 'Flat'
    $b.FlatAppearance.BorderSize = 0
    $b.BackColor = $color
    $b.ForeColor = [System.Drawing.Color]::White
    $b.Font = New-Font 16 $true
    $b.Cursor = [System.Windows.Forms.Cursors]::Hand
    return $b
}

function Test-Bluetooth {
    try {
        $found = Get-PnpDevice -Class Bluetooth -PresentOnly -ErrorAction Stop |
            Where-Object {
                $_.InstanceId -like 'BTH\MS_BTHBRB*' -or $_.InstanceId -like 'USB\*' -or
                $_.InstanceId -like 'PCI\*' -or $_.InstanceId -like 'ACPI\*'
            }
        return [bool]$found
    } catch {
        return $null
    }
}

# ---------- actions ----------
$openBluetoothSettings = {
    try {
        Start-Process 'ms-settings:bluetooth'
    } catch {
        try { Start-Process 'control.exe' -ArgumentList 'bthprops.cpl' }
        catch {
            [System.Windows.Forms.MessageBox]::Show(
                "Could not open Bluetooth settings.`nClick the Bluetooth icon near the clock instead.",
                'Easy File Transfer') | Out-Null
        }
    }
}

$openTransferTool = {
    $exe = Join-Path $env:windir 'System32\fsquirt.exe'
    if (Test-Path $exe) {
        Start-Process $exe
    } else {
        [System.Windows.Forms.MessageBox]::Show(
            "The Windows Bluetooth transfer tool was not found on this computer.`nMake sure Bluetooth is available and turned on.",
            'Easy File Transfer') | Out-Null
    }
}

# ---------- window ----------
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Easy File Transfer (Bluetooth)'
$form.ClientSize = New-Object System.Drawing.Size(780, 580)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedSingle'
$form.MaximizeBox = $false
$form.BackColor = [System.Drawing.Color]::White

$blue   = [System.Drawing.Color]::FromArgb(0, 102, 204)
$green  = [System.Drawing.Color]::FromArgb(30, 140, 70)
$orange = [System.Drawing.Color]::FromArgb(205, 100, 20)
$gray   = [System.Drawing.Color]::FromArgb(90, 100, 115)

# ----- home page -----
$pageHome = New-Object System.Windows.Forms.Panel
$pageHome.Dock = 'Fill'
$pageHome.Controls.Add((New-Lbl 'Easy File Transfer' 30 20 720 50 24 $true))
$pageHome.Controls.Add((New-Lbl 'Move files from one computer to another using Bluetooth. No internet needed. Install this on BOTH computers.' 30 75 720 60 13 $false))

$btnPair    = New-Btn '1.  Connect the two computers  (only once)' 30 150 720 85 $gray
$btnSend    = New-Btn '2.  SEND files from this computer' 30 250 720 85 $green
$btnReceive = New-Btn '3.  RECEIVE files on this computer' 30 350 720 85 $orange
$pageHome.Controls.AddRange(@($btnPair, $btnSend, $btnReceive))

$lblStatus = New-Lbl '' 30 455 720 80 12 $false
$bt = Test-Bluetooth
if ($bt -eq $true) {
    $lblStatus.Text = 'Bluetooth was found on this computer. Make sure it is turned ON.'
} elseif ($bt -eq $false) {
    $lblStatus.Text = 'No Bluetooth was found on this computer. You may need a small Bluetooth USB adapter.'
    $lblStatus.ForeColor = [System.Drawing.Color]::Firebrick
} else {
    $lblStatus.Text = 'Could not check Bluetooth. Make sure it is turned ON.'
}
$pageHome.Controls.Add($lblStatus)

# ----- steps page -----
$pageSteps = New-Object System.Windows.Forms.Panel
$pageSteps.Dock = 'Fill'
$pageSteps.Visible = $false
$lblStepsTitle = New-Lbl '' 30 20 720 50 22 $true
$lblStepsText  = New-Lbl '' 30 85 720 340 14 $false
$btnAction = New-Btn '' 30 450 470 80 $blue
$btnAction.TextAlign = 'MiddleCenter'
$btnBack = New-Btn 'Back' 520 450 230 80 $gray
$btnBack.TextAlign = 'MiddleCenter'
$pageSteps.Controls.AddRange(@($lblStepsTitle, $lblStepsText, $btnAction, $btnBack))

$script:currentAction = $null

function Show-Steps($title, $text, $buttonText, $action) {
    $lblStepsTitle.Text = $title
    $lblStepsText.Text = $text
    $btnAction.Text = $buttonText
    $script:currentAction = $action
    $pageHome.Visible = $false
    $pageSteps.Visible = $true
}

$btnBack.Add_Click({ $pageSteps.Visible = $false; $pageHome.Visible = $true })
$btnAction.Add_Click({ if ($script:currentAction) { & $script:currentAction } })

$btnPair.Add_Click({
    Show-Steps 'Connect the two computers' @"
Do this ONE time only. Put both computers next to each other.
Do the steps below on BOTH computers.

1.  Click the blue button below. Bluetooth settings open.
2.  Make sure Bluetooth is turned ON.
3.  Click 'Add device', then choose 'Bluetooth'.
4.  Pick the name of the OTHER computer from the list.
5.  The same number shows on both screens. If the numbers match,
     click 'Connect' (or 'Yes') on both computers.
"@ 'Open Bluetooth settings' $openBluetoothSettings
})

$btnSend.Add_Click({
    Show-Steps 'Send files' @"
First, on the OTHER computer, open this program and follow
'3. RECEIVE files'. Keep the computers close together.

1.  Click the blue button below. A window opens.
2.  Click 'Send files'.
3.  Choose the name of the other computer, then click 'Next'.
4.  Click 'Browse', pick your files, then click 'Next'.
5.  Wait until it says the transfer is complete.

Tip: Bluetooth is slow. A big file can take many minutes.
"@ 'Start sending' $openTransferTool
})

$btnReceive.Add_Click({
    Show-Steps 'Receive files' @"
1.  Click the blue button below. A window opens.
2.  Click 'Receive files'. Leave the window open. It says
     'Waiting for a connection'.
3.  On the OTHER computer, open this program and follow
     '2. SEND files'.
4.  When it asks where to save, pick a place you can find
     again, for example the Desktop.
5.  Wait until it says the transfer is complete.
"@ 'Start receiving' $openTransferTool
})

$form.Controls.AddRange(@($pageSteps, $pageHome))

try {
    [System.Windows.Forms.Application]::Run($form)
} catch {
    [System.Windows.Forms.MessageBox]::Show("Something went wrong:`n$($_.Exception.Message)", 'Easy File Transfer') | Out-Null
}
