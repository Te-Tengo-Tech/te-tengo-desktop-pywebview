"""Leave-one-dataset-out (LODO) evaluation of the post-hoc fixes F1 and F2 (ADR 0011).

Five datasets (URFD, CAUCAFall, GMDCSA24, UP-Fall subset and MCFD), poses already extracted by
``evaluar.py extraer`` (480p, 8 fps, JPEG quality 80, MediaPipe lite in VIDEO mode). Four rule
sets are compared, each with its own grid:

* **baseline**: the shipped rules R4–R9, only the speed ``v`` tunable;
* **F1**: R4 needs the person upright within the last T s (``erguido_previo_caida_s``);
* **F2**: leave ``EN_EL_SUELO`` silently after X s without floor evidence
  (``salida_suelo_sin_evidencia_s``);
* **F1 + F2**.

For each held-out dataset, ``v`` (0.01–1.00), T and X are chosen on the other four datasets by
two criteria (macro averages over the training datasets): the maximum Youden index, and the
maximum specificity subject to a sensitivity of at least 90 %. The protocol, the units and the
acceptance rule were fixed in ADR 0011 before running.

Units: one recording (video and camera) in the clip datasets; in MCFD, every labelled fall
window (positive) and every labelled non-fall period (negative).

Example:
    uv run python scripts/evaluar_lodo.py --procesos 10   # resultados/lodo-f1-f2-8fps.md
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

from barrer_rangos import acostadas_urfd, wilson
from evaluar import (
    DATASETS,
    POSICIONES_MCFD,
    RESULTADOS,
    Secuencia,
    Video,
    cargar_poses,
    listar_videos,
    nombre_variante,
)
from evaluar_candidatos import mcnemar_exacto
from evaluar_multicamara import Ventanas, ventanas_mcfd

from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, Fase, TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

CAIDA = TipoEvento.CAIDA.value
RECUPERACION = TipoEvento.RECUPERACION.value
CONFIRMADA = TipoEvento.CAIDA_CONFIRMADA.value
SALIDA = "salida_suelo"  # pseudo-event: F2 left EN_EL_SUELO without a recuperacion

VALORES_V = [round(0.01 * i, 2) for i in range(1, 101)]
VALORES_T = [1.0, 2.0, 3.0, 5.0, 10.0]  # F1 (ADR 0011)
VALORES_X = [2.0, 3.0, 5.0, 10.0, 20.0]  # F2 (ADR 0011)
SENSIBILIDAD_MIN = 0.90  # criterion 2
CRITERIOS = ("youden", "spec_sens90")
NOMBRES_CRITERIO = {
    "youden": "maximum Youden index",
    "spec_sens90": "maximum specificity with sensitivity ≥ 90 %",
}
SHIPPED = {"velocidad_descenso_min": 0.01}

Ajuste = dict[str, float | bool]
EventoVideo = tuple[str, float]
Eventos = dict[str, list[EventoVideo]]


def familias() -> dict[str, list[Ajuste]]:
    """The rule sets and their grids (3,600 pre-registered configurations + 500 for F3)."""
    v = [{"velocidad_descenso_min": x} for x in VALORES_V]
    t = [{"erguido_previo_caida_s": x} for x in VALORES_T]
    s = [{"salida_suelo_sin_evidencia_s": x} for x in VALORES_X]
    return {
        "baseline": v,
        "F1": [a | b for a, b in itertools.product(v, t)],
        "F2": [a | b for a, b in itertools.product(v, s)],
        "F1+F2": [a | b | c for a, b, c in itertools.product(v, t, s)],
        # Added after the first run (ADR 0011): F1 with the geometric upright test (no A6).
        "F3": [
            a | b | {"erguido_previo_exige_visibles": False} for a, b in itertools.product(v, t)
        ],
    }


# ------------------------------------------------------------------------------ replay


def replay(secuencia: Secuencia, umbrales: Umbrales) -> list[EventoVideo]:
    """Events of one recording, plus F2's silent exits from ``EN_EL_SUELO``."""
    c = ClasificadorCinematico(umbrales)
    eventos: list[EventoVideo] = []
    for instante, pose in secuencia:
        antes = c.fase
        nuevos = c.actualizar(instante, pose)
        eventos += [(e.tipo.value, e.instante) for e in nuevos]
        if (
            antes is Fase.EN_EL_SUELO
            and c.fase is Fase.NORMAL
            and not any(e.tipo is TipoEvento.RECUPERACION for e in nuevos)
        ):
            eventos.append((SALIDA, instante))
    return eventos


def caidas(eventos: list[EventoVideo]) -> list[float]:
    return [i for t, i in eventos if t == CAIDA]


# ------------------------------------------------------------------------------ units


@dataclass(frozen=True, slots=True)
class Unidad:
    dataset: str
    video: str
    positiva: bool
    actividad: str
    ventana: int | None = None  # MCFD fall window index
    periodo: tuple[float, float] | None = None  # MCFD non-fall period


def actividad(v: Video, tendidas: set[str]) -> str:
    if v.dataset == "urfd":
        if v.es_caida:
            return "fall"
        return "lying down on the floor on purpose" if v.nombre in tendidas else "other ADL"
    if v.dataset == "caucafall":
        return v.actividad.replace("_", " ")
    return v.actividad


def unidades(
    videos: Sequence[Video], ventanas: dict[str, Ventanas], tendidas: set[str]
) -> list[Unidad]:
    salida: list[Unidad] = []
    for v in videos:
        if v.dataset != "mcfd":
            salida.append(Unidad(v.dataset, v.nombre, v.es_caida, actividad(v, tendidas)))
            continue
        w = ventanas[v.nombre]
        for k in range(len(w.caidas)):
            salida.append(Unidad("mcfd", v.nombre, True, "fall", ventana=k))
        for a, b, codigo in w.periodos:
            if codigo in (2, 3):  # falling and lying on the ground belong to the fall windows
                continue
            salida.append(Unidad("mcfd", v.nombre, False, POSICIONES_MCFD[codigo], periodo=(a, b)))
    return salida


def alarma(u: Unidad, eventos: list[EventoVideo], ventanas: dict[str, Ventanas]) -> bool:
    """Whether the unit has a ``caida``: detected (positive) or a false alarm (negative)."""
    if u.dataset != "mcfd":
        return bool(caidas(eventos))
    w = ventanas[u.video]
    if u.ventana is not None:
        return any(w.en_caida(i) == u.ventana for i in caidas(eventos))
    assert u.periodo is not None
    a, b = u.periodo
    return any(
        a <= i < b and w.en_caida(i) is None and not w.en_ambigua(i) for i in caidas(eventos)
    )


# ------------------------------------------------------------------------------ workers

_ESTADO: dict[str, Any] = {}


def _iniciar(datos: Path, variante: str) -> None:
    videos = listar_videos(datos, DATASETS)
    ventanas = {v.nombre: ventanas_mcfd(v) for v in videos if v.dataset == "mcfd"}
    _ESTADO["poses"] = {v.nombre: cargar_poses(v, variante) for v in videos}
    _ESTADO["ventanas"] = ventanas
    _ESTADO["unidades"] = unidades(videos, ventanas, acostadas_urfd(videos, datos))


def _correr(ajuste: Ajuste) -> bytes:
    umbrales = Umbrales.model_validate(ajuste)
    eventos = {n: replay(s, umbrales) for n, s in _ESTADO["poses"].items()}
    us: list[Unidad] = _ESTADO["unidades"]
    return bytes(alarma(u, eventos[u.video], _ESTADO["ventanas"]) for u in us)


def _eventos(ajuste: Ajuste) -> Eventos:
    umbrales = Umbrales.model_validate(ajuste)
    return {n: replay(s, umbrales) for n, s in _ESTADO["poses"].items()}


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

    def __add__(self, o: "Cuenta") -> "Cuenta":
        return Cuenta(self.vp + o.vp, self.p + o.p, self.vn + o.vn, self.n + o.n)


def cuenta(us: Sequence[Unidad], salida: bytes, indices: Sequence[int]) -> Cuenta:
    vp = sum(1 for i in indices if us[i].positiva and salida[i])
    p = sum(1 for i in indices if us[i].positiva)
    vn = sum(1 for i in indices if not us[i].positiva and not salida[i])
    n = sum(1 for i in indices if not us[i].positiva)
    return Cuenta(vp, p, vn, n)


def macro(cuentas: Sequence[Cuenta]) -> tuple[float, float]:
    return (
        statistics.fmean(c.sens for c in cuentas),
        statistics.fmean(c.spec for c in cuentas),
    )


def clave(criterio: str, sens: float, spec: float, ajuste: Ajuste) -> tuple[float, ...]:
    """Sort key, larger is better; ties: lowest v, then largest T and X (closest to shipped)."""
    desempate = (
        -ajuste["velocidad_descenso_min"],
        ajuste.get("erguido_previo_caida_s", math.inf),
        ajuste.get("salida_suelo_sin_evidencia_s", math.inf),
    )
    if criterio == "youden":
        return (round(sens + spec - 1, 12), *desempate)
    if sens >= SENSIBILIDAD_MIN - 1e-12:
        return (1.0, round(spec, 12), round(sens, 12), *desempate)
    return (0.0, round(sens, 12), round(spec, 12), *desempate)


def elegir(
    criterio: str,
    ajustes: Sequence[Ajuste],
    por_dataset: Sequence[dict[str, Cuenta]],
    entrenamiento: Sequence[str],
) -> int:
    def k(j: int) -> tuple[float, ...]:
        s, e = macro([por_dataset[j][d] for d in entrenamiento])
        return clave(criterio, s, e, ajustes[j])

    return max(range(len(ajustes)), key=k)


def pct(x: float) -> str:
    return "—" if math.isnan(x) else f"{100 * x:.1f} %"


def con_ic(aciertos: int, total: int) -> str:
    if not total:
        return "—"
    a, b = wilson(aciertos, total)
    return f"{100 * aciertos / total:.1f} % ({100 * a:.1f}–{100 * b:.1f})"


def corto(a: Ajuste) -> str:
    partes = [f"v={a['velocidad_descenso_min']:g}"]
    if "erguido_previo_caida_s" in a:
        partes.append(f"T={a['erguido_previo_caida_s']:g}")
    if "salida_suelo_sin_evidencia_s" in a:
        partes.append(f"X={a['salida_suelo_sin_evidencia_s']:g}")
    return ", ".join(partes)


def mcnemar(
    us: Sequence[Unidad], base: bytes, otro: bytes, indices: Sequence[int]
) -> tuple[int, int, float]:
    """Discordant pairs on correctness: b = only the baseline right, c = only the other."""
    b = sum(1 for i in indices if (base[i] == us[i].positiva) and (otro[i] != us[i].positiva))
    c = sum(1 for i in indices if (otro[i] == us[i].positiva) and (base[i] != us[i].positiva))
    return b, c, mcnemar_exacto(b, c)


# ------------------------------------------------------------------------------ extras


def extras(videos: Sequence[Video], ventanas: dict[str, Ventanas], ev: Eventos) -> dict[str, Any]:
    """False recoveries, F2 exits on the floor, confirmations and MCFD latency and rate."""
    r: dict[str, Any] = defaultdict(int)
    latencias: list[float] = []
    falsas_mcfd = 0
    horas = 0.0
    for v in videos:
        e = ev[v.nombre]
        cs = caidas(e)
        recs = [i for t, i in e if t == RECUPERACION]
        sal = [i for t, i in e if t == SALIDA]
        if v.dataset == "mcfd":
            w = ventanas[v.nombre]
            for k, (inicio, fin) in enumerate(w.caidas):
                dentro = [i for i in cs if w.en_caida(i) == k]
                if not dentro:
                    continue
                latencias.append(dentro[0] - inicio)
                r["mcfd_detectadas"] += 1
                r["mcfd_rec_falsa"] += any(dentro[0] < x <= fin for x in recs)
                r["mcfd_salida_en_suelo"] += any(dentro[0] < x <= fin for x in sal)
                r["mcfd_confirmadas"] += any(dentro[0] < i for t, i in e if t == CONFIRMADA)
            falsas_mcfd += sum(
                1
                for i in cs
                if w.en_caida(i) is None and not w.en_ambigua(i) and w.en_etiquetado(i)
            )
            inicio, fin = w.etiquetado
            horas += ((fin - inicio) - sum(b - a for a, b in w.caidas)) / 3600
            continue
        if not v.es_caida or not cs:
            continue
        clave_ds = v.dataset
        r[f"{clave_ds}_detectadas"] += 1
        if v.dataset == "gmdcsa24":
            if v.se_levanta is False and v.inicio_caida is not None:
                r[f"{clave_ds}_rec_falsa"] += any(x > v.inicio_caida for x in recs)
                r[f"{clave_ds}_salida"] += any(x > v.inicio_caida for x in sal)
        else:
            r[f"{clave_ds}_rec_falsa"] += any(x > cs[0] for x in recs)
            r[f"{clave_ds}_salida"] += any(x > cs[0] for x in sal)
        r[f"{clave_ds}_confirmadas"] += any(t == CONFIRMADA for t, _ in e)
    r["mcfd_latencias"] = latencias
    r["mcfd_falsas"] = falsas_mcfd
    r["mcfd_horas"] = horas
    return dict(r)


# ------------------------------------------------------------------------------ diagnosis


def _diagnostico(_: object) -> list[str]:
    """Why F1 loses falls and why F2 does not unmask MCFD falls (frozen v = 0.01)."""
    poses: dict[str, Secuencia] = _ESTADO["poses"]
    ventanas: dict[str, Ventanas] = _ESTADO["ventanas"]
    base = Umbrales.model_validate(SHIPPED)
    f1 = base.model_copy(update={"erguido_previo_caida_s": 10.0})
    angulo, razon = base.angulo_linea_central_max_grados, base.razon_ancho_alto_min

    def traza(seq: Secuencia) -> list[tuple[float, Fase, Any]]:
        c = ClasificadorCinematico(base)
        out = []
        for t, pose in seq:
            c.actualizar(t, pose)
            out.append((t, c.fase, None if pose is None else c.ultima_medicion))
        return out

    def geometrico(m: Any) -> bool:
        pr = m.parametros
        return bool(
            not pr.cabeza_bajo_pies and pr.angulo_grados > angulo and pr.razon_ancho_alto < razon
        )

    perdidas: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for nombre, seq in poses.items():
        if nombre.startswith("chute"):
            continue
        cb = caidas(replay(seq, base))
        if not cb or caidas(replay(seq, f1)):
            continue
        t0 = cb[0]
        ms = [m for t, _, m in traza(seq) if m is not None and t0 - 10 <= t <= t0]
        u = next(x for x in _ESTADO["unidades"] if x.video == nombre)
        fila = perdidas[u.dataset]
        fila[0] += 1
        fila[1] += any(geometrico(m) for m in ms)
        fila[2] += any(geometrico(m) and m.parametros.puntos_visibles for m in ms)
    lineas = [
        "## Diagnosis (frozen v = 0.01)",
        "",
        "**F1 (T = 10 s) losses:** falls detected by the shipped classifier and not by F1, and "
        "whether the 10 s before the shipped `caida` had a frame upright by geometry only "
        "(θ > 45°, P < 1, head above the feet) or by the strict test (with A6).",
        "",
        "| Dataset | Falls lost | With a geometric upright frame | With a strict upright frame |",
        "|---|---|---|---|",
        *(f"| {d} | {a} | {b} | {c} |" for d, (a, b, c) in sorted(perdidas.items())),
        "",
    ]
    filas = []
    for nombre, seq in poses.items():
        w = ventanas.get(nombre)
        if w is None or not w.caidas:
            continue
        tr = traza(seq)
        for inicio, _ in w.caidas:
            antes = [x for x in tr if x[0] < inicio - 1.0]
            if not antes or antes[-1][1] is not Fase.EN_EL_SUELO:
                continue
            j = len(antes) - 1
            while j > 0 and antes[j - 1][1] is Fase.EN_EL_SUELO:
                j -= 1
            tramo = antes[j:]
            con_pose = [(t, m) for t, _, m in tramo if m is not None]
            sin_suelo = [(t, m) for t, m in con_pose if geometrico(m)]
            mejor, desde = 0.0, None
            for t, m in con_pose:
                if geometrico(m):
                    desde = t if desde is None else desde
                    mejor = max(mejor, t - desde)
                else:
                    desde = None
            filas.append((tramo[-1][0] - tramo[0][0], len(con_pose), len(sin_suelo), mejor))
    if filas:
        lineas += [
            f"**MCFD windows masked by an earlier `caida`** (state `EN_EL_SUELO` 1 s before the "
            f"labelled onset): {len(filas)}. Time in `EN_EL_SUELO` before the onset: median "
            f"{statistics.median(f[0] for f in filas):.1f} s, ≤ 2 s in "
            f"{sum(f[0] <= 2 for f in filas)}. Frames with a pose and no floor evidence (neither "
            f"M2 nor M3): median {100 * statistics.median(f[2] / max(f[1], 1) for f in filas):.1f} "
            f"% of the pose frames; the longest run without floor evidence reaches 1 s in "
            f"{sum(f[3] >= 1 for f in filas)} windows and 2 s in {sum(f[3] >= 2 for f in filas)}.",
            "",
        ]
    return lineas


# ------------------------------------------------------------------------------ main


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--procesos", type=int, default=8)
    parser.add_argument("--salida", type=Path, default=RESULTADOS / "lodo-f1-f2-8fps.md")
    args = parser.parse_args()

    variante = nombre_variante(args.modelo, "video", args.fps, True)
    videos = listar_videos(args.datos, DATASETS)
    faltan = [v.nombre for v in videos if not v.cache(variante).exists()]
    if faltan:
        print(f"Faltan poses ({variante}): {len(faltan)} videos", file=sys.stderr)
        return 1
    ventanas = {v.nombre: ventanas_mcfd(v) for v in videos if v.dataset == "mcfd"}
    tendidas = acostadas_urfd(videos, args.datos)
    us = unidades(videos, ventanas, tendidas)
    datasets = [d for d in DATASETS if any(u.dataset == d for u in us)]
    idx = {d: [i for i, u in enumerate(us) if u.dataset == d] for d in datasets}

    fams = familias()
    todos = [a for f in fams.values() for a in f]
    print(f"{len(videos)} videos · {len(us)} units · {len(todos)} configurations")
    with ProcessPoolExecutor(
        args.procesos, initializer=_iniciar, initargs=(args.datos, variante)
    ) as pool:
        salidas = list(pool.map(_correr, todos, chunksize=8))
    pos = 0
    curvas: dict[str, list[bytes]] = {}
    for nombre, f in fams.items():
        curvas[nombre] = salidas[pos : pos + len(f)]
        pos += len(f)
    cuentas = {n: [{d: cuenta(us, s, idx[d]) for d in datasets} for s in curvas[n]] for n in fams}

    # LODO selection.
    elegidos: dict[tuple[str, str, str], int] = {}  # (family, criterion, held-out) -> config
    finales: dict[tuple[str, str], int] = {}  # calibrated on all five
    for n, crit in itertools.product(fams, CRITERIOS):
        for d in datasets:
            elegidos[n, crit, d] = elegir(
                crit, fams[n], cuentas[n], [x for x in datasets if x != d]
            )
        finales[n, crit] = elegir(crit, fams[n], cuentas[n], datasets)

    def salida_lodo(n: str, crit: str) -> bytes:
        out = bytearray(len(us))
        for d in datasets:
            s = curvas[n][elegidos[n, crit, d]]
            for i in idx[d]:
                out[i] = s[i]
        return bytes(out)

    lodo = {(n, c): salida_lodo(n, c) for n in fams for c in CRITERIOS}
    with ProcessPoolExecutor(1, initializer=_iniciar, initargs=(args.datos, variante)) as pool:
        shipped_ev = pool.submit(_eventos, SHIPPED).result()
        diagnostico = pool.submit(_diagnostico, None).result()
        # Full events of every chosen configuration (for the extras).
        necesarios = sorted(
            {(n, j) for (n, _, _), j in elegidos.items()}
            | {(n, j) for (n, _), j in finales.items()}
        )
        ev_conf = {(n, j): pool.submit(_eventos, fams[n][j]).result() for n, j in necesarios}
    shipped = bytes(alarma(u, shipped_ev[u.video], ventanas) for u in us)

    def ev_lodo(n: str, crit: str) -> Eventos:
        out: Eventos = {}
        for v in videos:
            out[v.nombre] = ev_conf[n, elegidos[n, crit, v.dataset]][v.nombre]
        return out

    texto = informe(
        videos,
        us,
        datasets,
        idx,
        fams,
        elegidos,
        finales,
        cuentas,
        lodo,
        shipped,
        shipped_ev,
        ev_lodo,
        ventanas,
        ev_conf,
    )
    texto += diagnostico
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text("\n".join(texto).rstrip() + "\n", encoding="utf-8")
    datos_json = {
        "elegidos": {f"{n}|{c}|{d}": corto(fams[n][j]) for (n, c, d), j in elegidos.items()},
        "finales": {f"{n}|{c}": corto(fams[n][j]) for (n, c), j in finales.items()},
        "configuraciones": len(todos),
    }
    args.salida.with_suffix(".json").write_text(json.dumps(datos_json, indent=1), "utf-8")
    print("\n".join(texto))
    return 0


def informe(
    videos: Sequence[Video],
    us: Sequence[Unidad],
    datasets: Sequence[str],
    idx: dict[str, list[int]],
    fams: dict[str, list[Ajuste]],
    elegidos: dict[tuple[str, str, str], int],
    finales: dict[tuple[str, str], int],
    cuentas: dict[str, list[dict[str, Cuenta]]],
    lodo: dict[tuple[str, str], bytes],
    shipped: bytes,
    shipped_ev: Eventos,
    ev_lodo: Any,
    ventanas: dict[str, Ventanas],
    ev_conf: dict[tuple[str, int], Eventos],
) -> list[str]:
    todos_idx = list(range(len(us)))
    pos_idx = [i for i in todos_idx if us[i].positiva]
    neg_idx = [i for i in todos_idx if not us[i].positiva]
    lineas = [
        "# Leave-one-dataset-out evaluation of F1 and F2 (ADR 0011)",
        "",
        f"{len(videos)} recordings, {len(us)} units "
        f"({len(pos_idx)} positive, {len(neg_idx)} negative); "
        f"{sum(len(f) for f in fams.values())} configurations "
        + ", ".join(f"{n}: {len(f)}" for n, f in fams.items())
        + ". Units: one recording per camera; MCFD: fall windows (positive) and labelled "
        "non-fall periods (negative). Intervals: 95 % Wilson. McNemar: exact, two-sided, on "
        "correctness of paired units (b = only the baseline right, c = only the fix right).",
        "",
        "## 0. Frozen shipped classifier (v = 0.01, F1 and F2 off), per dataset",
        "",
        "| Dataset | Sensitivity | Specificity | Units (pos / neg) |",
        "|---|---|---|---|",
    ]
    for d in datasets:
        c = cuenta(us, shipped, idx[d])
        lineas.append(f"| {d} | {con_ic(c.vp, c.p)} | {con_ic(c.vn, c.n)} | {c.p} / {c.n} |")
    c = cuenta(us, shipped, todos_idx)
    s_m, e_m = macro([cuenta(us, shipped, idx[d]) for d in datasets])
    lineas += [
        f"| **pooled** | {con_ic(c.vp, c.p)} | {con_ic(c.vn, c.n)} | {c.p} / {c.n} |",
        f"| macro mean | {pct(s_m)} | {pct(e_m)} | |",
        "",
    ]

    for crit in CRITERIOS:
        lineas += [f"## Criterion: {NOMBRES_CRITERIO[crit]}", ""]
        lineas += [
            "### Configuration chosen in each training fold",
            "",
            "| Held-out | " + " | ".join(fams) + " |",
            "|---|" + "---|" * len(fams),
        ]
        for d in datasets:
            lineas.append(
                f"| {d} | " + " | ".join(corto(fams[n][elegidos[n, crit, d]]) for n in fams) + " |"
            )
        lineas.append(
            "| *all five (deployable)* | "
            + " | ".join(corto(fams[n][finales[n, crit]]) for n in fams)
            + " |"
        )
        lineas += [
            "",
            "### LODO result on each held-out dataset",
            "",
            "| Held-out | Rule set | Sensitivity | Specificity | McNemar vs baseline: all · "
            "positives · negatives |",
            "|---|---|---|---|---|",
        ]
        base = lodo["baseline", crit]
        for d in [*datasets, "pooled", "macro"]:
            for n in fams:
                s = lodo[n, crit]
                if d == "macro":
                    sm, em = macro([cuenta(us, s, idx[x]) for x in datasets])
                    lineas.append(f"| macro mean | {n} | {pct(sm)} | {pct(em)} | |")
                    continue
                ii = todos_idx if d == "pooled" else idx[d]
                c = cuenta(us, s, ii)
                if n == "baseline":
                    mc = "—"
                else:
                    partes = []
                    for grupo in (
                        ii,
                        [i for i in ii if us[i].positiva],
                        [i for i in ii if not us[i].positiva],
                    ):
                        b, cc, p = mcnemar(us, base, s, grupo)
                        partes.append(f"{b}/{cc} p={p:.3f}")
                    mc = " · ".join(partes)
                nombre = f"**{d}**" if d == "pooled" else d
                lineas.append(
                    f"| {nombre} | {n} | {con_ic(c.vp, c.p)} | {con_ic(c.vn, c.n)} | {mc} |"
                )
        lineas.append("")

        # Per activity (negatives) and per dataset falls.
        lineas += [
            "### False alarms per activity (negative units with a `caida`, LODO)",
            "",
            "| Dataset · activity | Units | shipped | " + " | ".join(fams) + " |",
            "|---|---|---|" + "---|" * len(fams),
        ]
        grupos: dict[tuple[str, str], list[int]] = defaultdict(list)
        for i in neg_idx:
            grupos[us[i].dataset, us[i].actividad].append(i)
        for (d, a), ii in sorted(grupos.items(), key=lambda x: (datasets.index(x[0][0]), x[0][1])):
            lineas.append(
                f"| {d} · {a} | {len(ii)} | {sum(shipped[i] for i in ii)} | "
                + " | ".join(str(sum(lodo[n, crit][i] for i in ii)) for n in fams)
                + " |"
            )
        lineas += [
            "",
            "### Falls detected per activity (positive units, LODO)",
            "",
            "| Dataset · activity | Units | shipped | " + " | ".join(fams) + " |",
            "|---|---|---|" + "---|" * len(fams),
        ]
        grupos = defaultdict(list)
        for i in pos_idx:
            grupos[us[i].dataset, us[i].actividad].append(i)
        for (d, a), ii in sorted(grupos.items(), key=lambda x: (datasets.index(x[0][0]), x[0][1])):
            lineas.append(
                f"| {d} · {a} | {len(ii)} | {sum(shipped[i] for i in ii)} | "
                + " | ".join(str(sum(lodo[n, crit][i] for i in ii)) for n in fams)
                + " |"
            )
        lineas += [
            "",
            "### Safety: false recoveries, F2 exits while on the floor, confirmations, MCFD",
            "",
            'Clip datasets: fall recordings with a `recuperacion` ("rec") or an F2 silent exit '
            '("exit") after the first `caida` (GMDCSA24: after the labelled onset, clips where '
            'nobody gets up); "conf" = detected falls with a `caida_confirmada`. MCFD: within '
            "the detected fall window (person labelled on the ground); latency from the labelled "
            "onset; false alarms per hour of labelled non-fall time (8 cameras).",
            "",
            "| Rule set | URFD rec / exit | CAUCAFall rec / exit | GMDCSA24 rec / exit | "
            "UP-Fall rec / exit | MCFD rec / exit / conf | MCFD FA (per hour) | MCFD latency "
            "median (p95) |",
            "|---|---|---|---|---|---|---|---|",
        ]
        filas: list[tuple[str, dict[str, Any]]] = [
            ("shipped", extras(videos, ventanas, shipped_ev))
        ]
        filas += [(n, extras(videos, ventanas, ev_lodo(n, crit))) for n in fams]
        for n, x in filas:
            lat = x["mcfd_latencias"]
            lat_txt = (
                f"{statistics.median(lat):.2f} s ({sorted(lat)[int(0.95 * (len(lat) - 1))]:.2f})"
                if lat
                else "—"
            )

            def par(d: str, x: dict[str, Any] = x) -> str:
                rec, sal = x.get(f"{d}_rec_falsa", 0), x.get(f"{d}_salida", 0)
                return f"{rec} / {sal} of {x.get(f'{d}_detectadas', 0)}"

            lineas.append(
                f"| {n} | {par('urfd')} | {par('caucafall')} | {par('gmdcsa24')} | "
                f"{par('upfall')} | {x.get('mcfd_rec_falsa', 0)} / "
                f"{x.get('mcfd_salida_en_suelo', 0)} / {x.get('mcfd_confirmadas', 0)} of "
                f"{x.get('mcfd_detectadas', 0)} | {x['mcfd_falsas']} "
                f"({x['mcfd_falsas'] / x['mcfd_horas']:.0f}/h) | {lat_txt} |"
            )
        lineas.append("")

    # Calibrated on all five (optimistic): the deployable configuration.
    lineas += [
        "## Calibrated on all five datasets (optimistic fit, not a test)",
        "",
        "| Criterion | Rule set | Configuration | Macro sensitivity | Macro specificity |",
        "|---|---|---|---|---|",
    ]
    for crit in CRITERIOS:
        for n in fams:
            j = finales[n, crit]
            sm, em = macro([cuentas[n][j][d] for d in datasets])
            lineas.append(
                f"| {NOMBRES_CRITERIO[crit]} | {n} | {corto(fams[n][j])} | {pct(sm)} | {pct(em)} |"
            )
    lineas.append("")
    del ev_conf
    return lineas


if __name__ == "__main__":
    sys.exit(main())
