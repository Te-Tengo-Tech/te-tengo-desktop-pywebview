# Hold-out evaluation on the Multiple Cameras Fall Dataset

Videos: 192 (176 falls, 16 without a fall) · Poses: `lite-video-8fps-jpeg` · Dataset: Multiple Cameras Fall Dataset (Auvinet et al., 2010, technical report 1350, DIRO, Université de Montréal; erratum by Feng and Meunier, 2025)

Intervals: 95 % Wilson. Nothing was calibrated on this dataset for sections 1 and 2.

## 1. Main result: frozen shipped thresholds, each camera on its own

Thresholds: `{'velocidad_descenso_min': 0.01, 'angulo_linea_central_max_grados': 45.0, 'razon_ancho_alto_min': 1.0, 'intervalo_velocidad_s': 0.25, 'ventana_velocidad_s': 1.0, 'persistencia_erguido_s': 1.0, 'ventana_reaccion_s': 1.48, 'confirmacion_suelo_s': 30.0, 'descenso_caida_lenta_min': 0.4, 'ventana_caida_lenta_s': 10.0, 'permanencia_caida_lenta_s': 2.0, 'sin_deteccion_confiable_s': 300.0, 'visibilidad_min': 0.5}`; without R9 = `descenso_caida_lenta_min = 1e+09`.

Videos: 192 (176 with a fall, 16 without), 2.41 h in total at the 30 fps time base.

### 1.1. Per video

Unit: one camera recording of one scenario. A fall scenario's video is a TP if it has any `caida` (the scenarios also contain daily activities before the fall, so this criterion can count a false alarm as a detection); the stricter row needs the `caida` inside a fall window (from 1 s before the labelled `falling` onset to the end of the labelled `lying on the ground` periods after it). Scenarios 23 and 24 (no fall) are the only negative videos: 16 of them.

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Without R9 (R4–R8), all cameras pooled | 176 | 16 | 151 | 25 | 1 | 15 | 85.8% (79.9%–90.2%) | 6.2% (1.1%–28.3%) | 79.2% (72.9%–84.3%) | 91.0% (85.6%–94.4%) | 0.883 |
| Without R9 (R4–R8), camera 1 | 22 | 2 | 19 | 3 | 0 | 2 | 86.4% (66.7%–95.3%) | 0.0% (0.0%–65.8%) | 79.2% (59.5%–90.8%) | 90.5% (71.1%–97.3%) | 0.884 |
| Without R9 (R4–R8), camera 2 | 22 | 2 | 22 | 0 | 0 | 2 | 100.0% (85.1%–100.0%) | 0.0% (0.0%–65.8%) | 91.7% (74.2%–97.7%) | 91.7% (74.2%–97.7%) | 0.957 |
| Without R9 (R4–R8), camera 3 | 22 | 2 | 21 | 1 | 0 | 2 | 95.5% (78.2%–99.2%) | 0.0% (0.0%–65.8%) | 87.5% (69.0%–95.7%) | 91.3% (73.2%–97.6%) | 0.933 |
| Without R9 (R4–R8), camera 4 | 22 | 2 | 18 | 4 | 0 | 2 | 81.8% (61.5%–92.7%) | 0.0% (0.0%–65.8%) | 75.0% (55.1%–88.0%) | 90.0% (69.9%–97.2%) | 0.857 |
| Without R9 (R4–R8), camera 5 | 22 | 2 | 9 | 13 | 0 | 2 | 40.9% (23.3%–61.3%) | 0.0% (0.0%–65.8%) | 37.5% (21.2%–57.3%) | 81.8% (52.3%–94.9%) | 0.545 |
| Without R9 (R4–R8), camera 6 | 22 | 2 | 22 | 0 | 0 | 2 | 100.0% (85.1%–100.0%) | 0.0% (0.0%–65.8%) | 91.7% (74.2%–97.7%) | 91.7% (74.2%–97.7%) | 0.957 |
| Without R9 (R4–R8), camera 7 | 22 | 2 | 19 | 3 | 1 | 1 | 86.4% (66.7%–95.3%) | 50.0% (9.5%–90.5%) | 83.3% (64.1%–93.3%) | 95.0% (76.4%–99.1%) | 0.905 |
| Without R9 (R4–R8), camera 8 | 22 | 2 | 21 | 1 | 0 | 2 | 95.5% (78.2%–99.2%) | 0.0% (0.0%–65.8%) | 87.5% (69.0%–95.7%) | 91.3% (73.2%–97.6%) | 0.933 |
| **With R9 (shipped)**, all cameras pooled | 176 | 16 | 155 | 21 | 1 | 15 | 88.1% (82.4%–92.1%) | 6.2% (1.1%–28.3%) | 81.2% (75.1%–86.1%) | 91.2% (86.0%–94.6%) | 0.896 |
| **With R9 (shipped)**, camera 1 | 22 | 2 | 21 | 1 | 0 | 2 | 95.5% (78.2%–99.2%) | 0.0% (0.0%–65.8%) | 87.5% (69.0%–95.7%) | 91.3% (73.2%–97.6%) | 0.933 |
| **With R9 (shipped)**, camera 2 | 22 | 2 | 22 | 0 | 0 | 2 | 100.0% (85.1%–100.0%) | 0.0% (0.0%–65.8%) | 91.7% (74.2%–97.7%) | 91.7% (74.2%–97.7%) | 0.957 |
| **With R9 (shipped)**, camera 3 | 22 | 2 | 21 | 1 | 0 | 2 | 95.5% (78.2%–99.2%) | 0.0% (0.0%–65.8%) | 87.5% (69.0%–95.7%) | 91.3% (73.2%–97.6%) | 0.933 |
| **With R9 (shipped)**, camera 4 | 22 | 2 | 18 | 4 | 0 | 2 | 81.8% (61.5%–92.7%) | 0.0% (0.0%–65.8%) | 75.0% (55.1%–88.0%) | 90.0% (69.9%–97.2%) | 0.857 |
| **With R9 (shipped)**, camera 5 | 22 | 2 | 10 | 12 | 0 | 2 | 45.5% (26.9%–65.3%) | 0.0% (0.0%–65.8%) | 41.7% (24.5%–61.2%) | 83.3% (55.2%–95.3%) | 0.588 |
| **With R9 (shipped)**, camera 6 | 22 | 2 | 22 | 0 | 0 | 2 | 100.0% (85.1%–100.0%) | 0.0% (0.0%–65.8%) | 91.7% (74.2%–97.7%) | 91.7% (74.2%–97.7%) | 0.957 |
| **With R9 (shipped)**, camera 7 | 22 | 2 | 20 | 2 | 1 | 1 | 90.9% (72.2%–97.5%) | 50.0% (9.5%–90.5%) | 87.5% (69.0%–95.7%) | 95.2% (77.3%–99.2%) | 0.930 |
| **With R9 (shipped)**, camera 8 | 22 | 2 | 21 | 1 | 0 | 2 | 95.5% (78.2%–99.2%) | 0.0% (0.0%–65.8%) | 87.5% (69.0%–95.7%) | 91.3% (73.2%–97.6%) | 0.933 |
| Without R9, all cameras, `caida` inside the fall window | 176 | 16 | 89 | 87 | 1 | 15 | 50.6% (43.2%–57.9%) | 6.2% (1.1%–28.3%) | 46.9% (39.9%–53.9%) | 85.6% (77.6%–91.1%) | 0.636 |
| With R9, all cameras, `caida` inside the fall window | 176 | 16 | 88 | 88 | 1 | 15 | 50.0% (42.7%–57.3%) | 6.2% (1.1%–28.3%) | 46.4% (39.4%–53.4%) | 85.4% (77.4%–91.0%) | 0.631 |

### 1.2. Per event (the main MCFD result)

Unit: a labelled fall (23 per camera: one in each of scenarios 1–22, two in scenario 4) for sensitivity, and a `caida` outside every fall window for false alarms, over all 24 scenarios. Only the labelled span of each video counts (from its first to its last labelled frame): before it the actor is often outside the room, and after it he gets up and other people walk in, unlabelled; a `caida` there is neither a detection nor a false alarm (counted in the last column). The non-fall time is the labelled span minus the fall windows. A `caida` in one of scenario 23's two labelled `falling` periods (frames 1520–1595 and 3574–3614 of camera 8, plus 5 s; both followed by `moving up`, never by `lying on the ground`) is neither: it is listed apart.

| Camera | Falls detected, without R9 (95 % CI) | With R9 (95 % CI) | False alarms without R9 (per hour) | With R9 (per hour) | Non-fall labelled time | Scenario 23 ambiguous `falling` (with R9) | `caida` outside the labelled span (with R9) |
|---|---|---|---|---|---|---|---|
| camera 1 | 9/23 = 39.1% (22.2%–59.2%) | 10/23 = 43.5% (25.6%–63.2%) | 17 (126.0/h) | 19 (140.8/h) | 8.1 min | 0 | 13 |
| camera 2 | 17/23 = 73.9% (53.5%–87.5%) | 17/23 = 73.9% (53.5%–87.5%) | 17 (126.0/h) | 16 (118.6/h) | 8.1 min | 1 | 2 |
| camera 3 | 16/23 = 69.6% (49.1%–84.4%) | 15/23 = 65.2% (44.9%–81.2%) | 18 (133.4/h) | 20 (148.2/h) | 8.1 min | 1 | 8 |
| camera 4 | 11/23 = 47.8% (29.2%–67.0%) | 11/23 = 47.8% (29.2%–67.0%) | 13 (96.4/h) | 13 (96.4/h) | 8.1 min | 0 | 13 |
| camera 5 | 5/23 = 21.7% (9.7%–41.9%) | 6/23 = 26.1% (12.5%–46.5%) | 9 (66.7/h) | 9 (66.7/h) | 8.1 min | 0 | 1 |
| camera 6 | 11/23 = 47.8% (29.2%–67.0%) | 10/23 = 43.5% (25.6%–63.2%) | 17 (126.0/h) | 18 (133.4/h) | 8.1 min | 1 | 5 |
| camera 7 | 11/23 = 47.8% (29.2%–67.0%) | 12/23 = 52.2% (33.0%–70.8%) | 11 (81.5/h) | 11 (81.5/h) | 8.1 min | 0 | 2 |
| camera 8 | 9/23 = 39.1% (22.2%–59.2%) | 7/23 = 30.4% (15.6%–50.9%) | 13 (96.4/h) | 17 (126.0/h) | 8.1 min | 1 | 7 |
| **8 cameras pooled (each on its own)** | 89/184 = 48.4% (41.3%–55.5%) | 88/184 = 47.8% (40.7%–55.0%) | 115 (106.5/h) | 123 (114.0/h) | 64.8 min | 4 | 51 |

Frames of the labelled spans with a pose from MediaPipe: camera 1 79%, camera 2 86%, camera 3 78%, camera 4 66%, camera 5 54%, camera 6 74%, camera 7 90%, camera 8 77%.

### False alarms by labelled activity at the moment of the `caida` (with R9)

| Labelled activity | False alarms (8 cameras) |
|---|---|
| walking, standing up | 45 |
| moving down | 39 |
| sitting | 15 |
| crouching | 13 |
| moving up | 8 |
| lying on a sofa | 3 |

### Per scenario (with R9)

| Scenario | Labelled sequence | Cameras with the fall detected (window) | False alarms (8 cameras) | Cameras with a `caida` (any) |
|---|---|---|---|---|
| 01 | walking, standing up → moving up → falling → lying on the ground | 6/8 | 0 | 7/8 |
| 02 | walking, standing up → falling → lying on the ground | 5/8 | 1 | 6/8 |
| 03 | walking, standing up → falling → lying on the ground | 6/8 | 0 | 6/8 |
| 04 | walking, standing up → falling → lying on the ground → moving up → falling → lying on the ground | 2/8 | 6 | 8/8 |
| 05 | walking, standing up → falling → lying on the ground | 3/8 | 0 | 6/8 |
| 06 | walking, standing up → falling → lying on the ground | 5/8 | 1 | 7/8 |
| 07 | walking, standing up → falling → lying on the ground | 7/8 | 0 | 8/8 |
| 08 | walking, standing up → falling → lying on the ground | 7/8 | 0 | 8/8 |
| 09 | walking, standing up → moving down → sitting → moving up → falling → lying on the ground | 4/8 | 5 | 8/8 |
| 10 | walking, standing up → moving down → falling → lying on the ground | 6/8 | 0 | 6/8 |
| 11 | walking, standing up → falling → lying on the ground | 5/8 | 0 | 7/8 |
| 12 | walking, standing up → falling → lying on the ground | 6/8 | 0 | 7/8 |
| 13 | walking, standing up → moving down → sitting → moving down → lying on a sofa → moving up → falling → lying on the ground | 3/8 | 6 | 8/8 |
| 14 | walking, standing up → moving down → lying on a sofa → moving up → falling → lying on the ground | 1/8 | 7 | 8/8 |
| 15 | walking, standing up → moving down → sitting → moving up → falling → lying on the ground | 2/8 | 6 | 7/8 |
| 16 | walking, standing up → moving down → crouching → moving up → moving down → crouching → moving up → moving down → sitting → moving up → falling → lying on the ground | 2/8 | 7 | 8/8 |
| 17 | walking, standing up → moving down → crouching → moving up → moving down → crouching → moving up → moving down → sitting → moving up → falling → lying on the ground | 2/8 | 6 | 7/8 |
| 18 | walking, standing up → moving down → sitting → moving up → falling → lying on the ground | 1/8 | 2 | 5/8 |
| 19 | walking, standing up → falling → lying on the ground | 4/8 | 2 | 7/8 |
| 20 | walking, standing up → falling → lying on the ground | 7/8 | 2 | 8/8 |
| 21 | walking, standing up → moving down → sitting → moving up → falling → lying on the ground | 2/8 | 6 | 7/8 |
| 22 | walking, standing up → moving down → sitting → moving up → falling → lying on the ground | 2/8 | 6 | 6/8 |
| 23 | walking, standing up → moving down → crouching → moving up → walking, standing up → falling → moving up → walking, standing up → moving down → crouching → moving up → walking, standing up → moving down → lying on a sofa → moving up → walking, standing up → moving down → lying on a sofa → moving up → falling → moving up → moving down → crouching → moving up → walking, standing up → moving down → sitting → moving up → walking, standing up | — | 37 | 7/8 |
| 24 | walking, standing up → moving down → crouching → moving up → walking, standing up → moving down → crouching → moving up → walking, standing up → moving down → crouching → moving up → walking, standing up → moving down → moving up → walking, standing up → moving down → crouching | — | 23 | 8/8 |

### Latency and false recoveries

- Without R9: latency (labelled `falling` onset → first `caida` in the window) n = 89, median 1.10 s, mean 1.37 s, p95 3.77 s, range -0.87 to 5.73 s; false recoveries (a `recuperacion` while the person is labelled on the ground, before the labels end) 0 of 89 detected falls.
- With R9: latency (labelled `falling` onset → first `caida` in the window) n = 88, median 1.08 s, mean 1.36 s, p95 3.53 s, range -0.87 to 5.43 s; false recoveries (a `recuperacion` while the person is labelled on the ground, before the labels end) 0 of 88 detected falls.

Onsets come from the report's frame labels at the assumed 30 fps; one frame is 33 ms.

### Missed fall windows (with R9)

96 missed of 184. State of the classifier at the labelled onset: already on the floor after an earlier `caida` (masked): 52; standing state, no `caida` in the window: 23; no event in the whole video: 21. While the classifier is in `EN_EL_SUELO` after an earlier `caida` (a false alarm or the first fall of scenario 4), a new fall cannot raise another `caida` until a `recuperacion`.

- chute01-cam4 fall 1 (onset 36.1 s): caida@46.9s recuperacion@48.5s
- chute01-cam5 fall 1 (onset 36.8 s): no events
- chute02-cam3 fall 1 (onset 12.6 s): no events
- chute02-cam4 fall 1 (onset 13.2 s): no events
- chute02-cam6 fall 1 (onset 13.7 s): caida@12.3s recuperacion@14.0s caida@26.0s recuperacion@27.9s
- chute03-cam4 fall 1 (onset 20.2 s): no events
- chute03-cam5 fall 1 (onset 20.9 s): no events
- chute04-cam1 fall 1 (onset 9.3 s): caida@13.9s
- chute04-cam1 fall 2 (onset 19.7 s): caida@13.9s
- chute04-cam2 fall 1 (onset 9.5 s): caida@13.1s recuperacion@34.1s
- chute04-cam2 fall 2 (onset 19.9 s): caida@13.1s recuperacion@34.1s
- chute04-cam3 fall 1 (onset 9.5 s): caida@24.8s
- chute04-cam4 fall 1 (onset 6.9 s): caida@10.5s recuperacion@29.9s
- chute04-cam4 fall 2 (onset 17.3 s): caida@10.5s recuperacion@29.9s
- chute04-cam5 fall 1 (onset 9.1 s): caida@13.3s
- chute04-cam5 fall 2 (onset 19.6 s): caida@13.3s
- chute04-cam6 fall 1 (onset 9.6 s): caida@23.1s recuperacion@32.5s
- chute04-cam7 fall 1 (onset 9.6 s): caida@13.3s recuperacion@20.1s
- chute04-cam7 fall 2 (onset 20.1 s): caida@13.3s recuperacion@20.1s
- chute04-cam8 fall 1 (onset 8.7 s): caida@14.3s
- chute04-cam8 fall 2 (onset 19.2 s): caida@14.3s
- chute05-cam1 fall 1 (onset 10.9 s): no events
- chute05-cam3 fall 1 (onset 10.5 s): caida@18.3s recuperacion@19.9s
- chute05-cam5 fall 1 (onset 11.0 s): no events
- chute05-cam7 fall 1 (onset 11.3 s): caida@6.3s
- chute05-cam8 fall 1 (onset 10.4 s): caida@16.5s
- chute06-cam3 fall 1 (onset 23.0 s): caida@18.5s
- chute06-cam4 fall 1 (onset 22.4 s): caida@13.4s recuperacion@15.3s caida@33.1s recuperacion@42.8s
- chute06-cam5 fall 1 (onset 22.4 s): no events
- chute07-cam6 fall 1 (onset 16.4 s): caida@25.6s recuperacion@29.8s
- chute08-cam8 fall 1 (onset 10.9 s): caida@18.6s recuperacion@21.1s
- chute09-cam1 fall 1 (onset 21.5 s): caida@19.0s recuperacion@29.8s
- chute09-cam5 fall 1 (onset 21.4 s): caida@0.9s recuperacion@14.3s
- chute09-cam6 fall 1 (onset 21.3 s): caida@17.1s
- chute09-cam8 fall 1 (onset 20.9 s): caida@16.6s
- chute10-cam5 fall 1 (onset 17.5 s): no events
- chute10-cam8 fall 1 (onset 17.1 s): no events
- chute11-cam2 fall 1 (onset 15.4 s): caida@24.9s
- chute11-cam5 fall 1 (onset 15.2 s): no events
- chute11-cam8 fall 1 (onset 15.6 s): caida@20.9s
- chute12-cam5 fall 1 (onset 20.2 s): no events
- chute12-cam8 fall 1 (onset 20.2 s): caida@27.6s recuperacion@29.8s
- chute13-cam1 fall 1 (onset 27.7 s): caida@15.9s recuperacion@29.4s caida@34.9s recuperacion@37.3s
- chute13-cam4 fall 1 (onset 27.4 s): caida@15.9s recuperacion@36.1s
- chute13-cam5 fall 1 (onset 28.1 s): caida@17.0s recuperacion@37.0s
- chute13-cam6 fall 1 (onset 28.1 s): caida@16.3s recuperacion@38.5s
- chute13-cam8 fall 1 (onset 27.6 s): caida@18.1s recuperacion@37.3s
- chute14-cam1 fall 1 (onset 34.7 s): caida@10.4s recuperacion@16.5s caida@21.1s recuperacion@40.0s caida@41.1s recuperacion@42.9s
- chute14-cam3 fall 1 (onset 34.3 s): caida@28.4s recuperacion@31.1s caida@33.3s recuperacion@42.3s
- chute14-cam4 fall 1 (onset 33.0 s): caida@22.9s recuperacion@41.6s
- chute14-cam5 fall 1 (onset 34.0 s): caida@17.3s recuperacion@44.0s
- chute14-cam6 fall 1 (onset 34.0 s): caida@38.6s recuperacion@45.1s
- chute14-cam7 fall 1 (onset 33.3 s): caida@19.4s recuperacion@41.4s
- chute14-cam8 fall 1 (onset 33.5 s): caida@20.1s recuperacion@42.3s
- chute15-cam1 fall 1 (onset 25.7 s): caida@20.6s
- chute15-cam3 fall 1 (onset 25.8 s): caida@24.6s
- chute15-cam5 fall 1 (onset 26.3 s): no events
- chute15-cam6 fall 1 (onset 26.5 s): caida@18.9s recuperacion@26.1s
- chute15-cam7 fall 1 (onset 25.9 s): caida@18.1s recuperacion@27.9s
- chute15-cam8 fall 1 (onset 25.2 s): caida@19.5s recuperacion@31.6s
- chute16-cam1 fall 1 (onset 30.4 s): caida@2.5s recuperacion@22.9s caida@24.8s recuperacion@33.5s
- chute16-cam2 fall 1 (onset 30.6 s): caida@22.4s recuperacion@24.0s caida@24.8s recuperacion@40.6s
- chute16-cam4 fall 1 (onset 29.7 s): caida@5.8s recuperacion@13.0s
- chute16-cam6 fall 1 (onset 29.9 s): caida@16.0s recuperacion@23.4s caida@24.1s recuperacion@39.4s
- chute16-cam7 fall 1 (onset 29.7 s): movimiento_inestable@20.0s caida@24.3s recuperacion@39.4s
- chute16-cam8 fall 1 (onset 29.7 s): caida@20.5s recuperacion@33.9s
- chute17-cam1 fall 1 (onset 25.0 s): movimiento_inestable@12.4s caida@19.4s recuperacion@31.0s caida@45.8s
- chute17-cam4 fall 1 (onset 24.3 s): caida@2.8s recuperacion@32.8s
- chute17-cam5 fall 1 (onset 24.7 s): no events
- chute17-cam6 fall 1 (onset 24.3 s): caida@11.6s recuperacion@32.6s
- chute17-cam7 fall 1 (onset 25.3 s): caida@11.9s recuperacion@17.3s caida@17.8s caida_confirmada@47.8s
- chute17-cam8 fall 1 (onset 24.9 s): caida@12.3s recuperacion@30.6s caida@31.8s recuperacion@33.6s
- chute18-cam1 fall 1 (onset 22.5 s): caida@3.0s recuperacion@13.6s caida@17.6s recuperacion@30.1s
- chute18-cam3 fall 1 (onset 22.1 s): caida@21.0s recuperacion@32.8s
- chute18-cam4 fall 1 (onset 19.2 s): no events
- chute18-cam5 fall 1 (onset 22.0 s): no events
- chute18-cam6 fall 1 (onset 22.8 s): caida@25.6s recuperacion@32.6s
- chute18-cam7 fall 1 (onset 22.9 s): no events
- chute18-cam8 fall 1 (onset 21.8 s): caida@23.8s recuperacion@30.6s
- chute19-cam1 fall 1 (onset 17.3 s): caida@0.3s recuperacion@15.1s
- chute19-cam3 fall 1 (onset 17.2 s): caida@1.8s recuperacion@11.9s caida@14.8s recuperacion@31.9s
- chute19-cam6 fall 1 (onset 17.6 s): caida@16.1s recuperacion@32.6s
- chute19-cam7 fall 1 (onset 16.6 s): no events
- chute20-cam6 fall 1 (onset 18.3 s): caida@1.3s recuperacion@12.0s caida@17.1s
- chute21-cam1 fall 1 (onset 29.5 s): caida@22.3s
- chute21-cam2 fall 1 (onset 29.8 s): caida@22.9s recuperacion@39.4s
- chute21-cam5 fall 1 (onset 29.1 s): no events
- chute21-cam6 fall 1 (onset 29.9 s): caida@21.6s
- chute21-cam7 fall 1 (onset 29.9 s): caida@23.4s
- chute21-cam8 fall 1 (onset 28.8 s): caida@19.0s
- chute22-cam1 fall 1 (onset 25.6 s): caida@24.4s recuperacion@35.6s
- chute22-cam2 fall 1 (onset 27.1 s): caida@17.9s recuperacion@21.0s caida@24.0s
- chute22-cam4 fall 1 (onset 26.9 s): no events
- chute22-cam5 fall 1 (onset 27.3 s): no events
- chute22-cam7 fall 1 (onset 27.1 s): caida@24.0s recuperacion@37.8s
- chute22-cam8 fall 1 (onset 26.7 s): caida@25.1s

## 2. Secondary: more cameras in the room (OR-fusion)

An alarm if **any** camera of the set fires. Per event: a fall is detected if any camera fires inside its window; the false alarms of the cameras are put on the common timeline (the cameras end together) and merged when closer than 5 s. Mean over every combination of k of the 8 cameras (min–max in brackets).

| Cameras (k) | Combinations | Falls detected, with R9 | False alarms (all 24 scenarios), with R9 | False alarms per hour, with R9 | Falls detected, without R9 | False alarms per hour, without R9 |
|---|---|---|---|---|---|---|
| 1 | 8 | 47.8 (26.1–73.9) % | 15.4 (9.0–20.0) | 114.0 (66.7–148.2) | 48.4 (21.7–73.9) % | 106.5 (66.7–133.4) |
| 2 | 28 | 68.2 (39.1–95.7) % | 24.1 (16.0–30.0) | 178.9 (118.6–222.4) | 69.4 (43.5–95.7) % | 170.5 (118.6–214.9) |
| 3 | 56 | 78.5 (52.2–95.7) % | 30.1 (22.0–36.0) | 222.8 (163.1–266.8) | 80.0 (56.5–95.7) % | 216.0 (155.7–266.8) |
| 4 | 70 | 85.0 (60.9–95.7) % | 34.4 (28.0–40.0) | 254.7 (207.5–296.5) | 86.2 (65.2–95.7) % | 250.7 (207.5–296.5) |
| 5 | 56 | 89.4 (73.9–95.7) % | 37.8 (33.0–43.0) | 279.9 (244.6–318.7) | 90.2 (73.9–95.7) % | 279.4 (244.6–318.7) |
| 6 | 28 | 92.5 (82.6–95.7) % | 40.6 (37.0–44.0) | 301.0 (274.2–326.1) | 92.9 (78.3–95.7) % | 304.4 (274.2–341.0) |
| 7 | 8 | 94.6 (87.0–95.7) % | 43.0 (41.0–45.0) | 318.7 (303.9–333.5) | 94.6 (91.3–95.7) % | 327.1 (303.9–348.4) |
| 8 | 1 | 95.7 (95.7–95.7) % | 45.0 (45.0–45.0) | 333.5 (333.5–333.5) | 95.7 (95.7–95.7) % | 348.4 (348.4–348.4) |

Per video (scenario level, secondary, tiny negative set): a fall scenario counts if any camera fires inside a fall window; scenarios 23 and 24 are false positives if any camera fires at all.

| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Without R9, 1 camera, best of 8 | 22 | 2 | 11 | 11 | 1 | 1 | 50.0% (30.7%–69.3%) | 50.0% (9.5%–90.5%) | 50.0% (31.4%–68.6%) | 91.7% (64.6%–98.5%) | 0.647 |
| Without R9, 1 camera, worst of 8 | 22 | 2 | 5 | 17 | 0 | 2 | 22.7% (10.1%–43.4%) | 0.0% (0.0%–65.8%) | 20.8% (9.2%–40.5%) | 71.4% (35.9%–91.8%) | 0.345 |
| Without R9, 2 cameras, best of 28 | 22 | 2 | 22 | 0 | 0 | 2 | 100.0% (85.1%–100.0%) | 0.0% (0.0%–65.8%) | 91.7% (74.2%–97.7%) | 91.7% (74.2%–97.7%) | 0.957 |
| Without R9, 2 cameras, worst of 28 | 22 | 2 | 10 | 12 | 0 | 2 | 45.5% (26.9%–65.3%) | 0.0% (0.0%–65.8%) | 41.7% (24.5%–61.2%) | 83.3% (55.2%–95.3%) | 0.588 |
| Without R9, 8 cameras | 22 | 2 | 22 | 0 | 0 | 2 | 100.0% (85.1%–100.0%) | 0.0% (0.0%–65.8%) | 91.7% (74.2%–97.7%) | 91.7% (74.2%–97.7%) | 0.957 |
| With R9 (shipped), 1 camera, best of 8 | 22 | 2 | 12 | 10 | 1 | 1 | 54.5% (34.7%–73.1%) | 50.0% (9.5%–90.5%) | 54.2% (35.1%–72.1%) | 92.3% (66.7%–98.6%) | 0.686 |
| With R9 (shipped), 1 camera, worst of 8 | 22 | 2 | 6 | 16 | 0 | 2 | 27.3% (13.2%–48.2%) | 0.0% (0.0%–65.8%) | 25.0% (12.0%–44.9%) | 75.0% (40.9%–92.9%) | 0.400 |
| With R9 (shipped), 2 cameras, best of 28 | 22 | 2 | 22 | 0 | 0 | 2 | 100.0% (85.1%–100.0%) | 0.0% (0.0%–65.8%) | 91.7% (74.2%–97.7%) | 91.7% (74.2%–97.7%) | 0.957 |
| With R9 (shipped), 2 cameras, worst of 28 | 22 | 2 | 9 | 13 | 0 | 2 | 40.9% (23.3%–61.3%) | 0.0% (0.0%–65.8%) | 37.5% (21.2%–57.3%) | 81.8% (52.3%–94.9%) | 0.545 |
| With R9 (shipped), 8 cameras | 22 | 2 | 22 | 0 | 0 | 2 | 100.0% (85.1%–100.0%) | 0.0% (0.0%–65.8%) | 91.7% (74.2%–97.7%) | 91.7% (74.2%–97.7%) | 0.957 |

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
