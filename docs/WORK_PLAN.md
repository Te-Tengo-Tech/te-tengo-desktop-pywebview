# Work plan

The agent is built task by task from this checklist. An agent working autonomously follows **the loop** below until every task is checked or only blocked tasks remain. The goal for the cloud is an agent that is **complete except for what needs real hardware** (webcam, display, Windows); the team then tests it locally with the checklist at the end.

## The loop
1. **Sync:** `git pull --rebase` if a remote branch exists. Read `AGENTS.md`, this file and `docs/BLOCKERS.md`.
2. **Pick** the first unchecked task (`- [ ]`).
3. **Read:**
   - the stories and criteria it names in `docs/references/PRODUCT_BACKLOG.md`;
   - its endpoints in `docs/AGENT_CONTRACT.md`;
   - for UI tasks, **open every PNG listed** in `docs/references/desktop-prototype/screens/` and take the markup, copy and icons from `docs/references/desktop-prototype/src/core.js` and `app.css`.
4. **Implement** it following the layout and rules in `AGENTS.md`.
5. **Test:** unit tests per acceptance criterion; backend calls against the fake backend; time-based logic with an injected clock (never `sleep` in tests).
6. **Verify:** `make revisar probar` must pass. Never skip or weaken a test.
7. **Record:** check the task as `- [x]` here and add a line under `[Unreleased]` in `CHANGELOG.md`.
8. **Commit:** one Conventional Commit in English, no co-author line. Then **push**.
9. **Next:** go back to step 2 **without waiting for confirmation**.

**When something is missing** (a contract detail, a team decision, hardware):
- write it in `docs/BLOCKERS.md`;
- implement behind an interface with a fake;
- mark the task `- [~]` with a note, and continue.

**Stop only** when no `- [ ]` remains. Then:
- run everything once more;
- update `README.md` and `docs/architecture.md` to describe the agent as it now is;
- open or update a pull request with a summary, the blockers and the local test checklist below.

## Tasks

### Foundation
- [x] **T01 Split the code into the detection core and the app** (ADR 0007).
  - Move `clasificacion/`, `pose/`, the clip buffer (`ingesta/buffer.py`) and the encoder (`codificar_mp4`) into `src/te_tengo_deteccion/` without changing their logic; the existing tests move with them and must pass unchanged in substance.
  - Create the empty `src/te_tengo_captura/` package and a test that fails if `te_tengo_deteccion` imports `te_tengo_captura`, `webview`, `pystray` or `httpx`.
  - Update `scripts/evaluar.py`, `probar_camara.py` and `visor.py` imports; they must keep working.
  - Update `pyproject.toml` (packages, ruff `known-first-party`, coverage source, a `te-tengo-captura` script entry).
- [x] **T02 Retire the cloud ingestion service.**
  - Delete the rest of `ingesta/` (keep the orchestration of `ProcesadorCamara` for T07, e.g. as `te_tengo_captura/captura/procesador.py`), `salud/`, `main.py`, `eventos/` (replaced by `backend/` in T04), S3 storage, `Dockerfile`, `.dockerignore`, `scripts/agente_simulado.py` and `docs/ingestion-protocol.md`, and their tests.
  - Remove `fastapi`, `uvicorn`, `boto3`, `websockets`, `httpx2` if unused; drop the Docker job from CI.
  - Record the retirement in ADR 0007 ("Consequences") and in `CHANGELOG.md`.
- [x] **T03 Installation configuration.**
  - A TOML file written by the project team, read from the platform config directory (`platformdirs`, app name `TeTengoCaptura`) or from `--config <path>`.
  - Fields: `api_url`, `credencial_instalacion`, `[webcam] indice, nombre, especificacion`, `[vivienda] nombre_adulto_mayor, direccion`, `[camara] nombre_habitacion`, `instalada_el`, optional `[clasificacion]` overrides.
  - Defaults for the classifier come from the calibrated values in `docs/validation.md` (today `.env.example`), not from new numbers.
  - Clear Spanish error message naming the missing field; `config.ejemplo.toml` at the repo root; the old `.env`/`config.py` go away.
- [x] **T04 Backend client** (`docs/AGENT_CONTRACT.md`).
  - `ClienteBackend` (httpx, `Api-Version: 1`): `registrar`, `estado_captura`, `senal`, `publicar_evento`, `solicitar_subida_clip`, `subir_clip`, `configuracion`.
  - Re-registers on `401` (not `CREDENCIAL_INVALIDA`); maps `ProblemDetail.codigo` to typed exceptions; timeouts and no secrets in logs.
  - `BackendFalso` (in-memory, on `httpx.MockTransport`) that implements the whole contract; it is reused by every later test and by `--backend-falso` for local runs without the API.
- [x] **T05 Outbox for events and clips.**
  - SQLite in the platform data directory: pending events and clip files, sent with exponential backoff (cap and jitter are implementation choices; document them).
  - Idempotent resend by `eventoId`; survives restarts; clip files deleted after a successful upload.
  - Tests: offline → online delivers in order; duplicate response `200` counts as delivered.

### Capture and detection
- [x] **T06 Webcam source.**
  - `FuenteWebcam` over `cv2.VideoCapture(indice)` behind a `FuenteVideo` protocol; a `FuenteArchivo` (video file) and a `FuenteFalsa` (generated frames) for tests and demos.
  - Downscale to 480p, sample by time at 8 fps, JPEG quality 80 (same as validation).
  - Detects disconnection (read failures for N seconds; N is an implementation choice) and reconnection; "Buscar de nuevo" forces a reopen.
- [x] **T07 Capture loop** (US-05 CA-05.1/05.2, US-11 to US-15, US-18, US-21, US-22 CA-22.1/22.3).
  - frame → MediaPipe (VIDEO mode, monotonic ms) → `ClasificadorCinematico` → events with UUID v7 → outbox.
  - Clip: for the events in `EVENTOS_CON_CLIP` (`caida`, `movimiento_inestable`, as today), keep the 6 s before and the 6 s after (CA-18.1), encode MP4, enqueue the upload. If the clip fails, the event is still sent (CA-18.2).
  - Gate: only runs while `capturaPermitida`; when it turns false, stop, drop the buffer and reset the classifier.
  - Tests with `FuenteArchivo` or recorded poses: a fall sequence produces `caida` then `caida_confirmada`; a paused camera produces nothing.
- [x] **T08 Heartbeat and capture state** (US-07 CA-07.1/07.2/07.3).
  - Heartbeat every 30 s with `webcamConectada` and `deteccionConfiable`; its response updates `capturaPermitida`, `pausadaHasta` and `nombreHabitacion`.
  - Offline handling: state "sin internet" with the retry countdown shown in the UI; "Reintentar ahora" retries at once.
- [x] **T09 Agent state model** (`estado.py`).
  - One immutable `EstadoAgente` derived from: webcam connected, internet, consent, pause, last successful send. Its priority order and texts follow `camState`, `health` and `trayState` in `src/core.js`.
  - Serializes to the JSON the web UI consumes (same fields as `baseState()` in `core.js`, plus the household and webcam data from the config).
  - Table-driven tests covering the five states and their priority.
- [x] **T10 Encode clips without a system FFmpeg.**
  - The packaged Windows app cannot rely on `ffmpeg` in `PATH`. Replace the subprocess with PyAV (its wheels bundle FFmpeg) or another option that works in PyInstaller on Windows, macOS and Linux; write ADR 0008.
  - Keep H.264, even dimensions and `yuv420p`; test that the output opens and has the expected frame count.

### Desktop UI
- [x] **T11 Status window** (screens 01–05).
  - `ui/web/`: `index.html`, `app.css` (tokens and components from the prototype's `app.css`, only what the window uses), `app.js` (port of `scrEstado`, `health`, `camState`, `roomSVG`, the icon set and the brand SVGs from `core.js`), fonts copied from `docs/references/desktop-prototype/fonts/` (OFL).
  - Window 960 × 640, not resizable, frameless with the prototype's 36 px title bar (minimize, disabled maximize, close). Close and minimize hide to the tray; they never stop the agent.
  - Bridge (`js_api`): `estado()`, `minimizar()`, `cerrar()`, `buscarWebcam()`, `reintentarAhora()`; Python pushes updates with `window.evaluate_js("ttg.actualizar(...)")`.
  - The retry countdown updates without moving focus; `role="status"`; `prefers-reduced-motion` respected.
  - Tests: the bridge object without pywebview; a test that the HTML references only local assets.
- [x] **T12 Splash window** (screen 00). 480 × 300, frameless, centered, `--morado`, the animated symbol, `BOOT_STEPS` driven by real startup steps (config, webcam, backend), version from the package, about 2.2 s minimum, then the status window.
- [x] **T13 Tray icon and notifications** (screens 06–07).
  - pystray icon with the status dot (green sending, grey paused, amber problem; `trayState` in `core.js`); menu «Abrir Te Tengo Captura» and «Salir» (implementation choice: confirm the exit text with the team, see blockers).
  - System notification when the window is closed the first time and when the webcam disconnects with the window closed, with the texts of `osToast`.
  - Tray icon images generated from the brand SVG at build time or committed as PNG.
- [x] **T14 Start with the system and single instance.**
  - Windows: a per-user `Run` registry entry (installer task or first run); macOS/Linux: document the LaunchAgent / autostart `.desktop` alternative.
  - A second launch focuses the running window instead of starting another agent.
- [x] **T15 Logging and crash recovery.** Rotating log files in the platform log directory (no secrets, no frames); unhandled errors in the capture thread restart the loop and are shown as the "problem" state.

### Delivery
- [x] **T16 Packaging.**
  - PyInstaller spec (`packaging/te-tengo-captura.spec`) including the MediaPipe model, `ui/web/` and the MediaPipe data files; one-folder build.
  - CI job on `windows-latest` that builds the app and uploads it as an artifact; a smoke test that runs the built exe with `--version`.
- [x] **T17 Remote thresholds** (`GET /api/agente/configuracion`). Applied at startup and every hour (implementation choice); invalid values are ignored and logged.
- [x] **T18 Live view on demand** (US-23). Unblocked by the decision of 2026-10-07 (MediaMTX, `docs/AGENT_CONTRACT.md`, "Live view"). Control channel `backend/transmision.py` (`CanalTransmision`: WebSocket `/api/agente/transmision`, bearer token, re-register on `401`, reconnect with backoff); `captura/en_vivo.py` (`TransmisionEnVivo`: bounded queue that drops the oldest frame, worker thread, closes at once on `transmitir:false` or when capture is not allowed); `captura/publicador.py` (H.264 with PyAV over RTSP/TCP, `zerolatency`, GOP 1 s); `captura/postura.py` (modes `VIDEO`, `VIDEO_CON_POSTURA`, `SOLO_POSTURA` without camera pixels). No «en vivo» indicator in the window: the prototype has no copy for it (see `docs/BLOCKERS.md`).
- [x] **T19 Documentation.** Rewrite `README.md` for the agent (install, configure, run, package); update `docs/architecture.md` with a component diagram of `te_tengo_captura`; add `docs/INSTALLATION.md` for the project team (config file, webcam position as in the validation datasets, autostart).
- [x] **T20 Live view v3** (US-23, approved on 2026-10-09). Live view at 15 fps (configurable) from every webcam frame, independent of the validated 8 fps detection sampling, with the skeleton from the latest pose; H.264 Constrained Baseline with a keyframe every 0.5 s and the first frame of every publication a keyframe (WebRTC playback); `{"preparar":true}` pre-warm for up to 60 s with no frame leaving the PC before `transmitir`; `--marca-tiempo` debug overlay for glass-to-glass measurements.

### PCs, cameras and movement data (change request «PCs, cámaras y datos de movimiento», US-28 to US-39)
Pending the advisor's approval; built ahead of it, additively: an installation with `config.toml` keeps working. Contract: `docs/AGENT_CONTRACT.md` (PC link, cameras of a linked PC, movement data, activity log). Design: the synthesized desktop prototype (`docs/references/desktop-prototype/`) and the brief (`docs/references/BRIEF-pcs-camaras-y-movimientos.md`).
- [x] **T21 Synthesized window** (screens 00–09, 20, 23). The Te Tengo brand kit (cream, violet and coral, Poppins bundled, two figures hugging in the app and tray icons); tabs Estado · Cámaras; one summary band and one row per camera; «Datos de la instalación» folded; the live view indicator (summary band, violet tray dot, system notice); «Cámaras» with each webcam and a preview only seen on this PC.
- [x] **T22 PC link** (US-28, US-31; CA-28.1–28.7, CA-31.1–31.6). RFC 8628 client (`vinculacion/`): code with QR and countdown, polling that honours `slow_down`, `expired_token`, `invalid_grant` and `access_denied`, the tokens in the OS credential store (`keyring`), silent renewal with the rotating refresh token, `401 PC_DESVINCULADA`/`invalid_grant`/`{"desvincular":true}` → stop, wipe, code again; «Desvincular» with «Borrar también los datos de esta PC», revoked offline later; the PC's heartbeat and control channel; installations keep working and are unlinked the same way.
- [x] **T23 Cameras of a linked PC** (US-29, US-30; CA-29.1–29.10). Inventory by the OS unique id (`PUT …/camaras/inventario` at start and on plug/unplug), the owner's assignments followed on the PC's channel (`{"camara":…}`, `{"buscarCamaras":true}`, `GET …/camaras` after reconnecting), one agent per camera in use (own capture loop, MediaPipe landmarker, heartbeat, outbox, clips, live view on its own path and channel, token), camera tokens renewed after the PC's, previews of webcams «sin usar» (CA-29.7) with the violet light, the local preview of «Cámaras», «Elegir aquí» (CA-29.8, last change wins: CA-29.10).
- [x] **T24 Advanced mode, activity and diagnostic** (US-32, US-33, US-34; CA-32.1–32.4, CA-33.1–33.4, CA-34.1–34.3). «Avanzado» tab, off by default; per-camera live log in plain language (logging handler → in-memory ring buffer, filters, search, pause, «Ver línea técnica» with «Copiar»); meters (fps, CPU, analysis time, person, key points' visibility, M1–M3 against their thresholds, the phase with the 1.48 s and 30 s timers, the skeleton, the reason when there is nothing to measure); the PC's activity log (`actividad.jsonl`, append-only, «Pendiente de enviar», `POST /api/agente/pc/actividad`); «Exportar diagnóstico» (logs, version, system, cameras and rooms, thresholds; no secrets, images or landmarks; no half file).
- [x] **T25 Local storage** (US-38, US-35; CA-38.1–38.5, CA-35.3–35.4). `almacen/`: movements as Parquet+zstd (33 points quantized, delta-encoded; θ, P, v, phase, event), one file per camera per 5 min; continuous video (off by default) H.264 480p 8 fps in 10-min fragmented MP4 parts; local copies of clips; AES-256-GCM at rest with the key in the OS credential store; SQLite index; retention per type and the space limit (oldest video first, then movements); gated by `GET /api/agente/movimientos/estado`, with the delete-or-keep question after a revocation; «Almacenamiento» sub-tab.
- [x] **T26 Movements in the cloud and clip landmarks** (US-37, US-36; CA-37.1–37.3, CA-36.1–36.2). `envios/movimientos.py`: the lowest outbox lane, the three-step upload with SHA-256 and rows, offline buffering in the encrypted folder, `409`/`422` handling, consent re-checked on `409`; a clip's 12 s of landmarks after its clip (`POST …/clip/puntos`). Verified end to end against the local API (consent, 30-day retention, clip landmarks URL in the app, upload after restart).
- [x] **T27 «Ver qué pasó» on the PC** (US-39; CA-39.2–39.5 on the PC). `almacen/repeticion.py` (window, events, stretches without data, poses in chunks, video frames from the encrypted segments) and the replay panel of the prototype (screens 54–59).
- [x] **T28 Light replay files** (US-36, US-39; backend ADR 0011, contract «Light replay format»). `almacen/ligero.py`: TTMOV v1 (gzip, 24-byte header, per frame `dtMs`, state byte and the 33 landmarks' x, y and visibility as deltas, the Parquet file's integers), written from the same rows next to each 5-minute Parquet file (encrypted, counted, uploaded and deleted with it) and each clip's landmarks; uploaded right after its Parquet file (`…/{archivoId}/ligero`, `…/ligero/confirmacion`, `…/clip/puntos/ligero`; an older API's `404` uploads the Parquet file only). Golden fixture from a real 12 s clip (`tests/fixtures/clip_caida.*`, `scripts/fixture_ligero.py`) for the app's decoder.

### Maintenance
- [x] **T29 Updates of the agent** (US-43; CA-43.1–43.3, CA-43.7–43.9; contract «Updates (US-43)»). `actualizaciones/`: `GET /api/versiones` without a token at start, daily and on demand; Windows download with a disk space check, SHA-256 verification and the silent Inno Setup install with `/RELANZAR` (the installer waits for the agent's named mutex and reopens it); waits during a fall alert, a live view or a preview; «Actualizar automáticamente» at 03:00 (on by default, in the heartbeat and the activity log); `PC_ACTUALIZADA` after a newer version starts; macOS only opens the downloads page. Band, «Acerca de», «Qué cambió», Mac steps, tray menu and one notice per version (screens 65–86). Real Windows install and relaunch: blocker.

## Local test checklist (for the team, after the cloud finishes)
Run on a real PC; these need hardware the cloud does not have.
1. `uv sync && make modelo && make revisar probar`.
2. `make validar` reproduces the numbers in `docs/validation.md` (the core did not change).
3. `uv run te-tengo-captura --backend-falso --config config.ejemplo.toml`: splash, then the window's «Estado» tab with «Te Tengo cuida la sala».
4. Unplug the webcam → state 05 and, with the window closed, notification 07; plug it back → resumes alone. Open «Cámaras»: the preview shows the real image, only on this PC.
5. Turn off Wi-Fi → state 04 with the countdown; «Reintentar ahora» works; events made offline arrive later.
6. With the real API running locally: consent missing → 03; pause from the mobile app → 02 and resumes at the hour.
7. Simulate a fall in front of the webcam → event and clip reach the API; the mobile app gets the push.
8. Build on Windows with PyInstaller; it starts with Windows and lives in the tray.
9. With the API's local compose (API + MediaMTX) and the mobile app: open the live view → the app plays the webcam within a few seconds; switch to «solo postura» → only the skeleton on the purple background; pause the camera from the app → the stream stops at once.
10. Open the camera screen of the app and wait: the agent logs «Vista en vivo: preparada» and MediaMTX shows no connection from the agent until the live view starts; with `--marca-tiempo`, compare the time drawn on the picture with a clock to measure the glass-to-glass latency.
11. PC link with the real API (local compose from `te-tengo-general-api` `develop`): start with no `config.toml` and `--api-url http://localhost:8080`; scan the QR with the phone (camera app and the app's scanner) and approve; the window says «Vinculada a la casa de …» and the app lists the PC «En línea»; remove it from the app → «Esta PC se quitó…» at once; «Desvincular» with and without «Borrar también los datos…». On Windows check the entries in Credential Manager («TeTengoCaptura»).
12. Cameras of a linked PC with the real API and the phone: plug two webcams; the app's «Elige las cámaras» lists both; assign them to two rooms → both rows appear in «Estado» with «En línea»; unplug one → «Desconectada» and its room stays; plug a third one before the others and reboot → each room keeps its camera; «Ver vista previa» in the app → the violet light on the PC; «Elegir aquí» on the PC → the app shows the room. On Windows repeat with the cameras on different USB ports.
13. Advanced mode on a real camera: switch it on (the app's activity shows «Desde la PC …: se activó el modo avanzado»), walk in front of the camera and sit down on the floor: the log says «Persona detectada…», «La cadera bajó rápido…», «Posible caída…», «Caída…», and «Medidores» moves through the phases with the 1.48 s window and the 30 s count. Export the diagnostic and check the zip has no token (search the API's tokens in it) and no image.
14. Updates on a real Windows PC with a published version newer than the installed one (`GET /api/versiones` of the local API): the band and the tray dot appear; «Descargar» shows the progress, «Verificando la descarga…» and «Reiniciando para actualizar…»; the agent closes, the installer runs silently and the new version opens with «Terminando la actualización…» and «Te Tengo Captura se actualizó a X», still linked, with its cameras and data; «Actividad» shows «Esta PC se actualizó a X». Repeat with a wrong `sha256` (nothing installed), during a live view from the app (it waits, then goes on), and with «Actualizar automáticamente» at 03:00 (change the PC's clock).
