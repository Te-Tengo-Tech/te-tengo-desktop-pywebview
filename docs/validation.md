# Classifier validation with public datasets

This document reports how the Kinematic Classification Service was validated with the two public datasets named in the project charter (URFD and CAUCAFall), what was changed based on the results, and which limitations remain. It is the technical basis for indicator OE4-I1 ("accuracy, sensitivity and specificity on public datasets").

To reproduce it:

```bash
make datasets   # downloads URFD and CAUCAFall into datos/ (about 220 MB)
make validar    # extracts poses and generates resultados/reporte.md
```

## 1. Data

| Dataset | Videos | Camera | Use |
|---|---|---|---|
| **URFD** (Kwolek and Kepski, 2014) | 30 falls and 40 daily activities, of which **16 end with the person lying on the floor on purpose**, according to the dataset's per-frame labels | Kinect parallel to the floor, at body height; the RGB half of the MP4 is used (320 × 240) | CC BY-NC-SA 4.0 |
| **CAUCAFall** (Eraso Guerrero et al., 2022) | 10 people × (5 falls: forward, backward, left, right and from sitting + 5 activities: walking, jumping, picking up an object, sitting down and kneeling) = 100 videos | Surveillance camera **elevated in a corner** of a home (720 × 480), with occlusions and lighting changes | CC BY 4.0 |

Neither one includes older adults or real falls; this limitation is declared in the charter (risk 9).

## 2. Protocol

1. **Same processing as in production.** Each video is downscaled to 480p and 8 fps (6 and 10 fps were also tested). It is compressed as JPEG with quality 80, as the agent does, and passed through MediaPipe Pose Landmarker *lite* in VIDEO mode. The poses are saved once and then replayed in **the same `ClasificadorCinematico` as the worker**.
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
24 videos (12 from URFD and 12 from CAUCAFall) were sent to the running worker, using the simulated agent over WebSocket. The fall events matched the offline evaluation in **24 of 24**.

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

1. **Lying down on the floor on purpose** is confused with a fall in 6 of 16 URFD cases. In a home, this means a false alarm when the older adult lies down on the floor by choice.
2. **Picking up an object and kneeling** produce false alarms in 3 of every 10 cases with an elevated camera.
3. **Calibration depends on the camera location** (section 3.3). It must be repeated with the pilot recordings, as the charter states (risks 2, 3 and 6).
4. **There are no older adults or real falls** in the data (charter risk 9). The real false alarm rate will be measured in the home (OE4-I2).
5. **The validation is per video,** not per instant. It does not measure the alert latency, whose requirement is under 10 s; the classifier emits the fall as soon as M3 is met.

## References

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744

Eraso Guerrero, J. C., Muñoz España, E., Muñoz Añasco, M., & Pinto Lopera, J. E. (2022). Dataset for human fall recognition in an uncontrolled environment. *Data in Brief, 45*, 108610. https://doi.org/10.1016/j.dib.2022.108610 · Datos: https://doi.org/10.17632/7w7fccy7ky.4

Kwolek, B., & Kepski, M. (2014). Human fall detection on embedded platform using depth maps and wireless accelerometer. *Computer Methods and Programs in Biomedicine, 117*(3), 489–501. https://doi.org/10.1016/j.cmpb.2014.09.005 · Datos: https://fenix.ur.edu.pl/~mkepski/ds/uf.html

Traverso, A., Bayram, A., Rossettini, G., Chiappinotto, S., Galazzi, A., & Palese, A. (2024). Investigating the biomechanics of falls in older adults in long-term care using a video camera: A scoping review. *BMC Geriatrics, 24*, 810. https://doi.org/10.1186/s12877-024-05395-2

Youden, W. J. (1950). Index for rating diagnostic tests. *Cancer, 3*(1), 32–35. https://doi.org/10.1002/1097-0142(1950)3:1<32::AID-CNCR2820030106>3.0.CO;2-3
