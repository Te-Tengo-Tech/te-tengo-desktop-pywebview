; Inno Setup 6 script of Te Tengo Captura: a per-user installer of the PyInstaller one-folder build
; (docs/RELEASES.md). It needs no administrator rights.
;
;   uv run pyinstaller packaging/te-tengo-captura.spec --noconfirm
;   iscc /DAppVersion=0.6.0 packaging\te-tengo-captura.iss
;   → dist\instalador\te-tengo-captura-0.6.0-instalador.exe
;
; What it does, consistent with docs/INSTALLATION.md:
; - installs dist\te-tengo-captura\ into %LOCALAPPDATA%\Programs\TeTengoCaptura (per user);
; - creates the Start menu shortcut;
; - registers the autostart entry HKCU\...\Run\TeTengoCaptura with exactly the value the agent writes
;   itself (src/te_tengo_captura/autoinicio.py: the quoted path of the exe), so the agent finds it in
;   place and nothing is registered twice; the uninstaller removes it;
; - optionally copies the installation file: /CONFIG="C:\ruta\config.toml" (never overwrites one);
; - stops this user's running agent before installing over it and before uninstalling;
; - silent update started by the agent itself (US-43, src/te_tengo_captura/actualizaciones/):
;     te-tengo-captura-setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /RELANZAR /LOG=<file>
;   waits until the agent has exited (its named mutex is gone; at most 60 s, then it is stopped
;   without touching its process tree, which holds this installer), installs, and opens the agent
;   again whether it is an installation (config.toml) or a linked PC (no config.toml). It never
;   touches config.toml, the data folder or the PC's tokens (Windows Credential Manager);
; - on uninstall, asks whether to restablish the PC as well (the default answer is «Sí»; silent
;   uninstalls do it only with /RESTABLECER): before removing the program it runs
;     te-tengo-captura.exe --restablecer --sin-interfaz --motivo desinstalada
;   which unlinks the PC in the API if there is internet (the family's app removes it and its
;   activity says «La PC … se desinstaló»), deletes its tokens and data key from Windows Credential
;   Manager, config.toml, the data folder and the logs, and the autostart entry. Offline it still
;   deletes everything here, and the app shows the PC «Sin conexión» until the owner removes it;
; - the finish page reminds that Te Tengo must stay on and starts with Windows.

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
; The named mutex the running agent holds (src/te_tengo_captura/instancia.py, MUTEX).
#define AppMutexName "TeTengoCapturaEnEjecucion"

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

[Messages]
; Draft copy (docs/BLOCKERS.md): detection only works while the program runs.
FinishedLabel=Te Tengo Captura quedó instalado.%n%nDéjalo encendido: solo detecta caídas mientras está abierto. Se inicia solo con Windows y, al cerrar la ventana, sigue en la bandeja junto al reloj.
FinishedLabelNoIcons=Te Tengo Captura quedó instalado.%n%nDéjalo encendido: solo detecta caídas mientras está abierto. Se inicia solo con Windows y, al cerrar la ventana, sigue en la bandeja junto al reloj.

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
  Flags: nowait postinstall; Check: HayConfiguracion and not SeDebeRelanzar
; A silent update started by the agent (/RELANZAR, US-43): always open it again, also a linked PC
; with no configuration file. Not a postinstall entry, so it runs in silent mode too.
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: SeDebeRelanzar

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function SeIndicoConfiguracion: Boolean;
begin
  Result := ExpandConstant('{param:CONFIG}') <> '';
end;

{ /RELANZAR: a silent update started by the running agent (US-43). }
function SeDebeRelanzar: Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), '/RELANZAR') = 0 then
    begin
      Result := True;
      Exit;
    end;
end;

function HayConfiguracion: Boolean;
begin
  Result := FileExists(ExpandConstant('{userappdata}\{#AppDirName}\config.toml'));
end;

{ Stops this user's running agent, so its files can be replaced or removed. The outbox is SQLite,
  which survives a forced stop; pending events are sent on the next start. With Arbol its child
  processes go too; a silent update never does that: this installer is one of them. }
procedure DetenerAgente(Arbol: Boolean);
var
  Codigo: Integer;
  Opciones: String;
begin
  Opciones := '/F ';
  if Arbol then
    Opciones := Opciones + '/T ';
  Exec(ExpandConstant('{sys}\taskkill.exe'),
    Opciones + '/IM {#AppExe} /FI "USERNAME eq ' + GetUserNameString + '"',
    '', SW_HIDE, ewWaitUntilTerminated, Codigo);
  Sleep(1000);
end;

{ A silent update: the agent started this installer and is closing itself (it holds the named
  mutex while it runs). Wait for it, at most 60 s. }
procedure EsperarQueSalgaElAgente;
var
  Intentos: Integer;
begin
  Intentos := 0;
  while CheckForMutexes('{#AppMutexName}') and (Intentos < 120) do
  begin
    Sleep(500);
    Intentos := Intentos + 1;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if SeDebeRelanzar then
  begin
    EsperarQueSalgaElAgente;
    DetenerAgente(False);
  end
  else
    DetenerAgente(True);
  Result := '';
end;

{ /RESTABLECER: a silent uninstall that also restablishes the PC. }
function SeDebeRestablecer: Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), '/RESTABLECER') = 0 then
    begin
      Result := True;
      Exit;
    end;
end;

{ Draft copy (docs/BLOCKERS.md). «Sí» is the default: an uninstalled PC should not stay in the
  family's app as if it still looked after someone. }
function PreguntarRestablecer: Boolean;
begin
  if UninstallSilent then
    Result := SeDebeRestablecer
  else
    Result := MsgBox('¿Quitar también esta PC de la casa y borrar sus datos?' + #13#10#13#10 +
      'Te Tengo dejará de detectar caídas con esta PC. La familia recibirá un aviso y la PC ' +
      'desaparecerá de la app. Se borrarán los accesos guardados, la configuración, los ' +
      'movimientos, video y clips, los avisos que aún no se enviaron y los registros.' + #13#10#13#10 +
      'Elige «No» solo si vas a volver a instalarlo en esta PC.',
      mbConfirmation, MB_YESNO) = IDYES;
end;

{ The agent itself unlinks the PC (the API, if there is internet) and deletes its tokens, its
  configuration, its data and its logs: te-tengo-captura.exe --restablecer (docs/INSTALLATION.md,
  "Uninstall"). It is a windowed exe, so Exec waits for it to exit; its HTTP calls time out. }
procedure Restablecer;
var
  Codigo: Integer;
begin
  if not Exec(ExpandConstant('{app}\{#AppExe}'), '--restablecer --sin-interfaz --motivo desinstalada',
    '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
    Log('No se pudo ejecutar --restablecer')
  else
    Log('--restablecer terminó con ' + IntToStr(Codigo));
  { Whatever the agent could not delete (a file in use, an old version without --restablecer). }
  DelTree(ExpandConstant('{userappdata}\{#AppDirName}'), True, True, True);
  DelTree(ExpandConstant('{localappdata}\{#AppDirName}'), True, True, True);
end;

var
  DebeRestablecer: Boolean;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    DetenerAgente(True);
    { Asked before the program is removed: the reset needs te-tengo-captura.exe. }
    DebeRestablecer := PreguntarRestablecer;
    if DebeRestablecer then
      Restablecer;
  end;
end;
