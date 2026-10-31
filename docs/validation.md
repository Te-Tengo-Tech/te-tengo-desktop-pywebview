# Classifier validation with public datasets

This document reports how the Kinematic Classification Service was validated with the two public datasets named in the project charter (URFD and CAUCAFall), what was changed based on the results, and which limitations remain. It is the technical basis for indicator OE4-I1 ("accuracy, sensitivity and specificity on public datasets").

To reproduce it:

```bash
make datasets   # downloads URFD and CAUCAFall into datos/ (about 220 MB)
make validar    # extracts poses and generates resultados/reporte.md
uv run python scripts/comparar_pipelines.py --todos --guardar   # agent vs validation, frame by frame (section 3.5)
```

The hold-out test on a third, unseen dataset (GMDCSA24) is in section 6; two more, UP-Fall and the Multiple Cameras Fall Dataset, with several cameras per room, are in section 8.

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

8. **Raising the sensitivity with pose rules alone did not work** (section 7): loosening the visibility gate of the speed, detecting tilts toward the camera, declaring a fall when the pose is lost after a fast descent and re-calibrating the angle and the ratio all lost more specificity than they gained sensitivity.

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

**Datasets that could not be used.** Le2i / ImViA fall detection dataset: the official page (https://imvia.ube.fr/?p=346, checked 2026-10-31) says the download is "waiting for new link", and the university data portal answers with a bot challenge, which was not bypassed. UP-Fall was not attempted in this round (its camera data is a large set of per-trial image archives); it was evaluated later, with the Multiple Cameras Fall Dataset, in section 8.

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

## 7. Attempts to raise sensitivity without forcing it (2026-10-31): none accepted

**Question.** Can the sensitivity of R4–R9 (82.5 %, 66/80 falls) be raised with a single camera and without trading it for specificity? **Answer on URFD + CAUCAFall: no.** Five rule changes and one re-calibration were tested; every one that raised sensitivity lowered specificity by more, and the classifier stays as validated in sections 3.1–3.6.

### 7.1. Protocol

1. **Development data only:** URFD and CAUCAFall, poses `lite-video-8fps-jpeg` (section 2). The per-video results of the third, hold-out dataset were not looked at.
2. **Diagnosis before the candidates.** The 14 misses of the baseline were traced frame by frame:
   - URFD `fall-10`, `-18`, `-24`, `-26` and `-30` have **one ankle** below visibility 0.5 during the whole descent (the Kinect at body height cuts off or hides one foot). A6 needs the nose, both hips and both ankles to measure the speed, so M1 is never evaluated in the frames where the body tilts. CAUCAFall subject 10 `Fall_right` has **both** ankles hidden in the whole clip.
   - `fall-27` and `fall-29` fall toward the camera: the center line shrinks from about 90 px to 19 px while its angle stays above 45°, and then the pose is lost.
   - Subject 8 `Fall_left`: fast descent while still upright (0.29 bodies/s), then no pose until the end of the clip. Subject 8 `Fall_forward`: no pose in any of its 49 frames, so no pose-based rule can detect it.
   - Subject 3 `Fall_forward` and `Fall_sitting`, subject 4 `Fall_sitting`: noisy or nearly static poses, no clear cue.
3. **Pre-registration.** The rationale and the prediction of each candidate were written down before running any of them (section 7.2). One more candidate (C1b) was designed after the first round and is marked **post hoc**.
4. **Nested selection.** Every re-calibrated or new threshold is chosen **inside each training fold** of the leave-one-group-out validation (maximum Youden index of the 10 training groups; ties: the lowest speed, then the most conservative value of the other thresholds, and for the angle and the ratio the published value), and only then applied to the held-out group. Cross-dataset: chosen on one dataset, measured on the other.
5. **Acceptance rule (fixed beforehand):** LOGO sensitivity must rise, the specificity loss must be smaller than the sensitivity gain, the gain must not come from one dataset while the other loses, and there must be no more false recoveries.
6. **Statistics:** 95 % Wilson intervals; McNemar's exact test (two-sided binomial on the discordant pairs) on the paired per-video outcomes against the baseline, on all 170 videos (correct or not) and on the 80 falls (detected or not).
7. **Multiple comparisons:** 13 candidate settings and **10,600 distinct threshold configurations** were evaluated (each candidate × 100 speeds × its own grid). With that many looks, a single "significant" improvement would be expected by chance; a **fully nested selection**, in which every training fold also chooses the candidate, estimates the whole procedure.

Reproduce (the candidates exist only at commit `233480f` of `feature/classifier-sensitivity`; later commits keep the script and the baseline):

```bash
git checkout 233480f
uv run python scripts/evaluar_candidatos.py      # writes resultados/candidatos/
```

### 7.2. Candidates and rationale

| ID | Change | Rationale (written before testing) | New threshold |
|---|---|---|---|
| **C1** | The speed (R1) needs only **both hips** visible; the scale is still the median center-line length of the last 2 s. "Upright" keeps the strict A6. | R1 measures the hip. A6 was introduced because doubtful **hips** jump; requiring the ankles too throws away frames where the hip is reliable and only a foot is hidden, which is common in falls. | none (v nested) |
| **C2** | M2 is also met, and the person is not upright, when the center line is shorter than cos 45° = 0.707 times its median length while upright in the last 10 s. | R2 sees only the tilt in the image plane. A segment of length L₀ tilted φ toward the camera projects as L₀ cos φ, so a tilt past the same 45° gives L < 0.707 L₀. The factor comes from θ₀, it is not fitted. | none |
| **C3** | `caida` if a frame shows a hip descent ≥ v_perdida and then no pose is seen for the whole reaction window (1.48 s). | MediaPipe loses people on the floor (section 4); a fall whose descent is seen but whose end is not is then missed. Walking out of the image does not drop the hip. | v_perdida ∈ {0.1, …, 1.0} nested |
| **C4** | Re-calibrate the angle and the ratio jointly with the speed. | 45° and 1 come from OpenPose, 14 points and side views (Chen et al., 2020); MediaPipe's 33 points and an elevated camera change both. | θ₀ ∈ {35…55°}, T ∈ {0.8…1.2} nested |
| **C1b** (post hoc) | The speed needs the nose, both hips and **at least one** ankle; with one ankle visible, the feet of the center line are that ankle. | After C1: its new false alarms had **both** ankles hidden, so the angle of M2 pointed to MediaPipe's guessed feet. One hidden ankle is the normal self-occlusion of a side view. | none (v nested) |

**Considered and not tested,** with the reason fixed beforehand: One-Euro or median smoothing of the landmarks (the misses come from gated or lost points, not from jitter, and at 8 fps a filter delays and flattens the 0.25–1 s descent that M1 needs); MediaPipe world landmarks for the vertical speed (their origin is the hip itself, A3); the *full* model only when *lite* loses the person (ADR 0006 found no gain, and on the already extracted non-JPEG poses the full model sees the same or fewer frames of the hardest misses: subject 8 `Fall_forward` 0/49 with both, subject 3 `Fall_forward` 17 vs 35 frames; it would also double the CPU load of the household PC); a speed threshold adapted to the body scale (R1 is already divided by the body length).

### 7.3. Results (8 fps, JPEG, leaving one group out, thresholds nested)

| Setting | Sensitivity (95 % CI) | Specificity (95 % CI) | URFD sens. / spec. | CAUCAFall sens. / spec. | False recoveries | McNemar p (all videos · falls) | Decision |
|---|---|---|---|---|---|---|---|
| **Baseline R4–R9** | **82.5 % (72.7–89.3)** | **78.9 % (69.4–86.0)** | 76.7 / 72.5 | 86.0 / 84.0 | 0/30 | — | **kept** |
| C1 | 92.5 % (84.6–96.5) | 61.1 % (50.8–70.5) | 93.3 / 60.0 | 92.0 / 62.0 | 0/30 | 0.169 · 0.021 | rejected |
| C2 | 85.0 % (75.6–91.2) | 71.1 % (61.0–79.5) | 83.3 / 52.5 | 86.0 / 86.0 | 0/30 | 0.227 · 0.500 | rejected |
| C3 | 82.5 % (72.7–89.3) | 76.7 % (66.9–84.2) | 76.7 / 67.5 | 86.0 / 84.0 | 0/30 | 0.500 · 1.000 | rejected |
| C4 | 80.0 % (70.0–87.3) | 80.0 % (70.6–87.0) | 70.0 / 75.0 | 86.0 / 84.0 | **1/30** | 1.000 · 0.500 | rejected |
| C1b (post hoc) | 88.8 % (80.0–94.0) | 66.7 % (56.4–75.5) | 93.3 / 60.0 | 86.0 / 72.0 | 0/30 | 0.263 · 0.180 | rejected |
| C1 + C2 | 95.0 % (87.8–98.0) | 55.6 % (45.3–65.4) | 100 / 50.0 | 92.0 / 60.0 | 0/30 | 0.080 · 0.006 | rejected |
| C1 + C3 | 92.5 % (84.6–96.5) | 58.9 % (48.6–68.5) | 93.3 / 55.0 | 92.0 / 62.0 | 0/30 | 0.087 · 0.021 | rejected |
| C2 + C3 | 85.0 % (75.6–91.2) | 68.9 % (58.7–77.5) | 83.3 / 47.5 | 86.0 / 86.0 | 0/30 | 0.092 · 0.500 | rejected |
| C1 + C2 + C3 | 81.2 % (71.3–88.3) | 55.6 % (45.3–65.4) | 100 / 45.0 | 70.0 / 64.0 | 0/30 | 0.001 · 1.000 | rejected |
| C1 + C4 | 87.5 % (78.5–93.1) | 62.2 % (51.9–71.5) | 86.7 / 60.0 | 88.0 / 64.0 | 1/30 | 0.061 · 0.388 | rejected |
| C1b + C2 (post hoc) | 91.2 % (83.0–95.7) | 62.2 % (51.9–71.5) | 100 / 50.0 | 86.0 / 72.0 | 0/30 | 0.169 · 0.065 | rejected |
| C1b + C3 (post hoc) | 85.0 % (75.6–91.2) | 64.4 % (54.2–73.6) | 93.3 / 55.0 | 80.0 / 72.0 | 0/30 | 0.043 · 0.774 | rejected |
| **Fully nested** (each fold also chooses the candidate) | 85.0 % (75.6–91.2) | 67.8 % (57.6–76.5) | | | | **0.039** · 0.500 | — |

McNemar on all videos counts correct outcomes: the low p of C1 + C2 + C3, C1b + C3 and the fully nested selection are significant **losses** (more videos wrong than the baseline). The p of 0.006–0.021 "on falls" of C1 and C1 + C2 only say that they detect more falls; they do so by raising the false alarms by 16–21 videos.

**Cross-dataset** (sensitivity / specificity on the test dataset):

| Setting | URFD → CAUCAFall | CAUCAFall → URFD |
|---|---|---|
| Baseline | 46.0 / 94.0 (v = 0.71) | 76.7 / 72.5 (v = 0.01) |
| C1 | 50.0 / 86.0 | 93.3 / 60.0 |
| C2 | 48.0 / 96.0 | 83.3 / 52.5 |
| C3 | 46.0 / 94.0 | 76.7 / 67.5 |
| C4 | 46.0 / 94.0 (θ₀ = 45°, T = 1) | 70.0 / 75.0 (θ₀ = 35°) |
| C1b | 46.0 / 86.0 | 93.3 / 60.0 |

**What changes, per activity** (videos with `caida`, LOGO):

| Activity | Videos | Baseline | C1 | C1b | C2 | C3 | C4 |
|---|---|---|---|---|---|---|---|
| URFD · falls | 30 | 23 | 28 | 28 | 25 | 23 | 21 |
| URFD · lying on the floor on purpose | 16 | 8 | 13 | 12 | 14 | 9 | 7 |
| URFD · other activities | 24 | 3 | 3 | 4 | 5 | 4 | 3 |
| CAUCAFall · falls (5 types) | 50 | 43 | 46 | 43 | 43 | 43 | 43 |
| CAUCAFall · walk | 10 | 1 | 3 | — | — | — | — |
| CAUCAFall · sit down | 10 | 1 | 5 | — | — | — | — |
| CAUCAFall · kneel | 10 | 3 | 6 | — | — | — | — |
| CAUCAFall · pick up an object | 10 | 3 | 5 | — | — | — | — |
| CAUCAFall · all daily activities | 50 | 8 | 19 | 14 | 7 | 8 | 8 |

(— : not broken down; the full per-activity tables are in the script's report.) C1b recovers URFD `fall-10`, `-18`, `-24`, `-26`, `-30`, CAUCAFall subject 3 `Fall_forward` and subject 8 `Fall_right`, and loses subjects 5 and 9 `Fall_forward`; it adds 11 false alarms: 4 URFD lying on the floor on purpose, 1 other URFD activity, and in CAUCAFall walking, sitting down (3), kneeling and picking up an object. **URFD latency** (median from the first "falling" frame) is 0.83 s for the baseline (23 falls) and 0.67–0.77 s for C1, C1b and C2, which detect 25–30 falls. False recoveries stay at 0/30 except with C4 (1/30).

### 7.4. Why the gains are not real

Sweeping the speed threshold on all 170 videos (descriptive, not nested; v = 0.01–1.0) shows that C1 and C1b mostly move the classifier along the sensitivity–specificity trade-off instead of improving it. Near the baseline's operating point the baseline is better at equal specificity: with 71–74 of 90 activities without alarm it detects 54–66 falls, while C1b first reaches 71 of 90 at v = 0.5 (74 of 90, 53 falls) and C1 at v = 0.7 (73 of 90, 52 falls). The curves cross only at high specificity (78 of 90: baseline 45 falls, C1b 50), where both detect far fewer falls than the validated setting. The diagnosis explains it: with v = 0.01, M1 means little more than "the hip could be measured and went down", so A6's visibility gate is what keeps the angle and the ratio of doubtful poses out of the decision, and loosening it lets in the false alarms of people lying on the floor on purpose, kneeling or sitting, exactly the known confusions. C2 helps with falls toward the camera, but crouching and lying down also shorten the center line (the body is not rigid). C3 found no fall that ends out of view that the other rules miss, because the nested v_perdida settles at 1.0 bodies/s in 10 of 11 folds. C4 picks 40° in 9 of 11 folds (45° in one, 35° in the URFD fold) and loses 2 URFD falls.

**Conclusion.** With a single camera, these pose-based changes do not raise the sensitivity of the classifier honestly; what remains are falls in which the pose is lost or never found (subject 8 `Fall_forward`), and confusions with lying down on purpose that pose geometry cannot resolve. Raising sensitivity further needs more information than one 2D pose per frame (for example, motion or appearance features where the pose is lost, or the pilot's own recordings), not looser thresholds.

### 7.5. Hold-out check

Because no change was accepted, the frozen classifier is the baseline itself (R4–R9, v = 0.01, the defaults of section 4 of the specification), and its hold-out result on GMDCSA24 is the one in section 6 (no recalibration). The most promising rejected candidate (C1b) was not run on the hold-out: since it was not accepted, there is nothing to confirm, and running it would only add a post hoc comparison. If a candidate is reconsidered with new data, it must be evaluated there once, with the thresholds fixed beforehand.

### 7.6. Threats to validity

- **Adaptive design.** The diagnosis and C1b used the same 170 videos as the evaluation; nesting protects the threshold values, not the choice of rules, so the C1b row is optimistic. 10,600 configurations were tried; none was accepted, so this inflates no reported gain, but it would have.
- **Small samples:** 80 falls and 90 activities give ±7–10 point intervals; the differences of C2, C3 and C4 are inside them.
- **Grouping:** URFD is one group (its subjects are not published), so its fold trains only on CAUCAFall.
- **Simulated falls by young adults,** short clips (sections 1 and 5).
- **Youden index** weighs a missed fall and a false alarm equally; a criterion that favored sensitivity would choose other operating points. Section 7.4 shows the baseline is better near its own operating point, but the curves of C1b and the baseline cross at high specificity, so the conclusion is specific to operating points with about 80 % specificity.

## 8. Hold-out evaluation on UP-Fall and the Multiple Cameras Fall Dataset (2026-10-31)

Two more public datasets, never used for any design decision, threshold or rule, tested with the **shipped classifier frozen** exactly as in section 6 (lite, VIDEO mode, 8 fps, 480p, JPEG quality 80, `velocidad_descenso_min = 0.01`, every other value at its default, with and without R9). Both were recorded with several cameras, so each camera is evaluated on its own (the agent runs one webcam), and OR-fusion of the cameras of the same trial or scenario is reported as a secondary analysis. Full reports: [resultados/holdout-upfall-8fps.md](../resultados/holdout-upfall-8fps.md) and [resultados/holdout-mcfd-8fps.md](../resultados/holdout-mcfd-8fps.md).

To reproduce (the archives are not downloaded by a script; extract them into `datos/upfall/<zip name>/` and `datos/mcfd/chuteNN/camM.avi`):

```bash
uv run python scripts/evaluar.py extraer --datasets upfall mcfd --fps 8
uv run python scripts/evaluar_multicamara.py upfall --logo   # resultados/holdout-upfall-8fps.md
uv run python scripts/evaluar_multicamara.py mcfd --logo     # resultados/holdout-mcfd-8fps.md
```

### 8.1. Data

| | UP-Fall, subset (Martínez-Villaseñor et al., 2019) | Multiple Cameras Fall Dataset, MCFD (Auvinet et al., 2010) |
|---|---|---|
| Source | Camera zips `SubjectXActivityYTrialZCameraW.zip` from the official HAR-UP site (https://sites.google.com/up.edu.mx/har-up/); article CC BY 4.0 | `dataset.zip` (3,782,815,282 bytes, `unzip -t` clean), technical report 1350 (DIRO, Université de Montréal) and its erratum (Feng and Meunier, 2025); the dataset page answered with a bot challenge, which was not bypassed, so its terms of use were not read |
| Used | Trial 1 of activities 1–5 (falls: forward using hands, forward using knees, backwards, sideward, sitting in an empty chair), 9 (picking up an object) and 11 (laying), cameras 1 and 2: **119 trials, 238 recordings** (85 falls and 34 ADL per camera) | All 24 scenarios × 8 cameras: **192 videos**. Scenarios 1–22 hold a fall (scenario 4 two) after daily activities; 23 and 24 only daily activities |
| People | 17 young healthy adults (9 men, 8 women, 18–24 years), simulated falls onto a mattress | One actor, simulated falls onto a mattress; other people walk in after some recordings |
| Cameras | Two Microsoft LifeCam Cinema, 640 × 480, **1.82 m above the floor**, camera 1 **lateral** view, camera 2 **frontal** view; nominal 18 Hz. PNG frames named by their capture timestamp; measured median rate per recording 15.3–21.2 fps, gaps up to 0.82 s, the same timestamps in both cameras | Eight wide-angle IP cameras (Gadspot GS-4600) around one room, 720 × 480, MPEG-4 with decoding errors on some frames |
| Frame rate used | The real timestamps, sampled to 8 fps with the agent's `Muestreador` (which restarts its grid after a gap, as with a webcam that stalls) | The AVI headers say 120 fps, but a person puts on a coat in about 70 frames and falls in about 20, which is 2.3 s and 0.6 s at 30 fps and implausible at 120 fps; 720 × 480 is the NTSC frame. The instants are taken as frame / **30**, an assumption |
| Ground truth | Per recording, from the activity id (1–5 fall). No per-frame labels in the camera data, so no fall onset and no latency | Per-frame position codes in the reference camera's frames (report, section 4.3), with the erratum applied (reference cameras "11" and "10" are 8 and 7; corrected periods in scenarios 2, 7, 8, 14 and 18), moved to each camera with the report's delays (cameras end together). The delays match the files' frame counts for scenarios 1–23; in scenario 24 they do not (camera 8 by 1 s), which only moves its unlabelled span edge |

Notes found while preparing the data, fixed before running the classifier: one UP-Fall zip (subject 4, activity 1, camera 2) also holds 59 duplicated frames in a `…Synced/` subfolder, and another (subject 7, activity 1, camera 2) one duplicated `… - copi.png` frame; both were ignored. **UP-Fall's "laying" is lying still**: in the recordings inspected (subjects 1 and 5) the subject is already lying on the mattress at the first frame and stays there for 60 s; it does not test lying down. **MCFD scenario 23 is not free of "falling" labels**: frames 1520–1595 (going down to the floor by a chair) and 3574–3614 (sliding from the sofa onto hands and knees) are coded `falling`, each followed by `moving up`, never by `lying on the ground`. Scenario 23 is kept as a no-fall scenario, as the dataset describes it, and a `caida` in those two periods is reported apart (4 of 8 cameras), neither a detection nor a false alarm.

### 8.2. Main result: UP-Fall, frozen thresholds, per recording

A recording is a TP if it has at least one `caida`; 95 % Wilson intervals.

| Classifier, camera | TP / falls | TN / ADL | Sensitivity | Specificity | Accuracy | Precision | F1 |
|---|---|---|---|---|---|---|---|
| Without R9, both cameras | 110/170 | 43/68 | 64.7 % (57.3–71.5) | 63.2 % (51.4–73.7) | 64.3 % (58.0–70.1) | 81.5 % (74.1–87.1) | 0.721 |
| **With R9 (shipped), both cameras** | **116/170** | **43/68** | **68.2 % (60.9–74.8)** | **63.2 % (51.4–73.7)** | **66.8 % (60.6–72.5)** | **82.3 % (75.1–87.7)** | **0.746** |
| With R9, camera 1 (lateral) | 67/85 | 19/34 | 78.8 % (69.0–86.2) | 55.9 % (39.5–71.1) | 72.3 % (63.6–79.5) | 81.7 % (72.0–88.6) | 0.802 |
| With R9, camera 2 (frontal) | 49/85 | 24/34 | 57.6 % (47.0–67.6) | 70.6 % (53.8–83.2) | 61.3 % (52.4–69.6) | 83.1 % (71.5–90.5) | 0.681 |

Without R9, camera 1: 74.1 % / 55.9 %; camera 2: 55.3 % / 70.6 %. R9 adds 6 detected falls and no false alarm.

| Activity (videos per camera: 17) | Camera 1 (lateral) | Camera 2 (frontal) |
|---|---|---|
| Fall forward using hands | 13 detected | 16 |
| Fall forward using knees | 6 | 12 |
| Fall backwards | 17 | 9 |
| Fall sideward | 16 | **3** |
| Fall sitting in an empty chair | 15 | 9 |
| Picking up an object | 1 false alarm | 2 |
| **Laying (lying still for 60 s)** | **14 false alarms** | **8** |

- **Laying gives 22 of the 25 false alarms** (22 of 34 recordings). Most `caida` come in the first 3 s (0.3–2.6 s; four later, at 7.7–30.2 s), with the person lying from the first frame. R4 needs no upright state before the fall: a lying body already meets M2 and M3, and with v = 0.01 any small downward jitter of the hip meets M1. It is the same mechanism as the bed in section 6 (12 of 12), here without even lying down.
- **Camera 2 misses many falls because the pose follows another person.** A second person sits at the right edge of camera 2's image. In 25 of the 36 falls missed by camera 2 the tracked mid-hip is at that edge (x > 0.75) in more than half of the frames with a pose, against 12 of 49 detected ones and none in camera 1 (a heuristic, checked by eye on two recordings: the pose jumps to the seated bystander during the fall). MediaPipe Pose Landmarker runs with one person; the agent has the same limitation in a room with several people.
- **Recoveries:** 12 of 170 fall recordings (all from camera 2) have a `recuperacion` after their `caida`; UP-Fall does not label getting up and the protocol leaves the subject on the mattress for the rest of the 10 s, so these are probably false, consistent with the pose jumping to the seated bystander (upright for the classifier); not checked one by one. 3 of 68 ADL recordings have a `movimiento_inestable`.

### 8.3. Main result: MCFD, frozen thresholds

**Per video** (any `caida` in the video): with R9, sensitivity 88.1 % (82.4–92.1, 155/176) and specificity 6.2 % (1.1–28.3, 1/16; only scenarios 23 and 24 are negative). This unit is misleading here: the fall scenarios contain daily activities before the fall, and when the `caida` must fall inside the fall window (1 s before the labelled `falling` onset to the end of the labelled `lying on the ground`), sensitivity drops to **50.0 % (42.7–57.3, 88/176)**.

**Per event (the main MCFD result).** Each labelled fall (23 per camera) is detected if a `caida` comes inside its window; every other `caida` inside the labelled span of the video is a false alarm. The labelled span is used because before it the actor is often outside the room and after it he gets up and other people walk in, unlabelled (51 `caida` with R9 fall there and are not counted). The non-fall labelled time is short: 8.1 min per camera.

| Camera | Falls detected, with R9 (95 % CI) | False alarms with R9 (per hour of non-fall time) | Frames with a pose |
|---|---|---|---|
| 1 | 10/23 = 43.5 % (25.6–63.2) | 19 (141/h) | 79 % |
| 2 | 17/23 = 73.9 % (53.5–87.5) | 16 (119/h) | 86 % |
| 3 | 15/23 = 65.2 % (44.9–81.2) | 20 (148/h) | 78 % |
| 4 | 11/23 = 47.8 % (29.2–67.0) | 13 (96/h) | 66 % |
| 5 | 6/23 = 26.1 % (12.5–46.5) | 9 (67/h) | 54 % |
| 6 | 10/23 = 43.5 % (25.6–63.2) | 18 (133/h) | 74 % |
| 7 | 12/23 = 52.2 % (33.0–70.8) | 11 (82/h) | 90 % |
| 8 | 7/23 = 30.4 % (15.6–50.9) | 17 (126/h) | 77 % |
| **8 cameras, each on its own** | **88/184 = 47.8 % (40.7–55.0)** | **123 (114/h)** | |
| Without R9, 8 cameras | 89/184 = 48.4 % (41.3–55.5) | 115 (107/h) | |

- **Where the false alarms come from** (with R9, 8 cameras): walking or standing 45, moving down 39, sitting 15, crouching 13, moving up 8, lying on a sofa 3. The two no-fall scenarios give 37 (scenario 23) and 23 (scenario 24).
- **Why falls are missed** (96 of 184 windows): in **52** the classifier was already in `EN_EL_SUELO` at the fall onset because of an earlier `caida` (a false alarm while sitting down, lying on the sofa or crouching, or the first fall of scenario 4) with no `recuperacion` before the real fall, so the real fall cannot raise a new `caida`; in 23 the person was standing and no rule fired; in 21 the video has no event at all (mostly camera 5, where MediaPipe finds a pose in 54 % of the frames). Scenarios with sitting, a sofa or crouching before the fall are detected by 1–4 of 8 cameras; the walk-and-fall scenarios by 3–7 (median 6).
- **Latency** (labelled onset → first `caida` in the window, 88 falls, with R9): median **1.08 s**, mean 1.36 s, p95 3.53 s, range −0.87 to 5.43 s (onsets from frame labels at the assumed 30 fps).
- **False recoveries: 0 of 88** (no `recuperacion` while the person is labelled on the ground). Before restricting to the labelled span, 56 recoveries appeared after the labels end; frame inspection of scenario 1 shows the actor getting up there, so they are real, unlabelled get-ups.

### 8.4. Secondary: more cameras per room (OR-fusion)

An alarm if **any** camera of the set fires. UP-Fall, per trial (85 falls, 34 ADL), with R9: **one camera or the other: 94.1 % sensitivity (87.0–97.5), 52.9 % specificity (36.7–68.5)**, against 78.8 % / 55.9 % for the better single camera; without R9 90.6 % / 52.9 %. Requiring both cameras (AND): 42.4 % / 73.5 %.

MCFD per event, with R9, averaged over every combination of k cameras (false alarms of different cameras merged when closer than 5 s on the common timeline):

| Cameras | Falls detected, mean (min–max) | False alarms in the 24 scenarios, mean | Per hour of non-fall time |
|---|---|---|---|
| 1 | 47.8 % (26.1–73.9) | 15.4 | 114 |
| 2 | 68.2 % (39.1–95.7) | 24.1 | 179 |
| 3 | 78.5 % (52.2–95.7) | 30.1 | 223 |
| 4 | 85.0 % (60.9–95.7) | 34.4 | 255 |
| 8 | 95.7 % (22/23) | 45.0 | 334 |

More cameras raise sensitivity steeply, because a fall missed in one view (occlusion, no pose, the pose on another person) is seen in another, but the false alarms add up almost as fast, since each camera produces its own: with this classifier, fusion buys sensitivity with false alarms rather than improving the trade-off. The per-hour rates come from 8.1 min of densely scripted confounding activity per camera and are not a home rate.

### 8.5. Secondary: leave-one-group-out recalibration over the five datasets

33 groups (URFD, 10 CAUCAFall subjects, 4 GMDCSA24 subjects, 17 UP-Fall subjects, MCFD as one group), unit = video per camera, speed calibrated by Youden in each fold as in section 2 (MCFD fall videos count as detected with any `caida`). Not the main result.

| Classifier | v chosen per fold | Sensitivity, 760 videos | Specificity | UP-Fall folds: sens. / spec. | MCFD folds | GMDCSA24 folds |
|---|---|---|---|---|---|---|
| With R9 | 0.72 in 23 folds, 0.71 in 1, 0.13–0.26 in 9 | 65.0 % (60.7–69.0) | 82.4 % (77.2–86.5) | 52.4 % / 92.6 % | 79.0 % / 6.2 % | 69.6 % / 86.4 % |
| Without R9 | 0.08 in 21 folds, 0.01–0.13 in 12 | 68.9 % (64.7–72.8) | 73.3 % (67.6–78.4) | 48.2 % / 80.9 % | 85.8 % / 6.2 % | 77.2 % / 69.1 % |

With the frozen v = 0.01 the same datasets give UP-Fall 68.2 % / 63.2 %, MCFD 88.1 % / 6.2 % and GMDCSA24 91.1 % / 65.4 %. Adding the new data moves the Youden optimum with R9 to v ≈ 0.72, which removes most lying false alarms (UP-Fall: 5 false alarms instead of 25) but loses many falls (GMDCSA24 91.1 → 69.6 %, UP-Fall 68.2 → 52.4 %, CAUCAFall 86.0 → 46.0 %). As in section 6.3, more data trades sensitivity for specificity instead of revealing a clearly better threshold; the shipped value is not changed by this analysis.

### 8.6. Interpretation

- **The single-camera sensitivity of sections 3 and 6 does not carry over.** On UP-Fall the frozen classifier detects 68.2 % of the falls (78.8 % with the lateral camera, 57.6 % with the frontal one), and on MCFD 47.8 % of the labelled falls per camera at event level, below the 82.5 % of section 3.6 and the 91.1 % of GMDCSA24. The causes are visible in the data, not in the thresholds: a second person in view (the pose model follows one person), cameras where the pose is often lost (MCFD camera 5), views from the front, and, on MCFD, earlier false alarms that leave the classifier "on the floor" when the real fall comes.
- **Lying is still the main false alarm, now without any lying-down movement.** 22 of 34 UP-Fall "laying" recordings fire, most in their first seconds: R4 has no requirement that the person was upright before the fall. Together with the bed of section 6 this is the clearest, reproducible limitation of the rules, and it would need a new rule and a new ADR, validated on new data; nothing was changed here.
- **On MCFD the per-video unit hides the problem** (88 % "sensitivity") that the event unit shows (48 %, and 114 false alarms per hour of scripted activity). MCFD's scenarios pack sitting, crouching, lying on a sofa and falls into a few seconds each, a harder stream than any clip dataset.
- **More cameras per room** raise sensitivity (UP-Fall 94.1 % with either of two cameras; MCFD 68 % with two and 96 % with eight), at a roughly proportional false-alarm cost. Fusion helps against occlusion and lost poses, not against the rules' confusion with lying down.
- **Limitations of this test:** young adults and one actor, simulated falls onto a mattress; UP-Fall's subset is trial 1 only and has no frame-level labels (no latency); MCFD's time base (30 fps) is inferred, its labels are given per frame of a reference camera and were moved with the report's delays, and the false-alarm rates come from 65 camera-minutes of non-fall time. The fused false-alarm merge window (5 s) and the 1 s onset tolerance were fixed before looking at the results; the restriction of the MCFD event count to the labelled span was added after a first run showed `recuperacion` and `caida` events in the unlabelled tails, and is reported with the number of events it leaves out (51).

## References

Alam, E., Sufian, A., Dutta, P., Leo, M., & Hameed, I. A. (2024). GMDCSA-24: A dataset for human fall detection in videos. *Data in Brief, 57*, 110892. https://doi.org/10.1016/j.dib.2024.110892 · Data: https://doi.org/10.5281/zenodo.13354453

Auvinet, E., Rougier, C., Meunier, J., St-Arnaud, A., & Rousseau, J. (2010). *Multiple cameras fall data set* (Technical Report No. 1350). DIRO, Université de Montréal. · Erratum: Feng, M., & Meunier, J. (2025, November 28). *Erratum — Technical report of the Multi-Camera Fall Dataset.*

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744

Eraso Guerrero, J. C., Muñoz España, E., Muñoz Añasco, M., & Pinto Lopera, J. E. (2022). Dataset for human fall recognition in an uncontrolled environment. *Data in Brief, 45*, 108610. https://doi.org/10.1016/j.dib.2022.108610 · Datos: https://doi.org/10.17632/7w7fccy7ky.4

Kwolek, B., & Kepski, M. (2014). Human fall detection on embedded platform using depth maps and wireless accelerometer. *Computer Methods and Programs in Biomedicine, 117*(3), 489–501. https://doi.org/10.1016/j.cmpb.2014.09.005 · Datos: https://fenix.ur.edu.pl/~mkepski/ds/uf.html

Martínez-Villaseñor, L., Ponce, H., Brieva, J., Moya-Albor, E., Núñez-Martínez, J., & Peñafort-Asturiano, C. (2019). UP-Fall Detection Dataset: A multimodal approach. *Sensors, 19*(9), 1988. https://doi.org/10.3390/s19091988 · Data: https://sites.google.com/up.edu.mx/har-up/

Traverso, A., Bayram, A., Rossettini, G., Chiappinotto, S., Galazzi, A., & Palese, A. (2024). Investigating the biomechanics of falls in older adults in long-term care using a video camera: A scoping review. *BMC Geriatrics, 24*, 810. https://doi.org/10.1186/s12877-024-05395-2

Youden, W. J. (1950). Index for rating diagnostic tests. *Cancer, 3*(1), 32–35. https://doi.org/10.1002/1097-0142(1950)3:1<32::AID-CNCR2820030106>3.0.CO;2-3
