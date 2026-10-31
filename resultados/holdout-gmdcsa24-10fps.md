# Hold-out evaluation on GMDCSA24

Videos: 160 (79 falls, 81 ADL) · Poses: `lite-video-10fps-jpeg` · Dataset: GMDCSA24 v2.1, https://doi.org/10.5281/zenodo.13354453

A video is a true positive if it has at least one `caida` event; an ADL video with any `caida` is a false positive. Intervals: 95 % Wilson.

## 1. Main result: frozen shipped thresholds (no recalibration)

Thresholds: `{'velocidad_descenso_min': 0.01, 'angulo_linea_central_max_grados': 45.0, 'razon_ancho_alto_min': 1.0, 'intervalo_velocidad_s': 0.25, 'ventana_velocidad_s': 1.0, 'persistencia_erguido_s': 1.0, 'ventana_reaccion_s': 1.48, 'confirmacion_suelo_s': 30.0, 'descenso_caida_lenta_min': 0.4, 'ventana_caida_lenta_s': 10.0, 'permanencia_caida_lenta_s': 2.0, 'sin_deteccion_confiable_s': 300.0, 'visibilidad_min': 0.5}`; without R9 = `descenso_caida_lenta_min = 1e+09` (R9 never fires).

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Without R9 (R4–R8) | 79 | 81 | 69 | 10 | 56 | 25 | 87.3% (78.2%–93.0%) | 69.1% (58.4%–78.1%) | 78.1% (71.1%–83.8%) | 73.4% (63.7%–81.3%) | 0.798 |
| **With R9 (shipped)** | 79 | 81 | 72 | 7 | 56 | 25 | 91.1% (82.8%–95.6%) | 69.1% (58.4%–78.1%) | 80.0% (73.1%–85.5%) | 74.2% (64.7%–81.9%) | 0.818 |
| Without R9, onset-aware | 79 | 81 | 68 | 11 | 56 | 25 | 86.1% (76.8%–92.0%) | 69.1% (58.4%–78.1%) | 77.5% (70.4%–83.3%) | 73.1% (63.3%–81.1%) | 0.791 |
| With R9, onset-aware | 79 | 81 | 71 | 8 | 56 | 25 | 89.9% (81.3%–94.8%) | 69.1% (58.4%–78.1%) | 79.4% (72.5%–84.9%) | 74.0% (64.4%–81.7%) | 0.811 |

F1 has no interval; precision depends on the 79/81 fall/ADL mix of the dataset, not on the prevalence of falls in a home.

**Onset-aware** (a stricter check, same thresholds): a fall video counts as detected only if a `caida` comes no earlier than 1 s before the labelled fall onset, so a `caida` fired while the person was still lying on the bed or standing before the fall does not count. Fall videos whose first `caida` is earlier than that:

- S2-Fall-11 (onset 5.9 s, Falling from bed to ground): caida@2.1s
- S2-Fall-13 (onset 2.5 s, Falling backward (side view)): caida@0.4s recuperacion@1.6s caida@3.8s

### Other events

- Without R9: false recoveries 1 of 78 falls in which nobody gets up (per the labels); daily activities with a `movimiento_inestable` 1 of 81; falls with `caida_confirmada` 0 of 79 (clips last at most 17.5 s, shorter than the 30 s confirmation).
  - false recovery in S2-Fall-13 (labelled onset 2.5 s): caida@0.4s recuperacion@1.6s caida@3.8s
- With R9: false recoveries 1 of 78 falls in which nobody gets up (per the labels); daily activities with a `movimiento_inestable` 1 of 81; falls with `caida_confirmada` 0 of 79 (clips last at most 17.5 s, shorter than the 30 s confirmation).
  - false recovery in S2-Fall-13 (labelled onset 2.5 s): caida@0.4s recuperacion@1.6s caida@3.8s

### Detection latency (labelled fall onset → first onset-aware `caida`)

- Without R9: n = 67, median 0.71 s, mean 0.94 s, p95 3.30 s, range -0.70 to 4.90 s
- With R9: n = 70, median 0.72 s, mean 1.01 s, p95 3.33 s, range -0.70 to 4.60 s

The onset is the start of the first `Falling` interval of the GMDCSA24 labels, given to 0.1 s by hand. A negative value means the `caida` came before the labelled onset (at most 1 s, by the onset-aware rule). 1 fall has no onset label and is left out.

### Falls by direction label

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| fall backward | 28 | 21 | 23 |
| fall forward | 23 | 21 | 22 |
| fall sideways | 28 | 27 | 27 |

### Falls by landing surface (from the description)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| onto the bed | 11 | 10 | 10 |
| onto the floor | 68 | 59 | 62 |

### False alarms by daily activity (`caida` = false alarm)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| exercise (push-ups, bending, arms) | 11 | 5 | 5 |
| lying down on / getting up from the bed | 12 | 12 | 12 |
| lying down on / getting up from the floor | 2 | 1 | 1 |
| picking up an object (mostly from the floor) | 12 | 3 | 3 |
| sitting on / getting up from the floor | 11 | 2 | 2 |
| sitting on a bed or chair | 25 | 2 | 2 |
| walking or standing | 8 | 0 | 0 |

### By subject and room (falls: detections; ADL: false alarms)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| S1 · room 1 (camera at 70 or 90 cm, two positions) · ADL | 16 | 6 | 6 |
| S1 · room 1 (camera at 70 or 90 cm, two positions) · falls | 16 | 15 | 15 |
| S2 · room 2 (camera at 135 cm) · ADL | 23 | 8 | 8 |
| S2 · room 2 (camera at 135 cm) · falls | 25 | 22 | 23 |
| S3 · room 2 (camera at 135 cm) · ADL | 22 | 5 | 5 |
| S3 · room 2 (camera at 135 cm) · falls | 21 | 17 | 19 |
| S4 · room 3 (camera at 64 cm) · ADL | 20 | 6 | 6 |
| S4 · room 3 (camera at 64 cm) · falls | 17 | 15 | 15 |

### By lighting (falls: detections; ADL: false alarms)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| day · ADL | 51 | 15 | 15 |
| day · falls | 62 | 53 | 56 |
| day, lights off · ADL | 12 | 4 | 4 |
| day, lights off · falls | 6 | 6 | 6 |
| night · ADL | 18 | 6 | 6 |
| night · falls | 11 | 10 | 10 |

### Videos with an error (with R9)

- S1-Fall-14 (missed fall, fall backward): Standing position to falling. Backward fall. Full body (both ankles) is not visible → no events
- S1-ADL-01 (false alarm, lying down on / getting up from the bed): Sitting on the bed to sleeping right side on the bed. Face towards camera → caida@1.7s
- S1-ADL-02 (false alarm, lying down on / getting up from the bed): Sitting on the bed to sleeping left side on the bed. Face towards the camera → caida@1.0s
- S1-ADL-03 (false alarm, lying down on / getting up from the bed): Sitting on the bed to sleeping left side on the bed. Face towards the ceiling → caida@1.5s
- S1-ADL-04 (false alarm, lying down on / getting up from the bed): From sleeping left side on the bed (Face towards the ceiling) to sitting on the bed → caida@1.0s recuperacion@3.9s
- S1-ADL-06 (false alarm, sitting on a bed or chair): Sitting on the bed (front view) to reading the book while supporting towards the wall. Side view → caida@2.8s
- S1-ADL-16 (false alarm, picking up an object (mostly from the floor)): Picking the mobile phone from the ground while sitting on the chair → caida@1.3s recuperacion@2.7s
- S2-Fall-05 (missed fall, fall sideways): Left side fall (face hidden by hand) → no events
- S2-Fall-08 (missed fall, fall backward): Reading a newspaper in the sitting position on the ground then falling backward → no events
- S2-ADL-03 (false alarm, lying down on / getting up from the bed): Walking; removing dust from the bed using a pillow; and sleeping on the bed → caida@8.3s
- S2-ADL-08 (false alarm, exercise (push-ups, bending, arms)): Exercising (Stretching thigh and trying to touch the ground:Pyramid Pose) → caida@2.1s recuperacion@4.7s caida@7.1s recuperacion@10.4s
- S2-ADL-12 (false alarm, lying down on / getting up from the bed): Going to bed and sleeping (belly facing downwards) → caida@3.2s
- S2-ADL-13 (false alarm, sitting on / getting up from the floor): Sitting on the ground and reading a book → caida@1.1s
- S2-ADL-16 (false alarm, lying down on / getting up from the bed): Reading a newspaper; throwing the newspaper; and sleeping → caida@0.7s
- S2-ADL-17 (false alarm, sitting on a bed or chair): Standing up from bed; walking; and checking the dress on the hanger → caida@1.3s recuperacion@3.5s
- S2-ADL-20 (false alarm, picking up an object (mostly from the floor)): Standing up; picking up a water bottle; and drinking water while sitting on the ground → caida@4.1s
- S2-ADL-22 (false alarm, exercise (push-ups, bending, arms)): Exercising (Push-up) and sitting → caida@4.9s
- S3-Fall-13 (missed fall, fall backward): Writing something in a notebook while sitting position on the floor; then falling backward → no events
- S3-Fall-15 (missed fall, fall backward): Trying to drink water from the water bottle and then falling on the floor → no events
- S3-ADL-03 (false alarm, lying down on / getting up from the bed): Getting up from the sleeping position from the bed; Putting a mask on the face; then walking → caida@0.6s recuperacion@3.6s
- S3-ADL-06 (false alarm, exercise (push-ups, bending, arms)): Exercising then sitting down on the floor → caida@0.3s recuperacion@3.6s caida@4.4s
- S3-ADL-09 (false alarm, lying down on / getting up from the floor): Sleeping on the floor to sitting and then standing → caida@3.0s recuperacion@7.7s
- S3-ADL-13 (false alarm, sitting on / getting up from the floor): Sitting on the floor → caida@0.3s
- S3-ADL-19 (false alarm, picking up an object (mostly from the floor)): Picking the pen from the floor and putting it on the bed → caida@1.5s recuperacion@4.3s
- S4-Fall-09 (missed fall, fall backward): Falling backward on the bed from sitting on the bed → no events
- S4-Fall-10 (missed fall, fall forward): Reading a book while sitting on the chair then falling (FW) on the ground → no events
- S4-ADL-06 (false alarm, exercise (push-ups, bending, arms)): Doing exercise (push-up); view 2 → caida@1.5s
- S4-ADL-07 (false alarm, exercise (push-ups, bending, arms)): Doing exercise (push-up); view 3 → caida@0.3s
- S4-ADL-08 (false alarm, lying down on / getting up from the bed): Sleeping to sitting; putting on the goggles and drinking water → caida@1.5s recuperacion@2.8s
- S4-ADL-10 (false alarm, lying down on / getting up from the bed): Walking then sleeping on the bed after removing the goggles → caida@5.1s
- S4-ADL-15 (false alarm, lying down on / getting up from the bed): Sitting to sleeping on the bed → caida@1.1s
- S4-ADL-16 (false alarm, lying down on / getting up from the bed): Sitting on the bed; removing the goggles; then sleeping → caida@2.9s

### Videos that change with R9

- S2-Fall-09 (fall, fall backward): detected only with R9
- S3-Fall-01 (fall, fall forward): detected only with R9
- S3-Fall-05 (fall, fall backward): detected only with R9
