# 0012. Specificity study: hold-and-cancel, ankle-free path and identity-jump gate

**Status:** proposed (2026-11-05). Draft written in two steps: the context, the candidates, their rationale, grids, predictions and the protocol (sections "Context" to "Protocol") were committed **before** any candidate was run on any dataset; "Results" and "Decision" were added afterwards. Every candidate is off by default, so the shipped classifier does not change unless this ADR is accepted.

## Context
On the development data (URFD + CAUCAFall, 170 videos, leaving one group out) the shipped classifier (R4–R9, v = 0.01) has 82.5 % sensitivity and 78.9 % specificity: 19 false alarms in 90 daily activities and 14 missed falls. On the hold-out sets specificity is lower (GMDCSA24 65.4 %, UP-Fall 63.2 %, MCFD 114 false alarms per hour). ADR 0010 rejected five ways of raising sensitivity (relaxing A6, foreshortening, lost pose, re-calibrating angle and ratio), and ADR 0011 proposed F3 (R4 needs a geometric upright frame in the last T s) for lying still.

**Diagnosis of the baseline errors** (frozen v = 0.01, development data only; done before writing the candidates, so the choice of candidates is adaptive, see "Threats"):

- 14 of the 19 false alarms show at least one geometrically upright frame (θ > 45°, P < 1, head above the feet) after the `caida`: kneeling (3/3) and picking up an object (3/3) stand up again 0.6–6 s later, as do 6 URFD activities (some of them lying down on the floor and getting up again). Among the 66 detected falls, 7 show upright frames after the `caida`, isolated or short runs (MediaPipe guessing a standing pose for a lying person, A8).
- The person was upright 0.1–2.1 s before every false alarm, so a recent-upright precondition (F3) cannot remove them on these data.
- At the instant of the `caida`, the hip drop from the last upright frame and the torso angle overlap between falls and false alarms (11 falls have dropped < 0.2 lengths when R4 fires, because M3 is reached mid-descent). A hip-drop or torso-angle gate at the trigger was therefore **not** made a candidate.
- 7 of the 14 misses never pass A6 during the descent because one or both ankles are hidden, while the nose, both shoulders and both hips are visible in every frame with a pose (URFD `fall-10`, `-18`, `-24`, `-26`, `-30`, CAUCAFall subject 10 `Fall_right`, subject 3 `Fall_forward`).

**Literature** (peer-reviewed, DOIs checked): falls are followed by lying low and still, while daily activities that bend or lower the body end with the person up again, and vision systems confirm a fall with a post-event period of 1–5 s of inactivity or of staying low (Rougier et al., 2011; Auvinet et al., 2011; Noury et al., 2007). Head and trunk points stay visible when the legs are hidden, and trunk or head velocity separates falls from daily activities (Wu, 2000; Bourke et al., 2008; Rougier et al., 2013). In real homes about half of the false alarms of a video detector came from a second person, a similar object or a split body, i.e. from following the wrong subject (Debard et al., 2016). Rest-zone masks for beds and sofas reduce false alarms (Lee & Mihailidis, 2005), but they need per-camera annotation that no dataset here has; keypoint smoothing (One-Euro; Casiez et al., 2012) has no fall-detection evidence and ADR 0010 already argued against it.

## Candidates (proposals)

### S1. Hold and cancel (`retencion_caida_s` = D, `retencion_erguido_s` = U, `retencion_exige_visibles`)
When R4 or R9 would emit `caida`, the classifier enters `EN_EL_SUELO` but **holds the event for D s**. If during the hold the person is seen upright for U continuous seconds, the alarm is cancelled: `movimiento_inestable` (with `caida_retirada = 1`) is emitted and the classifier returns to `NORMAL`. Otherwise `caida` is emitted D s after the trigger (on the next frame, with or without a pose), with the original measurements and `retenida_s`. R5 and R6 wait until the hold ends (R6 still counts from the trigger).

**Rationale.** It extends R7 (a stumble that ends upright) past the moment the body becomes horizontal: kneeling, bending to pick something up and crouching pass through a tilted, wide posture and end upright; a fall ends on the floor (Noury et al., 2007; Rougier et al., 2011). The upright test is either R5's (with A6, `retencion_exige_visibles = true`) or its geometry only (as F3). A8 found isolated upright frames in lying people, hence U ≥ 0.5 s.

**Cost.** Every alarm is delayed by D s. CA-11.3 and CA-16.1 give 10 s from the person on the floor to the notification; the classifier's median latency is 0.8 s, so D ≤ 5 s.

**Grid.** D ∈ {2, 3, 5} s × U ∈ {0.5, 1.0} s × test ∈ {strict, geometric}, with v: 1,200 configurations. Ties: the shortest D, the longest U and the strict test (the closest to the shipped behaviour).

**Evaluation of short clips.** Many development clips end less than D s after the `caida` (URFD falls end 0.1–2.2 s after it). A hold still running when a clip ends is counted as a `caida` (the alarm was not cancelled), and the number of such censored decisions is reported. The same rule applies to falls and to daily activities.

**Predictions.** Removes most kneeling and picking-up false alarms and the URFD activities in which the person gets up within D s; none of the people lying down on purpose who stay down. May lose a fall followed by a quick sit-up or by a guessed upright pose for U s (more likely with the geometric test).

### S2. F3 on the development data (ADR 0011)
F3 as written in ADR 0011, `erguido_previo_caida_s` = T ∈ {1, 2, 3, 5, 10}, `erguido_previo_exige_visibles = false` (500 configurations). It is the "descent profile" rule of the literature in its simplest form: R4 must follow a recent upright posture. It is included as a comparator and for combinations. **Prediction:** no specificity gain on the development data (diagnosis above).

### S3. Ankle-free path (`ruta_sin_tobillos`)
On frames that fail A6 only because the ankles are hidden — nose, both shoulders and both hips visible — M1 and M2 are measured from the upper body: the hip-centre descent speed is computed over those frames with the scale L̂ = 2.2 × the nose–hip-centre distance (median of the last 2 s), and M2 is the **torso angle** (shoulder midpoint → hip midpoint) below θ₀ = 45°. M3, R5 and R7 do not change (upright still needs A6).

**Rationale.** A6 drops these frames because a guessed ankle makes the center line and its angle unreliable (ADR 0010: C1 and C1b used that angle and added false alarms). The torso line avoids the guessed ankles, and the trunk is the segment that carries the fall signal (Wu, 2000; Bourke et al., 2008). 2.2 is the ratio of the nose-to-ankle height (≈ 0.90 H) to the nose-to-hip height (≈ 0.41 H) of the anthropometric segment table (Drillis and Contini, in Winter, 2009); it is fixed, not fitted.

**Grid.** None of its own (100 configurations with v). **Predictions:** recovers several of the 7 ankle-hidden misses; adds some false alarms (kneeling and picking up hide the feet too), which S1 should remove when combined.

### S4. Identity-jump gate (`salto_identidad_max` = J)
If the hip centre moves more than J center-line lengths between two consecutive frames with a pose less than 0.5 s apart, the classifier treats it as a different person: it clears the speed history, R9's upright memory, F3's last upright instant and the R5 upright run.

**Rationale.** The pose model follows one person; when it jumps to a bystander or to a reflection the hip "falls" or "rises" by an impossible amount in one frame (Debard et al., 2016: second person 16 % and split body 15 % of real-home false alarms). J = 1.0 length per frame (8 lengths per second at 8 fps) is far above the fastest physical hip motion of a fall (about 1–2 lengths per second; Bourke et al., 2008), so it is fixed a priori and not tuned. **Prediction:** no change on the single-person development data; its target is the hold-out bystanders (UP-Fall frontal camera, MCFD), where it can only be checked once.

### Combinations
After the development round, the finalists are combined with each other and with F3 (S2). Each combination reuses the grids of its parts; the number of configurations is reported.

### Considered and not tested
A hip-drop or torso-angle gate at the trigger (overlapping distributions in the diagnosis), rest-zone masks for beds and sofas (no annotated zones in any dataset; a per-camera installer feature, not a rule), One-Euro or Kalman smoothing (no fall-detection evidence; ADR 0010), k-of-n voting on M3 (validation.md section 4: requiring M3 to hold 0.25–1 s lost 11–20 % sensitivity), relaxing A6 (ADR 0010), and recalibrating θ₀ and T (ADR 0010, C4).

## Protocol (fixed before running)
1. **Development data only for the choice:** URFD and CAUCAFall, poses `lite-video-8fps-jpeg` (480p, 8 fps, JPEG 80, MediaPipe lite, VIDEO mode). Per-video criterion as in validation.md section 2.
2. **Nested selection:** every threshold (v and the candidate's own) is chosen inside each training fold by the maximum Youden index, with the ties above, and applied to the held-out group (leave one group out, 11 groups). Cross-dataset URFD → CAUCAFall and CAUCAFall → URFD. A fully nested selection in which each fold also picks the candidate estimates the whole procedure.
3. **Reported:** sensitivity and specificity with 95 % Wilson intervals; FN and FP; exact McNemar on paired per-video outcomes against the baseline (all videos and falls only); false recoveries in the 30 URFD falls; URFD latency from the first "falling" frame; per-activity false alarms; the number of configurations.
4. **Acceptance rule (per candidate):**
   1. LOGO specificity rises (S1, S4) or sensitivity rises (S3), and the loss of the other metric, if any, is smaller than that gain;
   2. the gain does not come from one dataset while the target metric of the other falls by more than 2 points;
   3. no more false recoveries than the baseline (0/30);
   4. McNemar on all videos is not a significant loss (p < 0.05 with more videos wrong);
   5. S1: median URFD latency stays below 6 s.
   S4 has no target on the development data; it is a finalist if it changes nothing there (rule 1 is replaced by "no metric falls").
5. **Hold-out, once, finalists only:** the configuration of each finalist is chosen on all 170 development videos with the same criterion and frozen; it is run once on GMDCSA24, UP-Fall and MCFD with the units of ADR 0011 (MCFD per event: fall windows and labelled non-fall periods, false alarms per hour). Nothing is tuned on them.
6. **Secondary:** leave one dataset out over the five datasets as in ADR 0011 (both criteria), for the finalists and their combinations with F3. This uses the hold-out sets as training folds, so it is reported after, and separately from, the frozen hold-out test.
7. **Adoption:** the shipped default changes only if a finalist passes the acceptance rule on the development data **and** does not lose specificity or sensitivity by more than 2 points on any hold-out dataset; otherwise it stays opt-in.

## Threats
The diagnosis that motivated S1 and S3 used the same 170 development videos; nesting protects the thresholds, not the choice of rules. The clips are short, so S1's hold is censored in many of them. Units are not independent (cameras of one scenario). Simulated falls by young adults.

## Results
*(added after the runs)*

## Decision
*(added after the runs)*

## References
Auvinet, E., Multon, F., Saint-Arnaud, A., Rousseau, J., & Meunier, J. (2011). Fall detection with multiple cameras: An occlusion-resistant method based on 3-D silhouette vertical distribution. *IEEE Transactions on Information Technology in Biomedicine, 15*(2), 290–300. https://doi.org/10.1109/TITB.2010.2087385

Bourke, A. K., O'Donovan, K. J., & ÓLaighin, G. (2008). The identification of vertical velocity profiles using an inertial sensor to investigate pre-impact detection of falls. *Medical Engineering & Physics, 30*(7), 937–946. https://doi.org/10.1016/j.medengphy.2007.12.003

Casiez, G., Roussel, N., & Vogel, D. (2012). 1 € filter: A simple speed-based low-pass filter for noisy input in interactive systems. *Proceedings of CHI '12*, 2527–2530. https://doi.org/10.1145/2207676.2208639

Debard, G., Mertens, M., Deschodt, M., Vlaeyen, E., Devriendt, E., Dejaeger, E., Milisen, K., Tournoy, J., Croonenborghs, T., Goedemé, T., Tuytelaars, T., & Vanrumste, B. (2016). Camera-based fall detection using real-world versus simulated data: How far are we from the solution? *Journal of Ambient Intelligence and Smart Environments, 8*(2), 149–168. https://doi.org/10.3233/AIS-160369

Lee, T., & Mihailidis, A. (2005). An intelligent emergency response system: Preliminary development and testing of automated fall detection. *Journal of Telemedicine and Telecare, 11*(4), 194–198. https://doi.org/10.1258/1357633054068946

Noury, N., Fleury, A., Rumeau, P., Bourke, A. K., Laighin, G. Ó., Rialle, V., & Lundy, J. E. (2007). Fall detection — Principles and methods. *29th Annual International Conference of the IEEE EMBS*, 1663–1666. https://doi.org/10.1109/IEMBS.2007.4352627

Rougier, C., Meunier, J., St-Arnaud, A., & Rousseau, J. (2011). Robust video surveillance for fall detection based on human shape deformation. *IEEE Transactions on Circuits and Systems for Video Technology, 21*(5), 611–622. https://doi.org/10.1109/TCSVT.2011.2129370

Rougier, C., Meunier, J., St-Arnaud, A., & Rousseau, J. (2013). 3D head tracking for fall detection using a single calibrated camera. *Image and Vision Computing, 31*(3), 246–254. https://doi.org/10.1016/j.imavis.2012.11.003

Winter, D. A. (2009). *Biomechanics and motor control of human movement* (4th ed.). Wiley. https://doi.org/10.1002/9780470549148

Wu, G. (2000). Distinguishing fall activities from normal activities by velocity characteristics. *Journal of Biomechanics, 33*(11), 1497–1500. https://doi.org/10.1016/S0021-9290(00)00117-2
