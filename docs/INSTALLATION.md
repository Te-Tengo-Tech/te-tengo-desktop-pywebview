# Installation guide (project team)

Te Tengo Captura is installed by the project team on the household PC, with a fixed configuration. The family does not configure anything on the PC: consent, pauses, room name and alerts are managed in the Te Tengo mobile app.

The steps in order:

1. Check the requirements.
2. Issue the credential.
3. Install the program.
4. Write `config.toml`.
5. Place the webcam.
6. Start the agent.
7. Verify the registration.

Section 8 explains each window state. Section 12 is a local end-to-end test recipe for developers.

## 1. What is needed

- A Windows 10 or 11 PC that stays on, with internet access.
- A USB webcam (the pilot uses a 1080p one; the agent works at 480p).
- The build of the agent: the `te-tengo-captura-windows` artifact of the CI `empaquetar` job, or `make empaquetar` on a Windows machine with the repository.
- The household already registered by the family in the mobile app (account, then household: US-01, US-04). The credential is issued for an existing household.
- The **installation credential** for this camera, issued by the team in `te-tengo-general-api` (section 2). It is secret: never write it in tickets, chats or logs.

## 2. Issue the installation credential

Each webcam has one installation credential. At startup the agent trades it for a per-camera token (`POST /api/agente/camaras/registro`, [AGENT_CONTRACT.md](AGENT_CONTRACT.md), "Registration"). The first registration creates the camera in the household with the room name of the configuration (CA-06.1). Later registrations with the same credential return the same `camaraId`.

### For a real household: `scripts/create-installation.sh`

In `te-tengo-general-api`:

```bash
# libpq connection variables of the target database
export PGHOST=… PGPORT=… PGDATABASE=… PGUSER=… PGPASSWORD=…
scripts/create-installation.sh <hogar-id>
```

The script:

- generates a random 32-byte credential (base64url);
- inserts a row in `instalaciones` with **only its SHA-256**;
- prints the credential **once**.

Copy the credential straight into `config.toml` (section 4); it cannot be shown again. If it is lost, run the script again: this inserts a new installation row.

To find the `hogar-id`, use either:

- the `hogarId` field of `GET /api/hogar` (the family's session, `docs/API_CONTRACT.md` of the API);
- or, with database access, this query:

  ```sql
  select id, adulto_mayor_nombre, adulto_mayor_direccion from hogares;
  ```

> **Open:** how the team issues credentials against the **production** database is not decided yet. The script needs direct database access. See `docs/BLOCKERS.md` of `te-tengo-general-api`, "T07 Installation credentials". There is also no endpoint to revoke a credential.

### For local tests only: `scripts/seed-demo.sh`

`scripts/seed-demo.sh [agent-config-output.toml]` seeds a **local** API (started with `./gradlew bootRun`) with the prototype's demo household. It creates:

- the demo account, using test values defined at the top of the script;
- the household of Rosa Huamán;
- the consent;
- one installation, with the same insert as `create-installation.sh`, run inside the compose PostgreSQL container.

With a path, it writes a complete agent configuration with the new credential. Without a path, it prints the credential. Every run issues a new credential. Never use it for a real household: it creates demo data. See section 12 for the full recipe.

## 3. Install the program

1. Unzip the `te-tengo-captura` folder to `%LOCALAPPDATA%\Programs\TeTengoCaptura\`.
2. The first time, Windows SmartScreen may warn that the program is not signed (`docs/BLOCKERS.md`, "Windows code signing"). Choose «Más información» → «Ejecutar de todas formas».
3. Optional: create a Start menu shortcut to `te-tengo-captura.exe`. Opening it again while it runs only shows its window.

## 4. Write the configuration file

Copy [`config.ejemplo.toml`](../config.ejemplo.toml) to the platform config directory with the name `config.toml`, or pass another path with `--config <path>`.

| OS | `config.toml` location |
|---|---|
| Windows | `%APPDATA%\TeTengoCaptura\config.toml` |
| macOS | `~/Library/Application Support/TeTengoCaptura/config.toml` |
| Linux | `~/.config/TeTengoCaptura/config.toml` |

These paths come from `platformdirs` with the app name `TeTengoCaptura` (`src/te_tengo_captura/config.py`, `ruta_predeterminada`); they are also listed at the top of `config.ejemplo.toml`. Fill in every field:

| Field | What to write |
|---|---|
| `api_url` | Base URL of `te-tengo-general-api` |
| `credencial_instalacion` | The installation credential of this camera (section 2) |
| `instalada_el` | Installation date (`2026-09-22`); shown as «Instalación» |
| `[webcam] indice` | OpenCV index of the webcam: `0` is the first one. If the PC also has a built-in camera, find the right index with `make camara ARGS="--listar-camaras"` from the repository (it saves a photo per camera) |
| `[webcam] nombre`, `especificacion` | How the window names the webcam, e.g. «Webcam USB HD (1080p)» and «USB · 1920 × 1080» |
| `[vivienda] nombre_adulto_mayor`, `direccion` | The household, as the family registered it in the app |
| `[camara] nombre_habitacion` | The room where the webcam is, e.g. «Sala». It is used on the first registration; afterwards the family renames it in the app (CA-06.2) |
| `[clasificacion]` | Leave it out. Without it the agent uses the thresholds validated in [validation.md](validation.md); change them only after re-validating |

If a field is missing or invalid, the agent does not start. It exits with code 2, and the log and the console say, in Spanish, which field to fix (`El archivo de configuración … está incompleto: Falta el campo «webcam.indice».`).

## 5. Place the webcam

The classifier was validated with the CAUCAFall dataset, recorded by a surveillance camera **elevated in a corner of a home** ([validation.md](validation.md), section 1). Its speed threshold was calibrated for that position. A threshold calibrated with a camera at body height (URFD) reached only 28% sensitivity on the elevated camera ([validation.md](validation.md), section 3.3). So place the webcam as in CAUCAFall:

- Mount the webcam **high in a corner** of the room (around 2 m), looking down and across the room.
- Frame the area where the older adult moves, **including the floor**. A fall is recognised when the body ends up horizontal or with the head below the feet.
- The **whole body** must be visible when standing: head, hips and ankles. Poses whose key points are not clearly visible cannot declare a recovery (adaptation A6), and frames without them are discarded (CA-15.2).
- Avoid backlight (a window behind the person) and very dark corners. If the person is not seen for 5 minutes, the agent sends `deteccion_no_confiable` and the family is told to check light and framing (CA-15.3).
- Never in a bathroom (desktop prototype, `docs/references/desktop-prototype/PRODUCT.md`, "Capabilities and Constraints").
- Use the same USB port every time: the window asks to reconnect the webcam there.

To check the framing, run `make camara` from the repository on that PC. It shows the skeleton and the three fall conditions live. The calibration depends on the camera location and must be repeated with the pilot recordings ([validation.md](validation.md), section 5).

## 6. First start

Start `te-tengo-captura.exe`. The splash shows «Iniciando…», «Abriendo la webcam configurada…» and «Conectando con Te Tengo…», then the status window appears. It should show «Enviando video · conectado», or «Esperando consentimiento» if the family has not registered consent yet. Any other state is explained in section 8.

Close the window: it stays in the tray, next to the clock, with a status dot (green sending, grey paused, amber problem). The first time, Windows shows «Te Tengo Captura sigue funcionando en segundo plano».

## 7. Verify that the agent registered

Check these, in order:

1. **Agent log** (section 9 gives the path). A good start has these lines, in Spanish:

   | Log line | Meaning |
   |---|---|
   | `Cámara registrada: <camaraId> (<habitación>)` | The credential was accepted and the camera exists in the household |
   | `Estado de captura: permitida=True motivo=None …` | Consent registered and no pause; `permitida=False motivo=SIN_CONSENTIMIENTO` or `motivo=EN_PAUSA` otherwise |
   | `Captura permitida: se abre la webcam` | The capture loop is running |
   | `Inicio con Windows registrado: …` | The autostart entry was written (packaged build only, section 10) |

2. **Mobile app** (the family's phone). The camera appears with the room name of the installation (CA-06.1) and «En línea» with the time of the last signal (CA-07.1). The agent sends a heartbeat every 30 s. The backend marks the camera `DESCONECTADA` after 3 missed heartbeats ([AGENT_CONTRACT.md](AGENT_CONTRACT.md), "Backend rules").

3. **API.** `GET /api/camaras` with a family member's token returns the camera with `estadoConexion: "EN_LINEA"` and a recent `ultimaSenal` (`docs/API_CONTRACT.md` of the API, section 4). Swagger UI is at `/swagger-ui.html`.

4. **Database** (if you have access). `instalaciones.camara_id` is set by the first registration:

   ```sql
   select i.id, i.camara_id, c.nombre_habitacion, c.estado_conexion, c.ultima_senal
   from instalaciones i left join camaras c on c.id = i.camara_id
   where i.hogar_id = '<hogar-id>';
   ```

   A `null` `camara_id` means the agent never registered with that credential.

## 8. Troubleshooting by window state

The window shows one state at a time, with this priority: webcam disconnected › no internet › waiting for consent › paused › sending. The order and copy come from `camState`, `health` and `trayState` in the prototype (`docs/references/desktop-prototype/src/core.js`), ported in `src/te_tengo_captura/estado.py`. The meanings below are the prototype's screen descriptions (`core.js`, list of screens).

| Screen | The window shows | Meaning (prototype) | What to check | Log |
|---|---|---|---|---|
| 01 | «Enviando video · conectado» (green) | Everything works | Nothing | `Evento … enviado` when an event goes out |
| 02 | «En pausa hasta las …» (grey stripes) | The family paused the camera from the app; nothing is processed until that hour, then it resumes on its own | Nothing. If nobody paused it, ask the family; pauses are only made and ended in the app (US-22) | `Estado de captura: permitida=False motivo=EN_PAUSA hasta=…` |
| 03 | «Esperando consentimiento» (amber) | Without the consent registered in the app, the webcam sends nothing | The family must complete the consent in the app (only the owner can register it); capture starts on its own (CA-05.1, CA-05.2) | `… motivo=SIN_CONSENTIMIENTO` |
| 04 | «Sin internet · reintentando en … s» (dark) | The webcam is still connected; sending resumes on its own when the connection returns | The PC's internet, then `api_url`. «Reintentar ahora» retries at once; otherwise retries wait 2 s, doubling up to 30 s (`latido.py`). Events made offline are kept in the outbox and sent later | `Sin conexión con Te Tengo: …`, later `Conexión con Te Tengo restablecida` |
| 05 | «Webcam desconectada: revisa el cable USB» (amber) | The USB webcam stopped answering; the app warns the family | The cable and the USB port; «Buscar de nuevo» reopens it. If the cable is fine, check `[webcam] indice` (`make camara ARGS="--listar-camaras"`) | `Webcam desconectada`, later `Webcam conectada` |

Cases the prototype has no screen for. Each is shown with an existing state (`docs/BLOCKERS.md`):

- **Rejected credential** (`401 CREDENCIAL_INVALIDA`): the window shows **04 «Sin internet»** and keeps retrying. The log says `Sin conexión con Te Tengo: POST /api/agente/camaras/registro → 401 CREDENCIAL_INVALIDA …`. Check that `credencial_instalacion` was copied exactly and that `api_url` points to the database where it was issued. If not, issue a new one (section 2).
- **Internal error in the capture loop:** the window shows **05 «Webcam desconectada»** while the loop restarts. The log says `Error en la captura; se reinicia en N s` with the traceback.
- **The agent does not start at all:** read the log. A configuration error names the field (section 4).
- **A second launch only shows a window:** this is expected; one agent at a time (section 11).

## 9. Files on the PC

| What | Windows | macOS | Linux |
|---|---|---|---|
| Configuration | `%APPDATA%\TeTengoCaptura\config.toml` | `~/Library/Application Support/TeTengoCaptura/config.toml` | `~/.config/TeTengoCaptura/config.toml` |
| Outbox and pending clips (`envios.sqlite3`, `clips/`, `estado_captura.json`) | `%LOCALAPPDATA%\TeTengoCaptura\` | `~/Library/Application Support/TeTengoCaptura/` | `~/.local/share/TeTengoCaptura/` |
| Logs (`te-tengo-captura.log`, 1 MB × 5, no secrets, no images) | `%LOCALAPPDATA%\TeTengoCaptura\Logs\` | `~/Library/Logs/TeTengoCaptura/` | `~/.local/state/TeTengoCaptura/log/` |

The macOS and Linux paths are the `platformdirs` defaults for the app name `TeTengoCaptura` (`src/te_tengo_captura/rutas.py`). `--datos <dir>` and `--logs <dir>` override them.

The only images ever written to disk are the clips of events, and only until they are uploaded. To check a build without a webcam, run `te-tengo-captura.exe --autoprueba --logs .`. It writes `te-tengo-captura.log` with one line per check and exits with 0 when all checks pass.

## 10. Start with the system

The window says «Se inicia con Windows»: the agent must start on its own when the household PC is turned on.

### Windows
Nothing to do. On every start, the packaged agent (`te-tengo-captura.exe`) writes or updates a per-user entry in the registry, once the configuration has loaded:

```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
  TeTengoCaptura = "C:\…\te-tengo-captura.exe"
```

- **Check it:** `reg query HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v TeTengoCaptura`.
- **Remove it** (uninstall): `reg delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v TeTengoCaptura /f`.

Nothing is written in these cases:

- the agent runs from source (`uv run te-tengo-captura`);
- the configuration is invalid;
- the registry cannot be written. The log then says `No se pudo registrar el inicio con Windows: …`.

The entry starts the agent when **this Windows user** signs in. The PC must sign in to that user after a restart.

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

## 11. Only one agent

Opening the program again (from the Start menu or a desktop shortcut) does not start a second agent: it shows the window of the one already running. The running agent holds a lock on `instancia.lock` in its data directory.

## 12. Local end-to-end test

This recipe runs the API, the demo household and the agent on one development machine. Instead of the webcam, the agent plays a URFD fall video. It needs:

- Docker (for the API's compose services);
- JDK 25;
- `jq`;
- `uv`;
- both repositories side by side.

**1. API** (terminal 1, in `te-tengo-general-api`):

```bash
./scripts/generate-keys.sh   # first time only: local RS256 keys in .claves/
./gradlew bootRun            # profile `local`: starts PostgreSQL and Floci (local AWS) from compose.yaml
```

Wait until `http://localhost:8080/actuator/health` answers `UP`.

**2. Demo household and agent configuration** (terminal 2, in `te-tengo-general-api`):

```bash
./scripts/seed-demo.sh ../te-tengo-desktop-pywebview/config.local.toml
```

This creates the demo account, the household, the consent and one installation, and writes `config.local.toml` with the new credential and `api_url = "http://localhost:8080"`. `config.local.toml` is git-ignored.

**3. A fall video** (in `te-tengo-desktop-pywebview`):

```bash
make instalar && make modelo
mkdir -p datos/urfd
curl -fL -o datos/urfd/fall-03-cam0.mp4 https://fenix.ur.edu.pl/~mkepski/ds/data/fall-03-cam0.mp4
```

You can also run `make datasets` to get both datasets (about 220 MB).

URFD MP4 files have the depth image on the left and the RGB image on the right (`scripts/evaluar.py`, `listar_videos`). The validation uses only the RGB half (`--recorte 320,0,320,240`). The agent's `--video` plays the whole frame. With the uncropped file, the classifier detects nothing, so crop the RGB half first:

```bash
uv run python - <<'EOF'
import cv2
src = cv2.VideoCapture("datos/urfd/fall-03-cam0.mp4")
fps = src.get(cv2.CAP_PROP_FPS)
out = cv2.VideoWriter("datos/urfd/fall-03-rgb.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))
while True:
    ok, frame = src.read()
    if not ok:
        break
    out.write(frame[0:240, 320:640])
out.release()
EOF
```

The output name does not end in `-cam0.mp4`, so `make validar` ignores it. Check that the cropped clip triggers a fall before starting the agent:

```bash
make camara ARGS="--video datos/urfd/fall-03-rgb.mp4 --sin-ventana"   # expect one `caida` event
```

URFD falls are detected in 23 of 30 videos ([validation.md](validation.md), section 3.1). If you pick another video, check it the same way. `make camara` can still disagree with the agent, so prefer `fall-03`: on `fall-01` `make camara` reports the fall, but in the agent MediaPipe finds the person in only about 1 frame in 10 and the agent misses the fall on the first pass of the video. With `fall-02` to `fall-06` the agent sends `caida` on the first pass; the automated test below uses `fall-03`.

**4. Agent** (terminal 3, in `te-tengo-desktop-pywebview`):

```bash
uv run te-tengo-captura --config config.local.toml --video datos/urfd/fall-03-rgb.mp4
```

Add `--sin-interfaz` to run it with no window nor tray (for example over SSH, or on a machine without a display). It then logs each state change (`Estado del agente: enviando`) and stops with Ctrl+C.

The video plays in a loop, in real time, instead of the webcam (`[webcam] indice` is ignored). Expected results:

- The window shows «Enviando video · conectado». The seed registered the consent, so capture is allowed.
- The log (macOS: `~/Library/Logs/TeTengoCaptura/te-tengo-captura.log`) shows:
  - `Cámara registrada`;
  - `Evento detectado: caida …`;
  - `Evento … enviado`;
  - about 6 s later, `Clip del evento … subido` (CA-18.1). The clip goes to Floci's S3 at `http://localhost:4566` (bucket `te-tengo-clips`).
- The fall repeats each time the video loops.

**5. Check the result in the API** (terminal 2). Sign in with the demo account defined at the top of `scripts/seed-demo.sh`, then list the cameras and the alerts:

```bash
API=http://localhost:8080
TOKEN=$(curl -s -X POST $API/api/sesiones -H 'Api-Version: 1' -H 'Content-Type: application/json' \
  -d "{\"correo\":\"$DEMO_CORREO\",\"contrasena\":\"$DEMO_CONTRASENA\"}" | jq -r .tokenAcceso)
curl -s $API/api/camaras -H 'Api-Version: 1' -H "Authorization: Bearer $TOKEN" | jq   # EN_LINEA
curl -s $API/api/alertas -H 'Api-Version: 1' -H "Authorization: Bearer $TOKEN" | jq   # a CAIDA alert
```

Export `DEMO_CORREO` and `DEMO_CONTRASENA` with the values from the script. The mobile app can sign in with the same account (`te-tengo-mobile-flutter`). Push needs a Firebase project, which is pending (`docs/BLOCKERS.md` of the mobile app). In each alert, `notificadaEn − ocurridaEn` is the backend side of the latency requirement of less than 10 s (CA-11.3, CA-16.1).

To try the other states, use the mobile app with the demo account:

- pause the camera → screen 02;
- revoke the consent → screen 03.

You can also stop the API → screen 04.

### Automated: `scripts/e2e.sh` in `te-tengo-general-api`

The same flow runs unattended as a smoke test of the agent ↔ API contract. From `te-tengo-general-api`, with this repository next to it:

```bash
./scripts/e2e.sh
```

The script:

- starts its own stack (compose project `tt-e2e`, API on 18080, PostgreSQL on 15432, Floci on 14566), so it runs while the steps above are running;
- seeds the demo household and registers a push device for the family;
- crops `fall-03` to its RGB half and holds the last frame 45 s, so the agent also sends `caida_confirmada`;
- runs this agent with `--sin-interfaz` and checks through the API, as the family, that:
  - a `CAIDA` alert is created and pushed;
  - the alert becomes `confirmada`;
  - its clip becomes `DISPONIBLE` and downloads from Floci;
- tears everything down, prints PASS or FAIL and the detection → push latency.

It takes about 1.5 minutes, plus the API build the first time. The agent's log is kept in the work directory that the summary prints. The API's `End-to-end` GitHub workflow runs the same script against a branch of this repository (see the API README).

## 13. Uninstall

1. «Salir» from the tray icon menu.
2. Remove the autostart entry (section 10) and delete `%LOCALAPPDATA%\Programs\TeTengoCaptura\`.
3. Delete `%APPDATA%\TeTengoCaptura\` (configuration) and `%LOCALAPPDATA%\TeTengoCaptura\` (outbox and logs). Pending events not yet sent are lost.

The installation credential stays valid in the backend until its `instalaciones` row is removed. There is no endpoint for this yet (`docs/BLOCKERS.md` of `te-tengo-general-api`, "T07 Installation credentials").
