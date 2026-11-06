# Specificity study (ADR 0012): leave one dataset out (secondary)

Five datasets, 1672 units, 3100 configurations; selection by macro criterion over the four training datasets, as in ADR 0011. This uses the hold-out sets as training folds: it is reported after, and separately from, the frozen hold-out test.

## Criterion: youden

| Rule set | urfd | caucafall | gmdcsa24 | upfall | mcfd | Macro sens / spec | Pooled McNemar vs baseline · vs shipped | Chosen (per held-out dataset) |
|---|---|---|---|---|---|---|---|---|
| base | 76.7 % / 75.0 % | 48.0 % / 90.0 % | 84.8 % / 77.8 % | 55.3 % / 91.2 % | 46.7 % / 88.4 % | 62.3 % / 84.5 % | — · 53/49 p=0.767 | urfd: v=0.12; caucafall: v=0.36; gmdcsa24: v=0.12; upfall: v=0.12; mcfd: v=0.12 |
| S2 (F3) | 76.7 % / 72.5 % | 82.0 % / 86.0 % | 88.6 % / 72.8 % | 68.2 % / 95.6 % | 47.3 % / 87.4 % | 72.6 % / 82.9 % | 29/59 p=0.002 · 6/32 p=0.000 | urfd: v=0.01, T=10; caucafall: v=0.01, T=10; gmdcsa24: v=0.01, T=10; upfall: v=0.01, T=10; mcfd: v=0.01, T=10 |
| S1 | 73.3 % / 82.5 % | 48.0 % / 94.0 % | 84.8 % / 88.9 % | 60.0 % / 67.6 % | 23.9 % / 94.3 % | 58.0 % / 85.5 % | 129/147 p=0.306 · 136/150 p=0.442 | urfd: v=0.12, D=3, U=0.5, A6=no; caucafall: v=0.35, D=3, U=0.5, A6=no; gmdcsa24: v=0.12, D=3, U=0.5, A6=no; upfall: v=0.01, D=3, U=0.5, A6=no; mcfd: v=0.12, D=5, U=0.5, A6=no |
| S4 | 76.7 % / 75.0 % | 48.0 % / 90.0 % | 84.8 % / 77.8 % | 68.2 % / 63.2 % | 45.7 % / 88.9 % | 64.7 % / 79.0 % | 24/30 p=0.497 · 36/38 p=0.908 | urfd: v=0.12; caucafall: v=0.36; gmdcsa24: v=0.12; upfall: v=0.01; mcfd: v=0.12 |
| S1+S4 | 73.3 % / 82.5 % | 48.0 % / 94.0 % | 84.8 % / 88.9 % | 60.0 % / 67.6 % | 23.9 % / 95.1 % | 58.0 % / 85.6 % | 128/153 p=0.152 · 135/156 p=0.241 | urfd: v=0.12, D=3, U=0.5, A6=no; caucafall: v=0.35, D=3, U=0.5, A6=no; gmdcsa24: v=0.12, D=3, U=0.5, A6=no; upfall: v=0.01, D=3, U=0.5, A6=no; mcfd: v=0.12, D=5, U=0.5, A6=no |
| *shipped (v = 0.01)* | 76.7 % / 72.5 % | 86.0 % / 84.0 % | 91.1 % / 65.4 % | 68.2 % / 63.2 % | 47.8 % / 87.2 % | 74.0 % / 74.5 % | | |

## Criterion: spec_sens90

| Rule set | urfd | caucafall | gmdcsa24 | upfall | mcfd | Macro sens / spec | Pooled McNemar vs baseline · vs shipped | Chosen (per held-out dataset) |
|---|---|---|---|---|---|---|---|---|
| base | 76.7 % / 72.5 % | 86.0 % / 84.0 % | 91.1 % / 65.4 % | 68.2 % / 63.2 % | 47.8 % / 87.2 % | 74.0 % / 74.5 % | — · 0/0 p=1.000 | urfd: v=0.01; caucafall: v=0.01; gmdcsa24: v=0.01; upfall: v=0.01; mcfd: v=0.01 |
| S2 (F3) | 76.7 % / 72.5 % | 82.0 % / 86.0 % | 88.6 % / 72.8 % | 68.2 % / 95.6 % | 47.3 % / 87.4 % | 72.6 % / 82.9 % | 6/32 p=0.000 · 6/32 p=0.000 | urfd: v=0.01, T=10; caucafall: v=0.01, T=10; gmdcsa24: v=0.01, T=10; upfall: v=0.01, T=10; mcfd: v=0.01, T=10 |
| S1 | 76.7 % / 72.5 % | 86.0 % / 86.0 % | 91.1 % / 69.1 % | 63.5 % / 67.6 % | 48.4 % / 88.9 % | 73.1 % / 76.8 % | 73/89 p=0.239 · 73/89 p=0.239 | urfd: v=0.01, D=2, U=1, A6=yes; caucafall: v=0.01, D=2, U=1, A6=yes; gmdcsa24: v=0.01, D=2, U=1, A6=yes; upfall: v=0.01, D=2, U=1, A6=yes; mcfd: v=0.01, D=2, U=1, A6=yes |
| S4 | 76.7 % / 72.5 % | 86.0 % / 84.0 % | 91.1 % / 65.4 % | 68.2 % / 63.2 % | 47.3 % / 87.8 % | 73.9 % / 74.6 % | 5/10 p=0.302 · 5/10 p=0.302 | urfd: v=0.01; caucafall: v=0.01; gmdcsa24: v=0.01; upfall: v=0.01; mcfd: v=0.01 |
| S1+S4 | 76.7 % / 72.5 % | 86.0 % / 86.0 % | 91.1 % / 69.1 % | 62.4 % / 67.6 % | 47.8 % / 89.5 % | 72.8 % / 76.9 % | 78/96 p=0.197 · 78/96 p=0.197 | urfd: v=0.01, D=2, U=1, A6=yes; caucafall: v=0.01, D=2, U=1, A6=yes; gmdcsa24: v=0.01, D=2, U=1, A6=yes; upfall: v=0.01, D=2, U=1, A6=no; mcfd: v=0.01, D=2, U=1, A6=yes |
| *shipped (v = 0.01)* | 76.7 % / 72.5 % | 86.0 % / 84.0 % | 91.1 % / 65.4 % | 68.2 % / 63.2 % | 47.8 % / 87.2 % | 74.0 % / 74.5 % | | |
