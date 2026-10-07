# Changelog

Format based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/); the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Added
- Detection core split into `te_tengo_deteccion` (classification, pose, clip buffer and MP4 encoding, unchanged logic) and the empty `te_tengo_captura` app package with the `te-tengo-captura` entry point; a test keeps the core free of app, GUI and network imports (T01).
- Logging and crash recovery (T15): rotating log files (1 MB × 5) in the platform log directory with a filter that masks the credential and the token, unhandled exceptions in any thread logged, and a capture loop that survives errors (reset and retry at 1 s doubling up to 30 s, shown as the webcam problem state meanwhile).
- Start with the system and single instance (T14): per-user `Run` registry entry written by the packaged agent on Windows, LaunchAgent and autostart `.desktop` documented in `docs/INSTALLATION.md`; a second launch shows the running agent's window (OS file lock plus a loopback socket with a token).
- Tray icon and notifications (T13): pystray icon drawn with Pillow from the brand app icon with the `trayState` dot (green, grey, amber), tooltip, menu «Abrir Te Tengo Captura» (default) and «Salir» (placeholders, see blockers); system notifications of `osToast` the first time the window is closed and when the webcam disconnects with the window closed.
- Splash window (T12): 480 × 300, frameless and centered in `--morado` with the animated symbol; `BOOT_STEPS` follow the real startup (threads, webcam, first heartbeat) with a 5 s limit per step and at least 2.2 s in total; the version comes from the package. Chromium screenshot matches screen 00.
- Status window (T11): pywebview window of 960 × 640, frameless with the prototype's title bar, that hides to the tray on close or minimize; `ui/web/` port of the prototype (tokens, icons, brand, room illustration, Atkinson Hyperlegible fonts under OFL); JS bridge `estado`, `minimizar`, `cerrar`, `buscarWebcam`, `reintentarAhora`; in-place updates so the countdown never moves focus; the `Agente` composition root and `--backend-falso`, `--video`, `--modelo` and `--datos` options. Chromium screenshots match screens 01–05.
- Clip encoding with PyAV (T10, ADR 0008): H.264 MP4 in `yuv420p` with even dimensions, without an `ffmpeg` executable; FFmpeg is no longer installed in CI.
- Agent state model (T09): immutable `EstadoAgente` with the priority and verbatim copy of `camState`, `health`, `trayState` and `osToast`, serialized to the JSON of `baseState()` plus the household and webcam data.
- Heartbeat and capture state (T08): `POST /api/agente/senal` every 30 s and at once when the webcam state changes; the answer updates consent, pause and room name; offline retries at 2, 4, 8, 16 then 30 s with a countdown and «Reintentar ahora»; the last capture state is stored on disk and a pause ends on its own at its hour.
- Capture loop (T07): frame → MediaPipe (VIDEO mode, in the capture thread) → classifier → events with UUID v7 → outbox; 6 s + 6 s clips for `caida` and `movimiento_inestable` encoded off the loop thread (the event is sent even if the clip fails); consent and pause gate that closes the webcam, drops the clip buffer and resets the classifier. Replaces the old async `ProcesadorCamara`.
- Video sources (T06): `FuenteWebcam`, `FuenteArchivo` and `FuenteFalsa` behind `FuenteVideo`; `Captador` downscales to 480p, samples at 8 fps and compresses at JPEG quality 80 like the validation, detects disconnection after 3 s of failed reads, reopens every 2 s and supports «Buscar de nuevo».
- Persistent outbox (T05): SQLite in the platform data directory for events and clip files, in-order delivery, idempotent resend by `eventoId`, exponential backoff (2 s doubling, 300 s cap, equal jitter), clip files deleted after upload, and a sender thread.
- Backend client for the agent contract (T04): `ClienteBackend` (httpx, `Api-Version: 1`, re-registers on `401`, typed errors per `ProblemDetail.codigo`, no secrets in logs) and the in-memory `BackendFalso` on `httpx.MockTransport`.
- Installation configuration (T03): TOML file in the platform config directory or `--config`, with `config.ejemplo.toml`, calibrated classifier defaults and Spanish errors naming the missing field. Replaces `.env`, `pydantic-settings` and `scripts/crear_env.py`.
- Work plan, agent contract, desktop prototype references and Claude Code cloud setup to build the agent autonomously (`AGENTS.md`, `docs/WORK_PLAN.md`, `.claude/`).

### Removed
- Cloud ingestion service (ADR 0007, T02): FastAPI app, WebSocket ingestion and its protocol, `/health`, S3 clip storage, the provisional event publisher, the Docker image and CI job, `scripts/agente_simulado.py` and the `fastapi`, `uvicorn`, `boto3`, `websockets` and `httpx2` dependencies. `ProcesadorCamara` moved to `te_tengo_captura/captura/procesador.py`.

### Pending
- Validate the unstable movement rule with our own recordings.
- Frame quality control, motion detection and backpressure.
- Forwarding the video to the Live Streaming Service.

## [0.2.0] - 2026-10-03

### Added
- Validation with URFD and CAUCAFall (`scripts/descargar_datasets.py`, `scripts/evaluar.py`, `make datasets`, `make validar`) and report in `docs/validation.md`: sensitivity 81.2%, specificity 81.1%, accuracy 81.2%.
- Test tools with webcam or video: `make camara` and `make agente`.
- Adaptation A7: the head below the feet indicates a fall toward the camera.
- Adaptation A8: recovery requires 1 s upright.

### Changed
- MediaPipe in VIDEO mode with one tracker per camera (ADR 0006).
- Signed descent speed, 1 s window and only with visible points (A3, A6).
- Calibrated speed threshold (0.01) in `.env.example`.

### Fixed
- Clips from 16:9 webcams with an odd width.
- False recoveries caused by single-frame MediaPipe errors.

## [0.1.0] - 2026-10-03

### Added
- Project structure by domain (`ingesta`, `pose`, `clasificacion`, `eventos`, `clips`, `salud`).
- Ingestion WebSocket `/v1/ingesta/{camara_id}` with a token and the binary protocol `[instante][JPEG]`.
- Pose estimation with MediaPipe 0.10.35 in a separate process.
- Classification with the thresholds of Chen et al. (2020): fall, confirmed fall (30 s), recovery, unstable movement (proposal) and unreliable detection (5 min).
- Clip buffer from 6 s before to 6 s after, MP4 encoding with FFmpeg and encrypted upload to S3.
- Event publishing to the Backend API (provisional contract).
- Tooling: uv, Ruff, strict mypy, pytest, pre-commit, multi-stage Dockerfile and GitHub Actions.
- Documentation: internal architecture, classification specification, ingestion protocol and ADR 0001–0005.
