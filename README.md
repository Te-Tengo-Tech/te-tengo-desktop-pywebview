# te-tengo-desktop-pywebview

[![CI](https://github.com/Te-Tengo-Tech/te-tengo-desktop-pywebview/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Te-Tengo-Tech/te-tengo-desktop-pywebview/actions/workflows/ci.yml)
[![Dependency audit](https://github.com/Te-Tengo-Tech/te-tengo-desktop-pywebview/actions/workflows/audit.yml/badge.svg)](https://github.com/Te-Tengo-Tech/te-tengo-desktop-pywebview/actions/workflows/audit.yml)
[![OSV-Scanner](https://github.com/Te-Tengo-Tech/te-tengo-desktop-pywebview/actions/workflows/osv-scanner.yml/badge.svg)](https://github.com/Te-Tengo-Tech/te-tengo-desktop-pywebview/actions/workflows/osv-scanner.yml)

**Te Tengo Captura**, the household agent of **Te Tengo**, a system that detects falls of older adults at home. It runs on the household PC, which stays on, and:

- opens the configured USB webcam;
- estimates the pose with **MediaPipe on the PC's CPU** and classifies the movement with the validated **kinematic classifier**, without training models;
- sends only **events and 6 s + 6 s clips** to the backend (`te-tengo-general-api`), never a continuous video stream;
- shows the state of the webcam in a small window and in the system tray.

The family manages consent, pauses, the room name and alerts in the Te Tengo mobile app. The agent has no settings screen: the project team installs it with a fixed configuration file.

> **Contributors and coding agents:** the rules are in [AGENTS.md](AGENTS.md), the backend contract in [docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md), the work plan in [docs/WORK_PLAN.md](docs/WORK_PLAN.md) and the open questions in [docs/BLOCKERS.md](docs/BLOCKERS.md).

## How it works

```
USB webcam → 480p · 8 fps · JPEG 80 → MediaPipe Pose (VIDEO mode) → kinematic classifier
                                                                        │ caida, caida_confirmada,
                                                                        │ movimiento_inestable,
                                                                        ▼ recuperacion, deteccion_no_confiable
 window + tray ◄── agent state ◄── heartbeat (consent, pause) ◄──► te-tengo-general-api ◄── persistent outbox (events + clips)
```

- **Consent and pauses are hard gates:** without consent, or while the family has paused the camera, the webcam is closed and nothing is classified or buffered (CA-05.2, CA-22.1). Capture resumes on its own (CA-22.3).
- **No event is lost:** events go to a SQLite outbox first and are sent with retries; `eventoId` (UUID v7) makes resending safe. Clips are deleted after upload.
- **Offline:** the window shows «Sin internet · reintentando en N s»; events made offline arrive later.

Details: [docs/architecture.md](docs/architecture.md). Formulas and sources: [docs/classification-spec.md](docs/classification-spec.md).

| Package | Contents |
|---|---|
| [`src/te_tengo_deteccion/`](src/te_tengo_deteccion) | Validated detection core: classification, pose, clip buffer and MP4 encoding. Pure Python, no GUI, no network |
| [`src/te_tengo_captura/`](src/te_tengo_captura) | The desktop agent: configuration, capture loop, backend client, outbox, heartbeat, window (pywebview) and tray (pystray) |
| [`scripts/`](scripts) | Validation with datasets and the webcam test tool |

## Requirements

| Tool | Version |
|---|---|
| Python | 3.11 (required by `mediapipe==0.10.35`) |
| [uv](https://docs.astral.sh/uv/) | 0.12 or later |
| OS | Windows 10/11 for the pilot. It also runs on macOS and Linux (on Linux pywebview needs GTK or Qt, and pystray needs a tray) |

No system FFmpeg is needed: clips are encoded with PyAV ([ADR 0008](docs/adr/0008-clip-encoding-with-pyav.md)).

## Getting started

```bash
make instalar                          # uv sync + pre-commit hooks
make modelo                            # downloads pose_landmarker_lite.task into models/
uv run te-tengo-captura --backend-falso --config config.ejemplo.toml
```

`--backend-falso` runs the agent against an in-memory backend that implements the whole contract, so the window shows «Enviando» without the API. Other options:

| Option | Purpose |
|---|---|
| `--config <path>` | Installation file (default: `config.toml` in the platform config directory) |
| `--backend-falso` | In-memory backend instead of `te-tengo-general-api` |
| `--video <file>` | Play a video in a loop instead of the webcam (demos) |
| `--modelo <path>` | MediaPipe model (default: `models/pose_landmarker_lite.task`, or the one bundled in the build) |
| `--datos <dir>`, `--logs <dir>` | Data (outbox, pending clips) and log directories |
| `--autoprueba` | Check the model, clip encoding and UI libraries, then exit (smoke test of a build) |
| `--version` | Print the version |

## Configuration

The project team writes a fixed TOML file: `%APPDATA%\TeTengoCaptura\config.toml` on Windows (platform config directory, app name `TeTengoCaptura`), or `--config <path>`. Every field is documented in [config.ejemplo.toml](config.ejemplo.toml): API URL, installation credential, webcam index and name, household, room and installation date. Without a `[clasificacion]` table, the agent uses the calibrated thresholds of [docs/validation.md](docs/validation.md). A missing field stops the agent with a Spanish message naming it. The backend can adjust thresholds remotely (`GET /api/agente/configuracion`, hourly).

Installing on a household PC (installation credential, configuration, webcam position, verification, troubleshooting, autostart and a local end-to-end test): [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Commands

| Command | What it does |
|---|---|
| `make instalar` | Installs the dependencies (`uv sync`) and the pre-commit hooks |
| `make modelo` | Downloads the MediaPipe model |
| `make revisar` | Lint (Ruff), formatting and types (mypy in strict mode) |
| `make probar` | Tests with coverage (pytest) |
| `make formatear` | Formats the code with Ruff |
| `make empaquetar` | Builds the one-folder app with PyInstaller into `dist/te-tengo-captura/` |
| `make camara` | Tests the classifier with the webcam or a video, with an on-screen overlay |
| `make datasets`, `make validar` | Downloads URFD and CAUCAFall and validates the classifier |

## Packaging

```bash
uv sync --group empaquetado && make modelo
uv run pyinstaller packaging/te-tengo-captura.spec --noconfirm
dist/te-tengo-captura/te-tengo-captura --autoprueba --logs .
```

The spec bundles the model, MediaPipe's data files and the web UI, and draws the icon from the brand. CI builds it on `windows-latest`, runs `--version` and `--autoprueba`, and uploads the folder as the `te-tengo-captura-windows` artifact. On Windows the agent registers itself to start when the user signs in, and a second launch only shows the running window.

## Testing with the webcam or videos

`make camara` opens the webcam or a video and runs the same classifier as the agent. It draws the skeleton, the center line, the hip center and the body box, plus a panel with the phase, the three fall conditions and the events. Keys: `q` quit, `r` reset, `c` screenshot.

```bash
make camara ARGS="--camara 0"                        # webcam, with the calibrated threshold
make camara ARGS="--listar-camaras"                  # saves a photo per camera to find the index
make camara ARGS="--video fall-01-cam0.mp4 --recorte 320,0,320,240 --csv mediciones.csv"
```

On macOS, give camera permission to the terminal the first time. An iPhone works as a camera through Continuity Camera.

## Validation with public datasets

The classifier was validated with **URFD** (70 videos) and **CAUCAFall** (100 videos) under production conditions: 480p, 8 fps, JPEG and MediaPipe in VIDEO mode, leaving each group out during calibration:

| Sensitivity | Specificity | Accuracy | False recoveries |
|---|---|---|---|
| **81.2%** | **81.1%** | **81.2%** | 0 of 30 |

Protocol, results per activity and limitations: [docs/validation.md](docs/validation.md). The agent did not change the classifier; to reproduce: `make datasets && make validar`.

## Tests

`make revisar probar` runs everything without a webcam or a display: fake video sources, the fake backend on `httpx.MockTransport`, an injected clock, and stand-ins for the `webview` and `pystray` modules. Where Node.js, Playwright and Chromium are available, the tests also render the window and the splash and compare them pixel by pixel with the prototype screens in `docs/references/desktop-prototype/screens/`. What needs real hardware is in the local test checklist of [docs/WORK_PLAN.md](docs/WORK_PLAN.md).

## Status

Version 0.2.0. The agent is complete except for what needs real hardware (webcam, display, Windows packaging run) and the live view, which waits for the transport decision. Open items: [docs/BLOCKERS.md](docs/BLOCKERS.md). Changes: [CHANGELOG.md](CHANGELOG.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md): Conventional Commits, branches and review before merging.

---

Thesis project, Software Engineering, Universidad Peruana de Ciencias Aplicadas (UPC). Authors: Jhosepmyr Gutierrez Soto and Elmer Riva Rodriguez.
