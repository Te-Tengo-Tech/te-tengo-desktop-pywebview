# Architecture decision records (ADR)

Each important decision is recorded in a short file using Michael Nygard's format: **context, decision, status and consequences** (Nygard, 2011). ADRs are not edited after they are accepted: if a decision changes, a new ADR is written that supersedes the previous one.

| No. | Decision | Status |
|---|---|---|
| [0001](0001-fastapi-and-uvicorn.md) | FastAPI and Uvicorn for the service | Accepted |
| [0002](0002-domain-structure.md) | Structure by domain with a pure core and adapters | Accepted |
| [0003](0003-mediapipe-in-separate-process.md) | MediaPipe 0.10.35 in a separate process | Accepted |
| [0004](0004-chen-thresholds.md) | Classification with the thresholds of Chen et al. (2020) | Accepted |
| [0005](0005-uv-ruff-mypy.md) | uv, Ruff and mypy as the project tools | Accepted |
| [0006](0006-mediapipe-video-mode.md) | MediaPipe in VIDEO mode, one tracker per camera | Accepted (replaces the mode of 0003) |
| [0007](0007-processing-on-household-pc.md) | Process the video on the household PC (this repository becomes the desktop agent) | Accepted by the team; change request to the charter pending |

Nygard, M. (2011, 15 de noviembre). *Documenting architecture decisions*. Cognitect. https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
