# Specificity study: fewer false alarms without training (2026-11-05)

**Question.** Can rule changes that keep the classifier training-free, interpretable, on the CPU and with one RGB camera lower its false alarms (and, ideally, recover missed falls)? **Answer: not with the rules tested here.** The best candidate on the development data, a hold-and-cancel window (S1), raised specificity by 5.5 points there but lost falls on two of the three hold-out sets, so it is rejected by the rule fixed beforehand. An identity-jump gate (S4) changes nothing on the development data and little on the hold-out sets; it is kept as an opt-in for the pilot. The shipped classifier does not change.

Rationale, grids, predictions and the acceptance rule: [ADR 0012](adr/0012-specificity-study.md), committed before any run. Full reports: `resultados/especificidad/desarrollo.md`, `holdout.md` and `lodo.md`.

```bash
uv run python scripts/evaluar_especificidad.py desarrollo --familias base S1 "S2 (F3)" S3 S4 S1+S4 S1+F3 S1+S4+F3 "S1+S3 (exploratory)"
uv run python scripts/evaluar_especificidad.py holdout --familias "S2 (F3)" S1 S4 S1+S4 S1+F3
uv run python scripts/evaluar_especificidad.py lodo --familias "S2 (F3)" S1 S4 S1+S4
```

## 1. Starting point

Shipped classifier (R4–R9, v = 0.01 bodies/s, 8 fps, 480p, JPEG 80, MediaPipe lite in VIDEO mode): on URFD + CAUCAFall, leaving one group out, 82.5 % sensitivity and 78.9 % specificity (14 misses, 19 false alarms). Hold-out: GMDCSA24 91.1 / 65.4 %, UP-Fall 68.2 / 63.2 %, MCFD 47.8 % of the falls per event and 114 false alarms per hour.

**Diagnosis of the baseline errors** (development data only, before writing the candidates): 14 of the 19 false alarms show a geometrically upright frame after the `caida` (kneeling, picking up an object, and URFD people lying down and getting up), against 7 of the 66 detected falls (isolated frames or a short sit-up). The person was upright 0.1–2.1 s before every false alarm, so a recent-upright precondition (F3) cannot remove them here. At the instant of the `caida` the hip drop and the torso angle overlap between falls and false alarms (R4 fires mid-descent). 7 of the 14 misses fail A6 only because the ankles are hidden, with the nose, shoulders and hips visible.

## 2. Literature and what was tested

| Strategy (source) | What the source reports | Here |
|---|---|---|
| Post-fall inactivity or "stays low" for 1–5 s (Rougier et al., 2011; Auvinet et al., 2011; Noury et al., 2007) | Shape deformation followed by stillness; Auvinet: ≥ 99.7 % sensitivity and specificity with ≥ 4 cameras, specificity mostly from the time window | **S1**: hold the `caida` D s and withdraw it if the person is upright again |
| Trunk or head velocity separates falls from activities (Wu, 2000; Bourke et al., 2008: −1.3 m/s, 100 % on 5 subjects; Amini et al., 2016) | Lab or depth-sensor studies | **S3**: hip speed and torso angle from the upper body when the ankles are hidden |
| Following the wrong subject causes about half of real-home false alarms (Debard et al., 2016: second person 16 %, split body 15 %, 178.7 false alarms per day) | Real homes, 2D video | **S4**: identity-jump gate |
| Recent upright posture before the fall (descent profile) | — (ADR 0011) | **S2 = F3**, as comparator |
| Rest zones for beds and sofas (Lee & Mihailidis, 2005: 77 % falls, 5 % false alarms) | Needs per-camera annotation | Not testable: no dataset has annotated zones |
| One-Euro or Kalman smoothing (Casiez et al., 2012) | No fall-detection evidence found | Not tested (ADR 0010) |
| Hip-drop or torso-angle gate at the trigger; k-of-n voting on M3 | — | Not tested: overlapping values in the diagnosis; voting already rejected (validation.md, section 4) |

No peer-reviewed training-free MediaPipe or OpenPose rule paper reporting specificity on URFD, Le2i, CAUCAFall, UP-Fall or MCFD was found; the closest (Saraswat & Malathi, 2024) gives accuracy only.

## 3. Protocol

As fixed in ADR 0012: thresholds (v and the candidate's own) chosen inside each training fold by the maximum Youden index, leave one group out (11 groups), cross-dataset, a fully nested selection, exact McNemar against the baseline, 95 % Wilson intervals, false recoveries and URFD latency. Finalists were frozen on all 170 development videos and run **once** on the hold-out sets. **Short clips and S1:** a hold still running when a clip ends counts as a `caida`; the number of such censored decisions is reported.

**Configurations evaluated:** 16,400 on the development data (15,200 pre-registered + 1,200 for the exploratory S1 + S3), 12 descriptive S1 settings at v = 0.01, 6 frozen configurations on the hold-out sets and 3,100 in the secondary leave-one-dataset-out run. With that many looks a single "significant" development gain is expected by chance; this is why the hold-out test decides.

## 4. Development results (URFD + CAUCAFall, leave one group out, nested)

| Rule set | Configs | Sensitivity (95 % CI) | Specificity (95 % CI) | FN | FP | McNemar all · falls · ADL (b/c, p) | False rec. | URFD latency median | Dev. rule |
|---|---|---|---|---|---|---|---|---|---|
| **Baseline** | 100 | 82.5 % (72.7–89.3) | 78.9 % (69.4–86.0) | 14 | 19 | — | 0/30 | 0.83 s | — |
| S1 hold-and-cancel | 1,200 | 80.0 % (70.0–87.3) | **84.4 % (75.6–90.5)** | 16 | 14 | 2/5 p = 0.45 · 2/0 p = 0.50 · 0/5 p = 0.06 | 0/30 | 2.13 s | **passes** |
| S2 = F3 | 500 | 80.0 % (70.0–87.3) | 80.0 % (70.6–87.0) | 16 | 18 | 2/1 p = 1.00 | 0/30 | 0.83 s | fails (gain < loss) |
| S3 ankle-free path | 100 | **85.0 % (75.6–91.2)** | 71.1 % (61.0–79.5) | 12 | 26 | 14/9 p = 0.41 | 0/30 | 0.75 s | fails (loss > gain) |
| S4 identity jump | 100 | 82.5 % | 78.9 % | 14 | 19 | 0/0 | 0/30 | 0.83 s | passes (no change) |
| S1 + S4 | 1,200 | 80.0 % | 84.4 % | 16 | 14 | 2/5 p = 0.45 | 0/30 | 2.13 s | = S1 |
| S1 + F3 | 6,000 | 77.5 % (67.2–85.3) | 84.4 % | 18 | 14 | 4/5 p = 1.00 | 0/30 | 2.13 s | — |
| S1 + S4 + F3 | 6,000 | 77.5 % | 84.4 % | 18 | 14 | 4/5 p = 1.00 | 0/30 | 2.13 s | — |
| S1 + S3 (exploratory, post hoc) | 1,200 | 81.2 % (71.3–88.3) | 75.6 % (65.8–83.3) | 15 | 22 | 15/11 p = 0.56 | 0/30 | 1.85 s | — |
| Fully nested, pre-registered sets (every fold picks S1) | 15,200 | 80.0 % (70.0–87.3) | 84.4 % (75.6–90.5) | 16 | 14 | 2/5 p = 0.45 | | | |
| Fully nested, all sets (10 folds pick the exploratory S1 + S3) | 16,400 | 75.0 % (64.5–83.2) | 81.1 % (71.8–87.9) | 20 | 17 | 10/6 p = 0.45 | | | |

**By dataset.** S1 changes only CAUCAFall (sensitivity 86.0 → 82.0 %, specificity 84.0 → 94.0 %): it withdraws 3/3 picking-up, 1/3 kneeling and 1/1 walking false alarms and loses subject 2's `Fall_backwards` and `Fall_sitting`, in which the person sits up on the floor (sitting passes the geometric upright test). URFD does not change, because its clips end 0.1–3 s after the `caida`: 39 of S1's detected falls and 12 of its false alarms are **censored holds**. S3 recovers the five URFD falls with a hidden ankle and CAUCAFall subject 8 `Fall_right`, but adds 7 false alarms (URFD lying on the floor and other activities, CAUCAFall sitting, walking, kneeling) and loses 4 CAUCAFall falls through the re-chosen speed (v = 0.15).

**Cross-dataset (sensitivity / specificity):** URFD → CAUCAFall: baseline 46.0 / 94.0, S1 52.0 / 96.0, S3 50.0 / 92.0; CAUCAFall → URFD: baseline 76.7 / 72.5, S1 76.7 / 72.5, S3 93.3 / 65.0.

**Grid edge.** Every fold chose S1's longest hold (D = 5 s), its shortest upright run (U = 0.5 s) and the geometric test (no A6). On all 170 videos at v = 0.01 (descriptive, not nested), U = 1 s removes 1–3 false alarms and loses no fall, and U = 0.5 s removes up to 10 but loses `fall-20` and subject 2's two falls; the strict and geometric tests differ only at D ≥ 3 s (the geometric one withdraws 2–4 more false alarms).

**Finalists:** S1 and S4 (and their combinations with each other and with F3).

## 5. Hold-out, frozen, run once

Configurations frozen on the development data: S1 = v 0.01, D = 5 s, U = 0.5 s, geometric test; S4 = v 0.01, J = 1 length; F3 = v 0.01, T = 10 s. McNemar against the frozen baseline on the same units.

| Rule set | GMDCSA24 sens / spec | UP-Fall sens / spec | MCFD sens / spec (events) | MCFD FA/h | MCFD latency | Pooled McNemar all (b/c, p) |
|---|---|---|---|---|---|---|
| **Baseline** | 91.1 / 65.4 | 68.2 / 63.2 | 47.8 / 87.2 | 114 | 1.08 s | — |
| S1 | 91.1 / **82.7** | **60.0** / 67.6 | **26.6** / 94.1 | 50 | 5.63 s | 110/138 p = 0.09 |
| S4 | 91.1 / 65.4 | 68.2 / 63.2 | 47.3 / 87.8 | 108 | 1.07 s | 5/10 p = 0.30 |
| S1 + S4 | 91.1 / 82.7 | 60.0 / 67.6 | 26.1 / 94.8 | 44 | 5.65 s | 110/143 p = 0.04 |
| S1 + F3 | 88.6 / 82.7 | 60.0 / **100** | 25.5 / 94.3 | 48 | 5.67 s | 110/158 p = 0.004 |
| F3 (comparator) | 88.6 / 72.8 | 68.2 / 95.6 | 47.3 / 87.4 | 112 | 1.07 s | 4/31 p < 0.001 |

95 % intervals and per-activity counts: `resultados/especificidad/holdout.md`. GMDCSA24 with S1: picking up 3 → 0, sitting on the floor 4 → 1, exercise 5 → 3, bed 12 → 9 false alarms, no fall lost. MCFD with S1: crouching 13 → 3, moving down 39 → 4, walking 40 → 9, but lying on a sofa 3 → 17 and moving up 8 → 15.

**Why S1 fails on the hold-out.** (1) UP-Fall frontal camera: 14 falls are withdrawn because, after the fall, the single-person pose follows a **seated bystander** or the faller sitting up, and sitting passes the geometric upright test. (2) MCFD: 46 of the 55 lost fall windows are not withdrawn but emitted 5 s after the trigger, **after the labelled lying period ends** (median lying period 5.5 s; 43 % are shorter than 5 s), so they count as misses and as false alarms of the next period (hence the sofa and moving-up increases). Credited at their trigger instant, S1 would detect 85 of 184 MCFD falls (46.2 %, against 88); this re-scoring is post hoc and only explains the loss. Either way, a 5 s hold is incompatible with the event scoring and adds 4.6 s of latency against a 10 s budget (CA-11.3, CA-16.1).

## 6. Secondary: leave one dataset out (five datasets)

Criteria and units as in ADR 0011; 3,100 configurations (baseline 100, F3 500, S1 1,200, S4 100, S1 + S4 1,200; S1 + F3 was not run here: 6,000 more configurations for a combination already rejected). This run uses the hold-out sets as training folds, so it was done after, and does not change, the decision of section 5. Macro mean over the five held-out datasets, sensitivity / specificity:

| Rule set | Criterion 1 (Youden) | Criterion 2 (max. specificity with sensitivity ≥ 90 %) | Chosen (criterion 2) |
|---|---|---|---|
| Shipped (v = 0.01) | 74.0 / 74.5 | 74.0 / 74.5 | — |
| Baseline (v re-chosen) | 62.3 / 84.5 | 74.0 / 74.5 | v = 0.01 |
| S1 | 58.0 / 85.5 | 73.1 / 76.8 (UP-Fall sens. 68.2 → 63.5) | v = 0.01, D = 2 s, U = 1 s, strict |
| S4 | 64.7 / 79.0 | 73.9 / 74.6 | v = 0.01 |
| S1 + S4 | 58.0 / 85.6 | 72.8 / 76.9 | as S1 |
| F3 (ADR 0011) | 72.6 / 82.9 | 72.6 / 82.9 | v = 0.01, T = 10 s |

When the hold-out sets take part in the selection, the folds pick a much milder S1 (2 s, 1 s, strict test), which gains 2.3 points of macro specificity for 0.9 of sensitivity and still loses 4.7 points of sensitivity on UP-Fall; under the Youden criterion S1 is worse than the re-chosen baseline. F3 remains the best of the opt-in rules for specificity (ADR 0011).

## 7. Decision

| Candidate | Development rule | Hold-out rule (no metric down > 2 points on any set) | Decision |
|---|---|---|---|
| S1 hold-and-cancel | passes | **fails**: UP-Fall −8.2 sens., MCFD −21.2 sens. | Rejected; flag kept off (`retencion_caida_s` unset) |
| S2 = F3 | fails | — (ADR 0011) | Unchanged: opt-in proposal of ADR 0011 |
| S3 ankle-free path | fails | not run | Rejected; flag kept off |
| S4 identity-jump gate | passes (no change) | passes (MCFD −0.5 sens., +0.6 spec., 114 → 108 FA/h) | **Opt-in for the pilot** (`salto_identidad_max = 1.0`); not a default: no significant effect |
| Combinations | — | fail (from S1) | Rejected |

## 8. Threats to validity

- **Adaptive design:** the diagnosis that motivated S1 and S3 used the 170 development videos, and the combinations were defined after the development round; nesting protects the thresholds, not the choice of rules. S1 + S3 is post hoc.
- **Censoring:** the development clips are too short for a 5 s hold; S1's development gain comes only from CAUCAFall, and 51 of its decisions there and in URFD are censored. The hold-out test is the fair test of S1, and it failed.
- **Grid edge:** S1's chosen D and U lie at the edge of the grid.
- **Small samples and clustering:** ±8–10 point intervals on the development data; cameras of one scenario are not independent (McNemar and Wilson treat them as such).
- **Simulated falls by young adults;** no older adults, no long recordings of daily life.

## 9. What would be needed

The failures point to the same missing information as ADR 0010 and 0011: who the pose belongs to (a seated bystander passes as "upright"), and a person's posture over minutes rather than seconds. A hold-and-cancel only works with an upright test that excludes sitting (for example, the hip high relative to a per-camera floor estimate), and must be tested on continuous recordings of daily life from the pilot, where the alarm timing can be scored without clip ends.

## References

Amini, A., Banitsas, K., & Cosmas, J. (2016). A comparison between heuristic and machine learning techniques in fall detection using Kinect v2. *2016 IEEE International Symposium on Medical Measurements and Applications (MeMeA)*, 1–6. https://doi.org/10.1109/MeMeA.2016.7533763

Saraswat, & Malathi. (2024). Pose estimation based fall detection system using MediaPipe. *2024 International Conference on Communication and Signal Processing (ICCSP)*, 1733–1738. https://doi.org/10.1109/ICCSP60870.2024.10543522

The other references (Auvinet et al., 2011; Bourke et al., 2008; Casiez et al., 2012; Debard et al., 2016; Lee & Mihailidis, 2005; Noury et al., 2007; Rougier et al., 2011, 2013; Winter, 2009; Wu, 2000) are listed in [ADR 0012](adr/0012-specificity-study.md).
