# Changelog

Format based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/); the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Added
- Live view pre-warm: the control message `{"preparar":true}` (the app opened the camera screen) gets everything local ready for up to 60 s (PyAV and libx264 loaded and run once on a grey picture, the webcam frames flowing at the live rate with only the newest kept in memory, the last publish host resolved again) and `transmitir` then publishes that frame at once. No frame leaves the PC and no connection to MediaMTX is opened before `transmitir`; the warm state is dropped on timeout, pause, consent revocation, `transmitir:false` and when the channel closes. Agents without it ignore the message.
- `--marca-tiempo` and `[vista_en_vivo] marca_tiempo` (off by default): the capture time in epoch milliseconds drawn on the live view, to measure glass-to-glass latency.

### Changed
- Live view at 15 fps (`[vista_en_vivo] fps`, 1–30), taken from every webcam frame through `Captador`'s new `al_leer` hook instead of the 8 fps detection frames; the classifier's input (480p, 8 fps, JPEG 80) does not change. The frame is downscaled to 480p in the live view's thread and the skeleton is drawn from the latest pose. Frames keep a constant-rate grid (`Ritmo`): one per 1/15 s slot, slots skipped after a webcam stall.
- Live view encoder: H.264 Constrained Baseline (WebRTC-compatible), keyframe every 0.5 s with no extra scene-cut keyframes, peak bitrate capped at 1.5 Mbit/s; every publication starts with a keyframe.

### Pending
- Validate the unstable movement rule with our own recordings.
- Frame quality control, motion detection and backpressure.

## [0.3.0] - 2026-10-09

### Changed
- Release flow: release candidates and the tag at the end. A push to `release/*` or `hotfix/*` builds the installer and the disk image once and stores them as the GitHub pre-release `vX.Y.Z-rc.N` (the release candidate; `N` grows with every push), with `SHA256SUMS.txt` and notes that record the build number (`X.Y.Z+<run number>`), the commit, the git tree hash and the SHA-256 of every asset; the asset names carry the final version, never "rc". `staging` (environment `staging`) downloads the candidate, verifies it and uploads it to R2 `staging/`, then the pull request `release: x.y.z` lists the candidate, the staging links and the hashes. The new `produccion.yml` (replaces `etiquetar.yml`) runs on `main`: it takes the newest candidate whose tree equals main's (and that passed staging or was built with it off) and fails otherwise; `produccion` (environment `produccion`) verifies the SHA-256 and uploads the same files to the R2 root keys; only when that succeeded does it create the tag `vX.Y.Z` and the GitHub Release (CHANGELOG section, candidate id, hashes; the candidate's files attached with `ENABLE_DESKTOP_GITHUB_RELEASE`) and the back-merge pull request. A failed production job is re-run with the same candidate and leaves no tag. New `rollback.yml` (manual, environment `produccion`) puts an earlier release back on the R2 keys. `preparar` now also refuses a version whose tag exists. Scripts `.github/scripts/version.sh` and `descargar_candidata.sh`. `docs/RELEASES.md` has the new flow with a Mermaid diagram and a rollback section.
- Release flow: build once, deploy many, from the release branch. A push to `release/*` or `hotfix/*` runs `release.yml`: version check (`pyproject.toml` = `__version__`), lint and tests, the Windows installer and the macOS disk image built once as run artifacts, then `staging` (environment `staging`, approval; R2 `staging/te-tengo-captura-setup.exe` and `staging/te-tengo-captura.dmg`) and `produccion` (environment `produccion`, approval; the stable keys `te-tengo-captura-setup.exe` and `te-tengo-captura.dmg`, and a draft GitHub Release `v<version>` with the same binaries), each upload checked by downloading it, and finally the pull request `release: x.y.z` to `main`. The new `etiquetar.yml` runs on `main`: tag `v<version>`, the GitHub Release with the CHANGELOG section (publishing the approved draft only when it was built from the same file tree), and the back-merge pull request to `develop`; nothing is deployed from `main`. Switches `ENABLE_STAGING`, `ENABLE_WINDOWS_INSTALLER`, `ENABLE_MAC_DMG`, `ENABLE_MAC_NOTARIZE`, `ENABLE_DESKTOP_GITHUB_RELEASE`; secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`; variable `DESCARGAS_BASE_URL`. This repository now uploads its own binaries to R2 instead of the landing. `docs/RELEASE_WINDOWS.md` became `docs/RELEASES.md`.
- Release switches: organization Actions variables, explicit opt-in (`true` turns a channel on, unset means off). `ENABLE_DESKTOP_GITHUB_RELEASE` gates the `Draft GitHub Release` job of `release-windows.yml` (the installer summary says when it is off); `ENABLE_WINDOWS_INSTALLER` gates the `publicar-escritorio` dispatch of `notificar-landing.yml`, and a `desactivado` job writes a notice when it is off. Jobs that run still wait for an approval on `produccion`. Table in `docs/RELEASE_WINDOWS.md`.
- Release flow: a release merged into `main` is published after an approval on the `produccion` environment (required reviewers, `main` only). The new `notificar-landing.yml` sends `repository_dispatch` `publicar-escritorio` with `{ref, version}` (the commit SHA and the `pyproject.toml` version) to `te-tengo-landing-astro` when `CI` succeeds on a push to `main` (needs the `DISPATCH_TOKEN` secret; a notice without it). `release-windows.yml` runs on push to `main` instead of `v*` tags, checks that `pyproject.toml` and `__version__` match, and its `Draft GitHub Release` job runs in `produccion` and drafts `v<version>` on the released commit.

### Added
- macOS disk image: the PyInstaller spec builds `Te Tengo Captura.app` with its version, the camera permission text (`NSCameraUsageDescription`) and the entitlements of `packaging/macos/entitlements.plist`, signed ad-hoc, or with a Developer ID (hardened runtime, secure timestamp) when `TT_MACOS_IDENTIDAD_FIRMA` names one; `packaging/macos/crear-dmg.sh` packages it with `hdiutil`. `release.yml` builds it on an Apple Silicon runner, checks the bundled model and MediaPipe library, smoke-tests the app and the mounted image, and notarizes and staples it with `ENABLE_MAC_NOTARIZE`. README: «Testing on macOS».
- Windows installer and release workflow: Inno Setup script `packaging/te-tengo-captura.iss` (per user, no administrator rights, Spanish, Start menu shortcut, the same `Run` autostart value the agent writes, optional `/CONFIG=`, stops the running agent before upgrading or uninstalling, asks before deleting the data) and `Release Windows`, which builds, smoke-tests, optionally signs (Azure Artifact Signing or a PFX, inert without secrets), compiles and install/uninstall-tests the installer, and creates a draft GitHub Release on `v*` tags. Distribution options, SmartScreen and update notices: `docs/RELEASE_WINDOWS.md`.
- Live view on demand (T18, US-23): WebSocket control channel `/api/agente/transmision` (bearer token, `transmitir`/`modo` text messages, re-registers on `401`, reconnects at 1 s doubling up to 30 s and stops the stream when it closes); H.264 publishing with PyAV to the `urlPublicacion` the API sends (RTSP over TCP, `zerolatency`, one keyframe per second, no audio) from a worker thread with a two-frame queue that drops the oldest frame, so the capture loop never waits; modes `VIDEO`, `VIDEO_CON_POSTURA` and `SOLO_POSTURA` (skeleton in the brand colours from the landmarks already estimated, no camera pixels); publishing stops at once on `transmitir:false` or when capture is not allowed; the publish token is masked in the logs. Integration test against a MediaMTX container (skipped without Docker).
- `--sin-interfaz`: runs the agent (capture loop, heartbeat, outbox, remote thresholds) without pywebview or pystray until Ctrl+C or SIGTERM, logging each state change and writing no autostart entry; the API's end-to-end smoke test (`scripts/e2e.sh` in `te-tengo-general-api`) runs it with a URFD fall clip, locally and in CI.
- Installation guide: issuing the installation credential (`create-installation.sh`, demo `seed-demo.sh`), `config.toml` location per OS, sourced webcam placement, verifying the registration (log, app, API, database), troubleshooting by window state (screens 01–05 and the cases without a screen) and a local end-to-end test with a cropped URFD fall video.
- CI: separate lint/types and test jobs (coverage XML/HTML artifact and summary) before the Windows package, superseded runs cancelled; weekly pip-audit and OSV-Scanner scans of the locked dependencies; Dependabot, CODEOWNERS, issue and pull request templates, security policy and code of conduct.
- Detection core split into `te_tengo_deteccion` (classification, pose, clip buffer and MP4 encoding, unchanged logic) and the empty `te_tengo_captura` app package with the `te-tengo-captura` entry point; a test keeps the core free of app, GUI and network imports (T01).
- Documentation (T19): README for the agent (install, configure, run, package), `docs/architecture.md` with the component diagram of `te_tengo_captura`, and `docs/INSTALLATION.md` for the project team (configuration file, webcam position as in the validation, autostart, files and uninstall).
- Remote thresholds (T17): `GET /api/agente/configuracion` at startup and every hour (5 min after a failure); each field is validated on its own and applied over the installation's values, unknown or invalid fields are logged and ignored, and the capture thread switches to a fresh classifier.
- Packaging (T16): PyInstaller spec `packaging/te-tengo-captura.spec` (one-folder build with the MediaPipe model, its data files, the web UI and an icon drawn from the brand), `make empaquetar`, a `--autoprueba` smoke test (model, clip encoding, UI libraries and assets) and a `windows-latest` CI job that builds, smoke-tests and uploads the app.
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

### Fixed
- Detection parity with the validation: `scripts/comparar_pipelines.py` runs a dataset clip through `evaluar.py extraer` and through the agent's capture loop and compares every frame. The agent already matched (170 of 170 videos, same landmarks, phase and events); the `fall-01` miss of the end-to-end test came from the lossy `mp4v` crop of the installation guide, which now writes the RGB half losslessly (FFV1). `make camara` (`probar_camara.py`) now samples and compresses exactly like the agent, so it no longer reports falls the agent cannot see; MediaPipe's confidences no longer follow `[clasificacion] visibilidad_min`; `evaluar.py evaluar --pipeline agente` measures the agent's own poses; a test locks the parity.
- Found by running the real app under Xvfb with pywebview's Qt backend: the splash keeps the prototype's cadence even when startup is instant, has no light flash before painting, and on Linux Qt no longer picks OpenCV's bundled Qt plugins.

### Removed
- `notificar-landing.yml` (the `publicar-escritorio` dispatch to the landing and its `DISPATCH_TOKEN` secret) and `release-windows.yml`, replaced by `release.yml` and `etiquetar.yml`.
- Cloud ingestion service (ADR 0007, T02): FastAPI app, WebSocket ingestion and its protocol, `/health`, S3 clip storage, the provisional event publisher, the Docker image and CI job, `scripts/agente_simulado.py` and the `fastapi`, `uvicorn`, `boto3`, `websockets` and `httpx2` dependencies (`websockets` came back for the live view control channel). `ProcesadorCamara` moved to `te_tengo_captura/captura/procesador.py`.

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
