# Hold-out evaluation on GMDCSA24

Videos: 160 (79 falls, 81 ADL) · Poses: `lite-video-8fps-jpeg` · Dataset: GMDCSA24 v2.1, https://doi.org/10.5281/zenodo.13354453

A video is a true positive if it has at least one `caida` event; an ADL video with any `caida` is a false positive. Intervals: 95 % Wilson.

## 1. Main result: frozen shipped thresholds (no recalibration)

Thresholds: `{'velocidad_descenso_min': 0.01, 'angulo_linea_central_max_grados': 45.0, 'razon_ancho_alto_min': 1.0, 'intervalo_velocidad_s': 0.25, 'ventana_velocidad_s': 1.0, 'persistencia_erguido_s': 1.0, 'ventana_reaccion_s': 1.48, 'confirmacion_suelo_s': 30.0, 'descenso_caida_lenta_min': 0.4, 'ventana_caida_lenta_s': 10.0, 'permanencia_caida_lenta_s': 2.0, 'sin_deteccion_confiable_s': 300.0, 'visibilidad_min': 0.5}`; without R9 = `descenso_caida_lenta_min = 1e+09` (R9 never fires).

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Without R9 (R4–R8) | 79 | 81 | 69 | 10 | 53 | 28 | 87.3% (78.2%–93.0%) | 65.4% (54.6%–74.9%) | 76.2% (69.1%–82.2%) | 71.1% (61.4%–79.2%) | 0.784 |
| **With R9 (shipped)** | 79 | 81 | 72 | 7 | 53 | 28 | 91.1% (82.8%–95.6%) | 65.4% (54.6%–74.9%) | 78.1% (71.1%–83.8%) | 72.0% (62.5%–79.9%) | 0.804 |
| Without R9, onset-aware | 79 | 81 | 68 | 11 | 53 | 28 | 86.1% (76.8%–92.0%) | 65.4% (54.6%–74.9%) | 75.6% (68.4%–81.6%) | 70.8% (61.1%–79.0%) | 0.777 |
| With R9, onset-aware | 79 | 81 | 71 | 8 | 53 | 28 | 89.9% (81.3%–94.8%) | 65.4% (54.6%–74.9%) | 77.5% (70.4%–83.3%) | 71.7% (62.2%–79.6%) | 0.798 |

F1 has no interval; precision depends on the 79/81 fall/ADL mix of the dataset, not on the prevalence of falls in a home.

**Onset-aware** (a stricter check, same thresholds): a fall video counts as detected only if a `caida` comes no earlier than 1 s before the labelled fall onset, so a `caida` fired while the person was still lying on the bed or standing before the fall does not count. Fall videos whose first `caida` is earlier than that:

- S2-Fall-11 (onset 5.9 s, Falling from bed to ground): caida@2.3s
- S2-Fall-13 (onset 2.5 s, Falling backward (side view)): caida@0.4s recuperacion@1.9s caida@3.8s

### Other events

- Without R9: false recoveries 1 of 78 falls in which nobody gets up (per the labels); daily activities with a `movimiento_inestable` 0 of 81; falls with `caida_confirmada` 0 of 79 (clips last at most 17.5 s, shorter than the 30 s confirmation).
  - false recovery in S2-Fall-13 (labelled onset 2.5 s): caida@0.4s recuperacion@1.9s caida@3.8s
- With R9: false recoveries 1 of 78 falls in which nobody gets up (per the labels); daily activities with a `movimiento_inestable` 0 of 81; falls with `caida_confirmada` 0 of 79 (clips last at most 17.5 s, shorter than the 30 s confirmation).
  - false recovery in S2-Fall-13 (labelled onset 2.5 s): caida@0.4s recuperacion@1.9s caida@3.8s

### Detection latency (labelled fall onset → first onset-aware `caida`)

- Without R9: n = 67, median 0.71 s, mean 0.91 s, p95 3.03 s, range -0.73 to 3.60 s
- With R9: n = 70, median 0.76 s, mean 1.00 s, p95 3.27 s, range -0.73 to 3.60 s

The onset is the start of the first `Falling` interval of the GMDCSA24 labels, given to 0.1 s by hand. A negative value means the `caida` came before the labelled onset (at most 1 s, by the onset-aware rule). 1 fall has no onset label and is left out.

### Falls by direction label

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| fall backward | 28 | 22 | 24 |
| fall forward | 23 | 20 | 21 |
| fall sideways | 28 | 27 | 27 |

### Falls by landing surface (from the description)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| onto the bed | 11 | 11 | 11 |
| onto the floor | 68 | 58 | 61 |

### False alarms by daily activity (`caida` = false alarm)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| exercise (push-ups, bending, arms) | 11 | 5 | 5 |
| lying down on / getting up from the bed | 12 | 12 | 12 |
| lying down on / getting up from the floor | 2 | 1 | 1 |
| picking up an object (mostly from the floor) | 12 | 3 | 3 |
| sitting on / getting up from the floor | 11 | 4 | 4 |
| sitting on a bed or chair | 25 | 3 | 3 |
| walking or standing | 8 | 0 | 0 |

### By subject and room (falls: detections; ADL: false alarms)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| S1 · room 1 (camera at 70 or 90 cm, two positions) · ADL | 16 | 6 | 6 |
| S1 · room 1 (camera at 70 or 90 cm, two positions) · falls | 16 | 15 | 15 |
| S2 · room 2 (camera at 135 cm) · ADL | 23 | 10 | 10 |
| S2 · room 2 (camera at 135 cm) · falls | 25 | 21 | 23 |
| S3 · room 2 (camera at 135 cm) · ADL | 22 | 6 | 6 |
| S3 · room 2 (camera at 135 cm) · falls | 21 | 18 | 19 |
| S4 · room 3 (camera at 64 cm) · ADL | 20 | 6 | 6 |
| S4 · room 3 (camera at 64 cm) · falls | 17 | 15 | 15 |

### By lighting (falls: detections; ADL: false alarms)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| day · ADL | 51 | 16 | 16 |
| day · falls | 62 | 55 | 57 |
| day, lights off · ADL | 12 | 4 | 4 |
| day, lights off · falls | 6 | 5 | 5 |
| night · ADL | 18 | 8 | 8 |
| night · falls | 11 | 9 | 10 |

### Videos with an error (with R9)

- S1-Fall-14 (missed fall, fall backward): Standing position to falling. Backward fall. Full body (both ankles) is not visible → no events
- S1-ADL-01 (false alarm, lying down on / getting up from the bed): Sitting on the bed to sleeping right side on the bed. Face towards camera → caida@1.7s
- S1-ADL-02 (false alarm, lying down on / getting up from the bed): Sitting on the bed to sleeping left side on the bed. Face towards the camera → caida@1.0s
- S1-ADL-03 (false alarm, lying down on / getting up from the bed): Sitting on the bed to sleeping left side on the bed. Face towards the ceiling → caida@0.8s
- S1-ADL-04 (false alarm, lying down on / getting up from the bed): From sleeping left side on the bed (Face towards the ceiling) to sitting on the bed → caida@1.0s recuperacion@4.0s
- S1-ADL-05 (false alarm, sitting on a bed or chair): Coming to the bed and reading book in the sitting position. Front view of the subject. One leg folded → caida@5.0s recuperacion@7.4s
- S1-ADL-06 (false alarm, sitting on a bed or chair): Sitting on the bed (front view) to reading the book while supporting towards the wall. Side view → caida@2.7s
- S2-Fall-05 (missed fall, fall sideways): Left side fall (face hidden by hand) → no events
- S2-Fall-08 (missed fall, fall backward): Reading a newspaper in the sitting position on the ground then falling backward → no events
- S2-ADL-02 (false alarm, picking up an object (mostly from the floor)): Picking up a water bottle from the ground and drinking while sitting on the bed → caida@7.5s recuperacion@8.8s
- S2-ADL-03 (false alarm, lying down on / getting up from the bed): Walking; removing dust from the bed using a pillow; and sleeping on the bed → caida@8.7s
- S2-ADL-08 (false alarm, exercise (push-ups, bending, arms)): Exercising (Stretching thigh and trying to touch the ground:Pyramid Pose) → caida@1.9s recuperacion@4.8s caida@7.1s recuperacion@10.4s
- S2-ADL-12 (false alarm, lying down on / getting up from the bed): Going to bed and sleeping (belly facing downwards) → caida@3.1s
- S2-ADL-13 (false alarm, sitting on / getting up from the floor): Sitting on the ground and reading a book → caida@1.1s
- S2-ADL-16 (false alarm, lying down on / getting up from the bed): Reading a newspaper; throwing the newspaper; and sleeping → caida@0.5s
- S2-ADL-17 (false alarm, sitting on a bed or chair): Standing up from bed; walking; and checking the dress on the hanger → caida@1.7s recuperacion@3.7s
- S2-ADL-19 (false alarm, sitting on / getting up from the floor): Sitting on the ground and writing in a notebook → caida@1.5s
- S2-ADL-20 (false alarm, picking up an object (mostly from the floor)): Standing up; picking up a water bottle; and drinking water while sitting on the ground → caida@4.1s
- S2-ADL-22 (false alarm, exercise (push-ups, bending, arms)): Exercising (Push-up) and sitting → caida@4.9s
- S3-Fall-13 (missed fall, fall backward): Writing something in a notebook while sitting position on the floor; then falling backward → no events
- S3-Fall-15 (missed fall, fall backward): Trying to drink water from the water bottle and then falling on the floor → no events
- S3-ADL-03 (false alarm, lying down on / getting up from the bed): Getting up from the sleeping position from the bed; Putting a mask on the face; then walking → caida@0.3s recuperacion@3.5s
- S3-ADL-06 (false alarm, exercise (push-ups, bending, arms)): Exercising then sitting down on the floor → caida@0.3s recuperacion@3.7s caida@4.4s
- S3-ADL-09 (false alarm, lying down on / getting up from the floor): Sleeping on the floor to sitting and then standing → caida@2.8s
- S3-ADL-13 (false alarm, sitting on / getting up from the floor): Sitting on the floor → caida@0.5s
- S3-ADL-15 (false alarm, sitting on / getting up from the floor): Reading newspaper while sitting on the floor → caida@5.9s
- S3-ADL-19 (false alarm, picking up an object (mostly from the floor)): Picking the pen from the floor and putting it on the bed → caida@0.4s recuperacion@6.3s
- S4-Fall-04 (missed fall, fall forward): Walking then falling (forward) view 2 → no events
- S4-Fall-10 (missed fall, fall forward): Reading a book while sitting on the chair then falling (FW) on the ground → no events
- S4-ADL-06 (false alarm, exercise (push-ups, bending, arms)): Doing exercise (push-up); view 2 → caida@1.5s
- S4-ADL-07 (false alarm, exercise (push-ups, bending, arms)): Doing exercise (push-up); view 3 → caida@0.3s
- S4-ADL-08 (false alarm, lying down on / getting up from the bed): Sleeping to sitting; putting on the goggles and drinking water → caida@1.5s recuperacion@2.9s
- S4-ADL-10 (false alarm, lying down on / getting up from the bed): Walking then sleeping on the bed after removing the goggles → caida@2.5s
- S4-ADL-15 (false alarm, lying down on / getting up from the bed): Sitting to sleeping on the bed → caida@1.1s
- S4-ADL-16 (false alarm, lying down on / getting up from the bed): Sitting on the bed; removing the goggles; then sleeping → caida@3.0s

### Videos that change with R9

- S2-Fall-09 (fall, fall backward): detected only with R9
- S2-Fall-10 (fall, fall backward): detected only with R9
- S3-Fall-01 (fall, fall forward): detected only with R9

## 2. Secondary: leave-one-group-out over all datasets (15 groups)

Not the main result. Each group is evaluated with the speed threshold calibrated by Youden (0.01–1.0, step 0.01, ties → lowest) on the other 14 groups, the same protocol as `evaluar.py --barrer`; every other value stays at its default. It shows whether adding GMDCSA24 to the calibration data changes `v` and the performance.

### With R9 (shipped)

Chosen v per held-out group: Subject.1: 0.12, Subject.10: 0.12, Subject.2: 0.12, Subject.3: 0.12, Subject.4: 0.12, Subject.5: 0.13, Subject.6: 0.12, Subject.7: 0.12, Subject.8: 0.12, Subject.9: 0.12, gmdcsa24-S1: 0.01, gmdcsa24-S2: 0.01, gmdcsa24-S3: 0.09, gmdcsa24-S4: 0.09, urfd: 0.12.

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **All 330 videos (pooled folds)** | 159 | 171 | 126 | 33 | 129 | 42 | 79.2% (72.3%–84.8%) | 75.4% (68.5%–81.3%) | 77.3% (72.5%–81.5%) | 75.0% (67.9%–80.9%) | 0.771 |
| urfd | 30 | 40 | 23 | 7 | 30 | 10 | 76.7% (59.1%–88.2%) | 75.0% (59.8%–85.8%) | 75.7% (64.5%–84.2%) | 69.7% (52.7%–82.6%) | 0.730 |
| caucafall | 50 | 50 | 36 | 14 | 43 | 7 | 72.0% (58.3%–82.5%) | 86.0% (73.8%–93.0%) | 79.0% (70.0%–85.8%) | 83.7% (70.0%–91.9%) | 0.774 |
| gmdcsa24 | 79 | 81 | 67 | 12 | 56 | 25 | 84.8% (75.3%–91.1%) | 69.1% (58.4%–78.1%) | 76.9% (69.8%–82.7%) | 72.8% (63.0%–80.9%) | 0.784 |

Calibrated on all 330 videos (optimistic, not a test): v = 0.12, sensitivity 80.5%, specificity 79.5%.

### Without R9

Chosen v per held-out group: Subject.1: 0.01, Subject.10: 0.01, Subject.2: 0.01, Subject.3: 0.01, Subject.4: 0.01, Subject.5: 0.01, Subject.6: 0.01, Subject.7: 0.01, Subject.8: 0.01, Subject.9: 0.01, gmdcsa24-S1: 0.01, gmdcsa24-S2: 0.01, gmdcsa24-S3: 0.01, gmdcsa24-S4: 0.01, urfd: 0.01.

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **All 330 videos (pooled folds)** | 159 | 171 | 134 | 25 | 126 | 45 | 84.3% (77.8%–89.1%) | 73.7% (66.6%–79.7%) | 78.8% (74.1%–82.9%) | 74.9% (68.0%–80.6%) | 0.793 |
| urfd | 30 | 40 | 23 | 7 | 31 | 9 | 76.7% (59.1%–88.2%) | 77.5% (62.5%–87.7%) | 77.1% (66.0%–85.4%) | 71.9% (54.6%–84.4%) | 0.742 |
| caucafall | 50 | 50 | 42 | 8 | 42 | 8 | 84.0% (71.5%–91.7%) | 84.0% (71.5%–91.7%) | 84.0% (75.6%–89.9%) | 84.0% (71.5%–91.7%) | 0.840 |
| gmdcsa24 | 79 | 81 | 69 | 10 | 53 | 28 | 87.3% (78.2%–93.0%) | 65.4% (54.6%–74.9%) | 76.2% (69.1%–82.2%) | 71.1% (61.4%–79.2%) | 0.784 |

Calibrated on all 330 videos (optimistic, not a test): v = 0.01, sensitivity 84.3%, specificity 73.7%.

## 3. Secondary, post hoc: speed sweep on GMDCSA24 alone (optimistic)

For interpretation only: the threshold is chosen **on the test data**, so this is an upper bound of what recalibrating `v` alone could give, not a test result.

| Classifier | Best v (Youden) | Sensitivity | Specificity | v = 0.05 (sens. / spec.) | v = 0.1 | v = 0.3 |
|---|---|---|---|---|---|---|
| With R9 (shipped) | 0.35 | 78.5% | 87.7% | 86.1% / 70.4% | 84.8% / 75.3% | 78.5% / 86.4% |
| Without R9 | 0.13 | 75.9% | 80.2% | 79.7% / 70.4% | 77.2% / 75.3% | 69.6% / 86.4% |

## 4. Secondary: frame rate (frozen thresholds, GMDCSA24 only)

| fps | Without R9: sens. / spec. / acc. | With R9: sens. / spec. / acc. | Latency with R9 (median) | False recoveries with R9 |
|---|---|---|---|---|
| 6 | 89.9% / 70.4% / 80.0% | 91.1% / 70.4% / 80.6% | 0.79 s | 0/78 |
| 8 | 87.3% / 65.4% / 76.2% | 91.1% / 65.4% / 78.1% | 0.76 s | 1/78 |
| 10 | 87.3% / 69.1% / 78.1% | 91.1% / 69.1% / 80.0% | 0.72 s | 1/78 |
