[Setup]
AppName=SiteForge AI
AppVersion=1.0.0
DefaultDirName={autopf}\SiteForge AI
DefaultGroupName=SiteForge AI
OutputDir=..\dist\installer
OutputBaseFilename=SiteForgeAI-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Files]
Source: "..\dist\SiteForgeAI\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\SiteForge AI"; Filename: "{app}\SiteForgeAI.exe"
Name: "{autodesktop}\SiteForge AI"; Filename: "{app}\SiteForgeAI.exe"

[Run]
Filename: "{app}\SiteForgeAI.exe"; Description: "Launch SiteForge AI"; Flags: nowait postinstall skipifsilent
