# te-tengo-desktop-pywebview

**Te Tengo Captura**, the household agent. Today it holds the **validated detection module** (MediaPipe, kinematic classification and clips) and its validation tools. The desktop application (pywebview) will be built here. It will **process the video on the PC** and send only events and clips to the backend.

> **Migration status (ADR 0007):** the code started as a cloud service (`te-tengo-service-detection-worker`, with FastAPI and WebSocket ingestion). The core (`clasificacion/`, `pose/`, the clip buffer and encoding, `eventos/`) is reused as is inside the agent; the ingestion server will be retired when the agent is ready. The change request to the charter is pending.


**Detection module** of Te Tengo, the pose-estimation-based system for detecting falls of older adults in their homes.

It receives the video from the Capture Agent, estimates the person's pose with MediaPipe and classifies the movement with **kinematic thresholds, without training models**. It detects falls, confirmed falls, recoveries, unstable movements and periods of unreliable detection. It reports each event to the system's Backend API and stores the clip from 6 s before to 6 s after the event.

## Place in the architecture

This repository implements the **Detection module** container of the C4 model. It maps to the **Video Processing Layer** of the logical architecture, except for the Live Streaming Service, which is separate.

| Logical architecture component | Folder |
|---|---|
| Video Ingestion Service | [`src/detection_worker/ingesta/`](src/detection_worker/ingesta) |
| Pose Estimation Service | [`src/detection_worker/pose/`](src/detection_worker/pose) |
| Kinematic Classification Service | [`src/detection_worker/clasificacion/`](src/detection_worker/clasificacion) |
| Communication with the system's Backend API | [`src/detection_worker/eventos/`](src/detection_worker/eventos) |
| Video clip persistence (write) | [`src/detection_worker/clips/`](src/detection_worker/clips) |

```
Capture Agent ──WSS (JPEG 480p, 5-10 fps)──► ingesta ──► pose (MediaPipe, separate process)
                                                │                │ 33 landmarks
                                                │                ▼
                                                │          clasificacion ──events──► Backend API
                                                └──clip 6 s + 6 s──► clips ──► object storage
```

The internal organization is explained in [docs/architecture.md](docs/architecture.md). The formulas and their sources are in [docs/classification-spec.md](docs/classification-spec.md).

## Requirements

| Tool | Version |
|---|---|
| Python | 3.11 (required by `mediapipe==0.10.35`, see [ADR 0003](docs/adr/0003-mediapipe-in-separate-process.md)) |
| [uv](https://docs.astral.sh/uv/) | 0.12 or later |
| FFmpeg | Any recent version (builds the MP4 clips) |
| Docker | 29 or later (optional, for the image) |

## Getting started

```bash
make instalar      # creates .venv with uv and installs the pre-commit hooks
make modelo        # downloads pose_landmarker_lite.task into models/
make env          # creates .env with local tokens (does not overwrite an existing one)
make ejecutar      # http://localhost:8001/docs
```

## Commands

| Command | What it does |
|---|---|
| `make instalar` | Installs the dependencies (`uv sync`) and the pre-commit hooks |
| `make env` | Creates `.env` from `.env.example` with random local tokens |
| `make modelo` | Downloads the MediaPipe model |
| `make ejecutar` | Starts the service with auto-reload |
| `make camara` | Tests the classifier with the webcam or a video, with an on-screen overlay |
| `make agente` | Sends the webcam or a video to the worker, like the real agent |
| `make datasets` | Downloads URFD and CAUCAFall |
| `make validar` | Validates the classifier with the datasets and generates the report |
| `make formatear` | Formats the code with Ruff |
| `make revisar` | Lint (Ruff), formatting and types (mypy in strict mode) |
| `make probar` | Tests with coverage (pytest) |
| `make imagen` | Builds the Docker image |

## Testing with the camera or with videos

There are two tools in `scripts/`. Neither one needs the backend or the real agent.

**1. Local classifier test** (`make camara`). Opens the webcam or a video and uses the same code as the worker. The window shows the video with the skeleton (colored by phase), the center line, the hip center (cyan) and the body bounding box. Next to it there is a panel with:
- the state: normal, possible fall or on the floor, with the countdown to 30 s;
- whether the person is detected and whether their key points are visible;
- the three fall conditions, with their value, a bar and the threshold;
- the progress toward "got up" and the list of events.

When an event occurs, a large notice appears over the video. Keys: `q` quit, `r` reset, `c` save screenshot.

```bash
make camara ARGS="--camara 0"                        # webcam, with the calibrated threshold
make camara ARGS="--solo-medir"                      # only shows the values, without classifying
make camara ARGS="--video fall-01-cam0.mp4 --recorte 320,0,320,240 --csv mediciones.csv"
```

- **URFD videos:** they have depth on the left and RGB on the right. Use `--recorte 320,0,320,240`.
- **`--csv`:** saves the angle, the ratio and the speed of each frame; useful for calibration.
- **`--sin-ventana`:** only prints the events, without opening a window.
- **On macOS:** the first time, you must give camera permission to the terminal or the IDE (System Settings → Privacy & Security → Camera).
- **iPhone as a camera (Continuity Camera):** with iOS 16 or later, macOS Ventura or later and the same Apple Account, the iPhone appears as one more camera. To see its index: `make camara ARGS="--listar-camaras"`; then use it with `--camara N`. Avoid "Desk View", which shows the desk from above.

**2. Simulated agent** (`make agente`). Sends the webcam or a video to the worker over WebSocket, just as Te Tengo Captura will (480p, 8 fps and JPEG). It tests the full service:

```bash
make ejecutar                                    # in one terminal (requires the threshold in .env)
make agente                                      # in another one: webcam
make agente ARGS="--video fall-01-cam0.mp4 --recorte 320,0,320,240"
```

The worker logs each event (`Evento detectado: caida en camara-local …`). Without the backend or SeaweedFS, it also logs a warning that it could not publish the event, but it keeps working.

## Validation with public datasets

The classifier was validated with **URFD** (70 videos) and **CAUCAFall** (100 videos) under production conditions: 480p, 8 fps, JPEG and MediaPipe in VIDEO mode. To measure without bias, each group was left out during calibration:

| Sensitivity | Specificity | Accuracy | False recoveries |
|---|---|---|---|
| **81.2%** | **81.1%** | **81.2%** | 0 of 30 |

Protocol, results per activity, changes made and limitations: [docs/validation.md](docs/validation.md). To reproduce it:

```bash
make datasets   # downloads the datasets into datos/ (not versioned)
make validar    # generates resultados/reporte.md
```

## Interfaces

| Interface | Details |
|---|---|
| `GET /health` | Liveness for Docker and the reverse proxy |
| `WS /v1/ingesta/{camara_id}` | Video from the Capture Agent. Format in [docs/ingestion-protocol.md](docs/ingestion-protocol.md). |
| Backend API → `POST /internal/v1/eventos` | Detected events (provisional contract) |
| Backend API → `PUT /internal/v1/eventos/{id}/clip` | Key of the stored clip |

## Configuration

All variables have the `TT_` prefix. The full list is in [.env.example](.env.example).

`TT_CLASIFICACION__VELOCIDAD_DESCENSO_MIN` has no default value in the code; `.env.example` has the calibrated value (0.01; see [docs/validation.md](docs/validation.md)). While it is empty, the service starts (`/health`, `/docs`), but ingestion closes the WebSocket with code 1011.

## Status

Version 0.2.0: classifier validated with URFD and CAUCAFall. Pending:
- Validate the unstable movement rule with our own recordings (the datasets have no labeled stumbles).
- Motion detection and frame quality control.
- Drop late frames (backpressure).
- Forward the video to the Live Streaming Service.

Details are in [CHANGELOG.md](CHANGELOG.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md): Conventional Commits, branches and review before merging.

---

Thesis project, Software Engineering, Universidad Peruana de Ciencias Aplicadas (UPC). Authors: Jhosepmyr Gutierrez Soto and Elmer Riva Rodriguez.
