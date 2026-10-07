# 0007. Process the video on the household PC

**Status:** accepted by the team (2026-10-07). It requires a change request to the charter, which states that processing runs in the cloud.

## Context
- **Bandwidth (measured):** sending 480p at 8 fps in JPEG requires about 2.8 Mbit/s of constant upload, about 31 GB per day per camera.
- **CPU (measured):** MediaPipe *lite* takes 6.5 ms per frame on CPU (MacBook M5 Pro); at 8 fps there is plenty of headroom.
- **Evidence:** in the systematic review, the direct comparison between edge and cloud (Mundody and Guddeti, 2026) favors the edge in latency under congestion and in privacy.

## Decision
- **This repository becomes the desktop agent** (`te-tengo-desktop-pywebview`): a single Python project, with the prototype's HTML interface shown with pywebview.
- **Detection lives as an internal package,** pure and tested.
- **The ingestion server is retired** (FastAPI and WebSocket).
- **The backend** receives the events (contract in `te-tengo-general-api/docs/CONTRATO_AGENTE.md`).

## Consequences
- The video does not leave the home, except for the event clip and the live view when the family member requests it.
- The validation (`scripts/evaluar.py`) and the specification remain valid, because the classification code does not change.
- The fps must be measured on the real pilot PC.
- The thresholds and updates must be distributed from the backend.

Mundody, S., & Guddeti, R. M. R. (2026). Pose-based fall detection with robust feature analysis and privacy-aware edge-fog-cloud deployment. *IEEE Access, 14*, 114183–114208. https://doi.org/10.1109/ACCESS.2026.3716718
