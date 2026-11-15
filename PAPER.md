# Paper artifacts

This branch is the code and the evaluation scripts behind the paper (household capture agent and training-free classifier). The backend, its integration tests and the end-to-end latency harness are in the companion repository.

| Paper | Where |
|---|---|
| Kinematic parameters and state machine (Sections 3.2, 3.3) | `src/te_tengo_deteccion/clasificacion/` (`parametros.py`, `medicion.py`, `estados.py`, `umbrales.py`); specification in `docs/classification-spec.md` |
| Capture agent, persistent event queue with retries (Section 3.1, Table 2) | `src/te_tengo_captura/` (`envios/cola.py`); tests in `tests/captura/envios/test_cola.py` |
| Development results, leave-one-group-out (Table 3) | `scripts/evaluar.py evaluar --barrer 0.01 1.0 0.01`; protocol in `docs/validation.md` |
| Hold-out tests (Fig. 6) | `scripts/evaluar_holdout.py`, `scripts/evaluar_multicamara.py`; results in `resultados/holdout-*.md` |
| Upright precondition, post hoc (Section 5) | `scripts/evaluar_lodo.py`, `scripts/evaluar_especificidad.py`; results in `resultados/lodo-f1-f2-8fps.md` and `resultados/especificidad/`; pre-registration in `docs/adr/0011-*.md` and `docs/adr/0012-*.md` |
| Per-frame processing time (O2) | `scripts/medir_latencia.py`; results in `resultados/latencia-gmdcsa24-8fps.md` |
| Same landmarks and events in the agent and the evaluation script (Section 4) | `scripts/comparar_pipelines.py --todos` |

The datasets are not redistributed: `scripts/descargar_datasets.py` downloads the public ones (URFD, CAUCAFall, GMDCSA-24, UP-Fall, MCFD) from their original sources. The MediaPipe model is downloaded with `scripts/descargar_modelo.sh`.

Run the tests with `uv run pytest`.
