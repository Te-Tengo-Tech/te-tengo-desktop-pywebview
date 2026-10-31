# Classifier validation with public datasets

This document reports how the Kinematic Classification Service was validated with the two public datasets named in the project charter (URFD and CAUCAFall), what was changed based on the results, and which limitations remain. It is the technical basis for indicator OE4-I1 ("accuracy, sensitivity and specificity on public datasets").

To reproduce it:

```bash
make datasets   # downloads URFD and CAUCAFall into datos/ (about 220 MB)
make validar    # extracts poses and generates resultados/reporte.md
uv run python scripts/comparar_pipelines.py --todos --guardar   # agent vs validation, frame by frame (section 3.5)
```

The hold-out test on a third, unseen dataset (GMDCSA24) is in section 6.

## 1. Data

| Dataset | Videos | Camera | Use |
|---|---|---|---|
| **URFD** (Kwolek and Kepski, 2014) | 30 falls and 40 daily activities, of which **16 end with the person lying on the floor on purpose**, according to the dataset's per-frame labels | Kinect parallel to the floor, at body height; the RGB half of the MP4 is used (320 × 240) | CC BY-NC-SA 4.0 |
| **CAUCAFall** (Eraso Guerrero et al., 2022) | 10 people × (5 falls: forward, backward, left, right and from sitting + 5 activities: walking, jumping, picking up an object, sitting down and kneeling) = 100 videos | Surveillance camera **elevated in a corner** of a home (720 × 480), with occlusions and lighting changes | CC BY 4.0 |

Neither one includes older adults or real falls; this limitation is declared in the charter (risk 9).

## 2. Protocol

1. **Same processing as in production.** Each video is downscaled to 480p and 8 fps (6 and 10 fps were also tested). It is compressed as JPEG with quality 80, as the agent does, and passed through MediaPipe Pose Landmarker *lite* in VIDEO mode. The poses are saved once and then replayed in **the same `ClasificadorCinematico` as the agent**.
2. **Per-video criterion.** A fall video is a true positive if the classifier emits at least one `caida` event. A daily activity video is a false positive if it emits any.
3. **Metrics.** Sensitivity = TP/(TP+FN), specificity = TN/(TN+FP) and accuracy = (TP+TN)/total, the same definitions as Chen et al. (2020, eq. 6–8) and the charter.
4. **Calibration.** The only calibrated threshold is the minimum descent speed (R1). 100 values (0.01–1.0) are tested and the one with the highest **Youden index** is chosen (J = sensitivity + specificity − 1; Youden, 1950). The angle (45°) and the ratio (1) are left at the published values: tuning them did not improve the cross-dataset validation.
5. **Honest performance estimate:**
   - **Leaving one group out.** There are 11 groups: each CAUCAFall subject and the whole of URFD, because URFD does not publish the subject of each video. Each group is evaluated with the threshold calibrated **without** its videos.
   - **Cross-dataset.** Calibrate with one and measure on the other.

## 3. Results

### 3.1. Main performance: 8 fps, JPEG, leaving one group out

| Group | Falls | Non-falls | TP | FN | TN | FP | Sensitivity | Specificity | Accuracy |
|---|---|---|---|---|---|---|---|---|---|
| **Total** | 80 | 90 | 65 | 15 | 73 | 17 | **81.2%** | **81.1%** | **81.2%** |
| URFD | 30 | 40 | 23 | 7 | 31 | 9 | 76.7% | 77.5% | 77.1% |
| CAUCAFall | 50 | 50 | 42 | 8 | 42 | 8 | 84.0% | 84.0% | 84.0% |

**By activity** (the figures of the previous table grouped by type):

| Activity | Result |
|---|---|
| CAUCAFall · backward fall | 10/10 detected |
| CAUCAFall · fall to the left | 9/10 |
| CAUCAFall · forward fall | 8/10 |
| CAUCAFall · fall to the right | 8/10 |
| CAUCAFall · fall from sitting | 7/10 |
| CAUCAFall · jumping | 0/10 false alarms |
| CAUCAFall · walking · sitting down | 1/10 false alarm each |
| CAUCAFall · kneeling · picking up an object | 3/10 false alarms each |
| URFD · falls | 23/30 detected |
| URFD · daily activities | 9/40 false alarms; **6 of them when lying down on the floor on purpose** |

**Other events:**
- **0 false recoveries** in the 30 URFD falls, in which nobody gets up.
- **2 of 90** daily activities produced a `movimiento_inestable`.

### 3.2. Robustness to the frame rate (leaving one group out)

The agent sends between 5 and 10 fps, per the architecture.

| fps | Sensitivity | Specificity | Accuracy | False recoveries |
|---|---|---|---|---|
| 6 | 76.2% | 83.3% | 80.0% | 0/30 |
| **8** | **81.2%** | **81.1%** | **81.2%** | 0/30 |
| 10 | 81.2% | 84.4% | 82.9% | 0/30 |

### 3.3. Cross-dataset validation (8 fps)

| Calibration → test | Threshold | Sensitivity | Specificity | Accuracy |
|---|---|---|---|---|
| URFD → CAUCAFall | 0.45 | 28.0% | 94.0% | 61.0% |
| CAUCAFall → URFD | 0.01 | 76.7% | 77.5% | 77.1% |

**A threshold calibrated with a camera at body height (URFD) does not work for an elevated camera (CAUCAFall).** From above, the descent of the hip looks shorter in the image. The threshold must be calibrated with a camera placed as in the home: that is why the CAUCAFall and full-set value (0.01) is used.

### 3.4. Live service check
24 videos (12 from URFD and 12 from CAUCAFall) were sent to the running worker (the cloud service retired in ADR 0007), using the simulated agent over WebSocket. The fall events matched the offline evaluation in **24 of 24**.

### 3.5. Parity with the desktop agent

The figures above describe the agent only if it gives MediaPipe the same frames as the validation. `scripts/comparar_pipelines.py` runs each video through `evaluar.py extraer` and through the agent's own capture loop (`FuenteArchivo` → `Captador` → `EstimadorMediaPipe` → `BucleCaptura`, with the URFD RGB half cropped in memory) and compares every frame. Measured on 2026-10-07 with MediaPipe 0.10.35:

- **170 of 170 videos** give the same timestamps, images (480p, BGR `uint8`, JPEG quality 80), landmarks, classifier phase and events in both paths; the 11,183 stored poses of the agent are identical to those of the validation.
- `evaluar.py evaluar --pipeline agente --barrer 0.01 1.0 0.01` on the agent's poses gives the same results as sections 3.1 and 3.3: **81.2% sensitivity and 81.1% specificity** leaving one group out, URFD → CAUCAFall 28.0% / 94.0% (v = 0.45) and CAUCAFall → URFD 76.7% / 77.5% (v = 0.01).
- A clip must reach the agent without an extra lossy step. Cropping the URFD RGB half to a new file with OpenCV's `mp4v` codec changes the pixels: on `fall-01` MediaPipe then misses the only frame with the person on the floor (30 instead of 31 poses in 43 frames) and the `caida` is lost. The installation guide crops it losslessly (FFV1).

`tests/captura/test_paridad.py` keeps the two paths identical.

### 3.6. Slow falls (rule R9)

Rule R9 ([classification-spec.md](classification-spec.md), ADR 0009) declares a fall when the person was upright in the last 10 s, the hip ends at least 0.4 body lengths lower and the body stays horizontal for 2 s, without looking at the speed. Its three values were fixed before replaying the datasets. `scripts/barrer_rangos.py` replays every video with and without it.

**Main performance, 8 fps, JPEG, leaving one group out** (95 % Wilson intervals; every fold still calibrates v = 0.01):

| Classifier | Sensitivity | Specificity | Accuracy | False recoveries |
|---|---|---|---|---|
| R4–R8 (sections 3.1–3.5) | 81.2 % (71–88) | 81.1 % (72–88) | 81.2 % (75–86) | 0/30 |
| **+ R9** | **82.5 % (73–89)** | **78.9 % (69–86)** | **80.6 % (74–86)** | 0/30 |
| URFD with R9 | 76.7 % | 72.5 % | 74.3 % | |
| CAUCAFall with R9 | 86.0 % | 84.0 % | 85.0 % | |

**Robustness:**

| | Without R9 | With R9 |
|---|---|---|
| 6 fps (sensitivity / specificity) | 77.5 % / 83.3 % | 78.8 % / 78.9 % |
| 10 fps | 81.2 % / 84.4 % | 83.8 % / 78.9 % |
| URFD → CAUCAFall (v calibrated with URFD: 0.45 without R9, 0.71 with it) | 28.0 % / 94.0 % | 46.0 % / 94.0 % |
| CAUCAFall → URFD (v = 0.01) | 76.7 % / 77.5 % | 76.7 % / 72.5 % |

**Slow falls.** The datasets do not label the speed of each fall, so a fall is called slow if its measured peak hip descent speed (R1) is below 0.3 bodies/s: at that speed, dropping the hip half a body length takes more than the 1.48 s window. At 8 fps, 18 of the 80 falls are slow and R4 already detects 12 of them; R9 adds 1 (CAUCAFall subject 9, fall from sitting, peak 0.08). Over 6, 8 and 10 fps R9 adds 4 detections, all of slow falls (peak 0.08–0.21 bodies/s): CAUCAFall subject 9's fall from sitting (8 and 10 fps), subject 6's fall to the left (6 fps) and URFD `fall-10` (10 fps). 7 falls have no measurable speed (MediaPipe does not see the hips and ankles clearly during the descent) and neither rule detects them.

**False alarms in daily activities (8 fps):**

| Activity | Videos | Without R9 | With R9 |
|---|---|---|---|
| URFD · lying down on the floor on purpose | 16 | 6 | 8 |
| URFD · other activities (sitting on a chair, a bed or a sofa, crouching, picking up) | 24 | 3 | 3 |
| CAUCAFall · kneeling | 10 | 3 | 3 |
| CAUCAFall · picking up an object | 10 | 3 | 3 |
| CAUCAFall · sitting down | 10 | 1 | 1 |
| CAUCAFall · walking · jumping | 20 | 1 | 1 |

All the new false alarms at 8 fps and 6 fps are people lying down on the floor on purpose (`adl-31` and `adl-35`; at 6 fps also `adl-37` and `adl-40`). At 10 fps R9 also adds one kneeling and one picking up an object. **No dataset has someone lying down on a bed or a sofa**; R9 excludes them by the hip drop, which only the synthetic tests check. The clips are short (at most 9.5 s after a fall), so a person who lies on the floor for longer than 2 s would also trigger R9 in a home: the specificity of these clips is an upper bound for that activity.

## 4. Changes made based on the validation

The figures in this section are **calibrated with all the videos**, so they are optimistic and are only useful to compare the stages with each other.

| Stage | Sensitivity | Specificity | What was changed and why |
|---|---|---|---|
| Adapted reference method (IMAGE mode) | 80.0% | 65.6% | Starting point. MediaPipe lost the person in 43% of the frames of CAUCAFall falls. |
| + MediaPipe in VIDEO mode | 80.0% | 68.9% | Tracking between frames raised the coverage of CAUCAFall falls from 57% to 82%. The *full* model did not improve over the *lite* model (ADR 0006). |
| + signed speed, 1 s window and only with visible points (A3, A6); head below the feet (A7); 0.5 s upright for recovery (A8) | 83.8% | 82.2% | **Speed:** with doubtful poses, in URFD, "lying down on purpose" gave **higher** speeds than the falls (median 1.78 vs. 1.01 bodies/s), which is physically impossible; with visible points they separate (median 0 vs. 0.88). The 1 s window covers the duration of the descent in a real fall of an older adult (583 ± 255 ms until pelvis impact; Choi et al., 2015, as cited in Traverso et al., 2024). **Head below the feet:** in forward falls with an elevated camera, the angle and the ratio do not change (only 3/10 met M2 and M3), but the head ends up below the feet in the image; with this signal 7/10 were detected. **Recovery:** 0.5 s upright reduced the false recoveries from 2 to 0 of 30. |
| + JPEG as in production and 1 s upright (final configuration) | 81.2% | 81.1% | With JPEG, the frames that MediaPipe detects change, so the validation must reproduce it; performance drops a little, but it is the realistic one. With JPEG, 0.5 s upright left 1 false recovery of 30; with 1 s, none. |

**Tested and discarded:** requiring the horizontal posture to hold for 0.25 to 1 s before declaring the fall. It lowered sensitivity to 61–70%, because MediaPipe loses the person lying down.

**About the speed threshold:** the calibrated value (0.01 bodies/s) almost means "the hip went down somewhat". In these datasets, at 8 fps and in 2D, speed contributes little on its own: falls are so fast that MediaPipe loses part of the descent frames, exactly the ones that would have the highest speed. The work of telling cases apart is done mostly by the angle, the ratio and the head below the feet.

## 5. Known limitations

1. **Lying down on the floor on purpose** is confused with a fall in 6 of 16 URFD cases, and in 8 with R9. In a home, this means a false alarm when the older adult lies down on the floor by choice.
2. **Picking up an object and kneeling** produce false alarms in 3 of every 10 cases with an elevated camera.
3. **Calibration depends on the camera location** (section 3.3). It must be repeated with the pilot recordings, as the charter states (risks 2, 3 and 6).
4. **There are no older adults or real falls** in the data (charter risk 9). The real false alarm rate will be measured in the home (OE4-I2).
5. **Almost no slow falls** in the data (section 3.6): R9 is checked on 18 falls with a low peak speed and on synthetic sequences; slow falls and lying down on a bed must be recorded in the pilot.
6. **Lying down on a bed** was not in URFD or CAUCAFall. On the hold-out dataset GMDCSA24 it gave a false alarm in **12 of 12** clips, through R4 (section 6.2).
7. **The validation is per video,** not per instant. It does not measure the alert latency, whose requirement is under 10 s; the classifier emits the fall as soon as M3 is met.

The ranges in which each tunable value keeps this performance (US-45) are measured in [validation-rangos.md](validation-rangos.md).

## 6. Hold-out evaluation on GMDCSA24

Sections 3 and 4 calibrate and test on the same two datasets (leaving one group out). This section tests the **shipped classifier, frozen**, on a public dataset that was not used for any design decision, threshold or rule: nothing was tuned on it for the main result.

To reproduce it:

```bash
uv run python scripts/descargar_datasets.py --datasets gmdcsa24   # 1.1 GB zip, MD5-checked
for f in 6 8 10; do uv run python scripts/evaluar.py extraer --datasets gmdcsa24 --fps $f; done
uv run python scripts/evaluar_holdout.py --logo --comparar-fps 6 8 10   # resultados/holdout-gmdcsa24-8fps.md
uv run python scripts/medir_latencia.py --salida resultados/latencia-gmdcsa24-8fps.md
```

### 6.1. Dataset

| | GMDCSA24 v2.1 (Alam et al., 2024) |
|---|---|
| Source | Zenodo, https://doi.org/10.5281/zenodo.13354453 (v2.1, 2024-08-21, `GMDCSA24-…-v2.1.zip`, 1,107,545,615 bytes, MD5 `3d36f2c5c1a666b99639e4e9fd843efb`); mirror of https://github.com/ekramalam/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos |
| License | CC BY 4.0 (Zenodo record); the GitHub copy carries an MIT `LICENSE` |
| Videos | 160 clips: **79 falls and 81 activities of daily living (ADL)** in the files (the paper's abstract says 81 falls and 79 ADL; its own per-subject counts and the files say 79 and 81). 1,288 s in total, 3–17.5 s each |
| Subjects | 4 adult actors (S1–S4), age, sex and height not published; no older adults, simulated falls |
| Camera | One static laptop webcam (HP 348 G5, 0.92 MP) in 3 home rooms: room 1 (S1) at 70 or 90 cm in two positions; room 2 (S2, S3) at 135 cm; room 3 (S4) at 64 cm. Day, lights-off and night recordings |
| Resolution | 1280 × 720 (147 clips) or 640 × 480 (13), about 30 or 15 fps; downscaled to 480p and sampled at 8 fps as in production |
| Labels | Clip level by folder (`Fall/` or `ADL/`), used as the ground truth. Each clip also has hand-made intervals in seconds (`Falling (BW)[1.5 to 5]; Standing[0 to 1.5]`) and a free-text description; the start of the first `Falling` interval is used as the fall onset (78 of 79 falls have one). No faller is labelled as getting up |
| Groups used here | Falls by direction label (forward, backward, sideways); ADL grouped by keyword rules on the description, fixed before running the classifier (`evaluar.actividad_gmdcsa24`) |

Unlike URFD and CAUCAFall, GMDCSA24 has **people lying down on a bed** (12 clips), exercise on the floor (push-ups), sitting on the floor, and **falls onto a bed** (11 clips).

**Datasets that could not be used.** Le2i / ImViA fall detection dataset: the official page (https://imvia.ube.fr/?p=346, checked 2026-10-31) says the download is "waiting for new link", and the university data portal answers with a bot challenge, which was not bypassed. UP-Fall was not attempted in this round (its camera data is a large set of per-trial image archives).

### 6.2. Main result: frozen thresholds, 8 fps, JPEG (no recalibration)

Thresholds exactly as shipped: `velocidad_descenso_min = 0.01` (`UMBRALES_CALIBRADOS`) and every other value at its default; "without R9" switches off only the slow-fall rule. Same per-video criterion as section 2; 95 % Wilson intervals.

| Classifier | TP | FN | TN | FP | Sensitivity | Specificity | Accuracy | Precision | F1 |
|---|---|---|---|---|---|---|---|---|---|
| Without R9 (R4–R8) | 69 | 10 | 53 | 28 | 87.3 % (78.2–93.0) | 65.4 % (54.6–74.9) | 76.2 % (69.1–82.2) | 71.1 % (61.4–79.2) | 0.784 |
| **With R9 (shipped)** | **72** | **7** | **53** | **28** | **91.1 % (82.8–95.6)** | **65.4 % (54.6–74.9)** | **78.1 % (71.1–83.8)** | **72.0 % (62.5–79.9)** | **0.804** |

Precision and F1 depend on the 79/81 mix of the clips, not on how rare falls are in a home.

- **Onset-aware check.** If a fall clip only counts when a `caida` comes no earlier than 1 s before the labelled onset, one detection is lost with and without R9: `S2-Fall-11` ("falling from bed to ground") fires while the person is still lying on the bed, 3.6 s before the fall. With R9: 89.9 % sensitivity (81.3–94.8).
- **False recoveries: 1 of 78** falls (with and without R9), `S2-Fall-13`: a `caida` at 0.4 s and a `recuperacion` at 1.9 s, both **before** the labelled onset (2.5 s), then the real `caida` at 3.8 s. No `recuperacion` follows a fall after its onset. **0 of 81** ADL have a `movimiento_inestable`. No clip is long enough for `caida_confirmada` (30 s).
- **Detection latency** (labelled onset → first onset-aware `caida`, 70 falls, with R9): median **0.76 s**, mean 1.00 s, p95 3.27 s, range −0.73 to 3.60 s. URFD gave a median of 0.80–0.83 s ([validation-rangos.md](validation-rangos.md)). The onsets are hand-labelled to 0.1 s.
- **R9** adds 3 detections (`S2-Fall-09`, `S2-Fall-10`, `S3-Fall-01`) and **no false alarm**.

**Where it fails (with R9):**

| Group | Videos | `caida` |
|---|---|---|
| Falls · sideways | 28 | 27 detected |
| Falls · forward | 23 | 21 |
| Falls · backward | 28 | 24 |
| Falls onto a bed | 11 | 11 |
| ADL · **lying down on / getting up from the bed** | 12 | **12 false alarms** |
| ADL · exercise (push-ups, bending, arms up and down) | 11 | 5 |
| ADL · sitting on / getting up from the floor | 11 | 4 |
| ADL · picking up an object (mostly from the floor) | 12 | 3 |
| ADL · sitting on a bed or a chair | 25 | 3 |
| ADL · lying down on / getting up from the floor | 2 | 1 |
| ADL · walking or standing | 8 | 0 |

By subject (falls detected · ADL false alarms): S1 15/16 · 6/16, S2 23/25 · 10/23, S3 19/21 · 6/22, S4 15/17 · 6/20. By lighting: day 57/62 · 16/51, day with lights off 5/6 · 4/12, night 10/11 · 8/18.

- **Lying down on a bed is always a false alarm.** All 12 fire without R9 as well, so they come from the fast rule R4: with v = 0.01, a hip that goes down while the body tilts and becomes horizontal within 1.48 s looks like a fall in 2D. R9 adds none of them, as its hip-drop condition intends. The previous datasets had no such clip (section 3.6), so this limitation was not measured before. Without these 12 clips the specificity would be 76.8 % (53/69), close to sections 3.1 and 3.6; this is descriptive, not a separate test.
- **Floor-level activities** (push-ups, sitting down on or getting up from the floor, picking up) give most of the other false alarms, as kneeling and picking up did in CAUCAFall.
- **Missed falls (7):** 3 start from sitting (on the floor `S2-Fall-08`, `S3-Fall-13`; on a chair `S4-Fall-10`), where the hip starts low and R9 needs the person upright in the last 10 s; 2 have part of the body hidden according to their descriptions (`S1-Fall-14`, ankles not visible; `S2-Fall-05`, face hidden by a hand); `S3-Fall-15` is a night clip and `S4-Fall-04` a second view of a forward fall. These are likely explanations from the descriptions, not checked frame by frame. Backward falls are missed most (4 of 28).

### 6.3. Secondary analyses (not the main result)

**More calibration data: leaving one group out over the three datasets** (15 groups: URFD, the 10 CAUCAFall subjects and the 4 GMDCSA24 subjects; `v` calibrated by Youden on the other 14 groups, as in section 2):

| Classifier | v chosen per fold | Sensitivity | Specificity | Accuracy | GMDCSA24 folds: sens. / spec. |
|---|---|---|---|---|---|
| With R9 | 0.12 in 10 folds, 0.13 in 1, 0.09 in 2, 0.01 in 2 | 79.2 % (72.3–84.8) | 75.4 % (68.5–81.3) | 77.3 % (72.5–81.5) | 84.8 % / 69.1 % |
| Without R9 | 0.01 in all 15 | 84.3 % (77.8–89.1) | 73.7 % (66.6–79.7) | 78.8 % (74.1–82.9) | 87.3 % / 65.4 % |

With R9, adding GMDCSA24 moves the calibrated speed from 0.01 to 0.12, but the Youden curve is flat: on all 330 videos J = 0.593 at v = 0.01, 0.595 at 0.09–0.10 and 0.600 at 0.12 (sensitivity 86.8 % → 80.5 %, specificity 72.5 % → 79.5 %). More data does not reveal a clearly better threshold; it trades sensitivity for specificity. The shipped value is not changed by this analysis.

**Post hoc, optimistic** (the threshold chosen on GMDCSA24 itself, an upper bound only): with R9 the best Youden is at v = 0.35, 78.5 % sensitivity and 87.7 % specificity; at v = 0.1, 84.8 % / 75.3 %. Raising `v` mostly removes bed false alarms (12 at v = 0.01, 6 at 0.1, 2 at 0.35), at the cost of falls.

**Frame rate** (frozen thresholds, GMDCSA24):

| fps | Without R9: sens. / spec. | With R9: sens. / spec. / acc. | Latency with R9 (median) | False recoveries with R9 |
|---|---|---|---|---|
| 6 | 89.9 % / 70.4 % | 91.1 % / 70.4 % / 80.6 % | 0.79 s | 0/78 |
| **8** | 87.3 % / 65.4 % | **91.1 % / 65.4 % / 78.1 %** | 0.76 s | 1/78 |
| 10 | 87.3 % / 69.1 % | 91.1 % / 69.1 % / 80.0 % | 0.72 s | 1/78 |

### 6.4. Hardware and per-frame cost

Measured with `scripts/medir_latencia.py` on the 160 GMDCSA24 clips (10,333 frames at 8 fps), one process, videos in sequence: Apple M5 Pro (15 cores), 24 GB, macOS 27.0.1, Python 3.11.16, MediaPipe 0.10.35 (Pose Landmarker lite, VIDEO mode, CPU delegate with XNNPACK), OpenCV 5.0.0.

| Stage, per sampled frame | Mean | Median | p95 |
|---|---|---|---|
| Preprocessing (resize to 480p, JPEG quality 80 encode + decode) | 1.54 ms | 1.43 ms | 2.20 ms |
| **MediaPipe Pose Landmarker lite** (`detect_for_video`, first frame of each clip excluded) | **7.56 ms** | **6.43 ms** | **12.10 ms** |
| Classifier (`ClasificadorCinematico.actualizar`) | 0.04 ms | 0.04 ms | 0.06 ms |
| **Agent cost per frame** (the three above) | **9.13 ms** | | **14.15 ms** |
| File decoding until the next sampled frame (not an agent cost: a webcam delivers frames) | 1.63 ms | 0.85 ms | 5.68 ms |

At 8 fps the agent has 125 ms per frame; it uses 7.3 % of it (wall time; MediaPipe may use several threads). The first MediaPipe frame of each clip (graph warm-up) takes 14.9 ms on average. End to end, including decoding and creating one landmarker per clip, one process handles 68.9 sampled frames/s, 8.6 times real time. The machine was shared with other work (1-minute load average about 8 during the run); two earlier runs under heavier load gave MediaPipe means of 11.5 and 15.6 ms, so the figures vary with contention. Six extraction processes in parallel took 35–65 s for the whole dataset at 6–10 fps.

The figures are a development laptop's, much faster than a typical household PC; they show the order of magnitude, not the cost on the pilot PCs. The earlier URFD and CAUCAFall poses re-extracted on this machine are identical to the stored ones (4 videos checked), and `evaluar.py evaluar --barrer 0.01 1.0 0.01` reproduces section 3.6 (82.5 % / 78.9 %).

### 6.5. Interpretation

On unseen data, from different rooms, people and a lower camera, the frozen classifier keeps its **sensitivity** (91.1 %, above the 82.5 % of section 3.6) but its **specificity drops to 65.4 %**, almost all because of activities that the calibration data did not contain: lying down on a bed (12 of 12) and floor-level exercise. This is the main threat to the false-alarm rate in a home (OE4-I2) and is consistent with limitation 1 of section 5, now measured for a bed. The intervals are wide (4 subjects, 160 clips), the falls are simulated by young adults, and the clips are short; the hold-out supports the sensitivity estimate and shows that specificity must be checked in the pilot, especially for lying down on a bed or a sofa.

## References

Alam, E., Sufian, A., Dutta, P., Leo, M., & Hameed, I. A. (2024). GMDCSA-24: A dataset for human fall detection in videos. *Data in Brief, 57*, 110892. https://doi.org/10.1016/j.dib.2024.110892 · Data: https://doi.org/10.5281/zenodo.13354453

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744

Eraso Guerrero, J. C., Muñoz España, E., Muñoz Añasco, M., & Pinto Lopera, J. E. (2022). Dataset for human fall recognition in an uncontrolled environment. *Data in Brief, 45*, 108610. https://doi.org/10.1016/j.dib.2022.108610 · Datos: https://doi.org/10.17632/7w7fccy7ky.4

Kwolek, B., & Kepski, M. (2014). Human fall detection on embedded platform using depth maps and wireless accelerometer. *Computer Methods and Programs in Biomedicine, 117*(3), 489–501. https://doi.org/10.1016/j.cmpb.2014.09.005 · Datos: https://fenix.ur.edu.pl/~mkepski/ds/uf.html

Traverso, A., Bayram, A., Rossettini, G., Chiappinotto, S., Galazzi, A., & Palese, A. (2024). Investigating the biomechanics of falls in older adults in long-term care using a video camera: A scoping review. *BMC Geriatrics, 24*, 810. https://doi.org/10.1186/s12877-024-05395-2

Youden, W. J. (1950). Index for rating diagnostic tests. *Cancer, 3*(1), 32–35. https://doi.org/10.1002/1097-0142(1950)3:1<32::AID-CNCR2820030106>3.0.CO;2-3
