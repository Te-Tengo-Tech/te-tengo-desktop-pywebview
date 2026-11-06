# Specificity study (ADR 0012): hold-out, frozen, run once

Each rule set is chosen on the 170 development videos (maximum Youden) and frozen: **base**: v=0.01; **S2 (F3)**: v=0.01, T=10; **S1**: v=0.01, D=5, U=0.5, A6=no; **S4**: v=0.01; **S1+S4**: v=0.01, D=5, U=0.5, A6=no; **S1+F3**: v=0.01, D=5, U=0.5, A6=no, T=10. Units as in ADR 0011 (recordings; MCFD fall windows and labelled non-fall periods). McNemar against the frozen baseline on the same units.

| Dataset | Rule set | Sensitivity | Specificity | McNemar all · positives · negatives |
|---|---|---|---|---|
| gmdcsa24 | base | 91.1 % (82.8–95.6) | 65.4 % (54.6–74.9) | — |
| gmdcsa24 | S2 (F3) | 88.6 % (79.7–93.9) | 72.8 % (62.3–81.3) | 2/6 p=0.289 · 2/0 p=0.500 · 0/6 p=0.031 |
| gmdcsa24 | S1 | 91.1 % (82.8–95.6) | 82.7 % (73.1–89.4) | 0/14 p=0.000 · 0/0 p=1.000 · 0/14 p=0.000 |
| gmdcsa24 | S4 | 91.1 % (82.8–95.6) | 65.4 % (54.6–74.9) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| gmdcsa24 | S1+S4 | 91.1 % (82.8–95.6) | 82.7 % (73.1–89.4) | 0/14 p=0.000 · 0/0 p=1.000 · 0/14 p=0.000 |
| gmdcsa24 | S1+F3 | 88.6 % (79.7–93.9) | 82.7 % (73.1–89.4) | 2/14 p=0.004 · 2/0 p=0.500 · 0/14 p=0.000 |
| upfall | base | 68.2 % (60.9–74.8) | 63.2 % (51.4–73.7) | — |
| upfall | S2 (F3) | 68.2 % (60.9–74.8) | 95.6 % (87.8–98.5) | 0/22 p=0.000 · 0/0 p=1.000 · 0/22 p=0.000 |
| upfall | S1 | 60.0 % (52.5–67.1) | 67.6 % (55.8–77.6) | 14/3 p=0.013 · 14/0 p=0.000 · 0/3 p=0.250 |
| upfall | S4 | 68.2 % (60.9–74.8) | 63.2 % (51.4–73.7) | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 |
| upfall | S1+S4 | 60.0 % (52.5–67.1) | 67.6 % (55.8–77.6) | 14/3 p=0.013 · 14/0 p=0.000 · 0/3 p=0.250 |
| upfall | S1+F3 | 60.0 % (52.5–67.1) | 100.0 % (94.7–100.0) | 14/25 p=0.108 · 14/0 p=0.000 · 0/25 p=0.000 |
| mcfd | base | 47.8 % (40.7–55.0) | 87.2 % (84.9–89.2) | — |
| mcfd | S2 (F3) | 47.3 % (40.2–54.5) | 87.4 % (85.1–89.4) | 2/3 p=1.000 · 2/1 p=1.000 · 0/2 p=0.500 |
| mcfd | S1 | 26.6 % (20.8–33.4) | 94.1 % (92.4–95.5) | 96/121 p=0.103 · 55/16 p=0.000 · 41/105 p=0.000 |
| mcfd | S4 | 47.3 % (40.2–54.5) | 87.8 % (85.6–89.8) | 5/10 p=0.302 · 2/1 p=1.000 · 3/9 p=0.146 |
| mcfd | S1+S4 | 26.1 % (20.3–32.9) | 94.8 % (93.2–96.0) | 96/126 p=0.051 · 55/15 p=0.000 · 41/111 p=0.000 |
| mcfd | S1+F3 | 25.5 % (19.8–32.3) | 94.3 % (92.7–95.7) | 94/119 p=0.100 · 55/14 p=0.000 · 39/105 p=0.000 |
| pooled | base | 63.7 % (59.1–68.1) | 84.0 % (81.7–86.1) | — |
| pooled | S2 (F3) | 63.0 % (58.4–67.5) | 86.8 % (84.6–88.7) | 4/31 p=0.000 · 4/1 p=0.375 · 0/30 p=0.000 |
| pooled | S1 | 51.5 % (46.8–56.2) | 91.6 % (89.8–93.1) | 110/138 p=0.086 · 69/16 p=0.000 · 41/122 p=0.000 |
| pooled | S4 | 63.5 % (58.9–67.9) | 84.6 % (82.3–86.6) | 5/10 p=0.302 · 2/1 p=1.000 · 3/9 p=0.146 |
| pooled | S1+S4 | 51.3 % (46.6–55.9) | 92.1 % (90.4–93.6) | 110/143 p=0.044 · 69/15 p=0.000 · 41/128 p=0.000 |
| pooled | S1+F3 | 50.6 % (45.9–55.3) | 93.8 % (92.2–95.1) | 110/158 p=0.004 · 71/14 p=0.000 · 39/144 p=0.000 |
| macro mean | base | 69.1 % | 71.9 % | |
| macro mean | S2 (F3) | 68.0 % | 85.3 % | |
| macro mean | S1 | 59.3 % | 81.5 % | |
| macro mean | S4 | 68.9 % | 72.2 % | |
| macro mean | S1+S4 | 59.1 % | 81.7 % | |
| macro mean | S1+F3 | 58.1 % | 92.4 % | |

## False alarms per activity (negative units with a `caida`)

| Dataset · activity | Units | base | S2 (F3) | S1 | S4 | S1+S4 | S1+F3 |
|---|---|---|---|---|---|---|---|
| gmdcsa24 · FALLS (detected) | 79 | 72 | 70 | 72 | 72 | 72 | 70 |
| gmdcsa24 · exercise (push-ups, bending, arms) | 11 | 5 | 5 | 3 | 5 | 3 | 3 |
| gmdcsa24 · lying down on / getting up from the bed | 12 | 12 | 9 | 9 | 12 | 9 | 9 |
| gmdcsa24 · lying down on / getting up from the floor | 2 | 1 | 0 | 0 | 1 | 0 | 0 |
| gmdcsa24 · picking up an object (mostly from the floor) | 12 | 3 | 2 | 0 | 3 | 0 | 0 |
| gmdcsa24 · sitting on / getting up from the floor | 11 | 4 | 4 | 1 | 4 | 1 | 1 |
| gmdcsa24 · sitting on a bed or chair | 25 | 3 | 2 | 1 | 3 | 1 | 1 |
| gmdcsa24 · walking or standing | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| mcfd · FALLS (detected) | 184 | 88 | 87 | 49 | 87 | 48 | 47 |
| mcfd · crouching | 88 | 13 | 13 | 3 | 12 | 3 | 3 |
| mcfd · lying on a sofa | 32 | 3 | 2 | 17 | 5 | 17 | 17 |
| mcfd · moving down | 208 | 39 | 39 | 4 | 37 | 5 | 4 |
| mcfd · moving up | 232 | 8 | 7 | 15 | 7 | 15 | 14 |
| mcfd · sitting | 72 | 15 | 15 | 6 | 15 | 6 | 6 |
| mcfd · walking, standing up | 288 | 40 | 40 | 9 | 36 | 2 | 8 |
| upfall · FALLS (detected) | 170 | 116 | 116 | 102 | 116 | 102 | 102 |
| upfall · laying | 34 | 22 | 0 | 22 | 22 | 22 | 0 |
| upfall · picking up an object | 34 | 3 | 3 | 0 | 3 | 0 | 0 |

## Safety and MCFD stream

| Rule set | False recoveries GMDCSA24 · UP-Fall · MCFD | MCFD false alarms (per hour) | MCFD latency median |
|---|---|---|---|
| base | 0/72 · 12/116 · 0/88 | 123 (114/h) | 1.08 s |
| S2 (F3) | 0/70 · 12/116 · 0/87 | 121 (112/h) | 1.07 s |
| S1 | 0/72 · 0/102 · 1/49 | 54 (50/h) | 5.63 s |
| S4 | 0/72 · 12/116 · 0/87 | 117 (108/h) | 1.07 s |
| S1+S4 | 0/72 · 0/102 · 1/48 | 48 (44/h) | 5.65 s |
| S1+F3 | 0/70 · 0/102 · 1/47 | 52 (48/h) | 5.67 s |

Recordings whose only `caida` is a censored hold: base 0, S2 (F3) 0, S1 82, S4 0, S1+S4 82, S1+F3 82
