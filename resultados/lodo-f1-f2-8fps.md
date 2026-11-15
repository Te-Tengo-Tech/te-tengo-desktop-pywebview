# Leave-one-dataset-out evaluation of F1 and F2 (ADR 0011)

760 recordings, 1672 units (513 positive, 1159 negative); 4100 configurations baseline: 100, F1: 500, F2: 500, F1+F2: 2500, F3: 500. Units: one recording per camera; MCFD: fall windows (positive) and labelled non-fall periods (negative). Intervals: 95 % Wilson. McNemar: exact, two-sided, on correctness of paired units (b = only the baseline right, c = only the fix right).

## 0. Frozen shipped classifier (v = 0.01, F1 and F2 off), per dataset

| Dataset | Sensitivity | Specificity | Units (pos / neg) |
|---|---|---|---|
| urfd | 76.7 % (59.1–88.2) | 72.5 % (57.2–83.9) | 30 / 40 |
| caucafall | 86.0 % (73.8–93.0) | 84.0 % (71.5–91.7) | 50 / 50 |
| gmdcsa24 | 91.1 % (82.8–95.6) | 65.4 % (54.6–74.9) | 79 / 81 |
| upfall | 68.2 % (60.9–74.8) | 63.2 % (51.4–73.7) | 170 / 68 |
| mcfd | 47.8 % (40.7–55.0) | 87.2 % (84.9–89.2) | 184 / 920 |
| **pooled** | 66.7 % (62.5–70.6) | 83.6 % (81.4–85.6) | 513 / 1159 |
| macro mean | 74.0 % | 74.5 % | |

## Criterion: maximum Youden index

### Configuration chosen in each training fold

| Held-out | baseline | F1 | F2 | F1+F2 | F3 |
|---|---|---|---|---|---|
| urfd | v=0.12 | v=0.13, T=10 | v=0.12, X=20 | v=0.13, T=10, X=20 | v=0.01, T=10 |
| caucafall | v=0.36 | v=0.74, T=3 | v=0.36, X=20 | v=0.74, T=3, X=20 | v=0.01, T=10 |
| gmdcsa24 | v=0.12 | v=0.23, T=10 | v=0.12, X=20 | v=0.23, T=10, X=20 | v=0.01, T=10 |
| upfall | v=0.12 | v=0.22, T=10 | v=0.01, X=2 | v=0.22, T=10, X=20 | v=0.01, T=10 |
| mcfd | v=0.12 | v=0.22, T=10 | v=0.12, X=20 | v=0.22, T=10, X=20 | v=0.01, T=10 |
| *all five (deployable)* | v=0.12 | v=0.22, T=10 | v=0.12, X=20 | v=0.22, T=10, X=20 | v=0.01, T=10 |

### LODO result on each held-out dataset

| Held-out | Rule set | Sensitivity | Specificity | McNemar vs baseline: all · positives · negatives |
|---|---|---|---|---|
| urfd | baseline | 76.7 % (59.1–88.2) | 75.0 % (59.8–85.8) | — |
| urfd | F1 | 66.7 % (48.8–80.8) | 75.0 % (59.8–85.8) | 3/0 p=0.250 · 3/0 p=0.250 · 0/0 p=1.000 |
| urfd | F2 | 76.7 % (59.1–88.2) | 75.0 % (59.8–85.8) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| urfd | F1+F2 | 66.7 % (48.8–80.8) | 75.0 % (59.8–85.8) | 3/0 p=0.250 · 3/0 p=0.250 · 0/0 p=1.000 |
| urfd | F3 | 76.7 % (59.1–88.2) | 72.5 % (57.2–83.9) | 1/0 p=1.000 · 0/0 p=1.000 · 1/0 p=1.000 |
| caucafall | baseline | 48.0 % (34.8–61.5) | 90.0 % (78.6–95.7) | — |
| caucafall | F1 | 44.0 % (31.2–57.7) | 94.0 % (83.8–97.9) | 2/2 p=1.000 · 2/0 p=0.500 · 0/2 p=0.500 |
| caucafall | F2 | 48.0 % (34.8–61.5) | 90.0 % (78.6–95.7) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| caucafall | F1+F2 | 44.0 % (31.2–57.7) | 94.0 % (83.8–97.9) | 2/2 p=1.000 · 2/0 p=0.500 · 0/2 p=0.500 |
| caucafall | F3 | 82.0 % (69.2–90.2) | 86.0 % (73.8–93.0) | 3/18 p=0.001 · 0/17 p=0.000 · 3/1 p=0.625 |
| gmdcsa24 | baseline | 84.8 % (75.3–91.1) | 77.8 % (67.6–85.5) | — |
| gmdcsa24 | F1 | 75.9 % (65.5–84.0) | 85.2 % (75.9–91.3) | 7/6 p=1.000 · 7/0 p=0.016 · 0/6 p=0.031 |
| gmdcsa24 | F2 | 84.8 % (75.3–91.1) | 77.8 % (67.6–85.5) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| gmdcsa24 | F1+F2 | 75.9 % (65.5–84.0) | 85.2 % (75.9–91.3) | 7/6 p=1.000 · 7/0 p=0.016 · 0/6 p=0.031 |
| gmdcsa24 | F3 | 88.6 % (79.7–93.9) | 72.8 % (62.3–81.3) | 9/8 p=1.000 · 2/5 p=0.453 · 7/3 p=0.344 |
| upfall | baseline | 55.3 % (47.8–62.6) | 91.2 % (82.1–95.9) | — |
| upfall | F1 | 54.1 % (46.6–61.4) | 97.1 % (89.9–99.2) | 2/4 p=0.688 · 2/0 p=0.500 · 0/4 p=0.125 |
| upfall | F2 | 68.2 % (60.9–74.8) | 63.2 % (51.4–73.7) | 19/22 p=0.755 · 0/22 p=0.000 · 19/0 p=0.000 |
| upfall | F1+F2 | 54.1 % (46.6–61.4) | 97.1 % (89.9–99.2) | 2/4 p=0.688 · 2/0 p=0.500 · 0/4 p=0.125 |
| upfall | F3 | 68.2 % (60.9–74.8) | 95.6 % (87.8–98.5) | 1/26 p=0.000 · 0/22 p=0.000 · 1/4 p=0.375 |
| mcfd | baseline | 46.7 % (39.7–53.9) | 88.4 % (86.1–90.3) | — |
| mcfd | F1 | 44.0 % (37.0–51.2) | 89.3 % (87.2–91.2) | 9/13 p=0.523 · 6/1 p=0.125 · 3/12 p=0.035 |
| mcfd | F2 | 46.7 % (39.7–53.9) | 88.4 % (86.1–90.3) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| mcfd | F1+F2 | 44.0 % (37.0–51.2) | 89.3 % (87.2–91.2) | 9/13 p=0.523 · 6/1 p=0.125 · 3/12 p=0.035 |
| mcfd | F3 | 47.3 % (40.2–54.5) | 87.4 % (85.1–89.4) | 15/7 p=0.134 · 3/4 p=1.000 · 12/3 p=0.035 |
| **pooled** | baseline | 57.3 % (53.0–61.5) | 87.4 % (85.4–89.2) | — |
| **pooled** | F1 | 53.6 % (49.3–57.9) | 89.2 % (87.3–90.9) | 23/25 p=0.885 · 20/1 p=0.000 · 3/24 p=0.000 |
| **pooled** | F2 | 61.6 % (57.3–65.7) | 85.8 % (83.6–87.7) | 19/22 p=0.755 · 0/22 p=0.000 · 19/0 p=0.000 |
| **pooled** | F1+F2 | 53.6 % (49.3–57.9) | 89.2 % (87.3–90.9) | 23/25 p=0.885 · 20/1 p=0.000 · 3/24 p=0.000 |
| **pooled** | F3 | 65.7 % (61.5–69.7) | 86.3 % (84.2–88.1) | 29/59 p=0.002 · 5/48 p=0.000 · 24/11 p=0.041 |
| macro mean | baseline | 62.3 % | 84.5 % | |
| macro mean | F1 | 57.0 % | 88.1 % | |
| macro mean | F2 | 64.9 % | 78.9 % | |
| macro mean | F1+F2 | 57.0 % | 88.1 % | |
| macro mean | F3 | 72.6 % | 82.9 % | |

### False alarms per activity (negative units with a `caida`, LODO)

| Dataset · activity | Units | shipped | baseline | F1 | F2 | F1+F2 | F3 |
|---|---|---|---|---|---|---|---|
| urfd · lying down on the floor on purpose | 16 | 8 | 7 | 7 | 7 | 7 | 8 |
| urfd · other ADL | 24 | 3 | 3 | 3 | 3 | 3 | 3 |
| caucafall · Hop | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| caucafall · Kneel | 10 | 3 | 3 | 2 | 3 | 2 | 3 |
| caucafall · Pick up object | 10 | 3 | 1 | 1 | 1 | 1 | 3 |
| caucafall · Sit down | 10 | 1 | 0 | 0 | 0 | 0 | 1 |
| caucafall · Walk | 10 | 1 | 1 | 0 | 1 | 0 | 0 |
| gmdcsa24 · exercise (push-ups, bending, arms) | 11 | 5 | 5 | 2 | 5 | 2 | 5 |
| gmdcsa24 · lying down on / getting up from the bed | 12 | 12 | 5 | 4 | 5 | 4 | 9 |
| gmdcsa24 · lying down on / getting up from the floor | 2 | 1 | 0 | 0 | 0 | 0 | 0 |
| gmdcsa24 · picking up an object (mostly from the floor) | 12 | 3 | 2 | 1 | 2 | 1 | 2 |
| gmdcsa24 · sitting on / getting up from the floor | 11 | 4 | 3 | 3 | 3 | 3 | 4 |
| gmdcsa24 · sitting on a bed or chair | 25 | 3 | 3 | 2 | 3 | 2 | 2 |
| gmdcsa24 · walking or standing | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| upfall · laying | 34 | 22 | 4 | 0 | 22 | 0 | 0 |
| upfall · picking up an object | 34 | 3 | 2 | 2 | 3 | 2 | 3 |
| mcfd · crouching | 88 | 13 | 10 | 8 | 10 | 8 | 13 |
| mcfd · lying on a sofa | 32 | 3 | 2 | 4 | 2 | 4 | 2 |
| mcfd · moving down | 208 | 39 | 37 | 34 | 37 | 34 | 39 |
| mcfd · moving up | 232 | 8 | 7 | 5 | 7 | 5 | 7 |
| mcfd · sitting | 72 | 15 | 16 | 16 | 16 | 16 | 15 |
| mcfd · walking, standing up | 288 | 40 | 35 | 31 | 35 | 31 | 40 |

### Falls detected per activity (positive units, LODO)

| Dataset · activity | Units | shipped | baseline | F1 | F2 | F1+F2 | F3 |
|---|---|---|---|---|---|---|---|
| urfd · fall | 30 | 23 | 23 | 20 | 23 | 20 | 23 |
| caucafall · Fall backwards | 10 | 10 | 6 | 5 | 6 | 5 | 10 |
| caucafall · Fall forward | 10 | 8 | 4 | 4 | 4 | 4 | 7 |
| caucafall · Fall left | 10 | 9 | 6 | 6 | 6 | 6 | 8 |
| caucafall · Fall right | 10 | 8 | 3 | 2 | 3 | 2 | 8 |
| caucafall · Fall sitting | 10 | 8 | 5 | 5 | 5 | 5 | 8 |
| gmdcsa24 · fall backward | 28 | 24 | 21 | 19 | 21 | 19 | 24 |
| gmdcsa24 · fall forward | 23 | 21 | 21 | 19 | 21 | 19 | 20 |
| gmdcsa24 · fall sideways | 28 | 27 | 25 | 22 | 25 | 22 | 26 |
| upfall · falling backwards | 34 | 26 | 14 | 14 | 26 | 14 | 26 |
| upfall · falling forward using hands | 34 | 29 | 28 | 27 | 29 | 27 | 29 |
| upfall · falling forward using knees | 34 | 18 | 16 | 16 | 18 | 16 | 18 |
| upfall · falling sideward | 34 | 19 | 18 | 17 | 19 | 17 | 19 |
| upfall · falling sitting in empty chair | 34 | 24 | 18 | 18 | 24 | 18 | 24 |
| mcfd · fall | 184 | 88 | 86 | 81 | 86 | 81 | 87 |

### Safety: false recoveries, F2 exits while on the floor, confirmations, MCFD

Clip datasets: fall recordings with a `recuperacion` ("rec") or an F2 silent exit ("exit") after the first `caida` (GMDCSA24: after the labelled onset, clips where nobody gets up); "conf" = detected falls with a `caida_confirmada`. MCFD: within the detected fall window (person labelled on the ground); latency from the labelled onset; false alarms per hour of labelled non-fall time (8 cameras).

| Rule set | URFD rec / exit | CAUCAFall rec / exit | GMDCSA24 rec / exit | UP-Fall rec / exit | MCFD rec / exit / conf | MCFD FA (per hour) | MCFD latency median (p95) |
|---|---|---|---|---|---|---|---|
| shipped | 0 / 0 of 23 | 1 / 0 of 43 | 0 / 0 of 72 | 12 / 0 of 116 | 0 / 0 / 0 of 88 | 123 (114/h) | 1.08 s (3.40) |
| baseline | 0 / 0 of 23 | 1 / 0 of 24 | 0 / 0 of 67 | 12 / 0 of 94 | 0 / 0 / 0 of 86 | 111 (103/h) | 1.08 s (4.43) |
| F1 | 0 / 0 of 20 | 0 / 0 of 22 | 0 / 0 of 60 | 12 / 0 of 92 | 0 / 0 / 0 of 81 | 102 (95/h) | 1.00 s (4.43) |
| F2 | 0 / 0 of 23 | 1 / 0 of 24 | 0 / 0 of 67 | 11 / 3 of 116 | 0 / 0 / 0 of 86 | 111 (103/h) | 1.08 s (4.43) |
| F1+F2 | 0 / 0 of 20 | 0 / 0 of 22 | 0 / 0 of 60 | 12 / 0 of 92 | 0 / 0 / 0 of 81 | 102 (95/h) | 1.00 s (4.43) |
| F3 | 0 / 0 of 23 | 0 / 0 of 41 | 0 / 0 of 70 | 12 / 0 of 116 | 0 / 0 / 0 of 87 | 121 (112/h) | 1.07 s (3.40) |

## Criterion: maximum specificity with sensitivity ≥ 90 %

### Configuration chosen in each training fold

| Held-out | baseline | F1 | F2 | F1+F2 | F3 |
|---|---|---|---|---|---|
| urfd | v=0.01 | v=0.01, T=10 | v=0.01, X=2 | v=0.01, T=10, X=2 | v=0.01, T=10 |
| caucafall | v=0.01 | v=0.01, T=10 | v=0.01, X=2 | v=0.01, T=10, X=2 | v=0.01, T=10 |
| gmdcsa24 | v=0.01 | v=0.05, T=10 | v=0.01, X=2 | v=0.05, T=10, X=2 | v=0.01, T=10 |
| upfall | v=0.01 | v=0.01, T=10 | v=0.01, X=2 | v=0.01, T=10, X=2 | v=0.01, T=10 |
| mcfd | v=0.01 | v=0.01, T=10 | v=0.01, X=20 | v=0.01, T=10, X=20 | v=0.01, T=10 |
| *all five (deployable)* | v=0.01 | v=0.01, T=10 | v=0.01, X=2 | v=0.01, T=10, X=2 | v=0.01, T=10 |

### LODO result on each held-out dataset

| Held-out | Rule set | Sensitivity | Specificity | McNemar vs baseline: all · positives · negatives |
|---|---|---|---|---|
| urfd | baseline | 76.7 % (59.1–88.2) | 72.5 % (57.2–83.9) | — |
| urfd | F1 | 66.7 % (48.8–80.8) | 72.5 % (57.2–83.9) | 3/0 p=0.250 · 3/0 p=0.250 · 0/0 p=1.000 |
| urfd | F2 | 76.7 % (59.1–88.2) | 72.5 % (57.2–83.9) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| urfd | F1+F2 | 66.7 % (48.8–80.8) | 72.5 % (57.2–83.9) | 3/0 p=0.250 · 3/0 p=0.250 · 0/0 p=1.000 |
| urfd | F3 | 76.7 % (59.1–88.2) | 72.5 % (57.2–83.9) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| caucafall | baseline | 86.0 % (73.8–93.0) | 84.0 % (71.5–91.7) | — |
| caucafall | F1 | 68.0 % (54.2–79.2) | 86.0 % (73.8–93.0) | 9/1 p=0.021 · 9/0 p=0.004 · 0/1 p=1.000 |
| caucafall | F2 | 86.0 % (73.8–93.0) | 84.0 % (71.5–91.7) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| caucafall | F1+F2 | 68.0 % (54.2–79.2) | 86.0 % (73.8–93.0) | 9/1 p=0.021 · 9/0 p=0.004 · 0/1 p=1.000 |
| caucafall | F3 | 82.0 % (69.2–90.2) | 86.0 % (73.8–93.0) | 2/1 p=1.000 · 2/0 p=0.500 · 0/1 p=1.000 |
| gmdcsa24 | baseline | 91.1 % (82.8–95.6) | 65.4 % (54.6–74.9) | — |
| gmdcsa24 | F1 | 81.0 % (71.0–88.1) | 77.8 % (67.6–85.5) | 8/10 p=0.815 · 8/0 p=0.008 · 0/10 p=0.002 |
| gmdcsa24 | F2 | 91.1 % (82.8–95.6) | 65.4 % (54.6–74.9) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| gmdcsa24 | F1+F2 | 81.0 % (71.0–88.1) | 77.8 % (67.6–85.5) | 8/10 p=0.815 · 8/0 p=0.008 · 0/10 p=0.002 |
| gmdcsa24 | F3 | 88.6 % (79.7–93.9) | 72.8 % (62.3–81.3) | 2/6 p=0.289 · 2/0 p=0.500 · 0/6 p=0.031 |
| upfall | baseline | 68.2 % (60.9–74.8) | 63.2 % (51.4–73.7) | — |
| upfall | F1 | 54.1 % (46.6–61.4) | 95.6 % (87.8–98.5) | 24/22 p=0.883 · 24/0 p=0.000 · 0/22 p=0.000 |
| upfall | F2 | 68.2 % (60.9–74.8) | 63.2 % (51.4–73.7) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| upfall | F1+F2 | 54.1 % (46.6–61.4) | 95.6 % (87.8–98.5) | 24/22 p=0.883 · 24/0 p=0.000 · 0/22 p=0.000 |
| upfall | F3 | 68.2 % (60.9–74.8) | 95.6 % (87.8–98.5) | 0/22 p=0.000 · 0/0 p=1.000 · 0/22 p=0.000 |
| mcfd | baseline | 47.8 % (40.7–55.0) | 87.2 % (84.9–89.2) | — |
| mcfd | F1 | 45.7 % (38.6–52.9) | 87.4 % (85.1–89.4) | 4/2 p=0.688 · 4/0 p=0.125 · 0/2 p=0.500 |
| mcfd | F2 | 47.8 % (40.7–55.0) | 87.2 % (84.9–89.2) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| mcfd | F1+F2 | 45.7 % (38.6–52.9) | 87.4 % (85.1–89.4) | 4/2 p=0.688 · 4/0 p=0.125 · 0/2 p=0.500 |
| mcfd | F3 | 47.3 % (40.2–54.5) | 87.4 % (85.1–89.4) | 2/3 p=1.000 · 2/1 p=1.000 · 0/2 p=0.500 |
| **pooled** | baseline | 66.7 % (62.5–70.6) | 83.6 % (81.4–85.6) | — |
| **pooled** | F1 | 57.3 % (53.0–61.5) | 86.6 % (84.5–88.5) | 48/35 p=0.187 · 48/0 p=0.000 · 0/35 p=0.000 |
| **pooled** | F2 | 66.7 % (62.5–70.6) | 83.6 % (81.4–85.6) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| **pooled** | F1+F2 | 57.3 % (53.0–61.5) | 86.6 % (84.5–88.5) | 48/35 p=0.187 · 48/0 p=0.000 · 0/35 p=0.000 |
| **pooled** | F3 | 65.7 % (61.5–69.7) | 86.3 % (84.2–88.1) | 6/32 p=0.000 · 6/1 p=0.125 · 0/31 p=0.000 |
| macro mean | baseline | 74.0 % | 74.5 % | |
| macro mean | F1 | 63.1 % | 83.9 % | |
| macro mean | F2 | 74.0 % | 74.5 % | |
| macro mean | F1+F2 | 63.1 % | 83.9 % | |
| macro mean | F3 | 72.6 % | 82.9 % | |

### False alarms per activity (negative units with a `caida`, LODO)

| Dataset · activity | Units | shipped | baseline | F1 | F2 | F1+F2 | F3 |
|---|---|---|---|---|---|---|---|
| urfd · lying down on the floor on purpose | 16 | 8 | 8 | 8 | 8 | 8 | 8 |
| urfd · other ADL | 24 | 3 | 3 | 3 | 3 | 3 | 3 |
| caucafall · Hop | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| caucafall · Kneel | 10 | 3 | 3 | 3 | 3 | 3 | 3 |
| caucafall · Pick up object | 10 | 3 | 3 | 3 | 3 | 3 | 3 |
| caucafall · Sit down | 10 | 1 | 1 | 1 | 1 | 1 | 1 |
| caucafall · Walk | 10 | 1 | 1 | 0 | 1 | 0 | 0 |
| gmdcsa24 · exercise (push-ups, bending, arms) | 11 | 5 | 5 | 4 | 5 | 4 | 5 |
| gmdcsa24 · lying down on / getting up from the bed | 12 | 12 | 12 | 7 | 12 | 7 | 9 |
| gmdcsa24 · lying down on / getting up from the floor | 2 | 1 | 1 | 0 | 1 | 0 | 0 |
| gmdcsa24 · picking up an object (mostly from the floor) | 12 | 3 | 3 | 2 | 3 | 2 | 2 |
| gmdcsa24 · sitting on / getting up from the floor | 11 | 4 | 4 | 3 | 4 | 3 | 4 |
| gmdcsa24 · sitting on a bed or chair | 25 | 3 | 3 | 2 | 3 | 2 | 2 |
| gmdcsa24 · walking or standing | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| upfall · laying | 34 | 22 | 22 | 0 | 22 | 0 | 0 |
| upfall · picking up an object | 34 | 3 | 3 | 3 | 3 | 3 | 3 |
| mcfd · crouching | 88 | 13 | 13 | 13 | 13 | 13 | 13 |
| mcfd · lying on a sofa | 32 | 3 | 3 | 2 | 3 | 2 | 2 |
| mcfd · moving down | 208 | 39 | 39 | 39 | 39 | 39 | 39 |
| mcfd · moving up | 232 | 8 | 8 | 7 | 8 | 7 | 7 |
| mcfd · sitting | 72 | 15 | 15 | 15 | 15 | 15 | 15 |
| mcfd · walking, standing up | 288 | 40 | 40 | 40 | 40 | 40 | 40 |

### Falls detected per activity (positive units, LODO)

| Dataset · activity | Units | shipped | baseline | F1 | F2 | F1+F2 | F3 |
|---|---|---|---|---|---|---|---|
| urfd · fall | 30 | 23 | 23 | 20 | 23 | 20 | 23 |
| caucafall · Fall backwards | 10 | 10 | 10 | 8 | 10 | 8 | 10 |
| caucafall · Fall forward | 10 | 8 | 8 | 5 | 8 | 5 | 7 |
| caucafall · Fall left | 10 | 9 | 9 | 6 | 9 | 6 | 8 |
| caucafall · Fall right | 10 | 8 | 8 | 8 | 8 | 8 | 8 |
| caucafall · Fall sitting | 10 | 8 | 8 | 7 | 8 | 7 | 8 |
| gmdcsa24 · fall backward | 28 | 24 | 24 | 21 | 24 | 21 | 24 |
| gmdcsa24 · fall forward | 23 | 21 | 21 | 19 | 21 | 19 | 20 |
| gmdcsa24 · fall sideways | 28 | 27 | 27 | 24 | 27 | 24 | 26 |
| upfall · falling backwards | 34 | 26 | 26 | 14 | 26 | 14 | 26 |
| upfall · falling forward using hands | 34 | 29 | 29 | 27 | 29 | 27 | 29 |
| upfall · falling forward using knees | 34 | 18 | 18 | 16 | 18 | 16 | 18 |
| upfall · falling sideward | 34 | 19 | 19 | 17 | 19 | 17 | 19 |
| upfall · falling sitting in empty chair | 34 | 24 | 24 | 18 | 24 | 18 | 24 |
| mcfd · fall | 184 | 88 | 88 | 84 | 88 | 84 | 87 |

### Safety: false recoveries, F2 exits while on the floor, confirmations, MCFD

Clip datasets: fall recordings with a `recuperacion` ("rec") or an F2 silent exit ("exit") after the first `caida` (GMDCSA24: after the labelled onset, clips where nobody gets up); "conf" = detected falls with a `caida_confirmada`. MCFD: within the detected fall window (person labelled on the ground); latency from the labelled onset; false alarms per hour of labelled non-fall time (8 cameras).

| Rule set | URFD rec / exit | CAUCAFall rec / exit | GMDCSA24 rec / exit | UP-Fall rec / exit | MCFD rec / exit / conf | MCFD FA (per hour) | MCFD latency median (p95) |
|---|---|---|---|---|---|---|---|
| shipped | 0 / 0 of 23 | 1 / 0 of 43 | 0 / 0 of 72 | 12 / 0 of 116 | 0 / 0 / 0 of 88 | 123 (114/h) | 1.08 s (3.40) |
| baseline | 0 / 0 of 23 | 1 / 0 of 43 | 0 / 0 of 72 | 12 / 0 of 116 | 0 / 0 / 0 of 88 | 123 (114/h) | 1.08 s (3.40) |
| F1 | 0 / 0 of 20 | 0 / 0 of 34 | 0 / 0 of 64 | 12 / 0 of 92 | 0 / 0 / 0 of 84 | 121 (112/h) | 0.98 s (3.40) |
| F2 | 0 / 0 of 23 | 1 / 0 of 43 | 0 / 0 of 72 | 11 / 3 of 116 | 0 / 0 / 0 of 88 | 123 (114/h) | 1.08 s (3.40) |
| F1+F2 | 0 / 0 of 20 | 0 / 0 of 34 | 0 / 0 of 64 | 11 / 3 of 92 | 0 / 0 / 0 of 84 | 121 (112/h) | 0.98 s (3.40) |
| F3 | 0 / 0 of 23 | 0 / 0 of 41 | 0 / 0 of 70 | 12 / 0 of 116 | 0 / 0 / 0 of 87 | 121 (112/h) | 1.07 s (3.40) |

## Calibrated on all five datasets (optimistic fit, not a test)

| Criterion | Rule set | Configuration | Macro sensitivity | Macro specificity |
|---|---|---|---|---|
| maximum Youden index | baseline | v=0.12 | 67.9 % | 83.7 % |
| maximum Youden index | F1 | v=0.22, T=10 | 60.0 % | 88.2 % |
| maximum Youden index | F2 | v=0.12, X=20 | 67.9 % | 83.7 % |
| maximum Youden index | F1+F2 | v=0.22, T=10, X=20 | 60.0 % | 88.2 % |
| maximum Youden index | F3 | v=0.01, T=10 | 72.6 % | 82.9 % |
| maximum specificity with sensitivity ≥ 90 % | baseline | v=0.01 | 74.0 % | 74.5 % |
| maximum specificity with sensitivity ≥ 90 % | F1 | v=0.01, T=10 | 63.6 % | 83.1 % |
| maximum specificity with sensitivity ≥ 90 % | F2 | v=0.01, X=2 | 74.2 % | 74.4 % |
| maximum specificity with sensitivity ≥ 90 % | F1+F2 | v=0.01, T=10, X=2 | 63.7 % | 83.0 % |
| maximum specificity with sensitivity ≥ 90 % | F3 | v=0.01, T=10 | 72.6 % | 82.9 % |

## Diagnosis (frozen v = 0.01)

**F1 (T = 10 s) losses:** falls detected by the shipped classifier and not by F1, and whether the 10 s before the shipped `caida` had a frame upright by geometry only (θ > 45°, P < 1, head above the feet) or by the strict test (with A6).

| Dataset | Falls lost | With a geometric upright frame | With a strict upright frame |
|---|---|---|---|
| caucafall | 9 | 7 | 0 |
| gmdcsa24 | 6 | 4 | 0 |
| upfall | 24 | 24 | 0 |
| urfd | 3 | 3 | 0 |

**MCFD windows masked by an earlier `caida`** (state `EN_EL_SUELO` 1 s before the labelled onset): 58. Time in `EN_EL_SUELO` before the onset: median 5.3 s, ≤ 2 s in 11. Frames with a pose and no floor evidence (neither M2 nor M3): median 0.8 % of the pose frames; the longest run without floor evidence reaches 1 s in 5 windows and 2 s in 1.
