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
- [ ] **T13 Tray icon and notifications** (screens 06–07).
  - pystray icon with the status dot (green sending, grey paused, amber problem; `trayState` in `core.js`); menu «Abrir Te Tengo Captura» and «Salir» (implementation choice: confirm the exit text with the team, see blockers).
  - System notification when the window is closed the first time and when the webcam disconnects with the window closed, with the texts of `osToast`.
  - Tray icon images generated from the brand SVG at build time or committed as PNG.
- [ ] **T14 Start with the system and single instance.**
  - Windows: a per-user `Run` registry entry (installer task or first run); macOS/Linux: document the LaunchAgent / autostart `.desktop` alternative.
  - A second launch focuses the running window instead of starting another agent.
- [ ] **T15 Logging and crash recovery.** Rotating log files in the platform log directory (no secrets, no frames); unhandled errors in the capture thread restart the loop and are shown as the "problem" state.

### Delivery
- [ ] **T16 Packaging.**
  - PyInstaller spec (`packaging/te-tengo-captura.spec`) including the MediaPipe model, `ui/web/` and the MediaPipe data files; one-folder build.
  - CI job on `windows-latest` that builds the app and uploads it as an artifact; a smoke test that runs the built exe with `--version`.
- [ ] **T17 Remote thresholds** (`GET /api/agente/configuracion`). Applied at startup and every hour (implementation choice); invalid values are ignored and logged.
- [~] **T18 Live view on demand** (US-23). Blocked: live view transport (see `docs/BLOCKERS.md`). Prepare a `TransmisorEnVivo` interface fed by the capture loop; no network implementation until the decision.
- [ ] **T19 Documentation.** Rewrite `README.md` for the agent (install, configure, run, package); update `docs/architecture.md` with a component diagram of `te_tengo_captura`; add `docs/INSTALLATION.md` for the project team (config file, webcam position as in the validation datasets, autostart).

## Local test checklist (for the team, after the cloud finishes)
Run on a real PC; these need hardware the cloud does not have.
1. `uv sync && make modelo && make revisar probar`.
2. `make validar` reproduces the numbers in `docs/validation.md` (the core did not change).
3. `uv run te-tengo-captura --backend-falso --config config.ejemplo.toml`: splash, then the status window in "Enviando".
4. Unplug the webcam → state 05 and, with the window closed, notification 07; plug it back → resumes alone.
5. Turn off Wi-Fi → state 04 with the countdown; «Reintentar ahora» works; events made offline arrive later.
6. With the real API running locally: consent missing → 03; pause from the mobile app → 02 and resumes at the hour.
7. Simulate a fall in front of the webcam → event and clip reach the API; the mobile app gets the push.
8. Build on Windows with PyInstaller; it starts with Windows and lives in the tray.
