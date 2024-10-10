[Setup]
AppName=FFInc.
AppVersion=0.1
DefaultDirName={pf}\FlowFactoryIncorporated
OutputBaseFilename=FFInc_Installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\app.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Rena-Regular.ttf"; DestDir: "{app}"; Flags: ignoreversion
Source: "joe.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_data.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "file_manager.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\FlowFactoryIncorporated"; Filename: "{app}\app.exe"
Name: "{commondesktop}\FlowFactoryIncorporated"; Filename: "{app}\app.exe"; Tasks: "desktopicon"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons"; 
Name: "pintaskbar"; Description: "Pin to taskbar"; GroupDescription: "Additional icons"; 

[Run]
Filename: "{app}\app.exe"; Description: "Launch the application"; Flags: nowait postinstall skipifsilent; 
