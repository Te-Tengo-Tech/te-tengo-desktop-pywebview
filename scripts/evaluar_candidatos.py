"""Nested evaluation of candidate classifier changes on URFD + CAUCAFall.

Every candidate is a set of fixed ``Umbrales`` changes (the structural part) plus a grid of
thresholds. Each threshold is chosen INSIDE every training fold (maximum Youden index of the
training groups; ties: lowest speed, then the most conservative value of the other ones) and
applied to the held-out group, never chosen on it. The script reports, per candidate:

* leave-one-group-out (11 groups) sensitivity, specificity and accuracy with 95 % Wilson CIs;
* cross-dataset URFD → CAUCAFall and CAUCAFall → URFD;
* false recoveries in URFD falls, URFD detection latency, per-activity false alarms and misses;
* McNemar's exact test on paired per-video outcomes against the baseline;
* the number of configurations evaluated, to expose the multiple-comparison risk.

It also runs a fully nested selection, in which each training fold chooses the candidate
itself as well as its thresholds, which estimates the whole selection procedure honestly.

Examples:
    uv run python scripts/evaluar_candidatos.py   # writes resultados/candidatos/
    uv run python scripts/evaluar_candidatos.py --datos ../otro/datos --candidatos base
"""

import argparse
import itertools
import json
import math
import statistics
import sys
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from barrer_rangos import acostadas_urfd, inicios_urfd, wilson
from evaluar import RESULTADOS, Secuencia, Video, cargar_poses, listar_videos, nombre_variante

from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

VELOCIDADES = [round(0.01 * i, 2) for i in range(1, 101)]  # the baseline grid (validation.md)

# name -> (fixed changes, grid of the other thresholds: name -> values, most conservative last)
PERDIDA = [round(0.1 * i, 1) for i in range(1, 11)]
# Published values last, so that ties keep them (the most conservative choice).
ANGULOS = [35.0, 55.0, 40.0, 50.0, 45.0]
RAZONES = [0.8, 1.2, 0.9, 1.1, 1.0]
C1 = {"velocidad_con_caderas": True}
C1B = {"velocidad_con_un_tobillo": True}
C2 = {"inclinacion_por_escorzo": True}
C3 = {"velocidad_perdida_min": PERDIDA}
C4 = {"angulo_linea_central_max_grados": ANGULOS, "razon_ancho_alto_min": RAZONES}
CANDIDATOS: dict[str, tuple[dict[str, Any], dict[str, list[Any]]]] = {
    "base": ({}, {}),
    "C1": (C1, {}),
    "C2": (C2, {}),
    "C3": ({}, C3),
    "C1+C2": (C1 | C2, {}),
    "C1+C3": (C1, C3),
    "C2+C3": (C2, C3),
    "C1+C2+C3": (C1 | C2, C3),
    "C4": ({}, C4),
    "C1+C4": (C1, C4),
    # Post-hoc (designed after round 1; see docs/validation.md section 6).
    "C1b": (C1B, {}),
    "C1b+C2": (C1B | C2, {}),
    "C1b+C3": (C1B, C3),
}

EventoVideo = tuple[str, float]
_POSES: dict[str, Secuencia] = {}


def _cargar(videos: list[Video], variante: str) -> None:
    _POSES.update({v.nombre: cargar_poses(v, variante) for v in videos})


def _correr(cambios: dict[str, Any]) -> dict[str, list[EventoVideo]]:
    umbrales = Umbrales(velocidad_descenso_min=0.01).model_copy(update=cambios)
    salida: dict[str, list[EventoVideo]] = {}
    for nombre, secuencia in _POSES.items():
        clasificador = ClasificadorCinematico(umbrales)
        eventos: list[EventoVideo] = []
        for instante, pose in secuencia:
            eventos += [(e.tipo.value, e.instante) for e in clasificador.actualizar(instante, pose)]
        salida[nombre] = eventos
    return salida


def detecto(eventos: list[EventoVideo]) -> bool:
    return any(t == TipoEvento.CAIDA.value for t, _ in eventos)


@dataclass(frozen=True, slots=True)
class Cuenta:
    vp: int
    fn: int
    vn: int
    fp: int

    @property
    def sens(self) -> float:
        return self.vp / (self.vp + self.fn) if self.vp + self.fn else math.nan

    @property
    def espec(self) -> float:
        return self.vn / (self.vn + self.fp) if self.vn + self.fp else math.nan

    @property
    def exact(self) -> float:
        return (self.vp + self.vn) / (self.vp + self.fn + self.vn + self.fp)

    @property
    def youden(self) -> float:
        s = 0.0 if math.isnan(self.sens) else self.sens
        e = 0.0 if math.isnan(self.espec) else self.espec
        return s + e - 1


def contar(videos: Sequence[Video], salida: dict[str, bool]) -> Cuenta:
    vp = sum(1 for v in videos if v.es_caida and salida[v.nombre])
    fn = sum(1 for v in videos if v.es_caida and not salida[v.nombre])
    vn = sum(1 for v in videos if not v.es_caida and not salida[v.nombre])
    fp = sum(1 for v in videos if not v.es_caida and salida[v.nombre])
    return Cuenta(vp, fn, vn, fp)


Ajuste = tuple[tuple[str, Any], ...]  # hashable configuration


def ajustes_de(fijos: dict[str, Any], rejilla: dict[str, list[Any]]) -> list[Ajuste]:
    nombres = ["velocidad_descenso_min", *rejilla]
    valores = [VELOCIDADES, *rejilla.values()]
    return [
        tuple(sorted({**fijos, **dict(zip(nombres, c, strict=True))}.items()))
        for c in itertools.product(*valores)
    ]


def clave_desempate(ajuste: Ajuste, rejilla: dict[str, list[Any]]) -> tuple[float, ...]:
    """Ties: lowest speed (as the baseline), then the most conservative value of the others."""
    d = dict(ajuste)
    return (-d["velocidad_descenso_min"], *(rejilla[n].index(d[n]) for n in rejilla))


def elegir(
    entrenamiento: Sequence[Video],
    ajustes: list[Ajuste],
    corridas: dict[Ajuste, dict[str, list[EventoVideo]]],
    rejillas: dict[Ajuste, dict[str, list[Any]]],
) -> Ajuste:
    def puntaje(a: Ajuste) -> tuple[float, ...]:
        salida = {v.nombre: detecto(corridas[a][v.nombre]) for v in entrenamiento}
        return (round(contar(entrenamiento, salida).youden, 6), *clave_desempate(a, rejillas[a]))

    return max(ajustes, key=puntaje)


@dataclass
class Resultado:
    nombre: str
    salida: dict[str, bool]  # per video, LOGO
    eventos: dict[str, list[EventoVideo]]  # per video, with the fold's thresholds
    elegidos: dict[str, Ajuste]  # per group
    cruzado: dict[str, tuple[Ajuste, Cuenta]]
    configuraciones: int


def evaluar_candidato(
    nombre: str,
    ajustes: list[Ajuste],
    corridas: dict[Ajuste, dict[str, list[EventoVideo]]],
    rejillas: dict[Ajuste, dict[str, list[Any]]],
    videos: list[Video],
) -> Resultado:
    salida: dict[str, bool] = {}
    eventos: dict[str, list[EventoVideo]] = {}
    elegidos: dict[str, Ajuste] = {}
    for grupo in sorted({v.grupo for v in videos}):
        entrenamiento = [v for v in videos if v.grupo != grupo]
        a = elegir(entrenamiento, ajustes, corridas, rejillas)
        elegidos[grupo] = a
        for v in videos:
            if v.grupo == grupo:
                eventos[v.nombre] = corridas[a][v.nombre]
                salida[v.nombre] = detecto(eventos[v.nombre])
    cruzado: dict[str, tuple[Ajuste, Cuenta]] = {}
    for rotulo, cal, prueba in (
        ("URFD → CAUCAFall", "urfd", "caucafall"),
        ("CAUCAFall → URFD", "caucafall", "urfd"),
    ):
        a = elegir([v for v in videos if v.dataset == cal], ajustes, corridas, rejillas)
        test = [v for v in videos if v.dataset == prueba]
        cruzado[rotulo] = (
            a,
            contar(test, {v.nombre: detecto(corridas[a][v.nombre]) for v in test}),
        )
    return Resultado(nombre, salida, eventos, elegidos, cruzado, len(ajustes))


# ------------------------------------------------------------------------------ statistics


def mcnemar_exacto(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value (binomial test of the discordant pairs, p = 0.5)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cola: float = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * cola)


def comparar(videos: list[Video], base: dict[str, bool], otro: dict[str, bool]) -> str:
    """Discordant pairs on correctness: b = only the baseline right, c = only the candidate."""
    acierto_b = {v.nombre: base[v.nombre] == v.es_caida for v in videos}
    acierto_c = {v.nombre: otro[v.nombre] == v.es_caida for v in videos}
    b = sum(1 for v in videos if acierto_b[v.nombre] and not acierto_c[v.nombre])
    c = sum(1 for v in videos if acierto_c[v.nombre] and not acierto_b[v.nombre])
    caidas = [v for v in videos if v.es_caida]
    bs = sum(1 for v in caidas if base[v.nombre] and not otro[v.nombre])
    cs = sum(1 for v in caidas if otro[v.nombre] and not base[v.nombre])
    return (
        f"all videos b={b}, c={c}, p={mcnemar_exacto(b, c):.3f}; "
        f"falls only b={bs}, c={cs}, p={mcnemar_exacto(bs, cs):.3f}"
    )


# ------------------------------------------------------------------------------ report


def pct_ic(aciertos: int, total: int) -> str:
    if total == 0:
        return "—"
    bajo, alto = wilson(aciertos, total)
    return f"{aciertos / total:.1%} ({bajo:.1%}–{alto:.1%})"


def corto(a: Ajuste, fijos: dict[str, Any]) -> str:
    return ", ".join(f"{n}={v}" for n, v in a if n not in fijos) or "—"


def informe(
    r: Resultado,
    videos: list[Video],
    base: Resultado | None,
    inicios: dict[str, float],
    tendidas: set[str],
    fijos: dict[str, Any],
) -> list[str]:
    total = contar(videos, r.salida)
    urfd = [v for v in videos if v.dataset == "urfd"]
    cauca = [v for v in videos if v.dataset == "caucafall"]
    cu, cc = contar(urfd, r.salida), contar(cauca, r.salida)
    caidas_urfd = [v for v in urfd if v.es_caida]
    falsas = sum(1 for v in caidas_urfd if any(t == "recuperacion" for t, _ in r.eventos[v.nombre]))
    lat = [
        next(i for t, i in r.eventos[v.nombre] if t == "caida") - inicios[v.nombre]
        for v in caidas_urfd
        if r.salida[v.nombre] and v.nombre in inicios
    ]
    lineas = [
        f"## {r.nombre}",
        "",
        f"Configurations evaluated: {r.configuraciones}",
        "",
        "| Set | Sensitivity (95 % CI) | Specificity (95 % CI) | Accuracy (95 % CI) | FN | FP |",
        "|---|---|---|---|---|---|",
    ]
    for rotulo, c in (("LOGO total", total), ("URFD", cu), ("CAUCAFall", cc)):
        lineas.append(
            f"| {rotulo} | {pct_ic(c.vp, c.vp + c.fn)} | {pct_ic(c.vn, c.vn + c.fp)} | "
            f"{pct_ic(c.vp + c.vn, c.vp + c.fn + c.vn + c.fp)} | {c.fn} | {c.fp} |"
        )
    for rotulo, (a, c) in r.cruzado.items():
        lineas.append(
            f"| {rotulo} ({corto(a, fijos)}) | {pct_ic(c.vp, c.vp + c.fn)} | "
            f"{pct_ic(c.vn, c.vn + c.fp)} | {pct_ic(c.vp + c.vn, c.vp + c.fn + c.vn + c.fp)} | "
            f"{c.fn} | {c.fp} |"
        )
    lineas += [
        "",
        f"- False recoveries: {falsas}/{len(caidas_urfd)} URFD falls",
        "- URFD latency (s from the first 'falling' frame): "
        + (
            f"median {statistics.median(lat):.2f}, "
            f"range {min(lat):.2f}–{max(lat):.2f} (n={len(lat)})"
            if lat
            else "—"
        ),
        "- Thresholds per fold: "
        + "; ".join(f"{g}: {corto(a, fijos)}" for g, a in r.elegidos.items()),
    ]
    if base is not None:
        lineas.append(f"- McNemar vs baseline: {comparar(videos, base.salida, r.salida)}")
    actividades: dict[str, list[Video]] = {}
    for v in videos:
        if v.dataset == "urfd":
            clave = (
                "URFD · fall"
                if v.es_caida
                else (
                    "URFD · lying on the floor on purpose"
                    if v.nombre in tendidas
                    else "URFD · other ADL"
                )
            )
        else:
            clave = f"CAUCAFall · {v.actividad}"
        actividades.setdefault(clave, []).append(v)
    lineas += ["", "| Activity | Videos | `caida` |" + (" `caida` baseline |" if base else ""),
               "|---|---|---|" + ("---|" if base else "")]  # fmt: skip
    for clave, grupo in sorted(actividades.items()):
        n = sum(r.salida[v.nombre] for v in grupo)
        extra = f" {sum(base.salida[v.nombre] for v in grupo)} |" if base else ""
        lineas.append(f"| {clave} | {len(grupo)} | {n} |{extra}")
    if base is not None:
        cambios = [
            f"- {v.nombre} ({'fall' if v.es_caida else 'ADL'}): "
            f"{'detected' if r.salida[v.nombre] else 'not detected'} "
            f"(baseline {'detected' if base.salida[v.nombre] else 'not detected'})"
            for v in videos
            if r.salida[v.nombre] != base.salida[v.nombre]
        ]
        lineas += ["", "Videos that change against the baseline:", "", *(cambios or ["- none"])]
    return [*lineas, ""]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--procesos", type=int, default=12)
    parser.add_argument("--salida", type=Path, default=RESULTADOS / "candidatos")
    parser.add_argument("--candidatos", nargs="*", help="Subset of candidate names")
    args = parser.parse_args()

    videos = [v for v in listar_videos(args.datos) if v.dataset in ("urfd", "caucafall")]
    variante = nombre_variante(args.modelo, "video", args.fps, True)
    if not videos or any(not v.cache(variante).exists() for v in videos):
        print(f"Faltan las poses ({variante}): scripts/evaluar.py extraer", file=sys.stderr)
        return 1
    nombres = args.candidatos or list(CANDIDATOS)
    rejillas: dict[Ajuste, dict[str, list[Any]]] = {}
    por_candidato: dict[str, list[Ajuste]] = {}
    for nombre in nombres:
        fijos, rejilla = CANDIDATOS[nombre]
        por_candidato[nombre] = ajustes_de(fijos, rejilla)
        for a in por_candidato[nombre]:
            rejillas[a] = rejilla
    todos = list(rejillas)
    print(f"{len(videos)} videos · {variante} · {len(todos)} configurations", flush=True)
    with ProcessPoolExecutor(
        args.procesos, initializer=_cargar, initargs=(videos, variante)
    ) as grupo:
        salidas = list(grupo.map(_correr, [dict(a) for a in todos], chunksize=8))
        corridas = dict(zip(todos, salidas, strict=True))

    inicios, tendidas = inicios_urfd(args.datos), acostadas_urfd(videos, args.datos)
    resultados = {
        n: evaluar_candidato(n, por_candidato[n], corridas, rejillas, videos) for n in nombres
    }
    base = resultados.get("base")
    texto = [
        "# Candidate classifier changes: nested evaluation",
        "",
        f"Videos: {len(videos)} · Poses: `{variante}` · Distinct configurations evaluated: "
        f"{len(todos)} · Candidates: {len(nombres)}",
        "",
    ]
    for n in nombres:
        texto += informe(
            resultados[n], videos, None if n == "base" else base, inicios, tendidas,
            CANDIDATOS[n][0],
        )  # fmt: skip

    # Fully nested: every training fold also chooses the candidate.
    salida: dict[str, bool] = {}
    elegidos: list[str] = []
    for g in sorted({v.grupo for v in videos}):
        entrenamiento = [v for v in videos if v.grupo != g]
        a = elegir(entrenamiento, todos, corridas, rejillas)
        dueno = next(n for n in nombres if a in por_candidato[n])
        elegidos.append(f"{g}: {dueno} ({corto(a, {})})")
        for v in videos:
            if v.grupo == g:
                salida[v.nombre] = detecto(corridas[a][v.nombre])
    c = contar(videos, salida)
    texto += [
        "## Fully nested selection (each fold also chooses the candidate)",
        "",
        f"Sensitivity {pct_ic(c.vp, c.vp + c.fn)} · specificity {pct_ic(c.vn, c.vn + c.fp)} · "
        f"accuracy {pct_ic(c.vp + c.vn, c.vp + c.fn + c.vn + c.fp)}",
        "",
        *(f"- {e}" for e in elegidos),
    ]
    if base is not None:
        texto += ["", f"- McNemar vs baseline: {comparar(videos, base.salida, salida)}"]
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "candidatos.md").write_text("\n".join(texto) + "\n", encoding="utf-8")
    (args.salida / "por_video.json").write_text(
        json.dumps({n: r.salida for n, r in resultados.items()}, indent=1), encoding="utf-8"
    )
    print("\n".join(texto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
