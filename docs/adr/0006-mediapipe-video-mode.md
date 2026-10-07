# 0006. MediaPipe in VIDEO mode, one tracker per camera

**Status:** accepted (2026-10-03). Replaces the `IMAGE` mode decision of ADR 0003; the rest of that ADR remains in force.

## Context
In the validation with URFD and CAUCAFall ([validation.md](../validation.md)), `IMAGE` mode lost the person in **43%** of the frames of the CAUCAFall falls, right during the descent. `VIDEO` mode tracks the person between frames and requires increasing timestamps.

| Variant (8 fps) | Coverage in CAUCAFall falls | Coverage in URFD falls |
|---|---|---|
| lite · IMAGE | 57% | 86% |
| **lite · VIDEO** | **82%** | **88%** |
| full · IMAGE | 57% | 83% |
| full · VIDEO | 82% | 89% |

## Decision
- Use `VIDEO` mode with the *lite* model. The *full* model does not improve coverage and uses more CPU.
- The inference process keeps **one landmarker per camera** with its last timestamp. If an earlier timestamp arrives (the agent reconnected), a new one is created.
- When the camera disconnects, its landmarker is released.

## Consequences
- The worker receives the `camara_id` and the agent's timestamp on each inference.
- The validation (`scripts/evaluar.py`) and the worker use the same mode, so their results match: 24 of 24 videos replayed live.
