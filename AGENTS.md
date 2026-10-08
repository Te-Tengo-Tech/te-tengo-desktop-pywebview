# AGENTS.md

## Purpose
**Te Tengo Captura**, the household agent of **Te Tengo** (a system that detects falls of older adults at home). It runs on the household PC, which stays on:
- it opens the configured USB webcam;
- it estimates the pose with MediaPipe **on the PC's CPU** and classifies the movement with the validated kinematic classifier (ADR 0007);
- it sends only **events and 6 s + 6 s clips** to the backend (`te-tengo-general-api`), never a continuous video stream; video leaves the PC only while a family member watches the **live view** (US-23), published to the streaming service on the API's request (`docs/AGENT_CONTRACT.md`, "Live view");
- it shows the state of the webcam in a small window and in the system tray.

The family manages everything else (consent, pauses, room name, alerts) in the mobile app (`te-tengo-mobile-flutter`). The agent has **no camera linking and no settings screen**: the project team installs it with a fixed configuration file.

## Where to look
| Question | Source |
|---|---|
| What to build, and in which order | [docs/WORK_PLAN.md](docs/WORK_PLAN.md) — a checklist; follow the autonomous loop described there |
| What the agent sends and receives (paths, bodies, errors) | [docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md) — **shared with the API; implement it exactly** |
| How the classifier works and why | [docs/classification-spec.md](docs/classification-spec.md), [docs/validation.md](docs/validation.md), ADRs in [docs/adr/](docs/adr) |
| What the window, splash and tray look like | `docs/references/desktop-prototype/`: `screens/00–07` PNGs, `DESIGN.md`, `PRODUCT.md` and the source `src/core.js`, `src/app.css` (exact Spanish copy, SVG icons and tokens) |
| Acceptance criteria (Given/When/Then) | [docs/references/PRODUCT_BACKLOG.md](docs/references/PRODUCT_BACKLOG.md) — Spanish source document; every business value comes from here |
| How each flow moves through the components | `docs/references/diagrams/integracion.puml` |

## Big picture (target layout, reached in T01)
```
src/te_tengo_deteccion/   validated detection core: pure Python, no GUI, no network
  clasificacion/          kinematic classifier (estados, medicion, parametros, umbrales)
  pose/                   MediaPipe Pose Landmarker in VIDEO mode
  clips/                  6 s + 6 s ring buffer and MP4 encoding
src/te_tengo_captura/     the desktop application
  config.py               fixed installation file (TOML)
  backend/                AGENT_CONTRACT client (httpx) + in-memory fake backend
  captura/                webcam reader, 480p / 8 fps sampling, capture loop
  envios/                 persistent outbox for events and clips (survives restarts and offline periods)
  estado.py               the agent state the UI shows (one source of truth)
  ui/                     pywebview window, splash and JS bridge; web/ holds HTML, CSS, JS and fonts
  bandeja/                pystray icon with the status dot and system notifications
  __main__.py             entry point: `uv run te-tengo-captura`
scripts/                  validation and camera test tools (keep them working)
```
- **Dependency rule:** `te_tengo_deteccion` never imports `te_tengo_captura`, pywebview, pystray or httpx. A test enforces it.
- **Threads:** pywebview owns the main thread. The capture loop runs in a worker thread (or asyncio loop in a thread); MediaPipe runs in that worker. The UI receives state through the bridge, never by reading globals.
- **Headless tests:** `ui/` and `bandeja/` import pywebview and pystray **inside functions**, so `pytest` runs in CI and in the cloud without a display.

## Rules
- **Do not change the validated behaviour** of `te_tengo_deteccion` (thresholds, A1–A8 adaptations, VIDEO mode). Moving files is fine; changing logic needs a new ADR and re-running `make validar` locally (blocker for the cloud).
- **Same processing as the validation:** 480p, 8 fps, JPEG quality 80, pose estimated on the JPEG-decoded frame (`docs/validation.md`, section 2).
- **Consent and pauses are hard gates:** while `capturaPermitida` is `false` the agent does not read the webcam frames into the classifier and keeps no clip buffer (CA-05.2, CA-22.1).
- **Never lose an event:** events go to the outbox first and are sent with retries; `eventoId` (UUID v7) makes resending safe.
- **Privacy:** no frames on disk except the clip of an event until it is uploaded; delete it after a successful upload.
- **UI copy:** Spanish, copied verbatim from `src/core.js` of the prototype. Never invent copy or business values; if something is missing, record it in `docs/BLOCKERS.md`.
- **Language:** domain identifiers are Spanish (the ubiquitous language of the thesis). Code comments, docstrings, docs and commit messages are **English**.
- **Secrets:** the installation credential and the camera token are never logged.

## Commands
| Command | Purpose |
|---|---|
| `uv sync` | Install dependencies (Python 3.11) |
| `make modelo` | Download the MediaPipe model into `models/` |
| `make revisar` | `ruff check`, `ruff format --check`, `mypy` (strict) |
| `make probar` | `pytest` with coverage |
| `make formatear` | Format and fix imports |
| `uv run te-tengo-captura --backend-falso --config config.ejemplo.toml` | Run the agent without the API (needs a display) |
| `uv run te-tengo-captura --sin-interfaz --config <toml> --video <file>` | Run the agent with no window nor tray (no display needed); the API's `scripts/e2e.sh` uses it |
| `make empaquetar` | PyInstaller one-folder build |
| `make camara`, `make validar` | Local tools: webcam test and dataset validation (need a webcam or the datasets) |

## Definition of done (every task)
1. **Every acceptance criterion the task names is covered by a test.**
2. **Backend calls match `docs/AGENT_CONTRACT.md` exactly** and are tested against the fake backend (`httpx.MockTransport`).
3. **`make revisar probar` passes** (ruff, mypy strict, pytest). Never skip or weaken a test.
4. **The validation tools still run:** `uv run python scripts/evaluar.py --help` and `uv run python scripts/probar_camara.py --help`.
5. **One Conventional Commit per task,** in English and with no co-author line (e.g. `feat(captura): capture loop with consent gate (US-05)`), and the task is checked off in `docs/WORK_PLAN.md`.
