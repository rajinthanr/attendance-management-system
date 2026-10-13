; Inno Setup script for the Attendance Logger's Windows installer.
; build_windows.bat runs it after PyInstaller has written build\windows-app\AttendanceLogger\ and make_icons.py build\icons\:
;     iscc /DAppVersion=1.0.0 packaging\installer.iss
; Output: dist\AttendanceLogger-Setup-<version>.exe. Installs per user by default (no admin prompt);
; the setup offers "install for all users" too. The database stays in %USERPROFILE%\AttendanceLogger and is
; not removed on uninstall.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "Attendance Logger"
#define AppExe "AttendanceLogger.exe"

[Setup]
AppId={{6E0F3C1A-4B7D-4C55-9C1E-2A8D7B3F9E51}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Attendance Management System
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=AttendanceLogger-Setup-{#AppVersion}
SetupIconFile=..\build\icons\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build\windows-app\AttendanceLogger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} (demo, made-up data)"; Filename: "{app}\{#AppExe}"; Parameters: "--demo"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
