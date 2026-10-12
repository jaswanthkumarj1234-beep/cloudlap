; CloudLap Windows installer (Inno Setup 6). Built automatically by .github/workflows/release.yml
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{B7C0A6D2-3F4E-4C1A-9E55-5C10D1A0C10D}
AppName=CloudLap
AppVersion={#AppVersion}
AppPublisher=CloudLap
AppPublisherURL=https://github.com/jaswanthkumarj1234-beep/cloudlap
DefaultDirName={localappdata}\CloudLap
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=CloudLap-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=CloudLap

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "server.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "totp.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "totp_setup.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "launcher.pyw"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup_gui.pyw"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup_wizard.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "watchdog.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.example.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "Start CloudLap.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "start.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "SETUP.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\CloudLap"; Filename: "{app}\Start CloudLap.bat"; WorkingDir: "{app}"; Flags: runminimized
Name: "{userdesktop}\CloudLap"; Filename: "{app}\Start CloudLap.bat"; WorkingDir: "{app}"; Flags: runminimized; Tasks: desktopicon

[Run]
Filename: "{app}\Start CloudLap.bat"; WorkingDir: "{app}"; Description: "Open CloudLap and finish setup"; Flags: postinstall nowait skipifsilent shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
