# 0009. Rule R9: declare slow falls that end on the floor

**Status:** proposed (2026-10-24). Adds a rule to the classifier of ADR 0004; the thresholds and adaptations A1–A8 do not change.

## Context
A fall is declared by R4: the hip goes down while the body is tilted (M1 and M2) and the body becomes horizontal (M3) within the 1.48 s reaction window. A family reported that fast falls are detected but **slow ones are not**: sliding down from a chair or a bed, sagging to the floor, kneeling and then lying down. In those falls the hip may stop going down before the body tilts (lying back from sitting on the floor), the torso may stay upright while the hip goes down (sliding down), or the body may become horizontal after the window. Real falls of older adults include such cases: in 227 falls filmed in long-term care, 12 % happened while sitting down and 11 % were collapses (Robinovitch et al., 2013).

The public datasets contain almost no slow falls: in 80 falls, 18 have a measured peak hip descent speed below 0.3 bodies/s, and R4 already detects 12 of them at 8 fps.

## Decision
Add **R9 (proposal)**: emit the same `caida` event, with `parametros.caida_lenta = 1` and the measured `descenso`, when

1. the person was seen upright during the last `ventana_caida_lenta_s` (10 s); the reference is the **highest hip** of those frames, so sitting or kneeling, which may still look upright, does not lower it;
2. the hip is at least `descenso_caida_lenta_min` (0.4) center-line lengths below that reference: about the floor, not a bed or a sofa; and
3. the body stays horizontal (M3) on every frame with a pose for `permanencia_caida_lenta_s` (2 s); frames without a pose do not interrupt the count.

After it the classifier goes to `EN_EL_SUELO` as usual (R5 recovery, R6 confirmation). The three values are part of the US-45 tunables. The defaults were fixed from the body geometry and the reported scenarios before replaying the datasets, not tuned on them.

## Consequences
- On URFD and CAUCAFall (8 fps, JPEG, leaving one group out) sensitivity goes from 81.2 % to 82.5 % and specificity from 81.1 % to 78.9 %. At 6, 8 and 10 fps R9 adds 4 falls in total, all slow ones (peak speed 0.08–0.21 bodies/s), and 11 false alarms, 9 of them people lying down on the floor on purpose ([validation.md](../validation.md), section 3.6). Calibrating the speed with URFD and testing on CAUCAFall goes from 28 % to 46 % sensitivity: R9 makes the classifier depend less on the speed threshold.
- Lying down on the floor on purpose cannot be told apart from a slow fall that ends lying; R9 makes that known limitation more frequent. Lying on a bed or a sofa is excluded by the hip drop, but **no dataset has it**: only synthetic tests cover it.
- With R9 the safe ranges of the angle and the ratio get narrower (angle 45–50°, ratio 1.0–1.4; [validation-rangos.md](../validation-rangos.md)).
- A slow fall that ends **sitting** on the floor is not declared, and neither is one that starts more than 10 s after the person was last seen upright.
- The pilot must record slow falls and lying down on a bed, a sofa and the floor to validate it.

## References
Robinovitch, S. N., Feldman, F., Yang, Y., Schonnop, R., Leung, P. M., Sarraf, T., Sims-Gould, J., & Loughin, M. (2013). Video capture of the circumstances of falls in elderly people residing in long-term care: An observational study. *The Lancet, 381*(9860), 47–54. https://doi.org/10.1016/S0140-6736(12)61263-X
