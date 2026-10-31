# 0010. Keep the validated classifier: the sensitivity candidates are rejected

**Status:** accepted (2026-10-31). The classifier of ADR 0004 with rule R9 (ADR 0009) does not change.

## Context
The validated classifier detects 66 of 80 falls (82.5 %) with 78.9 % specificity on URFD and CAUCAFall (8 fps, JPEG, leaving one group out). The thesis asked whether the sensitivity could be raised **without forcing it**, with one camera per room (fusing cameras is not an option), and with a protocol good enough for a paper. A frame-by-frame diagnosis of the 14 misses found three causes: one or both ankles hidden during the descent, so A6 never measures the speed while the body tilts (5 URFD falls and 1 CAUCAFall fall); falls toward the camera, in which the center line shortens without tilting in the image; and poses lost during or after the descent, including one fall with no pose in any frame.

## Decision
Four candidates were written down with their physical rationale before testing them, and one more after the first round (marked post hoc): speed with only the hips visible (C1), with the hips and one ankle (C1b), tilt toward the camera from the shortening of the center line (C2), a fall when the pose is lost right after a fast descent (C3), and re-calibration of the angle and the ratio (C4). Every threshold was chosen inside each training fold; 13 settings and 10,600 configurations were evaluated (`scripts/evaluar_candidatos.py`; [validation.md](../validation.md), section 7).

**None is adopted.** Each candidate that raised sensitivity lowered specificity by more (C1b, 88.8 % / 66.7 %, gained only in URFD; C1, 92.5 % / 61.1 %), and a fully nested selection in which each fold also picks the candidate is significantly worse than the baseline (85.0 % / 67.8 %, McNemar exact p = 0.039 on all videos). The candidates' code was removed from the classifier; it remains at commit `233480f` to reproduce the study.

## Consequences
- The agent, its thresholds, the safe ranges (US-45) and the parity with the validation do not change.
- A6's visibility gate is now known to carry part of the specificity, not only to stabilize the speed. Relaxing it must be validated as a change of the fall decision, not of the speed alone.
- Remaining misses need information that one 2D pose per frame does not give (the person is not found, or lying down on purpose looks like a fall). Candidates for future work: motion or appearance features in the frames without a pose, and the pilot recordings.
- The hold-out check on the third dataset needs no extra run: the frozen classifier is the baseline, so its hold-out result is the one in [validation.md](../validation.md), section 6.
