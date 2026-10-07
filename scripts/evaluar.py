"""Validation of the classifier with the public URFD and CAUCAFall datasets.

Two steps:

1. ``extraer``: runs each video through MediaPipe as the worker would (480p, ``--fps``, VIDEO
   mode) and stores the poses in ``resultados/poses/``. This is the slow part and runs only once.
2. ``evaluar``: replays the stored poses through the SAME classifier as the worker and computes
   sensitivity, specificity and accuracy. With ``--barrer`` it calibrates the speed threshold
   (maximum Youden index) and validates:

   * **across datasets**: calibrates with one and measures on the other;
   * **leaving one group out**: each CAUCAFall subject and the whole of URFD are evaluated with
     the threshold calibrated without that group (11 groups).

A video counts as a "detected fall" if there is at least one ``caida`` event. False recoveries
are also counted (in URFD no person gets up after falling, according to its per-frame labels),
as well as the unstable movements emitted in activities of daily living.

Examples:
    uv run python scripts/evaluar.py extraer
    uv run python scripts/evaluar.py evaluar --velocidad-min 0.2
    uv run python scripts/evaluar.py evaluar --barrer 0.05 2.0 0.05
"""

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.schemas import Landmark, Pose

DATOS, RESULTADOS = Path("datos"), Path("resultados")
ALTO_MAX = 480
CALIDAD_JPEG = 80  # the same as the simulated agent
Secuencia = list[tuple[float, Pose | None]]


@dataclass(frozen=True, slots=True)
class Video:
    dataset: str
    nombre: str
    ruta: Path
    es_caida: bool
    actividad: str
    grupo: str  # subject in CAUCAFall; "urfd" in URFD (it does not publish each video's subject)
    recorte: tuple[int, int, int, int] | None = None

    def cache(self, variante: str) -> Path:
        return RESULTADOS / "poses" / variante / self.dataset / f"{self.nombre}.json"


def listar_videos(datos: Path = DATOS) -> list[Video]:
    videos = []
    for ruta in sorted((datos / "urfd").glob("*-cam0.mp4")):
        nombre = ruta.name.removesuffix("-cam0.mp4")
        es_caida = nombre.startswith("fall")
        actividad = "caída" if es_caida else "actividad diaria"
        # URFD MP4 files have the depth image on the left and the RGB image on the right.
        videos.append(Video("urfd", nombre, ruta, es_caida, actividad, "urfd", (320, 0, 320, 240)))
    for ruta in sorted((datos / "caucafall").glob("Subject.*/*.avi")):
        sujeto, actividad = ruta.parent.name, ruta.stem
        nombre = f"{sujeto}-{actividad}".replace(" ", "_")
        videos.append(
            Video("caucafall", nombre, ruta, actividad.startswith("Fall"), actividad, sujeto)
        )
    return videos


# ------------------------------------------------------------------------------ extraction


def _extraer(video: Video, fps: float, modelo: str, modo: str, variante: str, jpeg: bool) -> str:
    import cv2

    from te_tengo_deteccion.pose.service import crear_landmarker, detectar

    # One landmarker per video: in VIDEO mode, timestamps must increase within the video.
    landmarker = crear_landmarker(modelo, modo=modo)
    captura = cv2.VideoCapture(str(video.ruta))
    fps_fuente = captura.get(cv2.CAP_PROP_FPS) or 30.0
    fotogramas: list[list[Any]] = []
    siguiente, indice, ancho, alto = 0.0, 0, 0, 0
    while True:
        ok, imagen = captura.read()
        if not ok:
            break
        instante = indice / fps_fuente
        indice += 1
        if instante + 1e-9 < siguiente:
            continue
        siguiente += 1 / fps
        if video.recorte:
            x, y, w, h = video.recorte
            imagen = imagen[y : y + h, x : x + w]
        alto, ancho = imagen.shape[:2]
        if alto > ALTO_MAX:
            imagen = cv2.resize(imagen, (round(ancho * ALTO_MAX / alto / 2) * 2, ALTO_MAX))
            alto, ancho = imagen.shape[:2]
        if jpeg:  # same as the agent: JPEG at quality 80
            _, comprimida = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPEG])
            imagen = cv2.imdecode(comprimida, cv2.IMREAD_COLOR)  # type: ignore[assignment]
        pose = detectar(landmarker, imagen, round(instante * 1000) if modo == "video" else None)
        puntos = None
        if pose is not None:
            puntos = [
                [round(lm.x, 5), round(lm.y, 5), round(lm.visibilidad, 3)] for lm in pose.landmarks
            ]
        fotogramas.append([round(instante, 4), puntos])
    captura.release()
    landmarker.close()
    destino = video.cache(variante)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({"fps": fps, "ancho": ancho, "alto": alto, "fotogramas": fotogramas}),
        encoding="utf-8",
    )
    return video.nombre


def nombre_variante(modelo: Path, modo: str, fps: float, jpeg: bool) -> str:
    sufijo = "-jpeg" if jpeg else ""
    return f"{modelo.stem.removeprefix('pose_landmarker_')}-{modo}-{fps:g}fps{sufijo}"


def extraer(
    videos: list[Video],
    fps: float,
    modelo: Path,
    modo: str,
    jpeg: bool,
    procesos: int,
    rehacer: bool,
) -> None:
    variante = nombre_variante(modelo, modo, fps, jpeg)
    pendientes = [v for v in videos if rehacer or not v.cache(variante).exists()]
    n = len(pendientes)
    print(f"{variante}: {len(videos)} videos, {n} por procesar.")
    with ProcessPoolExecutor(procesos) as grupo:
        hechos = grupo.map(
            _extraer,
            pendientes,
            [fps] * n,
            [str(modelo)] * n,
            [modo] * n,
            [variante] * n,
            [jpeg] * n,
        )
        for i, nombre in enumerate(hechos, 1):
            print(f"  [{i}/{n}] {nombre}")


# ------------------------------------------------------------------------------ evaluation


def cargar_poses(video: Video, variante: str) -> Secuencia:
    datos = json.loads(video.cache(variante).read_text(encoding="utf-8"))
    ancho, alto = datos["ancho"], datos["alto"]
    return [
        (t, None if puntos is None else Pose(tuple(Landmark(*lm) for lm in puntos), ancho, alto))
        for t, puntos in datos["fotogramas"]
    ]


def clasificar(secuencia: Iterable[tuple[float, Pose | None]], umbrales: Umbrales) -> list[str]:
    clasificador = ClasificadorCinematico(umbrales)
    eventos: list[str] = []
    for instante, pose in secuencia:
        eventos += [e.tipo.value for e in clasificador.actualizar(instante, pose)]
    return eventos


@dataclass(frozen=True, slots=True)
class Metricas:
    vp: int
    fn: int
    vn: int
    fp: int

    @property
    def sensibilidad(self) -> float:
        return self.vp / (self.vp + self.fn) if self.vp + self.fn else float("nan")

    @property
    def especificidad(self) -> float:
        return self.vn / (self.vn + self.fp) if self.vn + self.fp else float("nan")

    @property
    def exactitud(self) -> float:
        total = self.vp + self.fn + self.vn + self.fp
        return (self.vp + self.vn) / total if total else float("nan")

    @property
    def youden(self) -> float:
        return self.sensibilidad + self.especificidad - 1


Resultado = tuple[Video, list[str]]


def detecto(eventos: list[str]) -> bool:
    return TipoEvento.CAIDA.value in eventos


def metricas(resultados: list[Resultado]) -> Metricas:
    vp = sum(1 for v, e in resultados if v.es_caida and detecto(e))
    fn = sum(1 for v, e in resultados if v.es_caida and not detecto(e))
    vn = sum(1 for v, e in resultados if not v.es_caida and not detecto(e))
    fp = sum(1 for v, e in resultados if not v.es_caida and detecto(e))
    return Metricas(vp, fn, vn, fp)


def evaluar(
    poses: dict[str, Secuencia], videos: list[Video], umbrales: Umbrales
) -> list[Resultado]:
    return [(v, clasificar(poses[v.nombre], umbrales)) for v in videos]


def calibrar(
    poses: dict[str, Secuencia], videos: list[Video], base: Umbrales, valores: list[float]
) -> float:
    """Speed threshold with the maximum Youden index; on a tie, the lowest one."""
    curva = []
    for valor in valores:
        umbrales = base.model_copy(update={"velocidad_descenso_min": valor})
        curva.append((valor, metricas(evaluar(poses, videos, umbrales))))
    return max(curva, key=lambda par: (round(par[1].youden, 6), -par[0]))[0]


# ------------------------------------------------------------------------------ report

ENCABEZADO = [
    "| Grupo | Caídas | No caídas | VP | FN | VN | FP | Sensibilidad | Especificidad | Exactitud |",
    "|---|---|---|---|---|---|---|---|---|---|",
]


def fila(nombre: str, m: Metricas) -> str:
    def pct(x: float) -> str:
        return "—" if x != x else f"{x:.1%}"  # x != x only for NaN

    return (
        f"| {nombre} | {m.vp + m.fn} | {m.vn + m.fp} | {m.vp} | {m.fn} | {m.vn} | {m.fp} | "
        f"{pct(m.sensibilidad)} | {pct(m.especificidad)} | {pct(m.exactitud)} |"
    )


def tabla(resultados: list[Resultado], por_actividad: bool = True) -> list[str]:
    lineas = [*ENCABEZADO, fila("**Total**", metricas(resultados))]
    for dataset in ("urfd", "caucafall"):
        lineas.append(fila(dataset, metricas([r for r in resultados if r[0].dataset == dataset])))
    if por_actividad:
        grupos: dict[str, list[Resultado]] = defaultdict(list)
        for r in resultados:
            grupos[f"{r[0].dataset} · {r[0].actividad}"].append(r)
        lineas += ["", "Por actividad:", "", *ENCABEZADO]
        lineas += [fila(g, metricas(rs)) for g, rs in sorted(grupos.items())]
    return lineas


def otros_eventos(resultados: list[Resultado]) -> list[str]:
    caidas_urfd = [e for v, e in resultados if v.dataset == "urfd" and v.es_caida]
    falsas_rec = sum(1 for e in caidas_urfd if TipoEvento.RECUPERACION.value in e)
    adl = [e for v, e in resultados if not v.es_caida]
    inestables_adl = sum(1 for e in adl if TipoEvento.MOVIMIENTO_INESTABLE.value in e)
    return [
        f"- Recuperaciones falsas: {falsas_rec} de {len(caidas_urfd)} caídas de URFD "
        "(en ninguna la persona se levanta).",
        f"- Actividades diarias con algún `movimiento_inestable`: {inestables_adl} de {len(adl)}.",
    ]


def errores(resultados: list[Resultado]) -> list[str]:
    lineas = []
    for v, e in resultados:
        if v.es_caida != detecto(e):
            tipo = "caída no detectada" if v.es_caida else "falsa alarma"
            lineas.append(f"- {v.dataset}/{v.nombre} ({tipo}): {' '.join(e) or 'sin eventos'}")
    return lineas or ["- Ninguno"]


def main() -> int:
    formato = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=formato)
    sub = parser.add_subparsers(dest="comando", required=True)
    p_ext = sub.add_parser("extraer", help="Extrae y guarda las poses de todos los videos")
    p_eval = sub.add_parser("evaluar", help="Clasifica las poses guardadas y calcula métricas")
    for p in (p_ext, p_eval):
        p.add_argument("--fps", type=float, default=8.0)
        p.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
        p.add_argument("--modo", choices=["imagen", "video"], default="video")
        p.add_argument(
            "--sin-jpeg", action="store_true", help="No comprimir en JPEG como el agente"
        )
    p_ext.add_argument("--procesos", type=int, default=6)
    p_ext.add_argument("--rehacer", action="store_true")
    p_eval.add_argument("--velocidad-min", type=float, help="Umbral fijo (sin calibrar)")
    p_eval.add_argument("--barrer", nargs=3, type=float, metavar=("DESDE", "HASTA", "PASO"))
    p_eval.add_argument("--persistencia", type=float, default=None, help="persistencia_erguido_s")
    p_eval.add_argument("--salida", type=Path, default=RESULTADOS / "reporte.md")
    args = parser.parse_args()

    videos = listar_videos()
    if not videos:
        print(
            "No hay videos. Ejecuta: uv run python scripts/descargar_datasets.py", file=sys.stderr
        )
        return 1
    variante = nombre_variante(args.modelo, args.modo, args.fps, not args.sin_jpeg)
    if args.comando == "extraer":
        jpeg = not args.sin_jpeg
        extraer(videos, args.fps, args.modelo, args.modo, jpeg, args.procesos, args.rehacer)
        return 0
    if not args.barrer and args.velocidad_min is None:
        print("Indica --velocidad-min o --barrer.", file=sys.stderr)
        return 1
    faltan = [v.nombre for v in videos if not v.cache(variante).exists()]
    if faltan:
        print(
            f"Faltan poses de {len(faltan)} videos. Ejecuta primero: evaluar.py extraer",
            file=sys.stderr,
        )
        return 1

    poses = {v.nombre: cargar_poses(v, variante) for v in videos}
    base = Umbrales(velocidad_descenso_min=args.velocidad_min or 1.0)
    if args.persistencia is not None:
        base = base.model_copy(update={"persistencia_erguido_s": args.persistencia})
    texto = [
        "# Validación del clasificador",
        "",
        f"Videos: {len(videos)} · Poses: `{variante}`",
        "",
    ]

    if args.barrer:
        desde, hasta, paso = args.barrer
        valores = [round(desde + i * paso, 4) for i in range(round((hasta - desde) / paso) + 1)]
        urfd = [v for v in videos if v.dataset == "urfd"]
        cauca = [v for v in videos if v.dataset == "caucafall"]

        texto += ["## 1. Validación entre datasets", "", *ENCABEZADO]
        for nombre, cal, prueba in (
            ("URFD → CAUCAFall", urfd, cauca),
            ("CAUCAFall → URFD", cauca, urfd),
        ):
            valor = calibrar(poses, cal, base, valores)
            m = metricas(
                evaluar(poses, prueba, base.model_copy(update={"velocidad_descenso_min": valor}))
            )
            texto.append(fila(f"{nombre} (v = {valor})", m))

        texto += ["", "## 2. Validación dejando un grupo fuera (11 grupos)", ""]
        fuera: list[Resultado] = []
        for grupo in sorted({v.grupo for v in videos}):
            entrenamiento = [v for v in videos if v.grupo != grupo]
            valor = calibrar(poses, entrenamiento, base, valores)
            umbrales = base.model_copy(update={"velocidad_descenso_min": valor})
            fuera += evaluar(poses, [v for v in videos if v.grupo == grupo], umbrales)
            texto.append(f"- {grupo}: v = {valor}")
        texto += ["", *tabla(fuera, por_actividad=False)]

        valor = calibrar(poses, videos, base, valores)
        base = base.model_copy(update={"velocidad_descenso_min": valor})
        texto += [
            "",
            f"## 3. Umbral final calibrado con todos los videos: v = {valor}",
            "",
            f"Se probaron {len(valores)} valores ({desde}–{hasta}, paso {paso}); se elige el de "
            "mayor índice de Youden. Este resultado es optimista (se mide con los mismos videos "
            "con que se calibra); las secciones 1 y 2 son la estimación honesta.",
            "",
        ]

    resultados = evaluar(poses, videos, base)
    texto += [f"Umbrales: `{base.model_dump()}`", "", *tabla(resultados), ""]
    texto += ["### Otros eventos", "", *otros_eventos(resultados), "", "### Videos con error", ""]
    texto += errores(resultados)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text("\n".join(texto) + "\n", encoding="utf-8")
    print("\n".join(texto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
