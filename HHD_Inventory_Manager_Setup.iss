; HHD Inventory Manager Inno Setup Script
; Compile this file with Inno Setup after building the EXE with build_exe.bat.
; Expected build output:
;   dist\HHD_Inventory_Manager\HHD_Inventory_Manager.exe

#define MyAppName "HHD Inventory Manager"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Eduardo A. de Carvalho"
#define MyAppExeName "HHD_Inventory_Manager.exe"

[Setup]
AppId={{BBA3A99F-B6BA-4F98-88B2-CC7F5B8445C6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HHD Inventory Manager
DefaultGroupName=HHD Inventory Manager
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=HHD_Inventory_Manager_Setup_v1.0.0
SetupIconFile=hhd_inventory_manager.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
CloseApplications=yes
RestartIfNeededByRun=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\HHD_Inventory_Manager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "HHD_Inventory_Manager_User_Manual.pdf"; DestDir: "{app}"; Flags: ignoreversion
Source: "hhd_inventory_manager.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "hhd_inventory_manager.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\HHD Inventory Manager"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\hhd_inventory_manager.ico"
Name: "{group}\User Manual"; Filename: "{app}\HHD_Inventory_Manager_User_Manual.pdf"
Name: "{group}\Uninstall HHD Inventory Manager"; Filename: "{uninstallexe}"
Name: "{autodesktop}\HHD Inventory Manager"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\hhd_inventory_manager.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch HHD Inventory Manager"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Do not delete user database backups from Documents.
; Do not delete hhd_inventory.db here; users may want to preserve it for reinstall or manual backup.
Type: filesandordirs; Name: "{app}\__pycache__"
