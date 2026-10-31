"""Hold-out test of the shipped classifier on GMDCSA24, a public dataset it has never seen.

The thresholds are **frozen**: the agent's calibrated speed (``velocidad_descenso_min = 0.01``,
``te_tengo_captura.config.UMBRALES_CALIBRADOS``) and the published defaults of ``Umbrales``,
with and without the slow-fall rule R9. Nothing is calibrated on GMDCSA24 for the main result.

It replays the poses stored by ``evaluar.py extraer --datasets gmdcsa24`` (480p, ``--fps``,
JPEG quality 80, MediaPipe lite in VIDEO mode: the production conditions) through the agent's
``ClasificadorCinematico`` and reports, per video:

* TP/FN/TN/FP, sensitivity, specificity, accuracy, precision (95 % Wilson intervals) and F1;
* false alarms per activity, subject (room) and lighting;
* false recoveries (nobody gets up after a fall, according to the GMDCSA24 labels);
* detection latency, from the labelled fall onset to the ``caida`` event.

Secondary analyses (clearly labelled in the report, never used for the main result):

* ``--logo``: leave-one-group-out over URFD + CAUCAFall + GMDCSA24 (15 groups: URFD, the 10
  CAUCAFall subjects and the 4 GMDCSA24 subjects), calibrating the speed threshold by Youden in
  each fold, as ``evaluar.py --barrer`` does;
* ``--comparar-fps 6 8 10``: the frozen thresholds at other frame rates;
* a post-hoc speed sweep on GMDCSA24 alone (optimistic, for interpretation only).

Examples:
    uv run python scripts/descargar_datasets.py --datasets gmdcsa24
    uv run python scripts/evaluar.py extraer --datasets gmdcsa24 --fps 8
    uv run python scripts/evaluar_holdout.py --logo --comparar-fps 6 8 10
"""

import argparse
import math
import statistics
import sys
from collections import defaultdict
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from barrer_rangos import SIN_R9, EventoVideo, eventos_video, wilson
from evaluar import (
    DATASETS_VALIDACION,
    RESULTADOS,
    Secuencia,
    Video,
    cargar_poses,
    listar_videos,
    nombre_variante,
)

from te_tengo_deteccion.clasificacion.estados import TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

# The shipped configuration (te_tengo_captura.config.UMBRALES_CALIBRADOS + Umbrales defaults).
CONGELADOS = Umbrales(velocidad_descenso_min=0.01)
VALORES_V = [round(0.01 * i, 2) for i in range(1, 101)]  # the sweep of evaluar.py --barrer
CAIDA = TipoEvento.CAIDA.value
# The datasets of the leave-one-group-out of section 6.3 (UP-Fall and MCFD: evaluar_multicamara.py).
DATASETS = (*DATASETS_VALIDACION, "gmdcsa24")
# Onset-aware criterion: a fall video counts only if a ``caida`` comes at most this long before
# the labelled onset (the labels are hand-made to 0.1 s and the descent can start a bit earlier).
TOLERANCIA_INICIO_S = 1.0
SALAS = {
    "S1": "room 1 (camera at 70 or 90 cm, two positions)",
    "S2": "room 2 (camera at 135 cm)",
    "S3": "room 2 (camera at 135 cm)",
    "S4": "room 3 (camera at 64 cm)",
}


def condicion(v: Video) -> str:
    c = v.condicion.lower()
    if "night" in c:
        return "night"
    return "day, lights off" if "off" in c else "day"


def sujeto(v: Video) -> str:
    return v.grupo.removeprefix("gmdcsa24-")


# ------------------------------------------------------------------------------ replay

_POSES: dict[str, Secuencia] = {}


def _cargar(videos: list[Video], variante: str) -> None:
    _POSES.update({v.nombre: cargar_poses(v, variante) for v in videos})


def _correr(cambios: dict[str, float]) -> dict[str, list[EventoVideo]]:
    umbrales = CONGELADOS.model_copy(update=cambios)
    return {nombre: eventos_video(seq, umbrales) for nombre, seq in _POSES.items()}


def correr(
    videos: list[Video], variante: str, ajustes: list[dict[str, float]], procesos: int
) -> list[dict[str, list[EventoVideo]]]:
    with ProcessPoolExecutor(procesos, initializer=_cargar, initargs=(videos, variante)) as g:
        return list(g.map(_correr, ajustes, chunksize=2))


# ------------------------------------------------------------------------------ metrics


@dataclass(frozen=True, slots=True)
class Conteo:
    vp: int
    fn: int
    vn: int
    fp: int

    @property
    def sensibilidad(self) -> float:
        return self.vp / (self.vp + self.fn) if self.vp + self.fn else math.nan

    @property
    def especificidad(self) -> float:
        return self.vn / (self.vn + self.fp) if self.vn + self.fp else math.nan

    @property
    def exactitud(self) -> float:
        total = self.vp + self.fn + self.vn + self.fp
        return (self.vp + self.vn) / total if total else math.nan

    @property
    def precision(self) -> float:
        return self.vp / (self.vp + self.fp) if self.vp + self.fp else math.nan

    @property
    def f1(self) -> float:
        p, s = self.precision, self.sensibilidad
        return 2 * p * s / (p + s) if p + s else math.nan

    @property
    def youden(self) -> float:
        return self.sensibilidad + self.especificidad - 1

    def ic(self, cual: str) -> tuple[float, float]:
        aciertos, total = {
            "sensibilidad": (self.vp, self.vp + self.fn),
            "especificidad": (self.vn, self.vn + self.fp),
            "exactitud": (self.vp + self.vn, self.vp + self.fn + self.vn + self.fp),
            "precision": (self.vp, self.vp + self.fp),
        }[cual]
        return wilson(aciertos, total)


def detecto(eventos: list[EventoVideo]) -> bool:
    return any(t == CAIDA for t, _ in eventos)


def a_tiempo(v: Video, eventos: list[EventoVideo]) -> bool:
    """A ``caida`` after the labelled onset (minus the tolerance); any one if it is unknown."""
    if v.inicio_caida is None:
        return detecto(eventos)
    return any(t == CAIDA and i >= v.inicio_caida - TOLERANCIA_INICIO_S for t, i in eventos)


def contar(
    videos: Sequence[Video], eventos: dict[str, list[EventoVideo]], estricto: bool = False
) -> Conteo:
    def caida(v: Video) -> bool:
        return a_tiempo(v, eventos[v.nombre]) if estricto else detecto(eventos[v.nombre])

    vp = sum(1 for v in videos if v.es_caida and caida(v))
    fn = sum(1 for v in videos if v.es_caida and not caida(v))
    vn = sum(1 for v in videos if not v.es_caida and not detecto(eventos[v.nombre]))
    fp = sum(1 for v in videos if not v.es_caida and detecto(eventos[v.nombre]))
    return Conteo(vp, fn, vn, fp)


def latencias(videos: Sequence[Video], eventos: dict[str, list[EventoVideo]]) -> list[float]:
    """From the labelled fall onset to the first ``caida``, for the detected falls."""
    salida = []
    for v in videos:
        if v.es_caida and v.inicio_caida is not None and a_tiempo(v, eventos[v.nombre]):
            desde = v.inicio_caida - TOLERANCIA_INICIO_S
            primera = next(i for t, i in eventos[v.nombre] if t == CAIDA and i >= desde)
            salida.append(primera - v.inicio_caida)
    return salida


# ------------------------------------------------------------------------------ report


def pct(x: float) -> str:
    return "—" if x != x else f"{x:.1%}"


def con_ic(c: Conteo, cual: str) -> str:
    bajo, alto = c.ic(cual)
    if bajo != bajo:
        return "—"
    return f"{pct(getattr(c, cual))} ({bajo:.1%}–{alto:.1%})"


ENCABEZADO = [
    "| Setting | Falls | ADL | TP | FN | TN | FP | Sensitivity (95 % CI) | "
    "Specificity (95 % CI) | Accuracy (95 % CI) | Precision (95 % CI) | F1 |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|",
]


def fila(nombre: str, c: Conteo) -> str:
    return (
        f"| {nombre} | {c.vp + c.fn} | {c.vn + c.fp} | {c.vp} | {c.fn} | {c.vn} | {c.fp} | "
        f"{con_ic(c, 'sensibilidad')} | {con_ic(c, 'especificidad')} | "
        f"{con_ic(c, 'exactitud')} | {con_ic(c, 'precision')} | {c.f1:.3f} |"
    )


def resumen_latencia(xs: list[float]) -> str:
    if not xs:
        return "—"
    ordenadas = sorted(xs)
    p95 = ordenadas[min(len(ordenadas) - 1, math.ceil(0.95 * len(ordenadas)) - 1)]
    return (
        f"n = {len(xs)}, median {statistics.median(xs):.2f} s, mean {statistics.mean(xs):.2f} s, "
        f"p95 {p95:.2f} s, range {min(xs):.2f} to {max(xs):.2f} s"
    )


def desglose(
    titulo: str,
    videos: list[Video],
    sin: dict[str, list[EventoVideo]],
    con: dict[str, list[EventoVideo]],
    clave: Callable[[Video], str],
) -> list[str]:
    grupos: dict[str, list[Video]] = defaultdict(list)
    for v in videos:
        grupos[clave(v)].append(v)
    lineas = [
        f"### {titulo}",
        "",
        "| Group | Videos | `caida` without R9 | `caida` with R9 |",
        "|---|---|---|---|",
    ]
    for nombre, g in sorted(grupos.items()):
        lineas.append(
            f"| {nombre} | {len(g)} | {sum(detecto(sin[v.nombre]) for v in g)} | "
            f"{sum(detecto(con[v.nombre]) for v in g)} |"
        )
    return [*lineas, ""]


def seccion_principal(
    videos: list[Video],
    sin: dict[str, list[EventoVideo]],
    con: dict[str, list[EventoVideo]],
) -> list[str]:
    c_sin, c_con = contar(videos, sin), contar(videos, con)
    caidas = [v for v in videos if v.es_caida]
    adl = [v for v in videos if not v.es_caida]
    sin_levantarse = [v for v in caidas if v.se_levanta is False]
    lineas = [
        "## 1. Main result: frozen shipped thresholds (no recalibration)",
        "",
        f"Thresholds: `{CONGELADOS.model_dump()}`; without R9 = "
        f"`descenso_caida_lenta_min = {SIN_R9['descenso_caida_lenta_min']:g}` (R9 never fires).",
        "",
        *ENCABEZADO,
        fila("Without R9 (R4–R8)", c_sin),
        fila("**With R9 (shipped)**", c_con),
        fila("Without R9, onset-aware", contar(videos, sin, estricto=True)),
        fila("With R9, onset-aware", contar(videos, con, estricto=True)),
        "",
        "F1 has no interval; precision depends on the 79/81 fall/ADL mix of the dataset, not on "
        "the prevalence of falls in a home.",
        "",
        "**Onset-aware** (a stricter check, same thresholds): a fall video counts as detected "
        f"only if a `caida` comes no earlier than {TOLERANCIA_INICIO_S:g} s before the labelled "
        "fall onset, so a `caida` fired while the person was still lying on the bed or standing "
        "before the fall does not count. Fall videos whose first `caida` is earlier than that:",
        "",
        *(
            f"- {v.nombre} (onset {v.inicio_caida:g} s, {v.detalle}): "
            + " ".join(f"{t}@{i:.1f}s" for t, i in con[v.nombre])
            for v in caidas
            if v.inicio_caida is not None
            and detecto(con[v.nombre])
            and next(i for t, i in con[v.nombre] if t == CAIDA)
            < v.inicio_caida - TOLERANCIA_INICIO_S
        ),
        "",
        "### Other events",
        "",
    ]
    for nombre, ev in (("Without R9", sin), ("With R9", con)):
        rec = sum(
            TipoEvento.RECUPERACION.value in [t for t, _ in ev[v.nombre]] for v in sin_levantarse
        )
        ines = sum(
            TipoEvento.MOVIMIENTO_INESTABLE.value in [t for t, _ in ev[v.nombre]] for v in adl
        )
        conf = sum(
            TipoEvento.CAIDA_CONFIRMADA.value in [t for t, _ in ev[v.nombre]] for v in caidas
        )
        lineas.append(
            f"- {nombre}: false recoveries {rec} of {len(sin_levantarse)} falls in which nobody "
            f"gets up (per the labels); daily activities with a `movimiento_inestable` {ines} of "
            f"{len(adl)}; falls with `caida_confirmada` {conf} of {len(caidas)} (clips last at "
            "most 17.5 s, shorter than the 30 s confirmation)."
        )
        for v in sin_levantarse:
            if TipoEvento.RECUPERACION.value in [t for t, _ in ev[v.nombre]]:
                instantes = " ".join(f"{t}@{i:.1f}s" for t, i in ev[v.nombre])
                lineas.append(
                    f"  - false recovery in {v.nombre} (labelled onset {v.inicio_caida:g} s): "
                    f"{instantes}"
                )
    lineas += [
        "",
        "### Detection latency (labelled fall onset → first onset-aware `caida`)",
        "",
        f"- Without R9: {resumen_latencia(latencias(videos, sin))}",
        f"- With R9: {resumen_latencia(latencias(videos, con))}",
        "",
        "The onset is the start of the first `Falling` interval of the GMDCSA24 labels, given "
        "to 0.1 s by hand. A negative value means the `caida` came before the labelled onset "
        f"(at most {TOLERANCIA_INICIO_S:g} s, by the onset-aware rule). "
        f"{sum(1 for v in caidas if v.inicio_caida is None)} fall has no onset label and is "
        "left out.",
        "",
    ]
    lineas += desglose("Falls by direction label", caidas, sin, con, lambda v: v.actividad)
    lineas += desglose(
        "Falls by landing surface (from the description)",
        caidas,
        sin,
        con,
        lambda v: (
            "onto the bed"
            if "on the bed" in v.detalle.lower()
            and not any(k in v.detalle.lower() for k in ("floor", "ground"))
            else "onto the floor"
        ),
    )
    lineas += desglose(
        "False alarms by daily activity (`caida` = false alarm)",
        adl,
        sin,
        con,
        lambda v: v.actividad,
    )
    lineas += desglose(
        "By subject and room (falls: detections; ADL: false alarms)",
        videos,
        sin,
        con,
        lambda v: f"{sujeto(v)} · {SALAS[sujeto(v)]} · {'falls' if v.es_caida else 'ADL'}",
    )
    lineas += desglose(
        "By lighting (falls: detections; ADL: false alarms)",
        videos,
        sin,
        con,
        lambda v: f"{condicion(v)} · {'falls' if v.es_caida else 'ADL'}",
    )
    lineas += ["### Videos with an error (with R9)", ""]
    for v in videos:
        if v.es_caida != detecto(con[v.nombre]):
            tipo = "missed fall" if v.es_caida else "false alarm"
            eventos = " ".join(f"{t}@{i:.1f}s" for t, i in con[v.nombre]) or "no events"
            lineas.append(f"- {v.nombre} ({tipo}, {v.actividad}): {v.detalle} → {eventos}")
    cambios = [
        f"- {v.nombre} ({'fall' if v.es_caida else 'ADL'}, {v.actividad}): "
        f"{'detected' if v.es_caida else 'false alarm'} only with R9"
        for v in videos
        if detecto(sin[v.nombre]) != detecto(con[v.nombre])
    ]
    return [*lineas, "", "### Videos that change with R9", "", *(cambios or ["- none"]), ""]


def calibrar(
    curva: list[dict[str, list[EventoVideo]]], videos: list[Video]
) -> tuple[float, Conteo]:
    """Speed with the maximum Youden index on ``videos``; on a tie, the lowest one."""
    puntos = [(v, contar(videos, ev)) for v, ev in zip(VALORES_V, curva, strict=True)]
    return max(puntos, key=lambda par: (round(par[1].youden, 6), -par[0]))


def seccion_logo(
    videos: list[Video], curvas: dict[str, list[dict[str, list[EventoVideo]]]]
) -> list[str]:
    grupos = sorted({v.grupo for v in videos})
    lineas = [
        f"## 2. Secondary: leave-one-group-out over all datasets ({len(grupos)} groups)",
        "",
        "Not the main result. Each group is evaluated with the speed threshold calibrated by "
        f"Youden ({VALORES_V[0]}–{VALORES_V[-1]}, step 0.01, ties → lowest) on the other "
        f"{len(grupos) - 1} groups, the same protocol as `evaluar.py --barrer`; every other "
        "value stays at its default. It shows whether adding GMDCSA24 to the calibration data "
        "changes `v` and the performance.",
        "",
    ]
    for nombre, curva in curvas.items():
        fuera: dict[str, list[EventoVideo]] = {}
        elegidos = []
        for grupo in grupos:
            entrenamiento = [v for v in videos if v.grupo != grupo]
            valor, _ = calibrar(curva, entrenamiento)
            elegidos.append(f"{grupo}: {valor:g}")
            ev = curva[VALORES_V.index(valor)]
            fuera.update({v.nombre: ev[v.nombre] for v in videos if v.grupo == grupo})
        todos, c_todos = calibrar(curva, videos)
        lineas += [
            f"### {nombre}",
            "",
            "Chosen v per held-out group: " + ", ".join(elegidos) + ".",
            "",
            *ENCABEZADO,
            fila("**All 330 videos (pooled folds)**", contar(videos, fuera)),
        ]
        for d in DATASETS:
            lineas.append(fila(d, contar([v for v in videos if v.dataset == d], fuera)))
        lineas += [
            "",
            f"Calibrated on all 330 videos (optimistic, not a test): v = {todos:g}, "
            f"sensitivity {pct(c_todos.sensibilidad)}, specificity {pct(c_todos.especificidad)}.",
            "",
        ]
    return lineas


def seccion_post_hoc(
    videos: list[Video], curvas: dict[str, list[dict[str, list[EventoVideo]]]]
) -> list[str]:
    lineas = [
        "## 3. Secondary, post hoc: speed sweep on GMDCSA24 alone (optimistic)",
        "",
        "For interpretation only: the threshold is chosen **on the test data**, so this is an "
        "upper bound of what recalibrating `v` alone could give, not a test result.",
        "",
        "| Classifier | Best v (Youden) | Sensitivity | Specificity | "
        "v = 0.05 (sens. / spec.) | v = 0.1 | v = 0.3 |",
        "|---|---|---|---|---|---|---|",
    ]
    for nombre, curva in curvas.items():
        valor, c = calibrar(curva, videos)

        def en(x: float, curva: list[dict[str, list[EventoVideo]]] = curva) -> str:
            k = contar(videos, curva[VALORES_V.index(x)])
            return f"{pct(k.sensibilidad)} / {pct(k.especificidad)}"

        lineas.append(
            f"| {nombre} | {valor:g} | {pct(c.sensibilidad)} | {pct(c.especificidad)} | "
            f"{en(0.05)} | {en(0.1)} | {en(0.3)} |"
        )
    return [*lineas, ""]


def seccion_fps(filas: list[tuple[float, Conteo, Conteo, str, str]]) -> list[str]:
    lineas = [
        "## 4. Secondary: frame rate (frozen thresholds, GMDCSA24 only)",
        "",
        "| fps | Without R9: sens. / spec. / acc. | With R9: sens. / spec. / acc. | "
        "Latency with R9 (median) | False recoveries with R9 |",
        "|---|---|---|---|---|",
    ]
    for fps, c_sin, c_con, lat, rec in filas:
        lineas.append(
            f"| {fps:g} | {pct(c_sin.sensibilidad)} / {pct(c_sin.especificidad)} / "
            f"{pct(c_sin.exactitud)} | {pct(c_con.sensibilidad)} / {pct(c_con.especificidad)} / "
            f"{pct(c_con.exactitud)} | {lat} | {rec} |"
        )
    return [*lineas, ""]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--procesos", type=int, default=6)
    parser.add_argument("--logo", action="store_true", help="Secondary LOGO over all datasets")
    parser.add_argument("--comparar-fps", nargs="+", type=float, default=[], metavar="FPS")
    parser.add_argument(
        "--salida", type=Path, help="Default: resultados/holdout-gmdcsa24-<fps>fps.md"
    )
    args = parser.parse_args()

    def preparar(fps: float, datasets: Sequence[str]) -> tuple[list[Video], str] | None:
        videos = listar_videos(args.datos, datasets)
        variante = nombre_variante(args.modelo, "video", fps, True)
        faltan = [v.nombre for v in videos if not v.cache(variante).exists()]
        if not videos or faltan:
            print(
                f"Faltan poses ({variante}, {len(faltan)} videos). Ejecuta: "
                f"scripts/evaluar.py extraer --datasets {' '.join(datasets)} --fps {fps:g}",
                file=sys.stderr,
            )
            return None
        return videos, variante

    preparado = preparar(args.fps, ["gmdcsa24"])
    if preparado is None:
        return 1
    videos, variante = preparado
    sin, con = correr(videos, variante, [SIN_R9, {}], args.procesos)
    caidas = sum(v.es_caida for v in videos)
    texto = [
        "# Hold-out evaluation on GMDCSA24",
        "",
        f"Videos: {len(videos)} ({caidas} falls, {len(videos) - caidas} ADL) · "
        f"Poses: `{variante}` · Dataset: GMDCSA24 v2.1, https://doi.org/10.5281/zenodo.13354453",
        "",
        "A video is a true positive if it has at least one `caida` event; an ADL video with any "
        "`caida` is a false positive. Intervals: 95 % Wilson.",
        "",
        *seccion_principal(videos, sin, con),
    ]

    if args.logo:
        todos = preparar(args.fps, DATASETS)
        if todos is None:
            return 1
        videos_t, variante_t = todos
        ajustes = [{"velocidad_descenso_min": x} for x in VALORES_V]
        ajustes += [{"velocidad_descenso_min": x, **SIN_R9} for x in VALORES_V]
        corridas = correr(videos_t, variante_t, ajustes, args.procesos)
        n = len(VALORES_V)
        curvas = {"With R9 (shipped)": corridas[:n], "Without R9": corridas[n:]}
        texto += seccion_logo(videos_t, curvas)
        nombres = {v.nombre for v in videos}
        curvas_g = {
            k: [{x: e for x, e in ev.items() if x in nombres} for ev in c]
            for k, c in curvas.items()
        }
        texto += seccion_post_hoc(videos, curvas_g)

    if args.comparar_fps:
        filas = []
        for fps in args.comparar_fps:
            p = preparar(fps, ["gmdcsa24"])
            if p is None:
                return 1
            vs, var = p
            s, c = correr(vs, var, [SIN_R9, {}], args.procesos)
            sin_lev = [v for v in vs if v.es_caida and v.se_levanta is False]
            rec = sum(TipoEvento.RECUPERACION.value in [t for t, _ in c[v.nombre]] for v in sin_lev)
            lat = latencias(vs, c)
            mediana = f"{statistics.median(lat):.2f} s" if lat else "—"
            filas.append((fps, contar(vs, s), contar(vs, c), mediana, f"{rec}/{len(sin_lev)}"))
        texto += seccion_fps(filas)

    salida = args.salida or RESULTADOS / f"holdout-gmdcsa24-{args.fps:g}fps.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(texto).rstrip() + "\n", encoding="utf-8")
    print("\n".join(texto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
