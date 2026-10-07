# Installation guide (project team)

Te Tengo Captura is installed by the project team on the household PC, with a fixed configuration. The family does not configure anything on the PC: consent, pauses, room name and alerts are managed in the Te Tengo mobile app.

## 1. What is needed

- A Windows 10 or 11 PC that stays on, with internet access.
- A USB webcam (the pilot uses a 1080p one; the agent works at 480p).
- The build of the agent: the `te-tengo-captura-windows` artifact of the CI `empaquetar` job, or `make empaquetar` on a Windows machine with the repository.
- The **installation credential** for this camera, issued by the team in `te-tengo-general-api` (it is secret: never write it in tickets, chats or logs).

## 2. Install the program

1. Unzip the `te-tengo-captura` folder to `%LOCALAPPDATA%\Programs\TeTengoCaptura\`.
2. The first time, Windows SmartScreen may warn that the program is not signed (`docs/BLOCKERS.md`, "Windows code signing"): choose «Más información» → «Ejecutar de todas formas».
3. Optional: create a Start menu shortcut to `te-tengo-captura.exe`. Opening it again while it runs only shows its window.

## 3. Write the configuration file

Copy [`config.ejemplo.toml`](../config.ejemplo.toml) to `%APPDATA%\TeTengoCaptura\config.toml` and fill in every field:

| Field | What to write |
|---|---|
| `api_url` | Base URL of `te-tengo-general-api` |
| `credencial_instalacion` | The installation credential of this camera |
| `instalada_el` | Installation date (`2026-09-22`); shown as «Instalación» |
| `[webcam] indice` | OpenCV index of the webcam: `0` is the first one. If the PC has a built-in camera too, find the right index with `make camara ARGS="--listar-camaras"` from the repository (it saves a photo per camera) |
| `[webcam] nombre`, `especificacion` | How the window names the webcam, e.g. «Webcam USB HD (1080p)» and «USB · 1920 × 1080» |
| `[vivienda] nombre_adulto_mayor`, `direccion` | The household, as the family registered it in the app |
| `[camara] nombre_habitacion` | The room where the webcam is, e.g. «Sala». It is used on the first registration; afterwards the family renames it in the app (CA-06.2) |
| `[clasificacion]` | Leave it out. Without it the agent uses the thresholds validated in [validation.md](validation.md); change them only after re-validating |

If a field is missing or invalid, the agent does not start and the log says, in Spanish, which field to fix (`El archivo de configuración … está incompleto: Falta el campo «webcam.indice».`).

## 4. Place the webcam

The classifier was validated with the CAUCAFall dataset, recorded by a camera **elevated in a corner of a home**, and its speed threshold was calibrated for that position ([validation.md](validation.md), section 3.3). A camera at body height behaves differently. So:

- Mount the webcam **high in a corner** of the room (around 2 m), looking down and across the room, as in CAUCAFall.
- Frame the area where the older adult moves, **including the floor**: a fall is recognised when the body ends up horizontal or with the head below the feet.
- The **whole body** must be visible when standing: head, hips and ankles. Poses whose key points are not clearly visible cannot declare a recovery (adaptation A6).
- Avoid backlight (a window behind the person) and very dark corners. If the person is not seen for 5 minutes, the agent sends `deteccion_no_confiable` and the family is told to check light and framing (CA-15.3).
- Use the same USB port every time: the window asks to reconnect it there.

To check the framing, run `make camara` from the repository on that PC: it shows the skeleton and the three fall conditions live.

## 5. First start and checks

Start `te-tengo-captura.exe`. The splash shows «Iniciando…», «Abriendo la webcam configurada…» and «Conectando con Te Tengo…», then the status window appears:

| The window shows | Meaning | What to do |
|---|---|---|
| «Enviando video · conectado» (green) | Everything works | Nothing |
| «Esperando consentimiento» (amber) | The family has not registered consent in the app | Ask the family to complete it; capture starts on its own |
| «En pausa hasta las …» (grey stripes) | The family paused the camera from the app | Nothing; it resumes at that hour |
| «Sin internet · reintentando en … s» (dark) | No connection with Te Tengo | Check the PC's internet; «Reintentar ahora» retries at once |
| «Webcam desconectada: revisa el cable USB» (amber) | The webcam does not answer | Check the cable; «Buscar de nuevo» reopens it |

Close the window: it stays in the tray, next to the clock, with a status dot (green sending, grey paused, amber problem), and the first time Windows shows «Te Tengo Captura sigue funcionando en segundo plano».

## 6. Files on the PC

| What | Where (Windows) |
|---|---|
| Configuration | `%APPDATA%\TeTengoCaptura\config.toml` |
| Outbox and pending clips | `%LOCALAPPDATA%\TeTengoCaptura\` (`envios.sqlite3`, `clips\`, `estado_captura.json`) |
| Logs (1 MB × 5, no secrets, no images) | `%LOCALAPPDATA%\TeTengoCaptura\Logs\te-tengo-captura.log` |

The only images ever written to disk are the clips of events, and only until they are uploaded. To check a build without a webcam: `te-tengo-captura.exe --autoprueba --logs .` writes `te-tengo-captura.log` with one line per check and exits with 0 when all pass.

## 7. Start with the system

The window says «Se inicia con Windows»: the agent must start on its own when the household PC is turned on.

### Windows
Nothing to do. On every start, the packaged agent (`te-tengo-captura.exe`) writes or updates a per-user entry in the registry:

```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
  TeTengoCaptura = "C:\…\te-tengo-captura.exe"
```

To check it: `reg query HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v TeTengoCaptura`. To remove it (uninstall): `reg delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v TeTengoCaptura /f`. When run from source (`uv run te-tengo-captura`) nothing is written.

### macOS (LaunchAgent)
Save as `~/Library/LaunchAgents/pe.tetengo.captura.plist`, adjusting the path, and load it with `launchctl load ~/Library/LaunchAgents/pe.tetengo.captura.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>pe.tetengo.captura</string>
  <key>ProgramArguments</key>
  <array><string>/Applications/TeTengoCaptura/te-tengo-captura</string></array>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
```

### Linux (autostart `.desktop`)
Save as `~/.config/autostart/te-tengo-captura.desktop`, adjusting the path:

```ini
[Desktop Entry]
Type=Application
Name=Te Tengo Captura
Exec=/opt/te-tengo-captura/te-tengo-captura
X-GNOME-Autostart-enabled=true
```

## 8. Only one agent

Opening the program again (from the Start menu or a desktop shortcut) does not start a second agent: it shows the window of the one already running. The running agent holds a lock on `instancia.lock` in its data directory.

## 9. Uninstall

1. «Salir» from the tray icon menu.
2. Remove the autostart entry (section 7) and delete `%LOCALAPPDATA%\Programs\TeTengoCaptura\`.
3. Delete `%APPDATA%\TeTengoCaptura\` (configuration) and `%LOCALAPPDATA%\TeTengoCaptura\` (outbox and logs). Pending events not yet sent are lost.
