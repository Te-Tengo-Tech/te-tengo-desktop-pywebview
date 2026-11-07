"""Hold-out test of the shipped classifier on UP-Fall and the Multiple Cameras Fall Dataset (MCFD).

Neither dataset was used for any design decision or threshold. The thresholds are **frozen**,
exactly as in ``scripts/evaluar_holdout.py`` (``velocidad_descenso_min = 0.01`` and the published
defaults of ``Umbrales``), with and without the slow-fall rule R9. The poses come from
``evaluar.py extraer --datasets upfall mcfd`` (480p, 8 fps sampled by time, JPEG quality 80,
MediaPipe lite in VIDEO mode: the production conditions).

Main result (per video, each camera on its own, as the agent runs one webcam):

* TP/FN/TN/FP, sensitivity, specificity, accuracy, precision (95 % Wilson intervals) and F1,
  pooled over the cameras and per camera; errors per activity (UP-Fall) or scenario (MCFD);
* MCFD only, **per event**: each labelled fall is detected if a ``caida`` comes inside its
  window (from 1 s before the ``falling`` onset to the end of the ``lying on the ground``
  periods after it), and every other ``caida`` is a false alarm; latency from the labelled
  onset and false recoveries (a ``recuperacion`` while the person is labelled on the ground).

Secondary (labelled as such in the report):

* OR-fusion of the cameras of one trial or scenario (an alarm if any camera fires): UP-Fall's
  two cameras, and for MCFD every combination of 1 to 8 cameras;
* ``--logo``: leave-one-group-out recalibration of the speed over URFD, CAUCAFall, GMDCSA24,
  UP-Fall and MCFD (``evaluar.py --barrer`` protocol, Youden, ties → lowest speed).

Examples:
    uv run python scripts/evaluar.py extraer --datasets upfall mcfd --fps 8
    uv run python scripts/evaluar_multicamara.py upfall --logo
    uv run python scripts/evaluar_multicamara.py mcfd --logo
"""

import argparse
import itertools
import json
import statistics
import sys
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from barrer_rangos import SIN_R9, EventoVideo, wilson
from evaluar import (
    DATASETS,
    FPS_MCFD,
    POSICIONES_MCFD,
    RESULTADOS,
    RETARDOS_MCFD,
    Video,
    caidas_mcfd,
    cargar_poses,
    listar_videos,
    nombre_variante,
    periodos_mcfd,
)
from evaluar_holdout import (
    CAIDA,
    CONGELADOS,
    ENCABEZADO,
    TOLERANCIA_INICIO_S,
    VALORES_V,
    Conteo,
    calibrar,
    contar,
    correr,
    detecto,
    fila,
    pct,
    resumen_latencia,
)

from te_tengo_deteccion.clasificacion.estados import TipoEvento

Eventos = dict[str, list[EventoVideo]]
RECUPERACION = TipoEvento.RECUPERACION.value
# Fused alarms of several cameras closer than this are one alarm (a notification cooldown).
FUSION_S = 5.0
# MCFD scenario 23 labels two periods as "falling" (frames 1520–1595 and 3574–3614 of camera 8),
# each followed by "moving up", never by "lying on the ground": the actor goes down to the floor
# by a chair at the back of the room, and later slides from the sofa onto hands and knees, and
# gets up both times. The scenario is described as having no fall, so a ``caida`` there is
# neither a detection nor a false alarm in the event count; it is listed apart.
AMBIGUO_MCFD = 23
MARGEN_AMBIGUO_S = 5.0

FUENTES = {
    "upfall": (
        "UP-Fall Detection Dataset (Martínez-Villaseñor et al., 2019, "
        "https://doi.org/10.3390/s19091988), subset: trial 1, activities 1–5, 9 and 11, "
        "cameras 1 and 2"
    ),
    "mcfd": (
        "Multiple Cameras Fall Dataset (Auvinet et al., 2010, technical report 1350, DIRO, "
        "Université de Montréal; erratum by Feng and Meunier, 2025)"
    ),
}


# ------------------------------------------------------------------------------ helpers


def duracion(v: Video, variante: str) -> float:
    """Instant of the last sampled frame (s)."""
    datos = json.loads(v.cache(variante).read_text(encoding="utf-8"))
    fotogramas = datos["fotogramas"]
    return float(fotogramas[-1][0]) if fotogramas else 0.0


def numeros(v: Video) -> tuple[int, int]:
    """(scenario, camera) of an MCFD video."""
    return int(v.ensayo.removeprefix("chute")), int(v.camara.removeprefix("camera "))


def desfase(v: Video) -> float:
    """Seconds to subtract from the camera's instants to get the scenario's common timeline."""
    escenario, camara = numeros(v)
    return RETARDOS_MCFD[escenario][camara - 1] / FPS_MCFD


def instantes(eventos: list[EventoVideo], tipo: str) -> list[float]:
    return [i for t, i in eventos if t == tipo]


@dataclass(frozen=True, slots=True)
class Ventanas:
    """Fall windows of one MCFD video, in the camera's own timeline."""

    caidas: tuple[tuple[float, float], ...]  # (labelled onset, end of lying on the ground)
    ambiguas: tuple[tuple[float, float], ...]  # scenario 23's two "falling" periods
    periodos: tuple[tuple[float, float, int], ...]

    @property
    def etiquetado(self) -> tuple[float, float]:
        """From the first to the last labelled frame: the span the event count uses."""
        return self.periodos[0][0], self.periodos[-1][1]

    def en_etiquetado(self, instante: float) -> bool:
        inicio, fin = self.etiquetado
        return inicio <= instante <= fin

    def en_caida(self, instante: float) -> int | None:
        for k, (inicio, fin) in enumerate(self.caidas):
            if inicio - TOLERANCIA_INICIO_S <= instante <= fin:
                return k
        return None

    def en_ambigua(self, instante: float) -> bool:
        return any(a - TOLERANCIA_INICIO_S <= instante <= b for a, b in self.ambiguas)

    def codigo(self, instante: float) -> str:
        for a, b, c in self.periodos:
            if a <= instante < b:
                return POSICIONES_MCFD[c]
        return "unlabelled (before or after the labelled periods)"


def ventanas_mcfd(v: Video) -> Ventanas:
    escenario, camara = numeros(v)
    periodos = periodos_mcfd(escenario, camara)
    caidas = caidas_mcfd(periodos) if v.es_caida else []
    ambiguas = []
    if escenario == AMBIGUO_MCFD:
        ambiguas = [(p.desde, p.hasta + MARGEN_AMBIGUO_S) for p in periodos if p.codigo == 2]
    return Ventanas(
        tuple(caidas), tuple(ambiguas), tuple((p.desde, p.hasta, p.codigo) for p in periodos)
    )


# ------------------------------------------------------------------------------ per video


def contar_fusion(
    videos: Sequence[Video], alarma: Callable[[Video], bool], camaras: set[str] | None = None
) -> Conteo:
    """OR-fusion: a trial or scenario alarms if any of its cameras (in ``camaras``) does."""
    por_ensayo: dict[str, list[Video]] = defaultdict(list)
    for v in videos:
        if camaras is None or v.camara in camaras:
            por_ensayo[v.ensayo].append(v)
    vp = fn = vn = fp = 0
    for vs in por_ensayo.values():
        hay = any(alarma(v) for v in vs)
        if vs[0].es_caida:
            vp, fn = vp + hay, fn + (not hay)
        else:
            fp, vn = fp + hay, vn + (not hay)
    return Conteo(vp, fn, vn, fp)


def desglose(
    titulo: str,
    videos: Sequence[Video],
    sin: Eventos,
    con: Eventos,
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


def eventos_texto(eventos: list[EventoVideo]) -> str:
    return " ".join(f"{t}@{i:.1f}s" for t, i in eventos) or "no events"


def tabla_principal(
    videos: Sequence[Video],
    sin: Eventos,
    con: Eventos,
    a_tiempo: Callable[[Video, list[EventoVideo]], bool] | None = None,
) -> list[str]:
    lineas = [*ENCABEZADO]
    camaras = sorted({v.camara for v in videos}, key=lambda c: (len(c), c))
    for nombre, ev in (("Without R9 (R4–R8)", sin), ("**With R9 (shipped)**", con)):
        lineas.append(fila(f"{nombre}, all cameras pooled", contar(videos, ev)))
        for camara in camaras:
            vs = [v for v in videos if v.camara == camara]
            lineas.append(fila(f"{nombre}, {camara}", contar(vs, ev)))
    if a_tiempo is not None:
        for nombre, ev in (("Without R9", sin), ("With R9", con)):
            c = contar_estricto(videos, ev, a_tiempo)
            lineas.append(fila(f"{nombre}, all cameras, `caida` inside the fall window", c))
    return lineas


def contar_estricto(
    videos: Sequence[Video], ev: Eventos, a_tiempo: Callable[[Video, list[EventoVideo]], bool]
) -> Conteo:
    vp = sum(1 for v in videos if v.es_caida and a_tiempo(v, ev[v.nombre]))
    fn = sum(1 for v in videos if v.es_caida and not a_tiempo(v, ev[v.nombre]))
    vn = sum(1 for v in videos if not v.es_caida and not detecto(ev[v.nombre]))
    fp = sum(1 for v in videos if not v.es_caida and detecto(ev[v.nombre]))
    return Conteo(vp, fn, vn, fp)


# ------------------------------------------------------------------------------ UP-Fall


# Diagnostic for UP-Fall camera 2: a second person sits on a chair at the right edge of the
# image (x > 0.75) while the subject falls near the centre. The single-person pose model may
# follow the bystander instead; this flags videos where the hip is there in most pose frames.
BORDE_TESTIGO = 0.75


def fraccion_derecha(v: Video, variante: str) -> float:
    """Share of the frames with a pose whose mid-hip is at x > ``BORDE_TESTIGO``."""
    poses = [p for _, p in cargar_poses(v, variante) if p is not None]
    if not poses:
        return 0.0
    derecha = sum((p.landmarks[23].x + p.landmarks[24].x) / 2 > BORDE_TESTIGO for p in poses)
    return derecha / len(poses)


def reporte_upfall(videos: list[Video], sin: Eventos, con: Eventos, variante: str) -> list[str]:
    caidas = [v for v in videos if v.es_caida]
    adl = [v for v in videos if not v.es_caida]
    ensayos = len({v.ensayo for v in videos})
    lineas = [
        "## 1. Main result: frozen shipped thresholds, each camera on its own",
        "",
        f"Thresholds: `{CONGELADOS.model_dump()}`; without R9 = "
        f"`descenso_caida_lenta_min = {SIN_R9['descenso_caida_lenta_min']:g}`.",
        "",
        "Unit: one camera recording of one trial (a video). A fall video is a TP if it has at "
        "least one `caida`; an ADL video with any `caida` is a FP. UP-Fall has no per-frame "
        "fall onset in its camera data, so there is no onset-aware check and no latency.",
        "",
        *tabla_principal(videos, sin, con),
        "",
        f"F1 has no interval; precision depends on the {len(caidas)}/{len(adl)} fall/ADL mix.",
        "",
    ]
    lineas += desglose(
        "Per activity and camera (falls: detections; ADL: false alarms)",
        videos,
        sin,
        con,
        lambda v: f"{v.detalle.split(',')[0]} · {v.actividad} · {v.camara}",
    )
    lineas += desglose(
        "Per subject (falls: detections; ADL: false alarms; both cameras)",
        videos,
        sin,
        con,
        lambda v: f"{v.grupo.removeprefix('upfall-')} · {'falls' if v.es_caida else 'ADL'}",
    )
    lineas += ["### Other events", ""]
    for nombre, ev in (("Without R9", sin), ("With R9", con)):
        rec = [v for v in caidas if recupera_despues(ev[v.nombre])]
        ines = sum(
            TipoEvento.MOVIMIENTO_INESTABLE.value in [t for t, _ in ev[v.nombre]] for v in adl
        )
        lineas.append(
            f"- {nombre}: fall videos with a `recuperacion` after their first `caida`: "
            f"{len(rec)} of {len(caidas)} (UP-Fall does not label getting up; the 10 s fall trials "
            f"leave a 6 s safe period on the mattress); ADL videos with a "
            f"`movimiento_inestable`: {ines} of {len(adl)}."
        )
        lineas += [f"  - {v.nombre}: {eventos_texto(ev[v.nombre])}" for v in rec]
    primeras = [instantes(con[v.nombre], CAIDA)[0] for v in caidas if detecto(con[v.nombre])]
    if primeras:
        lineas += [
            "",
            "Instant of the first `caida` in the detected fall videos, from the start of the "
            f"10 s trial (with R9; descriptive, not a latency): median "
            f"{statistics.median(primeras):.2f} s, "
            f"range {min(primeras):.2f}–{max(primeras):.2f} s.",
        ]
    lineas += [
        "",
        "### Diagnostic: the bystander in camera 2",
        "",
        "In camera 2 (frontal) a second person sits at the right edge of the image. Videos in "
        f"which the mid-hip of the tracked pose is at x > {BORDE_TESTIGO:g} (that edge) in more "
        "than half of the pose frames, i.e. the pose follows the bystander rather than the "
        "subject (a heuristic checked by eye on two videos, not a per-frame label):",
        "",
        "| Camera · group (with R9) | Videos | Pose on the bystander |",
        "|---|---|---|",
    ]
    for camara in sorted({v.camara for v in videos}):
        for etiqueta, grupo in (
            ("falls detected", [v for v in caidas if detecto(con[v.nombre])]),
            ("falls missed", [v for v in caidas if not detecto(con[v.nombre])]),
            ("ADL with a false alarm", [v for v in adl if detecto(con[v.nombre])]),
            ("ADL without", [v for v in adl if not detecto(con[v.nombre])]),
        ):
            vs = [v for v in grupo if v.camara == camara]
            testigo = sum(fraccion_derecha(v, variante) > 0.5 for v in vs)
            lineas.append(f"| {camara} · {etiqueta} | {len(vs)} | {testigo} |")
    lineas += ["", "### Videos with an error (with R9)", ""]
    for v in videos:
        if v.es_caida != detecto(con[v.nombre]):
            tipo = "missed fall" if v.es_caida else "false alarm"
            lineas.append(f"- {v.nombre} ({tipo}, {v.actividad}): {eventos_texto(con[v.nombre])}")
    cambios = [
        f"- {v.nombre} ({v.actividad}): {'detected' if v.es_caida else 'false alarm'} only with R9"
        for v in videos
        if detecto(sin[v.nombre]) != detecto(con[v.nombre])
    ]
    lineas += ["", "### Videos that change with R9", "", *(cambios or ["- none"]), ""]

    lineas += [
        "## 2. Secondary: OR-fusion of the two cameras",
        "",
        f"Unit: one trial ({ensayos} trials). The trial alarms if camera 1 **or** camera 2 has "
        "a `caida`. Both cameras share the timestamps of the dataset.",
        "",
        *ENCABEZADO,
    ]
    for nombre, ev in (("Without R9", sin), ("With R9 (shipped)", con)):

        def alarma(v: Video, ev: Eventos = ev) -> bool:
            return detecto(ev[v.nombre])

        lineas.append(fila(f"{nombre}, camera 1 or 2", contar_fusion(videos, alarma)))
        lineas.append(fila(f"{nombre}, camera 1 and 2 (both must fire)", contar_y(videos, alarma)))
    lineas.append("")
    return lineas


def recupera_despues(eventos: list[EventoVideo]) -> bool:
    caidas = instantes(eventos, CAIDA)
    return bool(caidas) and any(i > caidas[0] for i in instantes(eventos, RECUPERACION))


def contar_y(videos: Sequence[Video], alarma: Callable[[Video], bool]) -> Conteo:
    """AND-fusion (for contrast): a trial alarms only if all its cameras do."""
    por_ensayo: dict[str, list[Video]] = defaultdict(list)
    for v in videos:
        por_ensayo[v.ensayo].append(v)
    vp = fn = vn = fp = 0
    for vs in por_ensayo.values():
        hay = all(alarma(v) for v in vs)
        if vs[0].es_caida:
            vp, fn = vp + hay, fn + (not hay)
        else:
            fp, vn = fp + hay, vn + (not hay)
    return Conteo(vp, fn, vn, fp)


# ------------------------------------------------------------------------------ MCFD


@dataclass(frozen=True, slots=True)
class Evento:
    """Event-level result of a set of cameras over all scenarios."""

    caidas: int
    detectadas: int
    falsas: int  # false alarms (fused within FUSION_S when several cameras)
    horas_sin_caida: float  # labelled time outside the fall windows
    ambiguas: int  # scenarios with a ``caida`` in the ambiguous windows of scenario 23
    sin_etiqueta: int  # ``caida`` outside the labelled span (not counted)

    @property
    def sensibilidad(self) -> float:
        return self.detectadas / self.caidas if self.caidas else float("nan")

    @property
    def por_hora(self) -> float:
        return self.falsas / self.horas_sin_caida if self.horas_sin_caida else float("nan")


def fundir(instantes_: list[float]) -> int:
    """Number of alarms after merging those closer than FUSION_S to the previous kept one."""
    cuenta, ultimo = 0, None
    for t in sorted(instantes_):
        if ultimo is None or t - ultimo >= FUSION_S:
            cuenta, ultimo = cuenta + 1, t
    return cuenta


def evento(
    videos: Sequence[Video],
    ev: Eventos,
    ventanas: dict[str, Ventanas],
    camaras: set[int],
) -> Evento:
    """Event-level counts of the OR-fusion of ``camaras`` (one camera: no fusion)."""
    por_escenario: dict[int, list[Video]] = defaultdict(list)
    for v in videos:
        escenario, camara = numeros(v)
        if camara in camaras:
            por_escenario[escenario].append(v)
    caidas = detectadas = falsas = ambiguas = sin_etiqueta = 0
    segundos_sin_caida = 0.0
    for vs in por_escenario.values():
        # Fall windows and video span in the common timeline (the cameras end together).
        ref = vs[0]
        comunes = [(a - desfase(ref), b - desfase(ref)) for a, b in ventanas[ref.nombre].caidas]
        caidas += len(comunes)
        hallada = [False] * len(comunes)
        fuera: list[float] = []
        hay_ambigua = False
        for v in vs:
            w = ventanas[v.nombre]
            for i in instantes(ev[v.nombre], CAIDA):
                k = w.en_caida(i)
                if k is not None:
                    hallada[k] = True
                elif w.en_ambigua(i):
                    hay_ambigua = True
                elif not w.en_etiquetado(i):
                    sin_etiqueta += 1
                else:
                    fuera.append(i - desfase(v))
        detectadas += sum(hallada)
        falsas += fundir(fuera) if len(vs) > 1 else len(fuera)
        ambiguas += hay_ambigua
        inicio, fin = ventanas[ref.nombre].etiquetado
        segundos_sin_caida += (fin - inicio) - sum(b - a for a, b in comunes)
    return Evento(caidas, detectadas, falsas, segundos_sin_caida / 3600, ambiguas, sin_etiqueta)


def reporte_mcfd(videos: list[Video], sin: Eventos, con: Eventos, variante: str) -> list[str]:
    duraciones = {v.nombre: duracion(v, variante) for v in videos}
    ventanas = {v.nombre: ventanas_mcfd(v) for v in videos}

    def a_tiempo(v: Video, eventos: list[EventoVideo]) -> bool:
        return any(ventanas[v.nombre].en_caida(i) is not None for i in instantes(eventos, CAIDA))

    caidas = [v for v in videos if v.es_caida]
    horas = sum(duraciones.values()) / 3600
    lineas = [
        "## 1. Main result: frozen shipped thresholds, each camera on its own",
        "",
        f"Thresholds: `{CONGELADOS.model_dump()}`; without R9 = "
        f"`descenso_caida_lenta_min = {SIN_R9['descenso_caida_lenta_min']:g}`.",
        "",
        f"Videos: {len(videos)} ({len(caidas)} with a fall, {len(videos) - len(caidas)} without), "
        f"{horas:.2f} h in total at the 30 fps time base.",
        "",
        "### 1.1. Per video",
        "",
        "Unit: one camera recording of one scenario. A fall scenario's video is a TP if it has "
        "any `caida` (the scenarios also contain daily activities before the fall, so this "
        "criterion can count a false alarm as a detection); the stricter row needs the `caida` "
        f"inside a fall window (from {TOLERANCIA_INICIO_S:g} s before the labelled `falling` "
        "onset to the end of the labelled `lying on the ground` periods after it). Scenarios "
        "23 and 24 (no fall) are the only negative videos: 16 of them.",
        "",
        *tabla_principal(videos, sin, con, a_tiempo),
        "",
    ]

    lineas += [
        "### 1.2. Per event (the main MCFD result)",
        "",
        "Unit: a labelled fall (23 per camera: one in each of scenarios 1–22, two in scenario 4) "
        "for sensitivity, and a `caida` outside every fall window for false alarms, over all 24 "
        "scenarios. Only the labelled span of each video counts (from its first to its last "
        "labelled frame): before it the actor is often outside the room, and after it he gets up "
        "and other people walk in, unlabelled; a `caida` there is neither a detection nor a "
        "false alarm (counted in the last column). The non-fall time is the labelled span minus "
        "the fall windows. A `caida` in one of scenario 23's two "
        "labelled `falling` periods (frames 1520–1595 and 3574–3614 of camera 8, plus "
        f"{MARGEN_AMBIGUO_S:g} s; both followed by `moving up`, never by `lying on the ground`) "
        "is neither: it is listed apart.",
        "",
        "| Camera | Falls detected, without R9 (95 % CI) | With R9 (95 % CI) | False alarms "
        "without R9 (per hour) | With R9 (per hour) | Non-fall labelled time | Scenario 23 "
        "ambiguous `falling` (with R9) | `caida` outside the labelled span (with R9) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for camara in range(1, 9):
        e_sin = evento(videos, sin, ventanas, {camara})
        e_con = evento(videos, con, ventanas, {camara})
        lineas.append(fila_evento(f"camera {camara}", e_sin, e_con))
    total_sin = sumar([evento(videos, sin, ventanas, {c}) for c in range(1, 9)])
    total_con = sumar([evento(videos, con, ventanas, {c}) for c in range(1, 9)])
    lineas.append(fila_evento("**8 cameras pooled (each on its own)**", total_sin, total_con))
    lineas.append("")

    pose = []
    for camara in range(1, 9):
        marcos = [
            p
            for v in videos
            if numeros(v)[1] == camara
            for t, p in cargar_poses(v, variante)
            if ventanas[v.nombre].en_etiquetado(t)
        ]
        pose.append(f"camera {camara} {sum(p is not None for p in marcos) / len(marcos):.0%}")
    lineas += [
        "Frames of the labelled spans with a pose from MediaPipe: " + ", ".join(pose) + ".",
        "",
        "### False alarms by labelled activity at the moment of the `caida` (with R9)",
        "",
    ]
    por_actividad: dict[str, int] = defaultdict(int)
    por_escenario: dict[str, int] = defaultdict(int)
    for v in videos:
        w = ventanas[v.nombre]
        for i in instantes(con[v.nombre], CAIDA):
            if w.en_caida(i) is None and not w.en_ambigua(i) and w.en_etiquetado(i):
                por_actividad[w.codigo(i)] += 1
                por_escenario[v.ensayo] += 1
    lineas += ["| Labelled activity | False alarms (8 cameras) |", "|---|---|"]
    lineas += [f"| {k} | {n} |" for k, n in sorted(por_actividad.items(), key=lambda x: -x[1])]
    lineas += ["", "### Per scenario (with R9)", ""]
    lineas += [
        "| Scenario | Labelled sequence | Cameras with the fall detected (window) | False alarms "
        "(8 cameras) | Cameras with a `caida` (any) |",
        "|---|---|---|---|---|",
    ]
    for ensayo in sorted({v.ensayo for v in videos}):
        vs = [v for v in videos if v.ensayo == ensayo]
        detect = (
            f"{sum(a_tiempo(v, con[v.nombre]) for v in vs)}/{len(vs)}" if vs[0].es_caida else "—"
        )
        lineas.append(
            f"| {ensayo.removeprefix('chute')} | {vs[0].detalle} | {detect} | "
            f"{por_escenario.get(ensayo, 0)} | "
            f"{sum(detecto(con[v.nombre]) for v in vs)}/{len(vs)} |"
        )
    lineas.append("")

    lineas += ["### Latency and false recoveries", ""]
    for nombre, ev in (("Without R9", sin), ("With R9", con)):
        lat, falsas_rec, total_ventanas = [], [], 0
        for v in caidas:
            w = ventanas[v.nombre]
            for k, (inicio, fin) in enumerate(w.caidas):
                total_ventanas += 1
                dentro = [i for i in instantes(ev[v.nombre], CAIDA) if w.en_caida(i) == k]
                if not dentro:
                    continue
                lat.append(dentro[0] - inicio)
                if any(dentro[0] < r <= fin for r in instantes(ev[v.nombre], RECUPERACION)):
                    falsas_rec.append(f"{v.nombre} (fall {k + 1})")
        lineas.append(
            f"- {nombre}: latency (labelled `falling` onset → first `caida` in the window) "
            f"{resumen_latencia(lat)}; false recoveries (a `recuperacion` while the person is "
            f"labelled on the ground, before the labels end) {len(falsas_rec)} of {len(lat)} "
            "detected falls" + (f": {', '.join(falsas_rec)}" if falsas_rec else "") + "."
        )
    lineas += [
        "",
        "Onsets come from the report's frame labels at the assumed 30 fps; one frame is 33 ms.",
        "",
        "### Missed fall windows (with R9)",
        "",
    ]
    perdidas: list[str] = []
    motivos: dict[str, int] = defaultdict(int)
    for v in caidas:
        w = ventanas[v.nombre]
        hechas = {w.en_caida(i) for i in instantes(con[v.nombre], CAIDA)}
        for k, (inicio, _) in enumerate(w.caidas):
            if k not in hechas:
                motivos[motivo_perdida(con[v.nombre], inicio)] += 1
                perdidas.append(
                    f"- {v.nombre} fall {k + 1} (onset {inicio:.1f} s): "
                    f"{eventos_texto(con[v.nombre])}"
                )
    lineas += [
        f"{len(perdidas)} missed of {sum(len(ventanas[v.nombre].caidas) for v in caidas)}. "
        "State of the classifier at the labelled onset: "
        + "; ".join(f"{k}: {n}" for k, n in sorted(motivos.items(), key=lambda x: -x[1]))
        + ". While the classifier is in `EN_EL_SUELO` after an earlier `caida` (a false alarm "
        "or the first fall of scenario 4), a new fall cannot raise another `caida` until a "
        "`recuperacion`.",
        "",
        *perdidas,
        "",
    ]

    lineas += [
        "## 2. Secondary: more cameras in the room (OR-fusion)",
        "",
        "An alarm if **any** camera of the set fires. Per event: a fall is detected if any "
        "camera fires inside its window; the false alarms of the cameras are put on the common "
        f"timeline (the cameras end together) and merged when closer than {FUSION_S:g} s. Mean "
        "over every combination of k of the 8 cameras (min–max in brackets).",
        "",
        "| Cameras (k) | Combinations | Falls detected, with R9 | False alarms (all 24 "
        "scenarios), with R9 | False alarms per hour, with R9 | Falls detected, without R9 | "
        "False alarms per hour, without R9 |",
        "|---|---|---|---|---|---|---|",
    ]
    for k in range(1, 9):
        combos = [set(c) for c in itertools.combinations(range(1, 9), k)]
        l_con = [evento(videos, con, ventanas, c) for c in combos]
        l_sin = [evento(videos, sin, ventanas, c) for c in combos]

        def rango(xs: list[float], fmt: str) -> str:
            media, bajo, alto = (format(x, fmt) for x in (statistics.mean(xs), min(xs), max(xs)))
            return f"{media} ({bajo}–{alto})"

        lineas.append(
            f"| {k} | {len(combos)} | {rango([e.sensibilidad * 100 for e in l_con], '.1f')} % | "
            f"{rango([float(e.falsas) for e in l_con], '.1f')} | "
            f"{rango([e.por_hora for e in l_con], '.1f')} | "
            f"{rango([e.sensibilidad * 100 for e in l_sin], '.1f')} % | "
            f"{rango([e.por_hora for e in l_sin], '.1f')} |"
        )
    lineas += [
        "",
        "Per video (scenario level, secondary, tiny negative set): a fall scenario counts if any "
        "camera fires inside a fall window; scenarios 23 and 24 are false positives if any "
        "camera fires at all.",
        "",
        *ENCABEZADO,
    ]
    for nombre, ev in (("Without R9", sin), ("With R9 (shipped)", con)):

        def alarma(v: Video, ev: Eventos = ev) -> bool:
            return a_tiempo(v, ev[v.nombre]) if v.es_caida else detecto(ev[v.nombre])

        for k in (1, 2, 8):
            conteos = [
                contar_fusion(videos, alarma, {f"camera {c}" for c in combo})
                for combo in itertools.combinations(range(1, 9), k)
            ]
            mejor = max(conteos, key=lambda c: (c.youden, c.vp))
            peor = min(conteos, key=lambda c: (c.youden, c.vp))
            etiqueta = f"{nombre}, {k} camera{'s' if k > 1 else ''}"
            if k == 8:
                lineas.append(fila(f"{etiqueta}", conteos[0]))
            else:
                lineas.append(fila(f"{etiqueta}, best of {len(conteos)}", mejor))
                lineas.append(fila(f"{etiqueta}, worst of {len(conteos)}", peor))
    lineas.append("")
    return lineas


def motivo_perdida(eventos: list[EventoVideo], inicio: float) -> str:
    """Why a fall window got no ``caida``, from the events before its onset."""
    antes = [(t, i) for t, i in eventos if i < inicio - TOLERANCIA_INICIO_S]
    ultimo = next((t for t, _ in reversed(antes) if t in (CAIDA, RECUPERACION)), None)
    if ultimo == CAIDA:
        return "already on the floor after an earlier `caida` (masked)"
    if not eventos:
        return "no event in the whole video"
    return "standing state, no `caida` in the window"


def sumar(es: list[Evento]) -> Evento:
    return Evento(
        sum(e.caidas for e in es),
        sum(e.detectadas for e in es),
        sum(e.falsas for e in es),
        sum(e.horas_sin_caida for e in es),
        sum(e.ambiguas for e in es),
        sum(e.sin_etiqueta for e in es),
    )


def fila_evento(nombre: str, sin: Evento, con: Evento) -> str:
    def sens(e: Evento) -> str:
        bajo, alto = wilson(e.detectadas, e.caidas)
        return f"{e.detectadas}/{e.caidas} = {pct(e.sensibilidad)} ({bajo:.1%}–{alto:.1%})"

    return (
        f"| {nombre} | {sens(sin)} | {sens(con)} | {sin.falsas} ({sin.por_hora:.1f}/h) | "
        f"{con.falsas} ({con.por_hora:.1f}/h) | {con.horas_sin_caida * 60:.1f} min | "
        f"{con.ambiguas} | {con.sin_etiqueta} |"
    )


# ------------------------------------------------------------------------------ LOGO


def seccion_logo(videos: list[Video], curvas: dict[str, list[Eventos]]) -> list[str]:
    grupos = sorted({v.grupo for v in videos})
    datasets = [d for d in DATASETS if any(v.dataset == d for v in videos)]
    lineas = [
        f"## 3. Secondary: leave-one-group-out recalibration over all datasets ({len(grupos)} "
        "groups)",
        "",
        "Not the main result. Unit: video (per camera). Each group is evaluated with the speed "
        f"threshold chosen by Youden ({VALORES_V[0]}–{VALORES_V[-1]}, step 0.01, ties → lowest) "
        f"on the other {len(grupos) - 1} groups; every other value stays at its default. Groups: "
        "URFD (1, subjects not published), the 10 CAUCAFall subjects, the 4 GMDCSA24 subjects, "
        "the 17 UP-Fall subjects and MCFD (1: a single actor). MCFD fall videos count as "
        "detected with any `caida`, as in section 1.1.",
        "",
    ]
    for nombre, curva in curvas.items():
        fuera: Eventos = {}
        elegidos: dict[float, int] = defaultdict(int)
        for grupo in grupos:
            valor, _ = calibrar(curva, [v for v in videos if v.grupo != grupo])
            elegidos[valor] += 1
            ev = curva[VALORES_V.index(valor)]
            fuera.update({v.nombre: ev[v.nombre] for v in videos if v.grupo == grupo})
        todos, c_todos = calibrar(curva, videos)
        congelado = curva[VALORES_V.index(0.01)]
        lineas += [
            f"### {nombre}",
            "",
            "Chosen v (folds): "
            + ", ".join(f"{v:g} ({n})" for v, n in sorted(elegidos.items()))
            + ".",
            "",
            *ENCABEZADO,
            fila(f"**All {len(videos)} videos (pooled folds)**", contar(videos, fuera)),
        ]
        for d in datasets:
            vs = [v for v in videos if v.dataset == d]
            lineas.append(fila(f"{d}, LOGO", contar(vs, fuera)))
            lineas.append(fila(f"{d}, frozen v = 0.01 (for comparison)", contar(vs, congelado)))
        lineas += [
            "",
            f"Calibrated on all {len(videos)} videos (optimistic, not a test): v = {todos:g}, "
            f"sensitivity {pct(c_todos.sensibilidad)}, specificity {pct(c_todos.especificidad)}.",
            "",
        ]
    return lineas


# ------------------------------------------------------------------------------ main


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("dataset", choices=["upfall", "mcfd"])
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--procesos", type=int, default=8)
    parser.add_argument("--logo", action="store_true", help="Secondary LOGO over all datasets")
    parser.add_argument("--salida", type=Path, help="Default: resultados/holdout-<dataset>-8fps.md")
    args = parser.parse_args()

    variante = nombre_variante(args.modelo, "video", args.fps, True)

    def preparar(datasets: Sequence[str]) -> list[Video] | None:
        videos = listar_videos(args.datos, datasets)
        faltan = [v.nombre for v in videos if not v.cache(variante).exists()]
        if not videos or faltan:
            print(
                f"Faltan poses ({variante}, {len(faltan)} videos). Ejecuta: scripts/evaluar.py "
                f"extraer --datasets {' '.join(datasets)} --fps {args.fps:g}",
                file=sys.stderr,
            )
            return None
        return videos

    videos = preparar([args.dataset])
    if videos is None:
        return 1
    sin, con = correr(videos, variante, [SIN_R9, {}], args.procesos)
    caidas = sum(v.es_caida for v in videos)
    titulo = "UP-Fall (subset)" if args.dataset == "upfall" else "the Multiple Cameras Fall Dataset"
    texto = [
        f"# Hold-out evaluation on {titulo}",
        "",
        f"Videos: {len(videos)} ({caidas} falls, {len(videos) - caidas} without a fall) · "
        f"Poses: `{variante}` · Dataset: {FUENTES[args.dataset]}",
        "",
        "Intervals: 95 % Wilson. Nothing was calibrated on this dataset for sections 1 and 2.",
        "",
    ]
    if args.dataset == "upfall":
        texto += reporte_upfall(videos, sin, con, variante)
    else:
        texto += reporte_mcfd(videos, sin, con, variante)

    if args.logo:
        todos = preparar(DATASETS)
        if todos is None:
            return 1
        ajustes = [{"velocidad_descenso_min": x} for x in VALORES_V]
        ajustes += [{"velocidad_descenso_min": x, **SIN_R9} for x in VALORES_V]
        corridas = correr(todos, variante, ajustes, args.procesos)
        n = len(VALORES_V)
        texto += seccion_logo(
            todos, {"With R9 (shipped)": corridas[:n], "Without R9": corridas[n:]}
        )

    salida = args.salida or RESULTADOS / f"holdout-{args.dataset}-{args.fps:g}fps.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(texto).rstrip() + "\n", encoding="utf-8")
    print("\n".join(texto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
