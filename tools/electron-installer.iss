#define MyAppName "绮录QQ聊天记录导出软件"
#define MyAppExeName "绮录QQ聊天记录导出软件.exe"
#ifndef MyAppVersion
  #error MyAppVersion is required
#endif
#ifndef SourceDir
  #error SourceDir is required
#endif

[Setup]
AppId=qingzhi-star.Qilu.Desktop
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=qingzhi-star
DefaultDirName={localappdata}\Programs\Qilu
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=Qilu-Setup-{#MyAppVersion}-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\qqexport\assets\qilu.ico
PrivilegesRequired=lowest
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  CanSetRuntimePermissions: Boolean;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ProgramDir: String;
begin
  ProgramDir := ExpandConstant('{app}');
  CanSetRuntimePermissions := not DirExists(ProgramDir) or
    ((CompareText(ProgramDir, ExpandConstant('{localappdata}\Programs\Qilu')) = 0) and
      FileExists(AddBackslash(ProgramDir) + '{#MyAppExeName}'));
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ExitCode: Integer;
begin
  if (CurStep <> ssPostInstall) or not CanSetRuntimePermissions then
    Exit;
  { Electron 的沙箱进程需要读取应用自己的 EXE、DLL 和资源。 }
  if not Exec(ExpandConstant('{sys}\icacls.exe'),
      '"' + ExpandConstant('{app}') + '" /grant "*S-1-15-2-1:(OI)(CI)(RX)" /Q',
      '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
    Log('Could not start the runtime ACL setup: ' + SysErrorMessage(ExitCode))
  else if ExitCode <> 0 then
    Log('Runtime ACL setup failed with exit code ' + IntToStr(ExitCode));
end;
