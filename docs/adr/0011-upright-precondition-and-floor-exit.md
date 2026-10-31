# 0011. Two post-hoc fixes for the hold-out failures: upright precondition (F1) and leaving the floor without evidence (F2)

**Status:** decided (2026-10-31): F1, F2 and F1 + F2 rejected; F3 accepted under criterion 2 only, as an opt-in configuration; **the shipped default does not change**. Both rules are **post hoc**: they were designed after seeing the hold-out results of [validation.md](../validation.md), sections 6 and 8. They are off by default (`None`), so the shipped classifier does not change unless this ADR is accepted.

This ADR is written in two steps. The context, the rules, their physical rationale and the evaluation protocol (sections "Context" to "Protocol") were committed **before** any run of F1 or F2 on any dataset; "Results" and "Decision" were added afterwards.

## Context
The hold-out tests found two failure mechanisms that no threshold of the shipped rules can remove:

1. **Lying still fires R4.** R4 starts (`NORMAL` → `INICIO_CAIDA`) when the hip goes down (M1) while the body is tilted (M2), and fires when the body is horizontal (M3) within 1.48 s. A person who is already lying meets M2 and M3 on every frame, and with v = 0.01 bodies/s any small downward jitter of the hip meets M1. UP-Fall "laying" (the subject lies still on a mattress from the first frame): 22 of 34 recordings fire, most in the first 3 s. GMDCSA24 lying down on a bed: 12 of 12.
2. **One false alarm masks the next fall.** After a `caida` the classifier stays in `EN_EL_SUELO` until R5 sees the person upright, with the nose, hips and ankles visible (A6), for 1 continuous second (A8). On MCFD's wide-angle cameras that evidence is often missing, so after a false alarm while sitting down, crouching or lying on a sofa the classifier never returns to `NORMAL`: 52 of the 96 fall windows missed per camera were already in `EN_EL_SUELO` at the fall onset, and the real fall could not raise a new `caida`.

## Rules (proposals)
### F1. Upright precondition for R4 (`erguido_previo_caida_s` = T)
R4 may start only if the person was seen **upright** (the existing definition of R5: θ > 45°, P < 1, head above the feet and the nose, hips and ankles visible, A6) on some frame during the last T seconds. R9 is not changed (it already requires being upright in the last 10 s), nor is R7.

**Physical rationale.** A fall is a loss of balance of a body that was supported over its feet or its seat: it starts from standing, walking or sitting upright. R4 models the fast part of that process (inverted pendulum, 1.0–1.48 s from losing balance to the floor; Gutiérrez et al., 2023), so the last upright frame must come shortly before M1 and M2 hold together. A person who has been lying for longer than that has no balance to lose: their hip can only move along the floor or the bed, and any M1 there is noise or a deliberate movement. Seated upright also passes the upright test (as noted for R9), so falls from a chair keep R4. The strict upright test (with A6) is used, as R9 does, because a doubtful pose of a person lying can look upright and would re-enable R4.

**Grid and prior.** T ∈ {1, 2, 3, 5, 10} s. The a-priori value is 3 s: about twice the reaction window, to tolerate the frames that MediaPipe loses or doubts during the descent (A3, A6).

**Predictions (written before running).** Removes most UP-Fall "laying" alarms (the subject is never upright in those recordings). Helps less with lying down on a bed, where the person sits on the bed (upright) seconds before lying. May lose falls whose key points are hidden while the person stands (URFD, where one ankle is often below visibility 0.5; [validation.md](../validation.md) section 7.1), and falls that start from a lying or kneeling posture (not in R4's scope anyway).

### F2. Leave `EN_EL_SUELO` without floor evidence (`salida_suelo_sin_evidencia_s` = X)
While in `EN_EL_SUELO`, if on every frame with a pose during X seconds the body is **neither tilted (M2) nor horizontal (M3)**, the classifier returns to `NORMAL` **without emitting `recuperacion`**, and the pending R6 confirmation is dropped. Frames without a pose neither restart nor advance the decision (it is taken on a frame with a pose), as in R6 and R9.

**Physical rationale.** A person on the floor after a fall is horizontal or at least tilted (M2 or M3; A7 covers the foreshortened case). A body that stays vertical and narrow for several seconds is not lying on the floor, whatever the visibility of its feet. R5 needs stronger evidence (A6, A8) because `recuperacion` tells the family that the person got up; F2 asserts nothing to the family, it only stops assuming that the person is still on the floor, so the next fall can be detected. The visibility gate of A6 is therefore not required, and in exchange the evidence must last longer than A8's 1 s.

**Why silent, and why R6 is dropped.** Emitting `recuperacion` on weaker evidence would add false recoveries, which A6 and A8 were introduced to avoid. Keeping the R6 timer after leaving the floor would confirm, 30 s later, a fall the classifier no longer believes. The risk is that a real fall followed by **sitting up on the floor** for X s (which can look vertical and narrow) cancels its confirmation; the `caida` alarm itself has already been sent. R5 already does the same, with a `recuperacion`, when sitting up is seen with the key points visible. The evaluation reports the confirmations lost and every silent exit while the person is labelled on the ground (MCFD).

**Grid and prior.** X ∈ {2, 3, 5, 10, 20} s. The a-priori value is 5 s (five times A8, because the evidence is weaker).

**Predictions.** Recovers part of MCFD's 52 masked falls; adds false alarms, because a re-armed classifier can fire again on the next sitting or crouching (MCFD false alarms per hour should rise). Little effect on the clip datasets, whose clips mostly end on the floor or are too short.

### F1 + F2
Both together, with T and X chosen jointly.

## Protocol (fixed before running)
- **Data:** URFD, CAUCAFall, GMDCSA24, UP-Fall (subset, 2 cameras) and MCFD (8 cameras), poses `lite-video-8fps-jpeg` already extracted (480p, 8 fps, JPEG quality 80, MediaPipe lite in VIDEO mode). Each camera is a separate recording.
- **Units:** per recording (video and camera) for URFD, CAUCAFall, GMDCSA24 and UP-Fall (a fall recording is detected with any `caida`; an ADL recording is a false positive with any `caida`). MCFD: per event as in section 8.3 — each labelled fall window (1 s before the `falling` onset to the end of `lying on the ground`) is a positive unit, detected if a `caida` comes inside it; each labelled **non-fall period** (one per position code of the dataset's labels, outside the fall windows and the ambiguous windows of scenario 23) is a negative unit, a false positive if a `caida` comes inside it. False alarms per hour of labelled non-fall time are reported too.
- **Leave one dataset out (LODO):** 5 folds. In each fold the four other datasets choose v (0.01–1.00, step 0.01), T and X from their grids; the chosen configuration is applied to the held-out dataset.
- **Training objective:** macro average over the four training datasets of sensitivity and specificity (each dataset weighs the same, whatever its size). Two criteria, both reported:
  1. maximum macro Youden index J = sens + spec − 1;
  2. maximum macro specificity subject to macro sensitivity ≥ 90 %; if no configuration reaches 90 %, the maximum macro sensitivity (ties: maximum specificity).
  Ties: the lowest v, then the largest T and X (the closest to the shipped behaviour).
- **Configurations:** baseline 100 (v), F1 500, F2 500, F1 + F2 2,500: **3,600** in total.
- **Reported per held-out dataset and overall** (pooled units and macro mean over the five folds): sensitivity and specificity with 95 % Wilson intervals; exact McNemar tests (two-sided binomial on the discordant pairs) of each fix against the baseline under the same criterion, on paired units (recordings; MCFD fall windows and non-fall periods); also the frozen shipped classifier (v = 0.01, F1 and F2 off) per dataset; false recoveries; per-activity false alarms (lying still / on a bed, kneeling, picking up, sitting); MCFD false alarms per hour and latency; F2's lost confirmations and its silent exits while the person is labelled on the ground.
- **Acceptance rule (per fix and criterion), against the LODO baseline with the same criterion:**
  1. the macro mean over the five held-out datasets of the targeted metric (specificity for F1, sensitivity for F2; either for F1 + F2) rises, and the other metric's macro loss, if any, is **smaller than that gain**;
  2. **consistency:** the targeted metric rises in at least 3 of the 5 held-out datasets and falls by more than 2 points in none;
  3. false recoveries do not increase, and F2's silent exits while labelled on the ground stay rare (at most 5 % of the detected MCFD falls);
  4. McNemar on all pooled held-out units is not a significant loss (p < 0.05 with more units wrong than the baseline).
- **If accepted:** the deployed configuration is calibrated on all five datasets with the same criterion, and its expected performance is the LODO result, not the calibration fit. The shipped default changes only if the fix is accepted under criterion 1 (the validated protocol) and the parity tests pass.

### F3 (added after the first LODO run; doubly post hoc): F1 with the geometric upright test
**Why it was added.** In the first run (results below) F1 lost 72 falls that the baseline detected, and the training folds always chose the most permissive window (T = 10 s), so the window was not the problem. Tracing those 72 falls (frozen v = 0.01, 10 s before the baseline's `caida`): **none** had a frame that passed the strict upright test, and **42** had frames that passed its geometry (θ > 45°, P < 1, head above the feet) with some key point below visibility 0.5 (UP-Fall 24, CAUCAFall 7, GMDCSA24 5, URFD 3 of their losses). The visibility gate of A6, not the precondition itself, removes these falls.

**Rule.** F1 with `erguido_previo_exige_visibles = False`: the precondition accepts a frame that passes the geometry of the upright test without A6. **Rationale:** A6 protects decisions that tell the family the person is fine (R5) or downgrade an alarm (R7); in F1 a doubtful upright frame only lets R4 run as it does today, so the error it can cause is at most the shipped behaviour. **Grid:** v × T as F1 (500 configurations); not combined with F2, because F2 changed nothing (see Results). **Prediction:** recovers most of the 42 falls; gives back part of the lying-still false alarms if MediaPipe estimates a lying person as geometrically upright on isolated frames (A8). Same protocol and acceptance rule as F1.

**Erratum to the F3 note above (found after the second run).** The trace that motivated F3 counted every recording whose `caida` F1 removed, ADL included. Restricted to fall recordings, F1 loses 42 falls (not 72), none with a strict upright frame in the 10 s before the shipped `caida` and 38 (not 42) with a geometric one. The motivation is unchanged; F3 was not modified.

## Results
Leave one dataset out, 4,100 configurations; full tables in [validation.md](../validation.md), section 9, and `resultados/lodo-f1-f2-8fps.md`. Macro mean over the five held-out datasets, sensitivity / specificity:

| Rule set | Criterion 1 (Youden) | Criterion 2 (spec., sens. ≥ 90 %) |
|---|---|---|
| Shipped (v = 0.01) | 74.0 / 74.5 | 74.0 / 74.5 |
| Baseline (v re-chosen) | 62.3 / 84.5 | 74.0 / 74.5 |
| F1 | 57.0 / 88.1 | 63.1 / 83.9 |
| F2 | 64.9 / 78.9 | 74.0 / 74.5 |
| F1 + F2 | 57.0 / 88.1 | 63.1 / 83.9 |
| **F3** | **72.6 / 82.9** | **72.6 / 82.9** |

- **F1**: removes the UP-Fall lying-still alarms (22 → 0) and 5 of the 12 bed alarms, but loses falls in every dataset, because no frame before them passes A6's visibility gate (the window is not the issue: every fold chose T = 10 s).
- **F2**: no effect. On MCFD the body shows M2 or M3 on 99 % of the pose frames before the masked falls; 11 of the 58 masked windows were entered ≤ 2 s before the labelled onset, i.e., an early detection of the same descent rather than an unrelated false alarm.
- **F3**: every fold, under both criteria, chose v = 0.01 and T = 10 s. Against the shipped classifier (= criterion-2 baseline): UP-Fall specificity 63.2 → 95.6 %, GMDCSA24 65.4 → 72.8 % (bed 12 → 9), CAUCAFall 84 → 86 %; 6 of 513 positive units lost, 32 units corrected (McNemar 6/32, p < 0.001); no new false recovery; MCFD 112 false alarms per hour (114 shipped), latency 1.07 s.

## Decision
- F1, F2 and F1 + F2 are **rejected** (F1: its specificity gain is smaller than its sensitivity loss; F2: no change).
- F3 meets the acceptance rule under **criterion 2**. Under criterion 1 it does not: its target, specificity, falls 1.6 points against the Youden baseline, and its gain shows up as sensitivity (+10.3 points) because without lying-still alarms the folds keep v = 0.01.
- As fixed beforehand, the default changes only with acceptance under criterion 1, so **the shipped classifier does not change**. F3 stays in the code, off by default, and the configuration `erguido_previo_caida_s = 10`, `erguido_previo_exige_visibles = false` (v = 0.01) is the proposal for the pilot, with the LODO result (macro 72.6 % / 82.9 %) as its expected performance.

## Consequences
- Two new `[clasificacion]` values, `erguido_previo_caida_s` and `erguido_previo_exige_visibles`, and one for F2, `salida_suelo_sin_evidencia_s`; unset, the agent behaves exactly as validated (the parity tests do not change).
- Lying down on a bed after sitting on it remains a false alarm with any precondition. MCFD's masked falls need another mechanism (the person does look tilted on wide-angle views).
- F3 is doubly post hoc and was chosen at the edge of its grid (T = 10 s); it must be confirmed on data not used here before it becomes the default.

## References
Gutiérrez, J., Martin, S., & Rodriguez, V. (2023). Human stability assessment and fall detection based on dynamic descriptors. *IET Image Processing, 17*(11), 3177–3195. https://doi.org/10.1049/ipr2.12847
