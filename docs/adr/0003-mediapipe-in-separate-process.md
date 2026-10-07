# 0003. MediaPipe 0.10.35 in a separate process

**Status:** accepted (2026-10-03). `IMAGE` mode was replaced by `VIDEO` mode in [ADR 0006](0006-mediapipe-video-mode.md).

## Context
- Pose estimation is CPU-intensive (the EC2 t3.small has no GPU). Awaiting it inside an `async` route, or sending it to a thread, does not help due to the GIL; another process must be used (Zhanymkanov, s.f.).
- MediaPipe 1.0.1 fails when building the graph on macOS with CPU (google-ai-edge/mediapipe#6356). Version 0.10.35 works and has installers for Linux x86_64 and Windows.

## Decision
- Pin `mediapipe==0.10.35` and Python 3.11.
- Run the Pose Landmarker (*lite* model) in a `ProcessPoolExecutor` with a single process, which creates the model once at startup.
- Use `IMAGE` mode: each frame is independent, so it tolerates agent reconnections without requiring increasing timestamps like `VIDEO` mode does.

## Consequences
- The WebSocket keeps receiving while inference runs.
- `IMAGE` mode does not use tracking between frames. If accuracy requires it, `VIDEO` mode with one landmarker per camera will be evaluated.
- Before updating MediaPipe, check first that the macOS bug is fixed.

Google AI Edge. (2026). *Tasks Vision graphs with TensorsToDetectionsCalculator abort at graph build on macOS CPU* (Issue 6356). GitHub. https://github.com/google-ai-edge/mediapipe/issues/6356
Zhanymkanov, Y. (s.f.). *FastAPI best practices: CPU intensive tasks*. https://github.com/zhanymkanov/fastapi-best-practices
