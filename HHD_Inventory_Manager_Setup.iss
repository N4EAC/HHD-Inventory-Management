; HHD Inventory Manager Inno Setup Script
; Program Files installer
; Version 1.0.2
;
; Run build_exe.bat first, then compile this script with Inno Setup.

#define MyAppName "HHD Inventory Manager"
#define MyAppVersion "1.0.4"
#define MyAppPublisher "Eduardo A. de Carvalho"
#define MyAppExeName "HHD_Inventory_Manager.exe"
#define MyAppBuildDir "dist\HHD_Inventory_Manager"

[Setup]
AppId={{BBA3A99F-B6BA-4F98-88B2-CC7F5B8445C6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={commonpf}\HHD Inventory Manager
PrivilegesRequired=admin

DefaultGroupName=HHD Inventory Manager
DisableProgramGroupPage=yes
DisableDirPage=no

OutputDir=installer_output
OutputBaseFilename=HHD_Inventory_Manager_Setup_v1.0.4
SetupIconFile=hhd_inventory_manager.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartIfNeededByRun=no
AlwaysRestart=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#MyAppBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "HHD_Inventory_Manager_User_Manual.pdf"; DestDir: "{app}"; Flags: ignoreversion
Source: "hhd_inventory_manager.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "hhd_inventory_manager.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\HHD Inventory Manager"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\hhd_inventory_manager.ico"
Name: "{group}\User Manual"; Filename: "{app}\HHD_Inventory_Manager_User_Manual.pdf"
Name: "{group}\Uninstall HHD Inventory Manager"; Filename: "{uninstallexe}"
Name: "{commondesktop}\HHD Inventory Manager"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\hhd_inventory_manager.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch HHD Inventory Manager"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; User data is stored in AppData and backups are stored in Documents.
; Do not delete user data or backup files automatically.
Type: filesandordirs; Name: "{app}\__pycache__"
