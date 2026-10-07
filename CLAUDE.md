@AGENTS.md

## Notes for Claude Code
- **Working mode:** this repository is meant to be built autonomously from [docs/WORK_PLAN.md](docs/WORK_PLAN.md). When asked to "work", "continue" or `/work`, follow the loop in that file **until every task is checked or only blocked tasks remain. Do not stop after one task.**
- **Cloud environment:** the `SessionStart` hook (`scripts/cloud/setup-environment.sh`) installs Python 3.11 with uv, the system libraries MediaPipe needs on Linux (`libgles2`, `libegl1`) and `ffmpeg`, runs `uv sync` and downloads the MediaPipe model.
  - There is no webcam and no display in the cloud: verify with `make revisar probar`, using `FuenteArchivo`/`FuenteFalsa` and the fake backend. pywebview and pystray must never be imported at module level.
  - Compare the UI against the PNG screens by reading the images and the prototype source.
  - The validation datasets are not reachable from the cloud; never change the detection logic there (see `docs/BLOCKERS.md`).
- **User rules:**
  - English for docs and commits; Conventional Commits with **no co-author line**.
  - Spanish UI copy taken from the references; never invent copy or business values.
