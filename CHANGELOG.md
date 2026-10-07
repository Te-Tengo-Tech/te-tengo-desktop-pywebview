# Changelog

Format based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/); the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Added
- Detection core split into `te_tengo_deteccion` (classification, pose, clip buffer and MP4 encoding, unchanged logic) and the empty `te_tengo_captura` app package with the `te-tengo-captura` entry point; a test keeps the core free of app, GUI and network imports (T01).
- Work plan, agent contract, desktop prototype references and Claude Code cloud setup to build the agent autonomously (`AGENTS.md`, `docs/WORK_PLAN.md`, `.claude/`).

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
