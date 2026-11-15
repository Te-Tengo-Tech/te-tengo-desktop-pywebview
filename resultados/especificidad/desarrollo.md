# Specificity study (ADR 0012): development data, nested

URFD + CAUCAFall, 170 videos, poses `lite-video-8fps-jpeg`. Thresholds chosen inside each training fold (maximum Youden; ties: lowest v, then the most conservative value). Distinct configurations evaluated: **16400**. Intervals: 95 % Wilson. McNemar: exact, two-sided, on correctness of paired videos (b = only the baseline right, c = only the candidate right). S1 holds still running at the end of a clip count as `caida` (censored).

## Summary (leave one group out)

| Rule set | Configs | Sensitivity | Specificity | FN | FP | URFD sens / spec | CAUCAFall sens / spec | McNemar all · falls · ADL | False recoveries | Censored TP / FP | URFD latency median (range), n |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **base** | 100 | 82.5 % (72.7–89.3) | 78.9 % (69.4–86.0) | 14 | 19 | 76.7 % / 72.5 % | 86.0 % / 84.0 % | — | 0/30 | 0 / 0 | 0.83 s (0.47–2.03), 23 |
| **S1** | 1200 | 80.0 % (70.0–87.3) | 84.4 % (75.6–90.5) | 16 | 14 | 76.7 % / 72.5 % | 82.0 % / 94.0 % | 2/5 p=0.453 · 2/0 p=0.500 · 0/5 p=0.062 | 0/30 | 39 / 12 | 2.13 s (1.10–3.07), 23 |
| **S2 (F3)** | 500 | 80.0 % (70.0–87.3) | 80.0 % (70.6–87.0) | 16 | 18 | 76.7 % / 72.5 % | 82.0 % / 86.0 % | 2/1 p=1.000 · 2/0 p=0.500 · 0/1 p=1.000 | 0/30 | 0 / 0 | 0.83 s (0.47–2.03), 23 |
| **S3** | 100 | 85.0 % (75.6–91.2) | 71.1 % (61.0–79.5) | 12 | 26 | 93.3 % / 65.0 % | 80.0 % / 76.0 % | 14/9 p=0.405 · 5/7 p=0.774 · 9/2 p=0.065 | 0/30 | 0 / 0 | 0.75 s (0.47–2.03), 28 |
| **S4** | 100 | 82.5 % (72.7–89.3) | 78.9 % (69.4–86.0) | 14 | 19 | 76.7 % / 72.5 % | 86.0 % / 84.0 % | 0/0 p=1.000 · 0/0 p=1.000 · 0/0 p=1.000 | 0/30 | 0 / 0 | 0.83 s (0.47–2.03), 23 |
| **S1+S4** | 1200 | 80.0 % (70.0–87.3) | 84.4 % (75.6–90.5) | 16 | 14 | 76.7 % / 72.5 % | 82.0 % / 94.0 % | 2/5 p=0.453 · 2/0 p=0.500 · 0/5 p=0.062 | 0/30 | 39 / 12 | 2.13 s (1.10–3.07), 23 |
| **S1+F3** | 6000 | 77.5 % (67.2–85.3) | 84.4 % (75.6–90.5) | 18 | 14 | 76.7 % / 72.5 % | 78.0 % / 94.0 % | 4/5 p=1.000 · 4/0 p=0.125 · 0/5 p=0.062 | 0/30 | 39 / 12 | 2.13 s (1.10–3.07), 23 |
| **S1+S4+F3** | 6000 | 77.5 % (67.2–85.3) | 84.4 % (75.6–90.5) | 18 | 14 | 76.7 % / 72.5 % | 78.0 % / 94.0 % | 4/5 p=1.000 · 4/0 p=0.125 · 0/5 p=0.062 | 0/30 | 39 / 12 | 2.13 s (1.10–3.07), 23 |
| **S1+S3 (exploratory)** | 1200 | 81.2 % (71.3–88.3) | 75.6 % (65.8–83.3) | 15 | 22 | 93.3 % / 60.0 % | 74.0 % / 88.0 % | 15/11 p=0.557 · 7/6 p=1.000 · 8/5 p=0.581 | 0/30 | 40 / 15 | 1.85 s (1.10–3.07), 28 |
| *Fully nested (each fold also picks the rule set)* | 16400 | 75.0 % (64.5–83.2) | 81.1 % (71.8–87.9) | 20 | 17 | | | 10/6 p=0.454 | | | |

Fully nested choices: Subject.1: S1+S3 (exploratory) (v=0.08, D=5, U=0.5, A6=no); Subject.10: S1+S3 (exploratory) (v=0.05, D=5, U=0.5, A6=no); Subject.2: S1+S3 (exploratory) (v=0.01, D=5, U=0.5, A6=no); Subject.3: S1+S3 (exploratory) (v=0.01, D=5, U=0.5, A6=no); Subject.4: S1+S3 (exploratory) (v=0.15, D=5, U=0.5, A6=no); Subject.5: S1+S3 (exploratory) (v=0.08, D=5, U=0.5, A6=no); Subject.6: S1+S3 (exploratory) (v=0.12, D=5, U=0.5, A6=no); Subject.7: S1+S3 (exploratory) (v=0.01, D=5, U=0.5, A6=no); Subject.8: S1+S3 (exploratory) (v=0.01, D=5, U=0.5, A6=no); Subject.9: S1+S3 (exploratory) (v=0.05, D=5, U=0.5, A6=no); urfd: S1 (v=0.01, D=5, U=1, A6=no)

## Cross-dataset (sensitivity / specificity on the test dataset)

| Rule set | URFD → CAUCAFall | CAUCAFall → URFD |
|---|---|---|
| base | 46.0 % / 94.0 % (v=0.71) | 76.7 % / 72.5 % (v=0.01) |
| S1 | 52.0 % / 96.0 % (v=0.31, D=5, U=0.5, A6=no) | 76.7 % / 72.5 % (v=0.01, D=5, U=1, A6=no) |
| S2 (F3) | 46.0 % / 94.0 % (v=0.71, T=10) | 76.7 % / 72.5 % (v=0.01, T=10) |
| S3 | 50.0 % / 92.0 % (v=0.45) | 93.3 % / 65.0 % (v=0.15) |
| S4 | 44.0 % / 94.0 % (v=0.71) | 76.7 % / 72.5 % (v=0.01) |
| S1+S4 | 52.0 % / 96.0 % (v=0.31, D=5, U=0.5, A6=no) | 76.7 % / 72.5 % (v=0.01, D=5, U=1, A6=no) |
| S1+F3 | 50.0 % / 96.0 % (v=0.18, D=5, U=0.5, A6=no, T=1) | 76.7 % / 72.5 % (v=0.01, D=5, U=1, A6=no, T=10) |
| S1+S4+F3 | 48.0 % / 96.0 % (v=0.18, D=5, U=0.5, A6=no, T=1) | 76.7 % / 72.5 % (v=0.01, D=5, U=1, A6=no, T=10) |
| S1+S3 (exploratory) | 58.0 % / 96.0 % (v=0.31, D=5, U=0.5, A6=no) | 93.3 % / 60.0 % (v=0.01, D=5, U=1, A6=no) |

## Configuration chosen per fold and on all 170 videos (frozen for the hold-out)

| Rule set | Per fold (count) | All development videos |
|---|---|---|
| base | v=0.01 ×11 | v=0.01 |
| S1 | v=0.01, D=5, U=0.5, A6=no ×10; v=0.01, D=5, U=1, A6=no ×1 | v=0.01, D=5, U=0.5, A6=no |
| S2 (F3) | v=0.01, T=10 ×11 | v=0.01, T=10 |
| S3 | v=0.08 ×2; v=0.15 ×9 | v=0.15 |
| S4 | v=0.01 ×11 | v=0.01 |
| S1+S4 | v=0.01, D=5, U=0.5, A6=no ×10; v=0.01, D=5, U=1, A6=no ×1 | v=0.01, D=5, U=0.5, A6=no |
| S1+F3 | v=0.01, D=5, U=0.5, A6=no, T=10 ×10; v=0.01, D=5, U=1, A6=no, T=10 ×1 | v=0.01, D=5, U=0.5, A6=no, T=10 |
| S1+S4+F3 | v=0.01, D=5, U=0.5, A6=no, T=10 ×10; v=0.01, D=5, U=1, A6=no, T=10 ×1 | v=0.01, D=5, U=0.5, A6=no, T=10 |
| S1+S3 (exploratory) | v=0.01, D=5, U=0.5, A6=no ×4; v=0.01, D=5, U=1, A6=no ×1; v=0.05, D=5, U=0.5, A6=no ×2; v=0.08, D=5, U=0.5, A6=no ×2; v=0.12, D=5, U=0.5, A6=no ×1; v=0.15, D=5, U=0.5, A6=no ×1 | v=0.01, D=5, U=0.5, A6=no |

## Videos with a `caida` per activity (LOGO)

| Activity | Videos | base | S1 | S2 (F3) | S3 | S4 | S1+S4 | S1+F3 | S1+S4+F3 | S1+S3 (exploratory) |
|---|---|---|---|---|---|---|---|---|---|---|
| CAUCAFall · Fall backwards | 10 | 10 | 9 | 10 | 8 | 10 | 9 | 9 | 9 | 7 |
| CAUCAFall · Fall forward | 10 | 8 | 8 | 7 | 6 | 8 | 8 | 7 | 7 | 6 |
| CAUCAFall · Fall left | 10 | 9 | 9 | 8 | 9 | 9 | 9 | 8 | 8 | 9 |
| CAUCAFall · Fall right | 10 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| CAUCAFall · Fall sitting | 10 | 8 | 7 | 8 | 9 | 8 | 7 | 7 | 7 | 7 |
| CAUCAFall · Hop | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CAUCAFall · Kneel | 10 | 3 | 2 | 3 | 4 | 3 | 2 | 2 | 2 | 2 |
| CAUCAFall · Pick up object | 10 | 3 | 0 | 3 | 4 | 3 | 0 | 0 | 0 | 2 |
| CAUCAFall · Sit down | 10 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 2 |
| CAUCAFall · Walk | 10 | 1 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0 |
| URFD · fall | 30 | 23 | 23 | 23 | 28 | 23 | 23 | 23 | 23 | 28 |
| URFD · lying on the floor on purpose | 16 | 8 | 8 | 8 | 11 | 8 | 8 | 8 | 8 | 12 |
| URFD · other ADL | 24 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 4 |

## Videos that change against the baseline (LOGO)

- **S1**: right only here: Subject.1-Kneel, Subject.1-Pick_up_object, Subject.10-Walk, Subject.2-Pick_up_object, Subject.9-Pick_up_object; wrong only here: Subject.2-Fall_backwards, Subject.2-Fall_sitting
- **S2 (F3)**: right only here: Subject.10-Walk; wrong only here: Subject.4-Fall_forward, Subject.5-Fall_left
- **S3**: right only here: adl-10, fall-10, fall-18, fall-24, fall-26, fall-30, Subject.3-Fall_sitting, Subject.8-Fall_right, Subject.8-Sit_down; wrong only here: adl-30, adl-32, adl-39, adl-40, Subject.1-Fall_backwards, Subject.1-Walk, Subject.10-Pick_up_object, Subject.10-Sit_down, Subject.3-Kneel, Subject.4-Fall_right, Subject.5-Fall_forward, Subject.6-Fall_backwards, Subject.9-Fall_forward, Subject.9-Sit_down
- **S4**: right only here: none; wrong only here: none
- **S1+S4**: right only here: Subject.1-Kneel, Subject.1-Pick_up_object, Subject.10-Walk, Subject.2-Pick_up_object, Subject.9-Pick_up_object; wrong only here: Subject.2-Fall_backwards, Subject.2-Fall_sitting
- **S1+F3**: right only here: Subject.1-Kneel, Subject.1-Pick_up_object, Subject.10-Walk, Subject.2-Pick_up_object, Subject.9-Pick_up_object; wrong only here: Subject.2-Fall_backwards, Subject.2-Fall_sitting, Subject.4-Fall_forward, Subject.5-Fall_left
- **S1+S4+F3**: right only here: Subject.1-Kneel, Subject.1-Pick_up_object, Subject.10-Walk, Subject.2-Pick_up_object, Subject.9-Pick_up_object; wrong only here: Subject.2-Fall_backwards, Subject.2-Fall_sitting, Subject.4-Fall_forward, Subject.5-Fall_left
- **S1+S3 (exploratory)**: right only here: fall-10, fall-18, fall-24, fall-26, fall-30, Subject.1-Kneel, Subject.1-Pick_up_object, Subject.10-Walk, Subject.2-Pick_up_object, Subject.8-Fall_right, Subject.9-Pick_up_object; wrong only here: adl-19, adl-30, adl-32, adl-39, adl-40, Subject.1-Fall_backwards, Subject.10-Pick_up_object, Subject.10-Sit_down, Subject.2-Fall_backwards, Subject.2-Fall_sitting, Subject.4-Fall_right, Subject.5-Fall_forward, Subject.6-Fall_backwards, Subject.8-Pick_up_object, Subject.9-Fall_forward
