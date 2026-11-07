# Hold-out evaluation on UP-Fall (subset)

Videos: 238 (170 falls, 68 without a fall) · Poses: `lite-video-8fps-jpeg` · Dataset: UP-Fall Detection Dataset (Martínez-Villaseñor et al., 2019, https://doi.org/10.3390/s19091988), subset: trial 1, activities 1–5, 9 and 11, cameras 1 and 2

Intervals: 95 % Wilson. Nothing was calibrated on this dataset for sections 1 and 2.

## 1. Main result: frozen shipped thresholds, each camera on its own

Thresholds: `{'velocidad_descenso_min': 0.01, 'angulo_linea_central_max_grados': 45.0, 'razon_ancho_alto_min': 1.0, 'intervalo_velocidad_s': 0.25, 'ventana_velocidad_s': 1.0, 'persistencia_erguido_s': 1.0, 'ventana_reaccion_s': 1.48, 'confirmacion_suelo_s': 30.0, 'descenso_caida_lenta_min': 0.4, 'ventana_caida_lenta_s': 10.0, 'permanencia_caida_lenta_s': 2.0, 'sin_deteccion_confiable_s': 300.0, 'visibilidad_min': 0.5}`; without R9 = `descenso_caida_lenta_min = 1e+09`.

Unit: one camera recording of one trial (a video). A fall video is a TP if it has at least one `caida`; an ADL video with any `caida` is a FP. UP-Fall has no per-frame fall onset in its camera data, so there is no onset-aware check and no latency.

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Without R9 (R4–R8), all cameras pooled | 170 | 68 | 110 | 60 | 43 | 25 | 64.7% (57.3%–71.5%) | 63.2% (51.4%–73.7%) | 64.3% (58.0%–70.1%) | 81.5% (74.1%–87.1%) | 0.721 |
| Without R9 (R4–R8), camera 1 (lateral view) | 85 | 34 | 63 | 22 | 19 | 15 | 74.1% (63.9%–82.2%) | 55.9% (39.5%–71.1%) | 68.9% (60.1%–76.5%) | 80.8% (70.7%–88.0%) | 0.773 |
| Without R9 (R4–R8), camera 2 (frontal view) | 85 | 34 | 47 | 38 | 24 | 10 | 55.3% (44.7%–65.4%) | 70.6% (53.8%–83.2%) | 59.7% (50.7%–68.0%) | 82.5% (70.6%–90.2%) | 0.662 |
| **With R9 (shipped)**, all cameras pooled | 170 | 68 | 116 | 54 | 43 | 25 | 68.2% (60.9%–74.8%) | 63.2% (51.4%–73.7%) | 66.8% (60.6%–72.5%) | 82.3% (75.1%–87.7%) | 0.746 |
| **With R9 (shipped)**, camera 1 (lateral view) | 85 | 34 | 67 | 18 | 19 | 15 | 78.8% (69.0%–86.2%) | 55.9% (39.5%–71.1%) | 72.3% (63.6%–79.5%) | 81.7% (72.0%–88.6%) | 0.802 |
| **With R9 (shipped)**, camera 2 (frontal view) | 85 | 34 | 49 | 36 | 24 | 10 | 57.6% (47.0%–67.6%) | 70.6% (53.8%–83.2%) | 61.3% (52.4%–69.6%) | 83.1% (71.5%–90.5%) | 0.681 |

F1 has no interval; precision depends on the 170/68 fall/ADL mix.

### Per activity and camera (falls: detections; ADL: false alarms)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| activity 1 · falling forward using hands · camera 1 (lateral view) | 17 | 13 | 13 |
| activity 1 · falling forward using hands · camera 2 (frontal view) | 17 | 16 | 16 |
| activity 11 · laying · camera 1 (lateral view) | 17 | 14 | 14 |
| activity 11 · laying · camera 2 (frontal view) | 17 | 8 | 8 |
| activity 2 · falling forward using knees · camera 1 (lateral view) | 17 | 4 | 6 |
| activity 2 · falling forward using knees · camera 2 (frontal view) | 17 | 11 | 12 |
| activity 3 · falling backwards · camera 1 (lateral view) | 17 | 17 | 17 |
| activity 3 · falling backwards · camera 2 (frontal view) | 17 | 9 | 9 |
| activity 4 · falling sideward · camera 1 (lateral view) | 17 | 16 | 16 |
| activity 4 · falling sideward · camera 2 (frontal view) | 17 | 2 | 3 |
| activity 5 · falling sitting in empty chair · camera 1 (lateral view) | 17 | 13 | 15 |
| activity 5 · falling sitting in empty chair · camera 2 (frontal view) | 17 | 9 | 9 |
| activity 9 · picking up an object · camera 1 (lateral view) | 17 | 1 | 1 |
| activity 9 · picking up an object · camera 2 (frontal view) | 17 | 2 | 2 |

### Per subject (falls: detections; ADL: false alarms; both cameras)

| Group | Videos | `caida` without R9 | `caida` with R9 |
|---|---|---|---|
| S01 · ADL | 4 | 2 | 2 |
| S01 · falls | 10 | 9 | 9 |
| S02 · ADL | 4 | 1 | 1 |
| S02 · falls | 10 | 6 | 6 |
| S03 · ADL | 4 | 2 | 2 |
| S03 · falls | 10 | 8 | 8 |
| S04 · ADL | 4 | 1 | 1 |
| S04 · falls | 10 | 7 | 7 |
| S05 · ADL | 4 | 0 | 0 |
| S05 · falls | 10 | 5 | 5 |
| S06 · ADL | 4 | 2 | 2 |
| S06 · falls | 10 | 5 | 5 |
| S07 · ADL | 4 | 2 | 2 |
| S07 · falls | 10 | 8 | 8 |
| S08 · ADL | 4 | 2 | 2 |
| S08 · falls | 10 | 6 | 6 |
| S09 · ADL | 4 | 2 | 2 |
| S09 · falls | 10 | 7 | 7 |
| S10 · ADL | 4 | 2 | 2 |
| S10 · falls | 10 | 6 | 6 |
| S11 · ADL | 4 | 0 | 0 |
| S11 · falls | 10 | 5 | 6 |
| S12 · ADL | 4 | 0 | 0 |
| S12 · falls | 10 | 4 | 5 |
| S13 · ADL | 4 | 1 | 1 |
| S13 · falls | 10 | 8 | 10 |
| S14 · ADL | 4 | 1 | 1 |
| S14 · falls | 10 | 8 | 8 |
| S15 · ADL | 4 | 2 | 2 |
| S15 · falls | 10 | 5 | 7 |
| S16 · ADL | 4 | 2 | 2 |
| S16 · falls | 10 | 6 | 6 |
| S17 · ADL | 4 | 3 | 3 |
| S17 · falls | 10 | 7 | 7 |

### Other events

- Without R9: fall videos with a `recuperacion` after their first `caida`: 12 of 170 (UP-Fall does not label getting up; the 10 s fall trials leave a 6 s safe period on the mattress); ADL videos with a `movimiento_inestable`: 3 of 68.
  - S11-A01-T1-C2: caida@1.5s recuperacion@3.1s
  - S12-A01-T1-C2: caida@1.4s recuperacion@2.9s
  - S14-A01-T1-C2: caida@2.3s recuperacion@3.7s
  - S14-A02-T1-C2: caida@2.1s recuperacion@4.8s
  - S15-A01-T1-C2: caida@1.3s recuperacion@2.5s
  - S15-A02-T1-C2: caida@0.9s recuperacion@2.4s
  - S17-A01-T1-C2: caida@1.7s recuperacion@9.1s
  - S02-A01-T1-C2: caida@1.8s recuperacion@4.2s
  - S04-A01-T1-C2: caida@2.4s recuperacion@3.8s
  - S08-A01-T1-C2: caida@1.8s recuperacion@3.8s
  - S08-A03-T1-C2: caida@2.4s recuperacion@4.1s
  - S08-A05-T1-C2: movimiento_inestable@2.1s caida@2.4s recuperacion@4.4s
- With R9: fall videos with a `recuperacion` after their first `caida`: 12 of 170 (UP-Fall does not label getting up; the 10 s fall trials leave a 6 s safe period on the mattress); ADL videos with a `movimiento_inestable`: 3 of 68.
  - S11-A01-T1-C2: caida@1.5s recuperacion@3.1s
  - S12-A01-T1-C2: caida@1.4s recuperacion@2.9s
  - S14-A01-T1-C2: caida@2.3s recuperacion@3.7s
  - S14-A02-T1-C2: caida@2.1s recuperacion@4.8s
  - S15-A01-T1-C2: caida@1.3s recuperacion@2.5s
  - S15-A02-T1-C2: caida@0.9s recuperacion@2.4s
  - S17-A01-T1-C2: caida@1.7s recuperacion@9.1s
  - S02-A01-T1-C2: caida@1.8s recuperacion@4.2s
  - S04-A01-T1-C2: caida@2.4s recuperacion@3.8s
  - S08-A01-T1-C2: caida@1.8s recuperacion@3.8s
  - S08-A03-T1-C2: caida@2.4s recuperacion@4.1s
  - S08-A05-T1-C2: movimiento_inestable@2.1s caida@2.4s recuperacion@4.4s

Instant of the first `caida` in the detected fall videos, from the start of the 10 s trial (with R9; descriptive, not a latency): median 2.27 s, range 0.53–9.03 s.

### Diagnostic: the bystander in camera 2

In camera 2 (frontal) a second person sits at the right edge of the image. Videos in which the mid-hip of the tracked pose is at x > 0.75 (that edge) in more than half of the pose frames, i.e. the pose follows the bystander rather than the subject (a heuristic checked by eye on two videos, not a per-frame label):

| Camera · group (with R9) | Videos | Pose on the bystander |
|---|---|---|
| camera 1 (lateral view) · falls detected | 67 | 0 |
| camera 1 (lateral view) · falls missed | 18 | 0 |
| camera 1 (lateral view) · ADL with a false alarm | 15 | 0 |
| camera 1 (lateral view) · ADL without | 19 | 0 |
| camera 2 (frontal view) · falls detected | 49 | 12 |
| camera 2 (frontal view) · falls missed | 36 | 25 |
| camera 2 (frontal view) · ADL with a false alarm | 10 | 1 |
| camera 2 (frontal view) · ADL without | 24 | 3 |

### Videos with an error (with R9)

- S10-A11-T1-C1 (false alarm, laying): caida@1.0s caida_confirmada@31.1s
- S10-A11-T1-C2 (false alarm, laying): caida@0.3s caida_confirmada@30.5s
- S10-A02-T1-C1 (missed fall, falling forward using knees): no events
- S10-A02-T1-C2 (missed fall, falling forward using knees): no events
- S10-A03-T1-C2 (missed fall, falling backwards): no events
- S10-A04-T1-C2 (missed fall, falling sideward): no events
- S11-A02-T1-C1 (missed fall, falling forward using knees): no events
- S11-A03-T1-C2 (missed fall, falling backwards): no events
- S11-A04-T1-C2 (missed fall, falling sideward): no events
- S11-A05-T1-C2 (missed fall, falling sitting in empty chair): no events
- S12-A02-T1-C1 (missed fall, falling forward using knees): no events
- S12-A02-T1-C2 (missed fall, falling forward using knees): no events
- S12-A03-T1-C2 (missed fall, falling backwards): no events
- S12-A04-T1-C2 (missed fall, falling sideward): no events
- S12-A05-T1-C2 (missed fall, falling sitting in empty chair): no events
- S13-A11-T1-C1 (false alarm, laying): caida@0.3s caida_confirmada@30.4s
- S14-A11-T1-C1 (false alarm, laying): caida@0.6s caida_confirmada@30.8s
- S14-A04-T1-C2 (missed fall, falling sideward): no events
- S14-A05-T1-C2 (missed fall, falling sitting in empty chair): no events
- S15-A11-T1-C1 (false alarm, laying): caida@0.3s caida_confirmada@30.3s
- S15-A03-T1-C2 (missed fall, falling backwards): no events
- S15-A04-T1-C2 (missed fall, falling sideward): no events
- S15-A05-T1-C2 (missed fall, falling sitting in empty chair): no events
- S15-A09-T1-C2 (false alarm, picking up an object): caida@0.9s recuperacion@2.5s
- S16-A11-T1-C1 (false alarm, laying): caida@2.6s caida_confirmada@32.6s
- S16-A11-T1-C2 (false alarm, laying): caida@1.8s recuperacion@12.7s
- S16-A01-T1-C2 (missed fall, falling forward using hands): no events
- S16-A02-T1-C1 (missed fall, falling forward using knees): no events
- S16-A03-T1-C2 (missed fall, falling backwards): no events
- S16-A04-T1-C2 (missed fall, falling sideward): no events
- S17-A11-T1-C1 (false alarm, laying): caida@0.7s caida_confirmada@30.7s
- S17-A03-T1-C2 (missed fall, falling backwards): no events
- S17-A04-T1-C2 (missed fall, falling sideward): no events
- S17-A05-T1-C2 (missed fall, falling sitting in empty chair): no events
- S17-A09-T1-C1 (false alarm, picking up an object): caida@1.5s recuperacion@3.1s
- S17-A09-T1-C2 (false alarm, picking up an object): caida@1.9s recuperacion@3.1s
- S01-A11-T1-C1 (false alarm, laying): caida@0.3s caida_confirmada@30.3s
- S01-A11-T1-C2 (false alarm, laying): caida@7.7s caida_confirmada@37.7s
- S01-A04-T1-C2 (missed fall, falling sideward): no events
- S02-A11-T1-C1 (false alarm, laying): caida@30.2s
- S02-A02-T1-C1 (missed fall, falling forward using knees): no events
- S02-A03-T1-C2 (missed fall, falling backwards): no events
- S02-A04-T1-C2 (missed fall, falling sideward): no events
- S02-A05-T1-C2 (missed fall, falling sitting in empty chair): no events
- S03-A11-T1-C1 (false alarm, laying): caida@0.5s caida_confirmada@30.6s
- S03-A11-T1-C2 (false alarm, laying): caida@1.2s caida_confirmada@31.2s
- S03-A04-T1-C2 (missed fall, falling sideward): no events
- S03-A05-T1-C1 (missed fall, falling sitting in empty chair): no events
- S04-A11-T1-C1 (false alarm, laying): caida@0.6s caida_confirmada@30.7s
- S04-A02-T1-C1 (missed fall, falling forward using knees): no events
- S04-A04-T1-C1 (missed fall, falling sideward): no events
- S04-A05-T1-C2 (missed fall, falling sitting in empty chair): no events
- S05-A01-T1-C1 (missed fall, falling forward using hands): no events
- S05-A02-T1-C1 (missed fall, falling forward using knees): no events
- S05-A02-T1-C2 (missed fall, falling forward using knees): no events
- S05-A04-T1-C2 (missed fall, falling sideward): no events
- S05-A05-T1-C1 (missed fall, falling sitting in empty chair): no events
- S06-A11-T1-C1 (false alarm, laying): caida@0.9s caida_confirmada@31.0s
- S06-A11-T1-C2 (false alarm, laying): caida@0.7s caida_confirmada@30.7s
- S06-A01-T1-C1 (missed fall, falling forward using hands): no events
- S06-A02-T1-C1 (missed fall, falling forward using knees): no events
- S06-A03-T1-C2 (missed fall, falling backwards): no events
- S06-A04-T1-C2 (missed fall, falling sideward): no events
- S06-A05-T1-C2 (missed fall, falling sitting in empty chair): no events
- S07-A11-T1-C1 (false alarm, laying): caida@11.6s caida_confirmada@41.7s
- S07-A11-T1-C2 (false alarm, laying): caida@11.9s caida_confirmada@41.9s
- S07-A02-T1-C1 (missed fall, falling forward using knees): no events
- S07-A02-T1-C2 (missed fall, falling forward using knees): no events
- S08-A11-T1-C1 (false alarm, laying): caida@0.3s caida_confirmada@30.3s
- S08-A11-T1-C2 (false alarm, laying): caida@2.5s caida_confirmada@32.6s
- S08-A01-T1-C1 (missed fall, falling forward using hands): no events
- S08-A02-T1-C1 (missed fall, falling forward using knees): no events
- S08-A02-T1-C2 (missed fall, falling forward using knees): no events
- S08-A04-T1-C2 (missed fall, falling sideward): no events
- S09-A11-T1-C1 (false alarm, laying): caida@0.4s caida_confirmada@30.4s
- S09-A11-T1-C2 (false alarm, laying): caida@2.5s caida_confirmada@32.6s
- S09-A01-T1-C1 (missed fall, falling forward using hands): no events
- S09-A02-T1-C1 (missed fall, falling forward using knees): no events
- S09-A04-T1-C2 (missed fall, falling sideward): no events

### Videos that change with R9

- S11-A02-T1-C2 (falling forward using knees): detected only with R9
- S12-A05-T1-C1 (falling sitting in empty chair): detected only with R9
- S13-A02-T1-C1 (falling forward using knees): detected only with R9
- S13-A04-T1-C2 (falling sideward): detected only with R9
- S15-A02-T1-C1 (falling forward using knees): detected only with R9
- S15-A05-T1-C1 (falling sitting in empty chair): detected only with R9

## 2. Secondary: OR-fusion of the two cameras

Unit: one trial (119 trials). The trial alarms if camera 1 **or** camera 2 has a `caida`. Both cameras share the timestamps of the dataset.

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Without R9, camera 1 or 2 | 85 | 34 | 77 | 8 | 18 | 16 | 90.6% (82.5%–95.2%) | 52.9% (36.7%–68.5%) | 79.8% (71.7%–86.1%) | 82.8% (73.9%–89.1%) | 0.865 |
| Without R9, camera 1 and 2 (both must fire) | 85 | 34 | 33 | 52 | 25 | 9 | 38.8% (29.2%–49.5%) | 73.5% (56.9%–85.4%) | 48.7% (39.9%–57.6%) | 78.6% (64.1%–88.3%) | 0.520 |
| With R9 (shipped), camera 1 or 2 | 85 | 34 | 80 | 5 | 18 | 16 | 94.1% (87.0%–97.5%) | 52.9% (36.7%–68.5%) | 82.4% (74.5%–88.2%) | 83.3% (74.6%–89.5%) | 0.884 |
| With R9 (shipped), camera 1 and 2 (both must fire) | 85 | 34 | 36 | 49 | 25 | 9 | 42.4% (32.4%–53.0%) | 73.5% (56.9%–85.4%) | 51.3% (42.4%–60.1%) | 80.0% (66.2%–89.1%) | 0.554 |

## 3. Secondary: leave-one-group-out recalibration over all datasets (33 groups)

Not the main result. Unit: video (per camera). Each group is evaluated with the speed threshold chosen by Youden (0.01–1.0, step 0.01, ties → lowest) on the other 32 groups; every other value stays at its default. Groups: URFD (1, subjects not published), the 10 CAUCAFall subjects, the 4 GMDCSA24 subjects, the 17 UP-Fall subjects and MCFD (1: a single actor). MCFD fall videos count as detected with any `caida`, as in section 1.1.

### With R9 (shipped)

Chosen v (folds): 0.13 (3), 0.22 (4), 0.26 (2), 0.71 (1), 0.72 (23).

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **All 760 videos (pooled folds)** | 505 | 255 | 328 | 177 | 210 | 45 | 65.0% (60.7%–69.0%) | 82.4% (77.2%–86.5%) | 70.8% (67.5%–73.9%) | 87.9% (84.2%–90.9%) | 0.747 |
| urfd, LOGO | 30 | 40 | 22 | 8 | 31 | 9 | 73.3% (55.6%–85.8%) | 77.5% (62.5%–87.7%) | 75.7% (64.5%–84.2%) | 71.0% (53.4%–83.9%) | 0.721 |
| urfd, frozen v = 0.01 (for comparison) | 30 | 40 | 23 | 7 | 29 | 11 | 76.7% (59.1%–88.2%) | 72.5% (57.2%–83.9%) | 74.3% (63.0%–83.1%) | 67.6% (50.8%–80.9%) | 0.719 |
| caucafall, LOGO | 50 | 50 | 23 | 27 | 45 | 5 | 46.0% (33.0%–59.6%) | 90.0% (78.6%–95.7%) | 68.0% (58.3%–76.3%) | 82.1% (64.4%–92.1%) | 0.590 |
| caucafall, frozen v = 0.01 (for comparison) | 50 | 50 | 43 | 7 | 42 | 8 | 86.0% (73.8%–93.0%) | 84.0% (71.5%–91.7%) | 85.0% (76.7%–90.7%) | 84.3% (72.0%–91.8%) | 0.851 |
| gmdcsa24, LOGO | 79 | 81 | 55 | 24 | 70 | 11 | 69.6% (58.8%–78.7%) | 86.4% (77.3%–92.2%) | 78.1% (71.1%–83.8%) | 83.3% (72.6%–90.4%) | 0.759 |
| gmdcsa24, frozen v = 0.01 (for comparison) | 79 | 81 | 72 | 7 | 53 | 28 | 91.1% (82.8%–95.6%) | 65.4% (54.6%–74.9%) | 78.1% (71.1%–83.8%) | 72.0% (62.5%–79.9%) | 0.804 |
| upfall, LOGO | 170 | 68 | 89 | 81 | 63 | 5 | 52.4% (44.9%–59.7%) | 92.6% (83.9%–96.8%) | 63.9% (57.6%–69.7%) | 94.7% (88.1%–97.7%) | 0.674 |
| upfall, frozen v = 0.01 (for comparison) | 170 | 68 | 116 | 54 | 43 | 25 | 68.2% (60.9%–74.8%) | 63.2% (51.4%–73.7%) | 66.8% (60.6%–72.5%) | 82.3% (75.1%–87.7%) | 0.746 |
| mcfd, LOGO | 176 | 16 | 139 | 37 | 1 | 15 | 79.0% (72.4%–84.3%) | 6.2% (1.1%–28.3%) | 72.9% (66.2%–78.7%) | 90.3% (84.6%–94.0%) | 0.842 |
| mcfd, frozen v = 0.01 (for comparison) | 176 | 16 | 155 | 21 | 1 | 15 | 88.1% (82.4%–92.1%) | 6.2% (1.1%–28.3%) | 81.2% (75.1%–86.1%) | 91.2% (86.0%–94.6%) | 0.896 |

Calibrated on all 760 videos (optimistic, not a test): v = 0.72, sensitivity 60.8%, specificity 91.4%.

### Without R9

Chosen v (folds): 0.01 (3), 0.08 (21), 0.09 (2), 0.12 (5), 0.13 (2).

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **All 760 videos (pooled folds)** | 505 | 255 | 348 | 157 | 187 | 68 | 68.9% (64.7%–72.8%) | 73.3% (67.6%–78.4%) | 70.4% (67.1%–73.5%) | 83.7% (79.8%–86.9%) | 0.756 |
| urfd, LOGO | 30 | 40 | 23 | 7 | 32 | 8 | 76.7% (59.1%–88.2%) | 80.0% (65.2%–89.5%) | 78.6% (67.6%–86.6%) | 74.2% (56.8%–86.3%) | 0.754 |
| urfd, frozen v = 0.01 (for comparison) | 30 | 40 | 23 | 7 | 31 | 9 | 76.7% (59.1%–88.2%) | 77.5% (62.5%–87.7%) | 77.1% (66.0%–85.4%) | 71.9% (54.6%–84.4%) | 0.742 |
| caucafall, LOGO | 50 | 50 | 31 | 19 | 43 | 7 | 62.0% (48.2%–74.1%) | 86.0% (73.8%–93.0%) | 74.0% (64.6%–81.6%) | 81.6% (66.6%–90.8%) | 0.705 |
| caucafall, frozen v = 0.01 (for comparison) | 50 | 50 | 42 | 8 | 42 | 8 | 84.0% (71.5%–91.7%) | 84.0% (71.5%–91.7%) | 84.0% (75.6%–89.9%) | 84.0% (71.5%–91.7%) | 0.840 |
| gmdcsa24, LOGO | 79 | 81 | 61 | 18 | 56 | 25 | 77.2% (66.8%–85.1%) | 69.1% (58.4%–78.1%) | 73.1% (65.8%–79.4%) | 70.9% (60.6%–79.5%) | 0.739 |
| gmdcsa24, frozen v = 0.01 (for comparison) | 79 | 81 | 69 | 10 | 53 | 28 | 87.3% (78.2%–93.0%) | 65.4% (54.6%–74.9%) | 76.2% (69.1%–82.2%) | 71.1% (61.4%–79.2%) | 0.784 |
| upfall, LOGO | 170 | 68 | 82 | 88 | 55 | 13 | 48.2% (40.8%–55.7%) | 80.9% (70.0%–88.5%) | 57.6% (51.2%–63.7%) | 86.3% (78.0%–91.8%) | 0.619 |
| upfall, frozen v = 0.01 (for comparison) | 170 | 68 | 110 | 60 | 43 | 25 | 64.7% (57.3%–71.5%) | 63.2% (51.4%–73.7%) | 64.3% (58.0%–70.1%) | 81.5% (74.1%–87.1%) | 0.721 |
| mcfd, LOGO | 176 | 16 | 151 | 25 | 1 | 15 | 85.8% (79.9%–90.2%) | 6.2% (1.1%–28.3%) | 79.2% (72.9%–84.3%) | 91.0% (85.6%–94.4%) | 0.883 |
| mcfd, frozen v = 0.01 (for comparison) | 176 | 16 | 151 | 25 | 1 | 15 | 85.8% (79.9%–90.2%) | 6.2% (1.1%–28.3%) | 79.2% (72.9%–84.3%) | 91.0% (85.6%–94.4%) | 0.883 |

Calibrated on all 760 videos (optimistic, not a test): v = 0.08, sensitivity 69.7%, specificity 75.7%.
