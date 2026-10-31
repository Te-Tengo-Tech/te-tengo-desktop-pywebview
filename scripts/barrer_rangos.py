"""Safe ranges of the tunable classification values (US-45), measured on URFD and CAUCAFall.

It replays the poses stored by ``evaluar.py extraer`` (480p, 8 fps, JPEG quality 80, MediaPipe
lite in VIDEO mode: the production conditions of ``docs/validation.md``) through the agent's
``ClasificadorCinematico`` with one value changed at a time around the validated defaults, and
with a small grid for the three values that interact (speed × angle × ratio). For each setting
it reports:

* sensitivity, specificity and accuracy per video, with 95 % Wilson intervals;
* false recoveries: URFD falls with a ``recuperacion`` (nobody gets up in them);
* detection latency: from the first URFD frame labelled "falling" to the ``caida`` event.

It also compares the classifier with and without the slow-fall rule R9, overall, per activity
and on the slow falls, identified by their measured peak hip descent speed.

The recommended safe range of a value is the interval of tested values around the default in
which sensitivity and specificity stay at or above 75 %, neither drops more than 5 points
below the default, and there are no more false recoveries than with the default.

Examples:
    uv run python scripts/evaluar.py extraer          # once: stores the poses
    uv run python scripts/barrer_rangos.py            # writes resultados/rangos/
    uv run python scripts/barrer_rangos.py --grafico docs/img/validacion-rangos.png
"""

import argparse
import csv
import itertools
import json
import math
import statistics
import sys
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from evaluar import (
    RESULTADOS,
    Secuencia,
    Video,
    cargar_poses,
    listar_videos,
    nombre_variante,
)

from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clasificacion.medicion import MedidorCinematico
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

# Validated values: the agent's calibrated speed and the published defaults of ``Umbrales``.
BASE = Umbrales(velocidad_descenso_min=0.01)
MINIMO = 0.75  # sensitivity and specificity required in the whole safe range
CAIDA_MAXIMA = 0.05  # largest drop allowed against the default (5 points)
Z95 = 1.959964

# Values tested one at a time. The proposed range of US-45 is inside each list, with some
# margin on both sides to see where the performance breaks.
BARRIDOS: dict[str, list[float]] = {
    "velocidad_descenso_min": [
        0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.075, 0.1, 0.2, 0.3, 0.5,
    ],
    "angulo_linea_central_max_grados": [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
    "razon_ancho_alto_min": [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0],
    "ventana_reaccion_s": [0.25, 0.5, 0.75, 1.0, 1.25, 1.48, 1.75, 2.0, 2.5, 3.0, 4.0],
    "confirmacion_suelo_s": [5, 10, 15, 30, 60, 120],
    "persistencia_erguido_s": [0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0],
    "descenso_caida_lenta_min": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0],
    "ventana_caida_lenta_s": [2, 3, 5, 10, 15, 20, 30, 60],
    "permanencia_caida_lenta_s": [0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0],
}  # fmt: skip

# R9 switched off: no hip drop is large enough.
SIN_R9: dict[str, float] = {"descenso_caida_lenta_min": 1e9}
# A fall is "slow" if its measured peak hip descent speed is below this value (bodies/s): at
# that speed, dropping the hip half a body length takes longer than the 1.48 s window of R4.
LENTA_MAX = 0.3

# The three values that decide the fall together (M1, M2 and M3).
REJILLA: dict[str, list[float]] = {
    "velocidad_descenso_min": [0.005, 0.01, 0.02, 0.03, 0.05],
    "angulo_linea_central_max_grados": [30, 40, 45, 50, 55, 60],
    "razon_ancho_alto_min": [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
}

# Proposed ranges of US-45, to compare them with the measured ones.
PROPUESTOS: dict[str, tuple[float, float]] = {
    "velocidad_descenso_min": (0.005, 0.05),
    "angulo_linea_central_max_grados": (30, 60),
    "razon_ancho_alto_min": (0.8, 1.5),
    "ventana_reaccion_s": (1.0, 3.0),
    "confirmacion_suelo_s": (15, 120),
    "persistencia_erguido_s": (0.5, 3.0),
    "descenso_caida_lenta_min": (0.3, 0.6),
    "ventana_caida_lenta_s": (5, 20),
    "permanencia_caida_lenta_s": (1.0, 5.0),
}

ROTULOS: dict[str, str] = {
    "velocidad_descenso_min": "Minimum descent speed (bodies/s)",
    "angulo_linea_central_max_grados": "Center-line angle (°)",
    "razon_ancho_alto_min": "Width/height ratio",
    "ventana_reaccion_s": "Reaction window (s)",
    "confirmacion_suelo_s": "Confirmation on the floor (s)",
    "persistencia_erguido_s": "Upright time for recovery (s)",
    "descenso_caida_lenta_min": "R9: hip drop (center-line lengths)",
    "ventana_caida_lenta_s": "R9: upright at most this long before (s)",
    "permanencia_caida_lenta_s": "R9: time horizontal (s)",
}

EventoVideo = tuple[str, float]  # (type, instant in s)


# ------------------------------------------------------------------------------ replay

_POSES: dict[str, Secuencia] = {}
DURACIONES: dict[str, float] = {}


def _cargar(videos: list[Video], variante: str) -> None:
    _POSES.update({v.nombre: cargar_poses(v, variante) for v in videos})


def velocidad_pico(secuencia: Secuencia) -> float | None:
    """Largest hip descent speed of R1 in the video, or ``None`` if it cannot be measured."""
    medidor = MedidorCinematico(
        BASE.intervalo_velocidad_s, BASE.ventana_velocidad_s, BASE.visibilidad_min
    )
    velocidades = [
        v
        for instante, pose in secuencia
        if pose is not None and (v := medidor.medir(instante, pose).velocidad) is not None
    ]
    return max(velocidades) if velocidades and max(velocidades) > 0 else None


def eventos_video(secuencia: Secuencia, umbrales: Umbrales) -> list[EventoVideo]:
    clasificador = ClasificadorCinematico(umbrales)
    eventos: list[EventoVideo] = []
    for instante, pose in secuencia:
        eventos += [(e.tipo.value, e.instante) for e in clasificador.actualizar(instante, pose)]
    return eventos


def _correr(cambios: dict[str, float]) -> dict[str, list[EventoVideo]]:
    umbrales = BASE.model_copy(update=cambios)
    return {nombre: eventos_video(seq, umbrales) for nombre, seq in _POSES.items()}


# ------------------------------------------------------------------------------ metrics


def wilson(aciertos: int, total: int) -> tuple[float, float]:
    """95 % Wilson score interval of a proportion (Wilson, 1927)."""
    if total == 0:
        return (math.nan, math.nan)
    p = aciertos / total
    z2 = Z95**2
    centro = (p + z2 / (2 * total)) / (1 + z2 / total)
    margen = Z95 * math.sqrt(p * (1 - p) / total + z2 / (4 * total**2)) / (1 + z2 / total)
    return (max(0.0, centro - margen), min(1.0, centro + margen))


def inicios_urfd(datos: Path) -> dict[str, float]:
    """Instant (s) of the first frame labelled "falling" (0) in each URFD fall, at 30 fps."""
    inicios: dict[str, float] = {}
    ruta = datos / "urfd" / "urfall-cam0-falls.csv"
    if not ruta.exists():
        return inicios
    with ruta.open(encoding="utf-8") as archivo:
        for fila in csv.reader(archivo):
            nombre, cuadro, etiqueta = fila[0], int(fila[1]), int(fila[2])
            if etiqueta >= 0 and nombre not in inicios:
                inicios[nombre] = (cuadro - 1) / 30
    return inicios


@dataclass(frozen=True, slots=True)
class Resumen:
    vp: int
    fn: int
    vn: int
    fp: int
    recuperaciones_falsas: int
    caidas_urfd: int
    inestables_adl: int
    latencias: tuple[float, ...]
    confirmadas: int  # fall videos with a ``caida_confirmada``
    en_suelo_max: float  # longest time a detected fall is still seen after ``caida``, in s

    @property
    def sensibilidad(self) -> float:
        return self.vp / (self.vp + self.fn)

    @property
    def especificidad(self) -> float:
        return self.vn / (self.vn + self.fp)

    @property
    def exactitud(self) -> float:
        return (self.vp + self.vn) / (self.vp + self.fn + self.vn + self.fp)

    def ic(self, cual: str) -> tuple[float, float]:
        if cual == "sensibilidad":
            return wilson(self.vp, self.vp + self.fn)
        if cual == "especificidad":
            return wilson(self.vn, self.vn + self.fp)
        return wilson(self.vp + self.vn, self.vp + self.fn + self.vn + self.fp)


def resumir(
    videos: Sequence[Video], eventos: dict[str, list[EventoVideo]], inicios: dict[str, float]
) -> Resumen:
    caida = TipoEvento.CAIDA.value
    vp = fn = vn = fp = falsas = caidas_urfd = inestables = confirmadas = 0
    latencias: list[float] = []
    en_suelo = 0.0
    for v in videos:
        tipos = [t for t, _ in eventos[v.nombre]]
        detectada = caida in tipos
        if v.es_caida:
            vp, fn = vp + detectada, fn + (not detectada)
            confirmadas += TipoEvento.CAIDA_CONFIRMADA.value in tipos
            if detectada and v.nombre in DURACIONES:
                primera = next(i for t, i in eventos[v.nombre] if t == caida)
                en_suelo = max(en_suelo, DURACIONES[v.nombre] - primera)
            if v.dataset == "urfd":
                caidas_urfd += 1
                falsas += TipoEvento.RECUPERACION.value in tipos
                if detectada and v.nombre in inicios:
                    primera = next(i for t, i in eventos[v.nombre] if t == caida)
                    latencias.append(primera - inicios[v.nombre])
        else:
            vn, fp = vn + (not detectada), fp + detectada
            inestables += TipoEvento.MOVIMIENTO_INESTABLE.value in tipos
    return Resumen(
        vp, fn, vn, fp, falsas, caidas_urfd, inestables, tuple(latencias), confirmadas, en_suelo
    )


def es_seguro(r: Resumen, base: Resumen) -> bool:
    return (
        r.sensibilidad >= MINIMO
        and r.especificidad >= MINIMO
        and r.sensibilidad >= base.sensibilidad - CAIDA_MAXIMA - 1e-9
        and r.especificidad >= base.especificidad - CAIDA_MAXIMA - 1e-9
        and r.recuperaciones_falsas <= base.recuperaciones_falsas
    )


def rango_seguro(
    valores: list[float], resumenes: list[Resumen], defecto: float, base: Resumen
) -> tuple[float, float] | None:
    """Largest run of consecutive safe tested values that contains the default."""
    if defecto not in valores:
        return None
    i = valores.index(defecto)
    if not es_seguro(resumenes[i], base):
        return None
    desde = hasta = i
    while desde > 0 and es_seguro(resumenes[desde - 1], base):
        desde -= 1
    while hasta < len(valores) - 1 and es_seguro(resumenes[hasta + 1], base):
        hasta += 1
    return (valores[desde], valores[hasta])


# ------------------------------------------------------------------------------ report


def pct(x: float) -> str:
    return "—" if x != x else f"{x:.1%}"


def con_ic(r: Resumen, cual: str) -> str:
    bajo, alto = r.ic(cual)
    return f"{pct(getattr(r, cual))} ({bajo:.0%}–{alto:.0%})"


def latencia(r: Resumen) -> str:
    if not r.latencias:
        return "—"
    return f"{statistics.median(r.latencias):.2f} ({min(r.latencias):.2f}–{max(r.latencias):.2f})"


ENCABEZADO = [
    "| Value | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | "
    "FN | FP | False recoveries | Latency s, median (min–max) | Safe |",
    "|---|---|---|---|---|---|---|---|---|",
]


def fila(valor: str, r: Resumen, seguro: bool) -> str:
    return (
        f"| {valor} | {con_ic(r, 'sensibilidad')} | {con_ic(r, 'especificidad')} | "
        f"{con_ic(r, 'exactitud')} | {r.fn} | {r.fp} | "
        f"{r.recuperaciones_falsas}/{r.caidas_urfd} | {latencia(r)} | {'yes' if seguro else 'no'} |"
    )


def numero(x: float) -> str:
    return f"{x:g}"


def graficar(
    destino: Path,
    curvas: dict[str, tuple[list[float], list[Resumen]]],
    rangos: dict[str, tuple[float, float] | None],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nombres = list(BARRIDOS)
    figura, ejes = plt.subplots(3, 3, figsize=(12, 10), constrained_layout=True)
    for eje, nombre in zip(ejes.flat, nombres, strict=True):
        valores, resumenes = curvas[nombre]
        for cual, color, rotulo in (
            ("sensibilidad", "#c2410c", "Sensitivity"),
            ("especificidad", "#1d4ed8", "Specificity"),
        ):
            y = [getattr(r, cual) * 100 for r in resumenes]
            bajo = [r.ic(cual)[0] * 100 for r in resumenes]
            alto = [r.ic(cual)[1] * 100 for r in resumenes]
            eje.fill_between(valores, bajo, alto, color=color, alpha=0.12, linewidth=0)
            eje.plot(valores, y, marker="o", markersize=3.5, color=color, label=rotulo)
        if nombre == "persistencia_erguido_s":
            falsas = [100 * r.recuperaciones_falsas / max(r.caidas_urfd, 1) for r in resumenes]
            eje.plot(
                valores, falsas, marker="s", markersize=3.5, color="#7c3aed",
                label="False recoveries (% of URFD falls)",
            )  # fmt: skip
            eje.legend(fontsize=8, loc="center right")
        if nombre == "confirmacion_suelo_s":
            eje.text(
                0.5, 0.35, "Not testable: no clip shows a fall\nlong enough to confirm it",
                transform=eje.transAxes, ha="center", fontsize=9, color="#404040",
            )  # fmt: skip
        rango = rangos.get(nombre)
        if rango is not None and nombre != "confirmacion_suelo_s":
            eje.axvspan(rango[0], rango[1], color="#16a34a", alpha=0.10, label="Safe range")
        eje.axvline(getattr(BASE, nombre), color="#404040", linestyle="--", linewidth=1)
        eje.axhline(MINIMO * 100, color="#737373", linestyle=":", linewidth=1)
        if nombre == "velocidad_descenso_min":
            eje.set_xscale("log")
        eje.set_ylim(0, 100)
        eje.set_title(ROTULOS[nombre], fontsize=10)
        eje.set_ylabel("%")
        eje.grid(alpha=0.25)
    ejes.flat[0].legend(fontsize=8, loc="lower left")
    figura.suptitle(
        "Te Tengo classifier with R9 on URFD + CAUCAFall (170 videos, 8 fps, JPEG): one value "
        "at a time, 95 % Wilson bands; dashed = default, dotted = 75 %",
        fontsize=10,
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(destino, dpi=110)
    plt.close(figura)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--procesos", type=int, default=6)
    parser.add_argument("--salida", type=Path, default=RESULTADOS / "rangos")
    parser.add_argument("--grafico", type=Path, help="PNG with the one-at-a-time curves")
    parser.add_argument("--sin-rejilla", action="store_true", help="Skip the 3-value grid")
    args = parser.parse_args()

    videos = listar_videos(args.datos)
    variante = nombre_variante(args.modelo, "video", args.fps, True)
    faltan = [v.nombre for v in videos if not v.cache(variante).exists()]
    if not videos or faltan:
        print(
            f"Faltan las poses ({variante}). Ejecuta: scripts/descargar_datasets.py y "
            "scripts/evaluar.py extraer",
            file=sys.stderr,
        )
        return 1
    inicios = inicios_urfd(args.datos)
    _cargar(videos, variante)
    DURACIONES.update({n: seq[-1][0] for n, seq in _POSES.items() if seq})
    picos = {n: velocidad_pico(seq) for n, seq in _POSES.items()}

    ajustes: list[dict[str, float]] = [{}, SIN_R9]
    ajustes += [{n: v} for n, valores in BARRIDOS.items() for v in valores]
    combinaciones = [] if args.sin_rejilla else list(itertools.product(*REJILLA.values()))
    ajustes += [dict(zip(REJILLA, c, strict=True)) for c in combinaciones]
    print(f"{len(videos)} videos · {variante} · {len(ajustes)} ajustes")
    _POSES.clear()  # each worker loads its own copy
    with ProcessPoolExecutor(args.procesos, initializer=_cargar, initargs=(videos, variante)) as g:
        corridas = list(g.map(_correr, ajustes, chunksize=4))

    base = resumir(videos, corridas[0], inicios)
    sin_r9 = corridas[1]
    i = 2
    curvas: dict[str, tuple[list[float], list[Resumen]]] = {}
    for nombre, valores in BARRIDOS.items():
        curvas[nombre] = (
            valores,
            [resumir(videos, c, inicios) for c in corridas[i : i + len(valores)]],
        )
        i += len(valores)
    rejilla = [
        (dict(zip(REJILLA, c, strict=True)), resumir(videos, corridas[i + k], inicios))
        for k, c in enumerate(combinaciones)
    ]
    rangos = {
        nombre: rango_seguro(valores, resumenes, getattr(BASE, nombre), base)
        for nombre, (valores, resumenes) in curvas.items()
    }

    texto = [
        "# Safe ranges of the tunable values (US-45)",
        "",
        f"Videos: {len(videos)} · Poses: `{variante}` · Defaults: `{BASE.model_dump()}`",
        "",
        f"Criterion: sensitivity and specificity ≥ {MINIMO:.0%}, at most "
        f"{CAIDA_MAXIMA * 100:g} points below the default, and no more false recoveries than "
        "the default.",
        "",
        "## Default",
        "",
        *ENCABEZADO,
        fila("default", base, True),
        "",
        f"Fall videos with `caida_confirmada`: {base.confirmadas}. Longest time a detected fall "
        f"is still on video after `caida`: {base.en_suelo_max:.1f} s, so "
        "`confirmacion_suelo_s` cannot be tested with these clips.",
        "",
    ]
    filas_csv: list[dict[str, object]] = []
    for nombre, (valores, resumenes) in curvas.items():
        propuesto = PROPUESTOS.get(nombre)
        rango = rangos[nombre]
        texto += [
            f"## `{nombre}` (default {numero(getattr(BASE, nombre))})",
            "",
            f"Proposed: {propuesto[0]:g}–{propuesto[1]:g} · " if propuesto else "",
            "Measured safe range: "
            + (f"**{numero(rango[0])}–{numero(rango[1])}**" if rango else "**none**"),
            "",
            *ENCABEZADO,
        ]
        for valor, r in zip(valores, resumenes, strict=True):
            texto.append(fila(numero(valor), r, es_seguro(r, base)))
            filas_csv.append(_fila_csv(nombre, valor, r, es_seguro(r, base)))
        texto.append("")
    if rejilla:
        seguras = [(c, r) for c, r in rejilla if es_seguro(r, base)]
        texto += [
            "## Grid: speed × angle × ratio",
            "",
            f"{len(seguras)} of {len(rejilla)} combinations are safe.",
            "",
            "| Speed | Angle | Ratio | Sensitivity (95 % CI) | Specificity (95 % CI) | "
            "Accuracy | Safe |",
            "|---|---|---|---|---|---|---|",
        ]
        for c, r in rejilla:
            seguro = es_seguro(r, base)
            texto.append(
                f"| {numero(c['velocidad_descenso_min'])} | "
                f"{numero(c['angulo_linea_central_max_grados'])} | "
                f"{numero(c['razon_ancho_alto_min'])} | {con_ic(r, 'sensibilidad')} | "
                f"{con_ic(r, 'especificidad')} | {pct(r.exactitud)} | {'yes' if seguro else 'no'} |"
            )
            filas_csv.append(_fila_csv("rejilla:" + json.dumps(c), math.nan, r, seguro))
    if rejilla:
        texto += ["", *caja_conjunta(rejilla, rangos, base)]
    texto += ["", *antes_despues(videos, sin_r9, corridas[0], inicios, picos)]
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "rangos.md").write_text("\n".join(texto) + "\n", encoding="utf-8")
    with (args.salida / "rangos.csv").open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas_csv[0]))
        escritor.writeheader()
        escritor.writerows(filas_csv)
    if args.grafico:
        graficar(args.grafico, curvas, rangos)
    print("\n".join(texto))
    return 0


def antes_despues(
    videos: list[Video],
    sin: dict[str, list[EventoVideo]],
    con: dict[str, list[EventoVideo]],
    inicios: dict[str, float],
    picos: dict[str, float | None],
) -> list[str]:
    """Classifier without and with the slow-fall rule R9, overall and by subset."""
    caida = TipoEvento.CAIDA.value

    def detecciones(eventos: dict[str, list[EventoVideo]], grupo: list[Video]) -> int:
        return sum(caida in [t for t, _ in eventos[v.nombre]] for v in grupo)

    lenta = [
        v
        for v in videos
        if v.es_caida and (pico := picos[v.nombre]) is not None and pico < LENTA_MAX
    ]
    sin_medida = [v for v in videos if v.es_caida and picos[v.nombre] is None]
    grupos: list[tuple[str, list[Video]]] = [
        ("All falls", [v for v in videos if v.es_caida]),
        (f"Slow falls (peak speed < {LENTA_MAX:g} bodies/s)", lenta),
        ("Falls whose speed cannot be measured", sin_medida),
        ("URFD falls", [v for v in videos if v.dataset == "urfd" and v.es_caida]),
        ("CAUCAFall falls", [v for v in videos if v.dataset == "caucafall" and v.es_caida]),
        ("All daily activities (false alarms)", [v for v in videos if not v.es_caida]),
    ]
    actividades = sorted({(v.dataset, v.actividad) for v in videos if v.dataset == "caucafall"})
    grupos += [
        (f"CAUCAFall · {a}", [v for v in videos if (v.dataset, v.actividad) == (d, a)])
        for d, a in actividades
    ]
    tendidas = acostadas_urfd(videos)
    grupos += [
        ("URFD · lying down on the floor on purpose", [v for v in videos if v.nombre in tendidas]),
        (
            "URFD · other daily activities",
            [
                v
                for v in videos
                if v.dataset == "urfd" and not v.es_caida and v.nombre not in tendidas
            ],
        ),
    ]
    antes, despues = resumir(videos, sin, inicios), resumir(videos, con, inicios)
    lineas = [
        "## Slow-fall rule R9: without and with it",
        "",
        "| Setting | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | "
        "FN | FP | False recoveries | Latency s |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nombre, r in (("Without R9", antes), ("With R9 (defaults)", despues)):
        lineas.append(
            f"| {nombre} | {con_ic(r, 'sensibilidad')} | {con_ic(r, 'especificidad')} | "
            f"{con_ic(r, 'exactitud')} | {r.fn} | {r.fp} | "
            f"{r.recuperaciones_falsas}/{r.caidas_urfd} | {latencia(r)} |"
        )
    lineas += [
        "",
        "| Subset | Videos | `caida` without R9 | `caida` with R9 |",
        "|---|---|---|---|",
    ]
    lineas += [
        f"| {nombre} | {len(g)} | {detecciones(sin, g)} | {detecciones(con, g)} |"
        for nombre, g in grupos
    ]
    cambios = [
        f"- {v.dataset}/{v.nombre} ({'fall' if v.es_caida else 'daily activity'}, peak speed "
        + ("not measurable" if picos[v.nombre] is None else f"{picos[v.nombre]:.2f}")
        + f"): {'detected' if v.es_caida else 'false alarm'} only with R9"
        for v in videos
        if detecciones(sin, [v]) != detecciones(con, [v])
    ]
    return [*lineas, "", "Videos that change:", "", *(cambios or ["- none"])]


def acostadas_urfd(videos: list[Video], datos: Path = Path("datos")) -> set[str]:
    """URFD daily activities that end lying on the floor on purpose (label 1 in its CSV)."""
    ruta = datos / "urfd" / "urfall-cam0-adls.csv"
    if not ruta.exists():
        return set()
    with ruta.open(encoding="utf-8") as archivo:
        return {fila[0] for fila in csv.reader(archivo) if fila[2] == "1"}


def caja_conjunta(
    rejilla: list[tuple[dict[str, float], Resumen]],
    rangos: dict[str, tuple[float, float] | None],
    base: Resumen,
) -> list[str]:
    """Checks the grid combinations inside the one-at-a-time safe ranges."""
    dentro = [
        (c, r)
        for c, r in rejilla
        if all(
            (rango := rangos.get(n)) is not None and rango[0] <= x <= rango[1] for n, x in c.items()
        )
    ]
    inseguras = [(c, r) for c, r in dentro if not es_seguro(r, base)]
    lineas = [
        "### Combinations inside the one-at-a-time safe ranges",
        "",
        f"{len(dentro) - len(inseguras)} of {len(dentro)} are safe. Unsafe ones:",
        "",
    ]
    lineas += [
        f"- v = {numero(c['velocidad_descenso_min'])}, "
        f"θ = {numero(c['angulo_linea_central_max_grados'])}, "
        f"P = {numero(c['razon_ancho_alto_min'])}: sensitivity {pct(r.sensibilidad)}, "
        f"specificity {pct(r.especificidad)}, false recoveries {r.recuperaciones_falsas}"
        for c, r in inseguras
    ] or ["- none"]
    return [*lineas, "", *caja_mayor(rejilla, base)]


def caja_mayor(rejilla: list[tuple[dict[str, float], Resumen]], base: Resumen) -> list[str]:
    """Largest box of grid values around the defaults in which every combination is safe.

    The installer can change the three values at once, so the range of each one must be safe
    whatever the other two are. Ties keep the first box found (widest speed range first).
    """
    seguro = {tuple(c.values()): es_seguro(r, base) for c, r in rejilla}
    ejes = list(REJILLA.values())
    centro = [eje.index(getattr(BASE, n)) for n, eje in zip(REJILLA, ejes, strict=True)]
    intervalos = [
        [(a, b) for a in range(c + 1) for b in range(c, len(eje))]
        for eje, c in zip(ejes, centro, strict=True)
    ]
    mejor: tuple[int, list[tuple[int, int]]] | None = None
    for caja in itertools.product(*intervalos):
        tamano = math.prod(b - a + 1 for a, b in caja)
        if mejor is not None and tamano <= mejor[0]:
            continue
        indices = itertools.product(*(range(a, b + 1) for a, b in caja))
        if all(seguro[tuple(e[i] for e, i in zip(ejes, idx, strict=True))] for idx in indices):
            mejor = (tamano, list(caja))
    if mejor is None:
        return ["### Largest jointly safe box", "", "- none"]
    return [
        "### Largest jointly safe box",
        "",
        *(
            f"- `{n}`: {numero(eje[a])}–{numero(eje[b])}"
            for n, eje, (a, b) in zip(REJILLA, ejes, mejor[1], strict=True)
        ),
    ]


def _fila_csv(nombre: str, valor: float, r: Resumen, seguro: bool) -> dict[str, object]:
    return {
        "valor": nombre,
        "x": valor,
        "vp": r.vp,
        "fn": r.fn,
        "vn": r.vn,
        "fp": r.fp,
        "sensibilidad": round(r.sensibilidad, 4),
        "especificidad": round(r.especificidad, 4),
        "exactitud": round(r.exactitud, 4),
        "recuperaciones_falsas": r.recuperaciones_falsas,
        "inestables_adl": r.inestables_adl,
        "confirmadas": r.confirmadas,
        "latencia_mediana_s": round(statistics.median(r.latencias), 3) if r.latencias else "",
        "seguro": seguro,
    }


if __name__ == "__main__":
    sys.exit(main())
