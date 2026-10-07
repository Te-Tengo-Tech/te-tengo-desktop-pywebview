# 0004. Classification with the thresholds of Chen et al. (2020)

**Status:** accepted (2026-10-03)

## Context
The project forbids training models. The IB3 benchmarking selected the geometric threshold method of Chen et al. (2020), with a score of 4.33.

## Decision
Implement its three conditions (descent speed of the hip center, center line angle < 45° and width/height ratio ≥ 1) and its rule to detect that the person gets up, adapted to MediaPipe. The details are in [classification-spec.md](../classification-spec.md).

## Consequences
- The speed threshold must be calibrated (the article has contradictory values).
- The side view and occlusion are known limitations that must be evaluated during validation.
- The unstable movement rule is our own proposal and is pending validation.

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744
