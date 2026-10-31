# Classifier validation with public datasets

This document reports how the Kinematic Classification Service was validated with the two public datasets named in the project charter (URFD and CAUCAFall), what was changed based on the results, and which limitations remain. It is the technical basis for indicator OE4-I1 ("accuracy, sensitivity and specificity on public datasets").

To reproduce it:

```bash
make datasets   # downloads URFD and CAUCAFall into datos/ (about 220 MB)
make validar    # extracts poses and generates resultados/reporte.md
uv run python scripts/comparar_pipelines.py --todos --guardar   # agent vs validation, frame by frame (section 3.5)
```

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
6. **The validation is per video,** not per instant. It does not measure the alert latency, whose requirement is under 10 s; the classifier emits the fall as soon as M3 is met.

7. **Raising the sensitivity with pose rules alone did not work** (section 6): loosening the visibility gate of the speed, detecting tilts toward the camera, declaring a fall when the pose is lost after a fast descent and re-calibrating the angle and the ratio all lost more specificity than they gained sensitivity.

The ranges in which each tunable value keeps this performance (US-45) are measured in [validation-rangos.md](validation-rangos.md).

## 6. Attempts to raise sensitivity without forcing it (2026-10-31): none accepted

**Question.** Can the sensitivity of R4–R9 (82.5 %, 66/80 falls) be raised with a single camera and without trading it for specificity? **Answer on URFD + CAUCAFall: no.** Five rule changes and one re-calibration were tested; every one that raised sensitivity lowered specificity by more, and the classifier stays as validated in sections 3.1–3.6.

### 6.1. Protocol

1. **Development data only:** URFD and CAUCAFall, poses `lite-video-8fps-jpeg` (section 2). The per-video results of the third, hold-out dataset were not looked at.
2. **Diagnosis before the candidates.** The 14 misses of the baseline were traced frame by frame:
   - URFD `fall-10`, `-18`, `-24`, `-26` and `-30` have **one ankle** below visibility 0.5 during the whole descent (the Kinect at body height cuts off or hides one foot). A6 needs the nose, both hips and both ankles to measure the speed, so M1 is never evaluated in the frames where the body tilts. CAUCAFall subject 10 `Fall_right` has **both** ankles hidden in the whole clip.
   - `fall-27` and `fall-29` fall toward the camera: the center line shrinks from about 90 px to 19 px while its angle stays above 45°, and then the pose is lost.
   - Subject 8 `Fall_left`: fast descent while still upright (0.29 bodies/s), then no pose until the end of the clip. Subject 8 `Fall_forward`: no pose in any of its 49 frames, so no pose-based rule can detect it.
   - Subject 3 `Fall_forward` and `Fall_sitting`, subject 4 `Fall_sitting`: noisy or nearly static poses, no clear cue.
3. **Pre-registration.** The rationale and the prediction of each candidate were written down before running any of them (section 6.2). One more candidate (C1b) was designed after the first round and is marked **post hoc**.
4. **Nested selection.** Every re-calibrated or new threshold is chosen **inside each training fold** of the leave-one-group-out validation (maximum Youden index of the 10 training groups; ties: the lowest speed, then the most conservative value of the other thresholds, and for the angle and the ratio the published value), and only then applied to the held-out group. Cross-dataset: chosen on one dataset, measured on the other.
5. **Acceptance rule (fixed beforehand):** LOGO sensitivity must rise, the specificity loss must be smaller than the sensitivity gain, the gain must not come from one dataset while the other loses, and there must be no more false recoveries.
6. **Statistics:** 95 % Wilson intervals; McNemar's exact test (two-sided binomial on the discordant pairs) on the paired per-video outcomes against the baseline, on all 170 videos (correct or not) and on the 80 falls (detected or not).
7. **Multiple comparisons:** 13 candidate settings and **10,600 distinct threshold configurations** were evaluated (each candidate × 100 speeds × its own grid). With that many looks, a single "significant" improvement would be expected by chance; a **fully nested selection**, in which every training fold also chooses the candidate, estimates the whole procedure.

Reproduce (the candidates exist only at commit `233480f` of `feature/classifier-sensitivity`; later commits keep the script and the baseline):

```bash
git checkout 233480f
uv run python scripts/evaluar_candidatos.py      # writes resultados/candidatos/
```

### 6.2. Candidates and rationale

| ID | Change | Rationale (written before testing) | New threshold |
|---|---|---|---|
| **C1** | The speed (R1) needs only **both hips** visible; the scale is still the median center-line length of the last 2 s. "Upright" keeps the strict A6. | R1 measures the hip. A6 was introduced because doubtful **hips** jump; requiring the ankles too throws away frames where the hip is reliable and only a foot is hidden, which is common in falls. | none (v nested) |
| **C2** | M2 is also met, and the person is not upright, when the center line is shorter than cos 45° = 0.707 times its median length while upright in the last 10 s. | R2 sees only the tilt in the image plane. A segment of length L₀ tilted φ toward the camera projects as L₀ cos φ, so a tilt past the same 45° gives L < 0.707 L₀. The factor comes from θ₀, it is not fitted. | none |
| **C3** | `caida` if a frame shows a hip descent ≥ v_perdida and then no pose is seen for the whole reaction window (1.48 s). | MediaPipe loses people on the floor (section 4); a fall whose descent is seen but whose end is not is then missed. Walking out of the image does not drop the hip. | v_perdida ∈ {0.1, …, 1.0} nested |
| **C4** | Re-calibrate the angle and the ratio jointly with the speed. | 45° and 1 come from OpenPose, 14 points and side views (Chen et al., 2020); MediaPipe's 33 points and an elevated camera change both. | θ₀ ∈ {35…55°}, T ∈ {0.8…1.2} nested |
| **C1b** (post hoc) | The speed needs the nose, both hips and **at least one** ankle; with one ankle visible, the feet of the center line are that ankle. | After C1: its new false alarms had **both** ankles hidden, so the angle of M2 pointed to MediaPipe's guessed feet. One hidden ankle is the normal self-occlusion of a side view. | none (v nested) |

**Considered and not tested,** with the reason fixed beforehand: One-Euro or median smoothing of the landmarks (the misses come from gated or lost points, not from jitter, and at 8 fps a filter delays and flattens the 0.25–1 s descent that M1 needs); MediaPipe world landmarks for the vertical speed (their origin is the hip itself, A3); the *full* model only when *lite* loses the person (ADR 0006 found no gain, and on the already extracted non-JPEG poses the full model sees the same or fewer frames of the hardest misses: subject 8 `Fall_forward` 0/49 with both, subject 3 `Fall_forward` 17 vs 35 frames; it would also double the CPU load of the household PC); a speed threshold adapted to the body scale (R1 is already divided by the body length).

### 6.3. Results (8 fps, JPEG, leaving one group out, thresholds nested)

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

### 6.4. Why the gains are not real

Sweeping the speed threshold on all 170 videos (descriptive, not nested; v = 0.01–1.0) shows that C1 and C1b mostly move the classifier along the sensitivity–specificity trade-off instead of improving it. Near the baseline's operating point the baseline is better at equal specificity: with 71–74 of 90 activities without alarm it detects 54–66 falls, while C1b first reaches 71 of 90 at v = 0.5 (74 of 90, 53 falls) and C1 at v = 0.7 (73 of 90, 52 falls). The curves cross only at high specificity (78 of 90: baseline 45 falls, C1b 50), where both detect far fewer falls than the validated setting. The diagnosis explains it: with v = 0.01, M1 means little more than "the hip could be measured and went down", so A6's visibility gate is what keeps the angle and the ratio of doubtful poses out of the decision, and loosening it lets in the false alarms of people lying on the floor on purpose, kneeling or sitting, exactly the known confusions. C2 helps with falls toward the camera, but crouching and lying down also shorten the center line (the body is not rigid). C3 found no fall that ends out of view that the other rules miss, because the nested v_perdida settles at 1.0 bodies/s in 10 of 11 folds. C4 picks 40° in 9 of 11 folds (45° in one, 35° in the URFD fold) and loses 2 URFD falls.

**Conclusion.** With a single camera, these pose-based changes do not raise the sensitivity of the classifier honestly; what remains are falls in which the pose is lost or never found (subject 8 `Fall_forward`), and confusions with lying down on purpose that pose geometry cannot resolve. Raising sensitivity further needs more information than one 2D pose per frame (for example, motion or appearance features where the pose is lost, or the pilot's own recordings), not looser thresholds.

### 6.5. Hold-out check

Because no change was accepted, the frozen classifier is the baseline itself (R4–R9, v = 0.01, the defaults of section 4 of the specification). On 2026-10-31 the third-dataset integration (GMDCSA-24, branch `feature/holdout-validation`) existed only as uncommitted work in progress, so it was not run from this branch. **Pending:** once that branch is merged, run once, without recalibration:

```bash
uv run python scripts/evaluar_holdout.py      # name and options as merged by feature/holdout-validation
```

and report the baseline (identical to the frozen classifier). As a secondary, declared-in-advance negative control, the most promising rejected candidate (C1b) can be run once on the same poses at commit `233480f` with v = 0.02 (the value chosen on all of URFD + CAUCAFall): if it does not beat the baseline there either, the rejection generalizes.

### 6.6. Threats to validity

- **Adaptive design.** The diagnosis and C1b used the same 170 videos as the evaluation; nesting protects the threshold values, not the choice of rules, so the C1b row is optimistic. 10,600 configurations were tried; none was accepted, so this inflates no reported gain, but it would have.
- **Small samples:** 80 falls and 90 activities give ±7–10 point intervals; the differences of C2, C3 and C4 are inside them.
- **Grouping:** URFD is one group (its subjects are not published), so its fold trains only on CAUCAFall.
- **Simulated falls by young adults,** short clips (sections 1 and 5).
- **Youden index** weighs a missed fall and a false alarm equally; a criterion that favored sensitivity would choose other operating points. Section 6.4 shows the baseline is better near its own operating point, but the curves of C1b and the baseline cross at high specificity, so the conclusion is specific to operating points with about 80 % specificity.

## References

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744

Eraso Guerrero, J. C., Muñoz España, E., Muñoz Añasco, M., & Pinto Lopera, J. E. (2022). Dataset for human fall recognition in an uncontrolled environment. *Data in Brief, 45*, 108610. https://doi.org/10.1016/j.dib.2022.108610 · Datos: https://doi.org/10.17632/7w7fccy7ky.4

Kwolek, B., & Kepski, M. (2014). Human fall detection on embedded platform using depth maps and wireless accelerometer. *Computer Methods and Programs in Biomedicine, 117*(3), 489–501. https://doi.org/10.1016/j.cmpb.2014.09.005 · Datos: https://fenix.ur.edu.pl/~mkepski/ds/uf.html

Traverso, A., Bayram, A., Rossettini, G., Chiappinotto, S., Galazzi, A., & Palese, A. (2024). Investigating the biomechanics of falls in older adults in long-term care using a video camera: A scoping review. *BMC Geriatrics, 24*, 810. https://doi.org/10.1186/s12877-024-05395-2

Youden, W. J. (1950). Index for rating diagnostic tests. *Cancer, 3*(1), 32–35. https://doi.org/10.1002/1097-0142(1950)3:1<32::AID-CNCR2820030106>3.0.CO;2-3
