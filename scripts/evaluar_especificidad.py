"""Specificity study of the classifier (ADR 0012): candidates S1–S4, nested and held out.

Three stages, in the order fixed by ADR 0012:

* ``desarrollo``: URFD + CAUCAFall only. Every threshold (the speed ``v`` and the candidate's
  own) is chosen inside each training fold by the maximum Youden index and applied to the
  held-out group (leave one group out, 11 groups); also cross-dataset, a fully nested selection
  (each fold also picks the candidate), exact McNemar against the baseline, false recoveries,
  URFD latency and per-activity false alarms.
* ``holdout``: each finalist is chosen on all 170 development videos, frozen, and run **once**
  on GMDCSA24, UP-Fall and MCFD (units of ADR 0011: recordings, MCFD fall windows and labelled
  non-fall periods, MCFD false alarms per hour).
* ``lodo``: secondary, leave one dataset out over the five datasets, as in ADR 0011, for the
  finalists and their combinations (it uses the hold-out sets as training folds).

S1 holds the ``caida`` for D s. Many clips end before the hold does: a hold still running at the
end of a clip is counted as a ``caida`` (it was not withdrawn) and reported as censored.

Examples:
    uv run python scripts/evaluar_especificidad.py desarrollo
    uv run python scripts/evaluar_especificidad.py holdout --familias S1 S1+S3
    uv run python scripts/evaluar_especificidad.py lodo --familias S1 S1+F3
"""

import argparse
import itertools
import json
import math
import statistics
import sys
from collections import defaultdict
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from barrer_rangos import acostadas_urfd, inicios_urfd, wilson
from evaluar import (
    DATASETS,
    DATASETS_VALIDACION,
    RESULTADOS,
    Secuencia,
    Video,
    cargar_poses,
    listar_videos,
    nombre_variante,
)
from evaluar_candidatos import mcnemar_exacto
from evaluar_lodo import Unidad, alarma, extras, unidades
from evaluar_multicamara import Ventanas, ventanas_mcfd

from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

CAIDA = TipoEvento.CAIDA.value
RECUPERACION = TipoEvento.RECUPERACION.value
CENSURADA = "censurada"  # pseudo-event: an S1 hold still running when the clip ended
HOLDOUT = ("gmdcsa24", "upfall", "mcfd")
VELOCIDADES = [round(0.01 * i, 2) for i in range(1, 101)]
SENSIBILIDAD_MIN = 0.90

Valor = float | bool
Ajuste = tuple[tuple[str, Valor], ...]  # hashable configuration
EventoVideo = tuple[str, float]
Eventos = dict[str, list[EventoVideo]]

# Grids: the most conservative value (closest to the shipped classifier) LAST, so that ties keep
# it. ADR 0012.
S1: dict[str, list[Valor]] = {
    "retencion_caida_s": [5.0, 3.0, 2.0],
    "retencion_erguido_s": [0.5, 1.0],
    "retencion_exige_visibles": [False, True],
}
F3: tuple[dict[str, Valor], dict[str, list[Valor]]] = (
    {"erguido_previo_exige_visibles": False},
    {"erguido_previo_caida_s": [1.0, 2.0, 3.0, 5.0, 10.0]},
)
S3: dict[str, Valor] = {"ruta_sin_tobillos": True}
S4: dict[str, Valor] = {"salto_identidad_max": 1.0}

# name -> (fixed changes, grid of the other thresholds)
FAMILIAS: dict[str, tuple[dict[str, Valor], dict[str, list[Valor]]]] = {
    "base": ({}, {}),
    "S1": ({}, S1),
    "S2 (F3)": F3,
    "S3": (S3, {}),
    "S4": (S4, {}),
}
# Combinations, defined after the development round (ADR 0012, Results): the finalists S1 and S4
# with each other and with F3, and S1 + S3 as an exploratory (post hoc, not pre-registered) row.
COMBINACIONES: dict[str, tuple[dict[str, Valor], dict[str, list[Valor]]]] = {
    "S1+S4": (S4, S1),
    "S1+F3": (F3[0], S1 | F3[1]),
    "S1+S4+F3": (S4 | F3[0], S1 | F3[1]),
    "S1+S3 (exploratory)": (S3, S1),
}
TODAS = FAMILIAS | COMBINACIONES


def ajustes_de(nombre: str) -> list[Ajuste]:
    fijos, rejilla = TODAS[nombre]
    nombres = ["velocidad_descenso_min", *rejilla]
    valores: list[list[Valor]] = [list(VELOCIDADES), *rejilla.values()]
    return [
        tuple(sorted({**fijos, **dict(zip(nombres, c, strict=True))}.items()))
        for c in itertools.product(*valores)
    ]


def desempate(nombre: str, ajuste: Ajuste) -> tuple[float, ...]:
    """Ties: the lowest speed, then the most conservative value of every other threshold."""
    rejilla = TODAS[nombre][1]
    d = dict(ajuste)
    return (-float(d["velocidad_descenso_min"]), *(rejilla[n].index(d[n]) for n in rejilla))


def corto(nombre: str, a: Ajuste) -> str:
    rejilla = TODAS[nombre][1]
    abreviaturas = {
        "velocidad_descenso_min": "v",
        "retencion_caida_s": "D",
        "retencion_erguido_s": "U",
        "retencion_exige_visibles": "A6",
        "erguido_previo_caida_s": "T",
    }
    d = dict(a)
    return ", ".join(
        f"{abreviaturas.get(n, n)}={d[n]:g}"
        if not isinstance(d[n], bool)
        else f"{abreviaturas.get(n, n)}={'yes' if d[n] else 'no'}"
        for n in ["velocidad_descenso_min", *rejilla]
    )


# ------------------------------------------------------------------------------ replay


def replay(secuencia: Secuencia, umbrales: Umbrales) -> list[EventoVideo]:
    """Events of one recording; an S1 hold running at the end counts as a ``caida``."""
    c = ClasificadorCinematico(umbrales)
    eventos: list[EventoVideo] = []
    instante = 0.0
    for instante, pose in secuencia:
        eventos += [(e.tipo.value, e.instante) for e in c.actualizar(instante, pose)]
    if c.caida_retenida:
        eventos += [(CAIDA, instante), (CENSURADA, instante)]
    return eventos


_POSES: dict[str, Secuencia] = {}


def _iniciar(videos: list[Video], variante: str) -> None:
    _POSES.update({v.nombre: cargar_poses(v, variante) for v in videos})


def _correr(ajuste: Ajuste) -> Eventos:
    umbrales = Umbrales.model_validate(dict(ajuste))
    return {n: replay(s, umbrales) for n, s in _POSES.items()}


def correr_todo(
    videos: list[Video], variante: str, ajustes: Sequence[Ajuste], procesos: int
) -> dict[Ajuste, Eventos]:
    with ProcessPoolExecutor(procesos, initializer=_iniciar, initargs=(videos, variante)) as pool:
        salidas = list(pool.map(_correr, ajustes, chunksize=4))
    return dict(zip(ajustes, salidas, strict=True))


def detecto(eventos: list[EventoVideo]) -> bool:
    return any(t == CAIDA for t, _ in eventos)


# ------------------------------------------------------------------------------ metrics


@dataclass(frozen=True, slots=True)
class Cuenta:
    vp: int
    p: int
    vn: int
    n: int

    @property
    def sens(self) -> float:
        return self.vp / self.p if self.p else math.nan

    @property
    def spec(self) -> float:
        return self.vn / self.n if self.n else math.nan

    @property
    def youden(self) -> float:
        s = 0.0 if math.isnan(self.sens) else self.sens
        e = 0.0 if math.isnan(self.spec) else self.spec
        return s + e - 1


def contar(videos: Sequence[Video], salida: dict[str, bool]) -> Cuenta:
    return Cuenta(
        sum(1 for v in videos if v.es_caida and salida[v.nombre]),
        sum(1 for v in videos if v.es_caida),
        sum(1 for v in videos if not v.es_caida and not salida[v.nombre]),
        sum(1 for v in videos if not v.es_caida),
    )


def con_ic(aciertos: int, total: int) -> str:
    if not total:
        return "—"
    a, b = wilson(aciertos, total)
    return f"{100 * aciertos / total:.1f} % ({100 * a:.1f}–{100 * b:.1f})"


def pct(x: float) -> str:
    return "—" if math.isnan(x) else f"{100 * x:.1f} %"


def mcnemar(
    pares: Sequence[tuple[bool, bool, bool]],
) -> tuple[int, int, float]:
    """(truth, baseline output, other output) → b = only the baseline right, c = only the other."""
    b = sum(1 for y, x, z in pares if x == y and z != y)
    c = sum(1 for y, x, z in pares if z == y and x != y)
    return b, c, mcnemar_exacto(b, c)


def elegir(
    familia: str,
    ajustes: Sequence[Ajuste],
    corridas: dict[Ajuste, Eventos],
    entrenamiento: Sequence[Video],
) -> Ajuste:
    def clave(a: Ajuste) -> tuple[float, ...]:
        salida = {v.nombre: detecto(corridas[a][v.nombre]) for v in entrenamiento}
        return (round(contar(entrenamiento, salida).youden, 9), *desempate(familia, a))

    return max(ajustes, key=clave)


# ------------------------------------------------------------------------------ development


@dataclass
class Resultado:
    nombre: str
    salida: dict[str, bool]
    eventos: Eventos
    elegidos: dict[str, Ajuste]
    cruzado: dict[str, tuple[Ajuste, Cuenta]]
    final: Ajuste  # chosen on all development videos (frozen for the hold-out)
    configuraciones: int


def evaluar_familia(
    nombre: str, ajustes: list[Ajuste], corridas: dict[Ajuste, Eventos], videos: list[Video]
) -> Resultado:
    salida: dict[str, bool] = {}
    eventos: Eventos = {}
    elegidos: dict[str, Ajuste] = {}
    for grupo in sorted({v.grupo for v in videos}):
        a = elegir(nombre, ajustes, corridas, [v for v in videos if v.grupo != grupo])
        elegidos[grupo] = a
        for v in videos:
            if v.grupo == grupo:
                eventos[v.nombre] = corridas[a][v.nombre]
                salida[v.nombre] = detecto(eventos[v.nombre])
    cruzado = {}
    for rotulo, cal, prueba in (
        ("URFD → CAUCAFall", "urfd", "caucafall"),
        ("CAUCAFall → URFD", "caucafall", "urfd"),
    ):
        a = elegir(nombre, ajustes, corridas, [v for v in videos if v.dataset == cal])
        test = [v for v in videos if v.dataset == prueba]
        cruzado[rotulo] = (
            a,
            contar(test, {v.nombre: detecto(corridas[a][v.nombre]) for v in test}),
        )
    final = elegir(nombre, ajustes, corridas, videos)
    return Resultado(nombre, salida, eventos, elegidos, cruzado, final, len(ajustes))


def actividad_dev(v: Video, tendidas: set[str]) -> str:
    if v.dataset == "urfd":
        if v.es_caida:
            return "URFD · fall"
        return (
            "URFD · lying on the floor on purpose" if v.nombre in tendidas else "URFD · other ADL"
        )
    return f"CAUCAFall · {v.actividad.replace('_', ' ')}"


def informe_desarrollo(
    resultados: dict[str, Resultado],
    videos: list[Video],
    inicios: dict[str, float],
    tendidas: set[str],
    anidado: tuple[dict[str, bool], list[str]],
    total_configuraciones: int,
) -> list[str]:
    base = resultados["base"]
    urfd = [v for v in videos if v.dataset == "urfd"]
    cauca = [v for v in videos if v.dataset == "caucafall"]
    lineas = [
        "# Specificity study (ADR 0012): development data, nested",
        "",
        f"URFD + CAUCAFall, {len(videos)} videos, poses `lite-video-8fps-jpeg`. Thresholds chosen "
        "inside each training fold (maximum Youden; ties: lowest v, then the most conservative "
        f"value). Distinct configurations evaluated: **{total_configuraciones}**. Intervals: 95 % "
        "Wilson. McNemar: exact, two-sided, on correctness of paired videos (b = only the "
        "baseline right, c = only the candidate right). S1 holds still running at the end of a "
        "clip count as `caida` (censored).",
        "",
        "## Summary (leave one group out)",
        "",
        "| Rule set | Configs | Sensitivity | Specificity | FN | FP | URFD sens / spec | "
        "CAUCAFall sens / spec | McNemar all · falls · ADL | False recoveries | Censored TP / FP | "
        "URFD latency median (range), n |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for nombre, r in resultados.items():
        c = contar(videos, r.salida)
        cu, cc = contar(urfd, r.salida), contar(cauca, r.salida)
        if nombre == "base":
            mc = "—"
        else:
            partes = []
            for grupo in (
                videos,
                [v for v in videos if v.es_caida],
                [v for v in videos if not v.es_caida],
            ):
                b, cc_, p = mcnemar(
                    [(v.es_caida, base.salida[v.nombre], r.salida[v.nombre]) for v in grupo]
                )
                partes.append(f"{b}/{cc_} p={p:.3f}")
            mc = " · ".join(partes)
        falsas = sum(
            1 for v in urfd if v.es_caida and any(t == RECUPERACION for t, _ in r.eventos[v.nombre])
        )
        cens_tp = sum(
            1
            for v in videos
            if v.es_caida and r.salida[v.nombre] and _solo_censurada(r.eventos[v.nombre])
        )
        cens_fp = sum(
            1
            for v in videos
            if not v.es_caida and r.salida[v.nombre] and _solo_censurada(r.eventos[v.nombre])
        )
        lat = [
            next(i for t, i in r.eventos[v.nombre] if t == CAIDA) - inicios[v.nombre]
            for v in urfd
            if v.es_caida and r.salida[v.nombre] and v.nombre in inicios
        ]
        lat_txt = (
            f"{statistics.median(lat):.2f} s ({min(lat):.2f}–{max(lat):.2f}), {len(lat)}"
            if lat
            else "—"
        )
        lineas.append(
            f"| **{nombre}** | {r.configuraciones} | {con_ic(c.vp, c.p)} | {con_ic(c.vn, c.n)} | "
            f"{c.p - c.vp} | {c.n - c.vn} | {pct(cu.sens)} / {pct(cu.spec)} | "
            f"{pct(cc.sens)} / {pct(cc.spec)} | {mc} | {falsas}/30 | {cens_tp} / {cens_fp} | "
            f"{lat_txt} |"
        )
    salida, elegidos = anidado
    c = contar(videos, salida)
    b, cc_, p = mcnemar([(v.es_caida, base.salida[v.nombre], salida[v.nombre]) for v in videos])
    lineas += [
        f"| *Fully nested (each fold also picks the rule set)* | {total_configuraciones} | "
        f"{con_ic(c.vp, c.p)} | {con_ic(c.vn, c.n)} | {c.p - c.vp} | {c.n - c.vn} | | | "
        f"{b}/{cc_} p={p:.3f} | | | |",
        "",
        "Fully nested choices: " + "; ".join(elegidos),
        "",
        "## Cross-dataset (sensitivity / specificity on the test dataset)",
        "",
        "| Rule set | URFD → CAUCAFall | CAUCAFall → URFD |",
        "|---|---|---|",
    ]
    for nombre, r in resultados.items():
        celdas = [
            f"{pct(cu.sens)} / {pct(cu.spec)} ({corto(nombre, a)})" for a, cu in r.cruzado.values()
        ]
        lineas.append(f"| {nombre} | {' | '.join(celdas)} |")
    lineas += [
        "",
        "## Configuration chosen per fold and on all 170 videos (frozen for the hold-out)",
        "",
        "| Rule set | Per fold (count) | All development videos |",
        "|---|---|---|",
    ]
    for nombre, r in resultados.items():
        cuenta_elegidos: dict[str, int] = defaultdict(int)
        for a in r.elegidos.values():
            cuenta_elegidos[corto(nombre, a)] += 1
        por_fold = "; ".join(f"{k} ×{n}" for k, n in sorted(cuenta_elegidos.items()))
        lineas.append(f"| {nombre} | {por_fold} | {corto(nombre, r.final)} |")
    lineas += [
        "",
        "## Videos with a `caida` per activity (LOGO)",
        "",
        "| Activity | Videos | " + " | ".join(resultados) + " |",
        "|---|---|" + "---|" * len(resultados),
    ]
    grupos: dict[str, list[Video]] = defaultdict(list)
    for v in videos:
        grupos[actividad_dev(v, tendidas)].append(v)
    for act, vs in sorted(grupos.items()):
        lineas.append(
            f"| {act} | {len(vs)} | "
            + " | ".join(str(sum(r.salida[v.nombre] for v in vs)) for r in resultados.values())
            + " |"
        )
    lineas += ["", "## Videos that change against the baseline (LOGO)", ""]
    for nombre, r in resultados.items():
        if nombre == "base":
            continue
        ganados = [
            v.nombre for v in videos if r.salida[v.nombre] == v.es_caida != base.salida[v.nombre]
        ]
        perdidos = [
            v.nombre for v in videos if base.salida[v.nombre] == v.es_caida != r.salida[v.nombre]
        ]
        lineas.append(
            f"- **{nombre}**: right only here: {', '.join(ganados) or 'none'}; "
            f"wrong only here: {', '.join(perdidos) or 'none'}"
        )
    return lineas


def _solo_censurada(eventos: list[EventoVideo]) -> bool:
    return sum(t == CAIDA for t, _ in eventos) == 1 and any(t == CENSURADA for t, _ in eventos)


def desarrollo(args: argparse.Namespace, variante: str) -> int:
    videos = [v for v in listar_videos(args.datos) if v.dataset in DATASETS_VALIDACION]
    if not videos or any(not v.cache(variante).exists() for v in videos):
        print(f"Faltan las poses ({variante})", file=sys.stderr)
        return 1
    nombres = args.familias or list(FAMILIAS)
    if "base" not in nombres:
        nombres = ["base", *nombres]
    por_familia = {n: ajustes_de(n) for n in nombres}
    todos = sorted({a for f in por_familia.values() for a in f}, key=repr)
    print(f"{len(videos)} videos · {len(todos)} configurations", flush=True)
    corridas = correr_todo(videos, variante, todos, args.procesos)
    resultados = {n: evaluar_familia(n, por_familia[n], corridas, videos) for n in nombres}

    salida: dict[str, bool] = {}
    elegidos: list[str] = []
    for g in sorted({v.grupo for v in videos}):
        entrenamiento = [v for v in videos if v.grupo != g]
        mejor = max(
            ((n, elegir(n, por_familia[n], corridas, entrenamiento)) for n in nombres),
            key=lambda x: (
                round(
                    contar(
                        entrenamiento,
                        {v.nombre: detecto(corridas[x[1]][v.nombre]) for v in entrenamiento},
                    ).youden,
                    9,
                ),
                x[0] == "base",
            ),
        )
        elegidos.append(f"{g}: {mejor[0]} ({corto(*mejor)})")
        for v in videos:
            if v.grupo == g:
                salida[v.nombre] = detecto(corridas[mejor[1]][v.nombre])

    texto = informe_desarrollo(
        resultados,
        videos,
        inicios_urfd(args.datos),
        acostadas_urfd(videos, args.datos),
        (salida, elegidos),
        len(todos),
    )
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "desarrollo.md").write_text("\n".join(texto) + "\n", encoding="utf-8")
    (args.salida / "desarrollo.json").write_text(
        json.dumps(
            {
                "configuraciones": len(todos),
                "finales": {n: dict(r.final) for n, r in resultados.items()},
                "por_video": {n: r.salida for n, r in resultados.items()},
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print("\n".join(texto))
    return 0


# ------------------------------------------------------------------------------ hold-out


def preparar_unidades(
    datos: Path, datasets: Sequence[str]
) -> tuple[list[Video], dict[str, Ventanas], list[Unidad]]:
    videos = listar_videos(datos, datasets)
    ventanas = {v.nombre: ventanas_mcfd(v) for v in videos if v.dataset == "mcfd"}
    return videos, ventanas, unidades(videos, ventanas, acostadas_urfd(videos, datos))


def salida_unidades(us: Sequence[Unidad], ev: Eventos, ventanas: dict[str, Ventanas]) -> bytes:
    return bytes(alarma(u, ev[u.video], ventanas) for u in us)


def cuenta(us: Sequence[Unidad], s: bytes, indices: Sequence[int]) -> Cuenta:
    return Cuenta(
        sum(1 for i in indices if us[i].positiva and s[i]),
        sum(1 for i in indices if us[i].positiva),
        sum(1 for i in indices if not us[i].positiva and not s[i]),
        sum(1 for i in indices if not us[i].positiva),
    )


def mcnemar_unidades(us: Sequence[Unidad], base: bytes, otro: bytes, indices: Sequence[int]) -> str:
    b, c, p = mcnemar([(us[i].positiva, bool(base[i]), bool(otro[i])) for i in indices])
    return f"{b}/{c} p={p:.3f}"


def fila_extras(nombre: str, x: dict[str, Any]) -> str:
    lat = x["mcfd_latencias"]
    lat_txt = f"{statistics.median(lat):.2f} s" if lat else "—"
    rec = " · ".join(
        f"{x.get(f'{d}_rec_falsa', 0)}/{x.get(f'{d}_detectadas', 0)}"
        for d in ("gmdcsa24", "upfall")
    )
    return (
        f"| {nombre} | {rec} · {x.get('mcfd_rec_falsa', 0)}/{x.get('mcfd_detectadas', 0)} | "
        f"{x['mcfd_falsas']} ({x['mcfd_falsas'] / x['mcfd_horas']:.0f}/h) | {lat_txt} |"
    )


def holdout(args: argparse.Namespace, variante: str) -> int:
    dev = [v for v in listar_videos(args.datos) if v.dataset in DATASETS_VALIDACION]
    nombres = ["base", *[n for n in args.familias or [] if n != "base"]]
    por_familia = {n: ajustes_de(n) for n in nombres}
    todos = sorted({a for f in por_familia.values() for a in f}, key=repr)
    corridas = correr_todo(dev, variante, todos, args.procesos)
    finales = {n: elegir(n, por_familia[n], corridas, dev) for n in nombres}
    print(
        "Frozen on the development data: "
        + "; ".join(f"{n}: {corto(n, a)}" for n, a in finales.items())
    )

    videos, ventanas, us = preparar_unidades(args.datos, HOLDOUT)
    faltan = [v.nombre for v in videos if not v.cache(variante).exists()]
    if faltan:
        print(f"Faltan poses: {len(faltan)}", file=sys.stderr)
        return 1
    unicos = sorted(set(finales.values()), key=repr)
    corridas_holdout = correr_todo(videos, variante, unicos, args.procesos)
    ev = {n: corridas_holdout[finales[n]] for n in nombres}
    salidas = {n: salida_unidades(us, ev[n], ventanas) for n in nombres}
    idx = {d: [i for i, u in enumerate(us) if u.dataset == d] for d in HOLDOUT}
    lineas = [
        "# Specificity study (ADR 0012): hold-out, frozen, run once",
        "",
        "Each rule set is chosen on the 170 development videos (maximum Youden) and frozen: "
        + "; ".join(f"**{n}**: {corto(n, a)}" for n, a in finales.items())
        + ". Units as in ADR 0011 (recordings; MCFD fall windows and labelled non-fall periods). "
        "McNemar against the frozen baseline on the same units.",
        "",
        "| Dataset | Rule set | Sensitivity | Specificity | McNemar all · positives · negatives |",
        "|---|---|---|---|---|",
    ]
    for d in [*HOLDOUT, "pooled", "macro"]:
        for n in nombres:
            if d == "macro":
                sm = statistics.fmean(cuenta(us, salidas[n], idx[x]).sens for x in HOLDOUT)
                em = statistics.fmean(cuenta(us, salidas[n], idx[x]).spec for x in HOLDOUT)
                lineas.append(f"| macro mean | {n} | {pct(sm)} | {pct(em)} | |")
                continue
            ii = list(range(len(us))) if d == "pooled" else idx[d]
            c = cuenta(us, salidas[n], ii)
            mc = (
                "—"
                if n == "base"
                else " · ".join(
                    mcnemar_unidades(us, salidas["base"], salidas[n], g)
                    for g in (
                        ii,
                        [i for i in ii if us[i].positiva],
                        [i for i in ii if not us[i].positiva],
                    )
                )
            )
            lineas.append(f"| {d} | {n} | {con_ic(c.vp, c.p)} | {con_ic(c.vn, c.n)} | {mc} |")
    lineas += [
        "",
        "## False alarms per activity (negative units with a `caida`)",
        "",
        "| Dataset · activity | Units | " + " | ".join(nombres) + " |",
        "|---|---|" + "---|" * len(nombres),
    ]
    grupos: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, u in enumerate(us):
        grupos[u.dataset, u.actividad if not u.positiva else "FALLS (detected)"].append(i)
    for (d, a), ii in sorted(grupos.items()):
        lineas.append(
            f"| {d} · {a} | {len(ii)} | "
            + " | ".join(str(sum(salidas[n][i] for i in ii)) for n in nombres)
            + " |"
        )
    lineas += [
        "",
        "## Safety and MCFD stream",
        "",
        "| Rule set | False recoveries GMDCSA24 · UP-Fall · MCFD | MCFD false alarms (per hour) | "
        "MCFD latency median |",
        "|---|---|---|---|",
    ]
    for n in nombres:
        lineas.append(fila_extras(n, extras(videos, ventanas, ev[n])))
    censuradas = {
        n: sum(1 for v in videos if v.dataset != "mcfd" and _solo_censurada(ev[n][v.nombre]))
        for n in nombres
    }
    lineas += [
        "",
        "Recordings whose only `caida` is a censored hold: "
        + ", ".join(f"{n} {c}" for n, c in censuradas.items()),
    ]
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "holdout.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 0


# ------------------------------------------------------------------------------ LODO


_ESTADO: dict[str, Any] = {}


def _iniciar_lodo(datos: Path, variante: str) -> None:
    videos, ventanas, us = preparar_unidades(datos, DATASETS)
    _ESTADO["poses"] = {v.nombre: cargar_poses(v, variante) for v in videos}
    _ESTADO["ventanas"], _ESTADO["unidades"] = ventanas, us


def _correr_lodo(ajuste: Ajuste) -> bytes:
    umbrales = Umbrales.model_validate(dict(ajuste))
    ev = {n: replay(s, umbrales) for n, s in _ESTADO["poses"].items()}
    return salida_unidades(_ESTADO["unidades"], ev, _ESTADO["ventanas"])


def lodo(args: argparse.Namespace, variante: str) -> int:
    videos, _, us = preparar_unidades(args.datos, DATASETS)
    nombres = ["base", *[n for n in args.familias or [] if n != "base"]]
    por_familia = {n: ajustes_de(n) for n in nombres}
    todos = sorted({a for f in por_familia.values() for a in f}, key=repr)
    print(f"{len(videos)} recordings · {len(us)} units · {len(todos)} configurations", flush=True)
    with ProcessPoolExecutor(
        args.procesos, initializer=_iniciar_lodo, initargs=(args.datos, variante)
    ) as pool:
        salidas = dict(zip(todos, pool.map(_correr_lodo, todos, chunksize=4), strict=True))
    datasets = list(DATASETS)
    idx = {d: [i for i, u in enumerate(us) if u.dataset == d] for d in datasets}
    cuentas = {a: {d: cuenta(us, s, idx[d]) for d in datasets} for a, s in salidas.items()}

    def clave(criterio: str, n: str, a: Ajuste, entrenamiento: Sequence[str]) -> tuple[float, ...]:
        s = statistics.fmean(cuentas[a][d].sens for d in entrenamiento)
        e = statistics.fmean(cuentas[a][d].spec for d in entrenamiento)
        if criterio == "youden":
            return (round(s + e - 1, 9), *desempate(n, a))
        if s >= SENSIBILIDAD_MIN - 1e-12:
            return (1.0, round(e, 9), round(s, 9), *desempate(n, a))
        return (0.0, round(s, 9), round(e, 9), *desempate(n, a))

    shipped = salidas[(("velocidad_descenso_min", 0.01),)]
    lineas = [
        "# Specificity study (ADR 0012): leave one dataset out (secondary)",
        "",
        f"Five datasets, {len(us)} units, {len(todos)} configurations; selection by macro "
        "criterion over the four training datasets, as in ADR 0011. This uses the hold-out sets "
        "as training folds: it is reported after, and separately from, the frozen hold-out test.",
        "",
    ]
    for criterio in ("youden", "spec_sens90"):
        lineas += [
            f"## Criterion: {criterio}",
            "",
            "| Rule set | " + " | ".join(datasets) + " | Macro sens / spec | Pooled McNemar vs "
            "baseline · vs shipped | Chosen (per held-out dataset) |",
            "|---|" + "---|" * len(datasets) + "---|---|---|",
        ]
        lodo_salidas: dict[str, bytes] = {}
        for n in nombres:
            out = bytearray(len(us))
            elegidos = []
            for d in datasets:
                entrenamiento = [x for x in datasets if x != d]
                a = max(por_familia[n], key=lambda a: clave(criterio, n, a, entrenamiento))
                elegidos.append(f"{d}: {corto(n, a)}")
                for i in idx[d]:
                    out[i] = salidas[a][i]
            lodo_salidas[n] = bytes(out)
            cs = [cuenta(us, lodo_salidas[n], idx[d]) for d in datasets]
            celdas = [f"{pct(c.sens)} / {pct(c.spec)}" for c in cs]
            todos_idx = list(range(len(us)))
            mc = (
                (
                    "—"
                    if n == "base"
                    else mcnemar_unidades(us, lodo_salidas["base"], lodo_salidas[n], todos_idx)
                )
                + " · "
                + mcnemar_unidades(us, shipped, lodo_salidas[n], todos_idx)
            )
            lineas.append(
                f"| {n} | {' | '.join(celdas)} | "
                f"{pct(statistics.fmean(c.sens for c in cs))} / "
                f"{pct(statistics.fmean(c.spec for c in cs))} | {mc} | {'; '.join(elegidos)} |"
            )
        cs = [cuenta(us, shipped, idx[d]) for d in datasets]
        lineas += [
            "| *shipped (v = 0.01)* | "
            + " | ".join(f"{pct(c.sens)} / {pct(c.spec)}" for c in cs)
            + f" | {pct(statistics.fmean(c.sens for c in cs))} / "
            f"{pct(statistics.fmean(c.spec for c in cs))} | | |",
            "",
        ]
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "lodo.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("etapa", choices=("desarrollo", "holdout", "lodo"))
    parser.add_argument("--familias", nargs="*", choices=list(TODAS))
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--procesos", type=int, default=12)
    parser.add_argument("--salida", type=Path, default=RESULTADOS / "especificidad")
    args = parser.parse_args()
    variante = nombre_variante(args.modelo, "video", args.fps, True)
    etapas = {"desarrollo": desarrollo, "holdout": holdout, "lodo": lodo}
    return etapas[args.etapa](args, variante)


if __name__ == "__main__":
    sys.exit(main())
