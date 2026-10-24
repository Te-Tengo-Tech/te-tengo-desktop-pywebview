# Kinematic classification specification

This document explains **what** the Kinematic Classification Service computes, **why**, and **where** each formula and each threshold **comes from**. The code does not cite authors: each function names the rule (R1–R9) or the adaptation (A1–A5) that it implements, and this document gives the details with their sources.

Code: [`src/te_tengo_deteccion/clasificacion/`](../src/te_tengo_deteccion/clasificacion) · Tests: [`tests/deteccion/clasificacion/`](../tests/deteccion/clasificacion)

**How to read the origin of each value**

| Mark | Meaning |
|---|---|
| **Source** | Stated in a publication. The section, equation or figure is given. |
| **Backlog** | Comes from an acceptance criterion in the project's product backlog. |
| **Adaptation** | Our own decision to bring the method to MediaPipe and a single camera. **Must be validated.** |
| **Proposal** | Our own rule that combines sources; it **has not been validated** yet. |

---

## 1. Input data

**MediaPipe Pose Landmarker** returns 33 landmarks for each person:
- `x` and `y` range from 0 to 1, divided by the image width and height, and `y` grows downward.
- `visibility` is the probability that the point is visible in the image.
- It also returns *world landmarks* in meters, but **with the hip center as the origin** (Google, s.f.-b).

The reference method (Chen et al., 2020) uses a **14-point** skeleton, s₀ to s₁₃, numbered in its Figure 4. The points used here are:

| Reference method point | MediaPipe landmark (Google, s.f.-a) | Use |
|---|---|---|
| s₀ head | 0 nose (**Adaptation A2**) | Upper end of the center line |
| s₈ right hip · s₁₁ left hip | 24 · 23 | Hip center |
| s₁₀ right ankle · s₁₃ left ankle | 28 · 27 | Lower end of the center line |

### Input adaptations

| ID | Adaptation | Reason |
|---|---|---|
| **A1** | All coordinates are converted to pixels (`x · ancho`, `y · alto`) before computing. | With a 640 × 480 image, normalized coordinates distort the angles and the width/height ratio. |
| **A2** | The nose replaces the "head". | MediaPipe has no head point; the nose is the most stable central point of the head. |
| **A3** | The speed is signed (only the descent counts), it is divided by the median length of the center line over the last 2 s, and it is the largest descent per second compared with any sample between 0.25 and 1 s earlier. | A 2D camera does not measure meters, and *world landmarks* do not help because their origin is the hip itself. The 1 s window tolerates the frames that MediaPipe loses during the fall and covers its duration (583 ± 255 ms until pelvis impact; Choi et al., 2015, as cited in Traverso et al., 2024). See the validation. |
| **A4** | Δt is the real difference between the sample timestamps. | The agent sends 5 to 10 fps, not a fixed rate. |
| **A6** | The speed (R1) and the "upright" state (R5 and R7) are computed only with the nose, hips and ankles visible (≥ 0.5). M2 and M3 do use poses with poorly visible points. | With poorly visible points, MediaPipe estimates unreliable positions: the hip "jumps" and produces impossible speeds, and a person lying down can look as if standing. A false alarm is preferable to missing a fall, but a false recovery is not. |
| **A7** | If the head is lower than the feet in the image, M2 and M3 are met and the person is not upright. | With an elevated camera, when falling toward the camera the body appears foreshortened: the angle with absolute value comes out "almost vertical" and the ratio does not exceed 1. When standing, the head is never below the feet. See the validation. |
| **A8** | Recovery requires looking upright for 1 continuous second. | MediaPipe sometimes estimates a person lying down as "standing" for one frame. 1 s is the smallest value that removed the false recoveries in the 30 URFD falls. |
| **A5** | Only landmarks with visibility ≥ 0.5 enter the body bounding box. | Hidden points "invented" by the model enlarge the box. 0.5 is used because it is the default value of the MediaPipe confidence thresholds (Google, s.f.-a). |

---

## 2. Per-frame conditions

### R1. Descent speed of the hip center → condition M1

**What it measures.** How fast the hip center moves down. The reference method uses it as a proxy for the center of gravity. In a sudden fall, the center of gravity changes sharply in the vertical direction.

**Source.** Chen et al. (2020), section 3.2, equations 1 to 3:

```
ȳ(t) = ( y_t,8 + y_t,11 ) / 2               hip center
Δt   = t₂ − t₁                               evaluated every 5 frames, 0.25 s
v    = | ȳ(t₂) − ȳ(t₁) | / Δt
M1   = 1  if  v ≥ v̄
```

**The published threshold is contradictory:** v̄ = 0.009 m/s in section 3.2, and 0.09 m/s in section 4.2 and Figure 9.

**Implementation (A3, A4, A6).**
```
v(t) = max  [ ȳ(t) − ȳ(tᵢ) ] / (t − tᵢ) / L̃        for each sample tᵢ ∈ [t − 1 s, t − 0.25 s]
L̃    = median length of the center line over the last 2 s
```
- **Signed:** it is positive when the hip moves down; getting up quickly does not count.
- **Unit:** bodies per second.
- **Reliable frames only:** only frames with the key points visible are used.
- **Calibrated threshold: 0.01 bodies/s** ([validation.md](validation.md)). It almost means "the hip went down somewhat". At 8 fps and in 2D, speed contributes little on its own, because MediaPipe loses part of the descent frames.

### R2. Angle of the center line with the floor → condition M2

**What it measures.** How much the body has tilted. When falling, the body tilts more and more and loses the vertical.

**Source.** Chen et al. (2020), section 3.3, equation 4 and Figure 6:

```
s̄(t) = ( s₁₀ + s₁₃ ) / 2                    midpoint of the ankles
L    = segment from s₀ (head) to s̄
θₜ   = arctan | ( y_t,0 − ȳₜ ) / ( x_t,0 − x̄ₜ ) |
M2   = 1  if  θ < θ₀ ,  θ₀ = 45°
```

**Implementation.** `θ = atan2(|Δy|, |Δx|)` gives the same result without dividing by zero when the person is fully vertical. In addition, M2 is met if the head is below the feet (A7).

**Note on the source.** The text of section 3.3 says "midpoint of s₁₂ and s₁₃", but the equation and Figure 6 use s₁₀ and s₁₃, the two ankles. The equation is followed, because s₁₂ is a knee.

### R3. Width/height ratio of the body bounding box → condition M3

**What it measures.** The final shape of the body: standing, it is narrow and tall; lying down, it is wide and low. Unlike the width or the height alone, the ratio does not change with the distance to the camera.

**Source.** Chen et al. (2020), section 3.4, equation 5 and Figure 7:

```
P  = Width / Height
M3 = 1  if  P ≥ T ,  T = 1         when walking P < 1; when falling P > 1
```

**Implementation (A1, A5).** The box is built from the visible landmarks, in pixels. If the height is 0, P = ∞. M3 is also met if the head is below the feet (A7).

---

## 3. Event rules

```
                 M1 and M2                        M3 within the window
   NORMAL ─────────────────► INICIO_CAÍDA ─────────────────────────────► EN_EL_SUELO
     ▲  ▲                      │       │                                   │      │
     │  └─ window expires ─────┘       │ upright again                     │      │ 30 s
     │     (no event)                  ▼                                   │      ▼
     │                    R7 movimiento_inestable                          │  R6 caida_confirmada
     └──────────── upright again: R5 recuperacion ◄────────────────────────┘
                                     (on entering EN_EL_SUELO: R4 caida)

   NORMAL or INICIO_CAÍDA ── upright ≤ 10 s ago, hip ≥ 0.4 L lower, horizontal 2 s ──► EN_EL_SUELO
                                                                    (R9 caida, slow fall)
```

"Upright" means θ > 45° and P < 1, the condition of R5.

| ID | Event | Rule | Origin |
|---|---|---|---|
| **R4** | `caida` | M1 and M2, and then M3 within the reaction window (1.48 s) | **Source:** Chen et al. (2020), Figure 2, which evaluates M1 → M2 → M3 in sequence. **Adaptation:** since they do not occur in the same frame, M3 is awaited within the window. |
| **R5** | `recuperacion` | While on the floor, upright (θ > 45°, P < 1, head above the feet and points visible) for 1 s | **Source:** Chen et al. (2020), section 3.5 and Figure 12: getting up is the reverse process of the fall, and it is recognized when the angle exceeds 45° again and the ratio stays below 1 "for a period". The article does not give its duration; the 1 s value is adaptation A8, calibrated. |
| **R6** | `caida_confirmada` | Still in `EN_EL_SUELO` after 30 s. If the person is not visible, the time keeps counting. | **Backlog:** US-13, "Confirmación por permanencia en el suelo". |
| **R7** | `movimiento_inestable` | M1 and M2 without reaching M3, and the person is upright again within the window | **Proposal** (see below). |
| **R8** | `deteccion_no_confiable` | 300 consecutive seconds without a valid pose. The notice is sent once, until the person is seen again. | **Backlog:** US-15, "Condiciones de captura". |
| **R9** | `caida` (slow fall) | Outside `EN_EL_SUELO`: the person was upright during the last 10 s, the hip is ≥ 0.4 center-line lengths below the highest upright hip of those 10 s, and the body has been horizontal (M3) for 2 s. Goes to `EN_EL_SUELO` like R4. | **Proposal** (see below; ADR 0009). |

### Reaction window: 1.48 s
Gutiérrez et al. (2023) model the body as an inverted pendulum. With the center of mass height of older adults (0.974 m in men and 0.930 m in women), they calculate that a fall without reaction takes **between 1.0 and 1.48 s**. The upper limit is used as the maximum time between the start of the fall and the horizontal posture.

### Why R7 requires M1 and M2 at the same time (proposal)
In the results of Chen et al. (2020), section 4.2:
- **Figure 9:** only falling and crouching exceed the speed threshold.
- **Figure 10:** only falling and bending over go below 45°.
- **Figure 11:** only the fall exceeds the ratio of 1.

Therefore, requiring M1 **and** M2 rules out crouching (M1 only) and bending over (M2 only). Walking and sitting down meet neither. If M3 does not follow and the person is upright again, the system treats it as a recovered loss of balance.

**Limitation:** it does not detect a slight sway while standing or a sudden lean without tilting. The search for sources for these cases is ongoing.

### R9: slow falls (proposal)
R4 needs the hip to go down **while** the body is tilted, and the horizontal posture within 1.48 s. A slow fall can break both: sliding down from a chair or a bed keeps the torso upright while the hip goes down; lying back after sagging to the floor or after kneeling tilts the body when the hip no longer goes down; and sagging can take longer than the window. Such falls are frequent in older adults: in 227 falls filmed in long-term care, 12 % happened while sitting down and 11 % were collapses (Robinovitch et al., 2013).

R9 looks at the **cumulative** drop instead of the speed:

```
ref   = upright frame of the last T s with the highest hip (smallest ȳ)       T = 10 s
D(t)  = ( ȳ(t) − ȳ_ref ) / L_ref                                             in center-line lengths
caida   if  D ≥ 0.4  and  M3 on every frame with a pose during the last P s   P = 2 s
```

- **Upright shortly before.** Only a person who was standing in the last 10 s can fall; someone who has been sitting or lying for longer cannot trigger R9. The reference is the highest hip, not the last upright frame, because sitting on the floor or kneeling still meets the "upright" test (θ > 45°, P < 1).
- **Floor, not bed.** Standing, the hip is about 0.6 lengths above the ankles. Lying on a bed or a sofa it is about 0.2 lengths lower, and on the floor about 0.5 lower (an estimate from body proportions for a side view; our own). 0.4 is between both.
- **Horizontal for 2 s.** A short stretch on the floor, or MediaPipe estimating one horizontal frame, does not trigger it. A frame with a pose that is not horizontal restarts the count; frames without a pose do not, because MediaPipe loses people lying on the floor, but the fall is declared on the next frame with a pose (declaring it without a pose added false alarms and no falls in the validation).
- The event is the same `caida`, with `caida_lenta = 1` and `descenso = D` in its parameters, and continues to `EN_EL_SUELO` as R4.

**Limitations:** lying down **on the floor** on purpose looks the same as a slow fall that ends lying (it adds false alarms in URFD); a slow fall that ends **sitting** on the floor is not detected; and lying on a bed is excluded only by geometry, because no dataset has it. The default values come from geometry and the reported scenarios; on the datasets they add the slow falls that R4 missed (see validation.md, section 3.6).

### Validation with datasets
Adaptations A3, A6, A7 and A8 and the speed threshold came from validating with URFD and CAUCAFall. Result under production conditions (8 fps, JPEG, leaving one group out): **sensitivity 81.2%, specificity 81.1%, accuracy 81.2%** and no false recoveries with R4 to R8; with R9, **82.5%, 78.9% and 80.6%**, still without false recoveries. Details, protocol and limitations in [validation.md](validation.md).

---

## 4. Threshold table

| Field (`[clasificacion]` of the installation file) | Value | Rule | Origin | Safe range (US-45) |
|---|---|---|---|---|
| `velocidad_descenso_min` | 0.01 (the agent's calibrated default in `te_tengo_captura/config.py`; the core has no default value) | R1 | Calibrated with URFD and CAUCAFall ([validation.md](validation.md)) | 0.005–0.05 |
| `intervalo_velocidad_s` | 0.25 s | R1 | Chen et al. (2020), sec. 3.2 | — (not in US-45) |
| `ventana_velocidad_s` | 1 s | R1 | Adaptation A3 (descent duration: Choi et al., 2015, in Traverso et al., 2024) | — (not in US-45) |
| `persistencia_erguido_s` | 1 s | R5 | Adaptation A8, calibrated with URFD | 0.75–3 s |
| `angulo_linea_central_max_grados` | 45° | R2, R5 | Chen et al. (2020), sec. 3.3 | 45–50° |
| `razon_ancho_alto_min` | 1 | R3, R5 | Chen et al. (2020), sec. 3.4 | 1.0–1.4 |
| `ventana_reaccion_s` | 1.48 s | R4, R7 | Gutiérrez et al. (2023) | 1.0–3.0 s (data insensitive) |
| `confirmacion_suelo_s` | 30 s | R6 | Backlog, US-13 | 15–120 s (untested) |
| `descenso_caida_lenta_min` | 0.4 lengths | R9 | Proposal: between a bed (≈ 0.2) and the floor (≈ 0.5) | 0.3–0.6 |
| `ventana_caida_lenta_s` | 10 s | R9 | Proposal | 5–20 s (untested) |
| `permanencia_caida_lenta_s` | 2 s | R9 | Proposal | 1.5–5 s |
| `sin_deteccion_confiable_s` | 300 s | R8 | Backlog, US-15 | — (not in US-45) |
| `visibilidad_min` | 0.5 | A5 | MediaPipe default value (Google, s.f.-a); to be calibrated | — (not in US-45) |

The safe ranges are those the installer may use per camera (US-45, CA-45.1 and CA-45.2). They were measured on URFD and CAUCAFall under production conditions in [validation-rangos.md](validation-rangos.md), which also says which ends are untested.

---

## 5. Evidence and limitations of the reference method

| Aspect | What Chen et al. (2020) report | Implication for Te Tengo |
|---|---|---|
| Validation | 10 volunteers (163–183 cm), 100 actions in a laboratory: 60 falls and 40 non-falls (sec. 4.1, Tables 3 and 4) | They are not older adults; validation with datasets and our own recordings is needed |
| Results | Sensitivity 98.3%, specificity 95% and accuracy 97% (Table 6) | They are the comparison target, not a guaranteed result |
| Errors | Two "bending over" actions were confused with a fall (Table 5). The authors attribute it to missing points, non-optimal thresholds and simulated falls with self-protection (sec. 4.2) | Calibrate the thresholds; R7 reduces the confusion with bending over |
| View | Only the action seen from the side was recognized (future work b) | Test falls toward the camera, away from it and diagonally |
| Occlusion | Not solved (future work a) | R6 keeps counting even if the person is not visible; evaluate occlusions |

---

## 6. How each rule is tested

| Rule | Test |
|---|---|
| R1–R3 | `tests/clasificacion/test_parametros.py` |
| R4–R8 | `tests/clasificacion/test_estados.py`: fall, confirmation, recovery, recovered stumble, stumble that ends in a fall, crouching, bending over, walking and 5 min without a person |
| R9 | `tests/clasificacion/test_estados.py`: sliding down and slumping back, kneeling and then lying, frames without a pose, lying on a bed, sitting on the floor for longer than the window, lying for less than 2 s, and horizontal after the reaction window |

---

## References

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744

Google. (s.f.-a). *Pose landmark detection guide*. Google AI Edge. https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker

Google. (s.f.-b). *Pose landmark detection guide for Python*. Google AI Edge. https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python

Traverso, A., Bayram, A., Rossettini, G., Chiappinotto, S., Galazzi, A., & Palese, A. (2024). Investigating the biomechanics of falls in older adults in long-term care using a video camera: A scoping review. *BMC Geriatrics, 24*, 810. https://doi.org/10.1186/s12877-024-05395-2

Robinovitch, S. N., Feldman, F., Yang, Y., Schonnop, R., Leung, P. M., Sarraf, T., Sims-Gould, J., & Loughin, M. (2013). Video capture of the circumstances of falls in elderly people residing in long-term care: An observational study. *The Lancet, 381*(9860), 47–54. https://doi.org/10.1016/S0140-6736(12)61263-X

Gutiérrez, J., Martin, S., & Rodriguez, V. (2023). Human stability assessment and fall detection based on dynamic descriptors. *IET Image Processing, 17*(11), 3177–3195. https://doi.org/10.1049/ipr2.12847

Gutierrez Soto, J. O., & Riva Rodriguez, E. A. (2026). *Product backlog del sistema basado en estimación de pose para la detección de caídas* [Documento interno del proyecto]. Universidad Peruana de Ciencias Aplicadas.
