; Inno Setup 6 script of Te Tengo Captura: a per-user installer of the PyInstaller one-folder build
; (docs/RELEASES.md). It needs no administrator rights.
;
;   uv run pyinstaller packaging/te-tengo-captura.spec --noconfirm
;   iscc /DAppVersion=0.4.3 packaging\te-tengo-captura.iss
;   → dist\instalador\te-tengo-captura-0.4.3-instalador.exe
;
; What it does, consistent with docs/INSTALLATION.md:
; - installs dist\te-tengo-captura\ into %LOCALAPPDATA%\Programs\TeTengoCaptura (per user);
; - creates the Start menu shortcut;
; - registers the autostart entry HKCU\...\Run\TeTengoCaptura with exactly the value the agent writes
;   itself (src/te_tengo_captura/autoinicio.py: the quoted path of the exe), so the agent finds it in
;   place and nothing is registered twice; the uninstaller removes it;
; - optionally copies the installation file: /CONFIG="C:\ruta\config.toml" (never overwrites one);
; - stops this user's running agent before installing over it and before uninstalling;
; - on uninstall, asks whether to also delete the configuration, the outbox and the logs.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\te-tengo-captura"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist\instalador"
#endif
; The brand icon, drawn by the PyInstaller spec into its work directory.
#ifndef IconFile
  #define IconFile "..\build\te-tengo-captura\te-tengo-captura.ico"
#endif

#define AppName "Te Tengo Captura"
#define AppExe "te-tengo-captura.exe"
; platformdirs app name of the agent (src/te_tengo_captura/rutas.py) and the autostart value name
; (src/te_tengo_captura/autoinicio.py): keep them in sync.
#define AppDirName "TeTengoCaptura"
#define RunValueName "TeTengoCaptura"

[Setup]
; Never change AppId: it identifies the installation for upgrades and uninstall.
AppId={{A7BBA129-4487-4DEF-BFD3-4C6C1F2EC0C3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Te Tengo
AppPublisherURL=https://github.com/Te-Tengo-Tech
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription=Instalador de {#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; Per user, without administrator rights: {autopf} is %LOCALAPPDATA%\Programs.
DefaultDirName={autopf}\{#AppDirName}
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=te-tengo-captura-{#AppVersion}-instalador
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
; The running agent is stopped by the [Code] section, not by the Restart Manager.
CloseApplications=no
SetupLogging=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; The installation file of this household (docs/INSTALLATION.md, section 4), when given with
; /CONFIG=<path>. It holds the installation credential: it is kept on uninstall unless the user
; chooses to delete the data.
Source: "{param:CONFIG}"; DestDir: "{userappdata}\{#AppDirName}"; DestName: "config.toml"; \
  Flags: external onlyifdoesntexist uninsneveruninstall; Check: SeIndicoConfiguracion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Registry]
; Same value name and data as autoinicio.registrar(): '"<path of the exe>"'.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
  ValueName: "{#RunValueName}"; ValueData: """{app}\{#AppExe}"""; Flags: uninsdeletevalue

[Run]
; Without a configuration file the agent cannot start, so it is only launched when there is one.
; Silent upgrades relaunch it as well (no skipifsilent).
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall; Check: HayConfiguracion

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function SeIndicoConfiguracion: Boolean;
begin
  Result := ExpandConstant('{param:CONFIG}') <> '';
end;

function HayConfiguracion: Boolean;
begin
  Result := FileExists(ExpandConstant('{userappdata}\{#AppDirName}\config.toml'));
end;

{ Stops this user's running agent, so its files can be replaced or removed. The outbox is SQLite,
  which survives a forced stop; pending events are sent on the next start. }
procedure DetenerAgente;
var
  Codigo: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'),
    '/F /T /IM {#AppExe} /FI "USERNAME eq ' + GetUserNameString + '"',
    '', SW_HIDE, ewWaitUntilTerminated, Codigo);
  Sleep(1000);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  DetenerAgente;
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    DetenerAgente;
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    if MsgBox('¿Eliminar también la configuración y los datos de {#AppName} en esta PC?' + #13#10#13#10 +
      'Se borrarán el archivo de instalación, los eventos que aún no se enviaron y los registros. ' +
      'Elige «No» si vas a volver a instalarlo.', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      DelTree(ExpandConstant('{userappdata}\{#AppDirName}'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\{#AppDirName}'), True, True, True);
    end;
end;
