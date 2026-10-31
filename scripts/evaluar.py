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

By default only URFD and CAUCAFall (the calibration data) are listed. ``--datasets`` adds the
hold-out datasets: GMDCSA24 (``docs/validation.md``, section 6; ``scripts/evaluar_holdout.py``),
UP-Fall and the Multiple Cameras Fall Dataset (section 8; ``scripts/evaluar_multicamara.py``),
which are evaluated with the shipped thresholds frozen.

A video counts as a "detected fall" if there is at least one ``caida`` event. False recoveries
are also counted (in URFD no person gets up after falling, according to its per-frame labels),
as well as the unstable movements emitted in activities of daily living.

Examples:
    uv run python scripts/evaluar.py extraer
    uv run python scripts/evaluar.py evaluar --velocidad-min 0.2
    uv run python scripts/evaluar.py evaluar --barrer 0.05 2.0 0.05
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from te_tengo_captura.captura.fuentes import Muestreador
from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.schemas import Landmark, Pose

DATOS, RESULTADOS = Path("datos"), Path("resultados")
ALTO_MAX = 480
CALIDAD_JPEG = 80  # the same as the simulated agent
Secuencia = list[tuple[float, Pose | None]]
DATASETS_VALIDACION = ("urfd", "caucafall")  # the calibration data of docs/validation.md
DATASETS = (*DATASETS_VALIDACION, "gmdcsa24", "upfall", "mcfd")
GMDCSA24 = Path("gmdcsa24") / "v2.1"  # Zenodo 10.5281/zenodo.13354453, see descargar_datasets.py
UPFALL = Path("upfall")  # one folder of timestamp-named PNG frames per camera zip of UP-Fall
MCFD = Path("mcfd")  # chuteNN/camM.avi of the Multiple Cameras Fall Dataset


@dataclass(frozen=True, slots=True)
class Video:
    dataset: str
    nombre: str
    ruta: Path
    es_caida: bool
    actividad: str
    grupo: str  # subject in CAUCAFall; "urfd" in URFD (it does not publish each video's subject)
    recorte: tuple[int, int, int, int] | None = None
    inicio_caida: float | None = None  # labelled fall onset in s, when the dataset gives it
    detalle: str = ""  # free-text description of the clip, when the dataset gives it
    condicion: str = ""  # recording condition (GMDCSA24: day, night, lights on or off)
    se_levanta: bool | None = None  # a non-fall label starts after the fall onset (GMDCSA24)
    camara: str = ""  # camera of a multi-camera recording (UP-Fall, MCFD)
    ensayo: str = ""  # the recording all cameras of one trial or scenario share (OR-fusion)
    fps_fuente: float | None = None  # real frame rate when the file header is wrong (MCFD)

    def cache(self, variante: str) -> Path:
        return RESULTADOS / "poses" / variante / self.dataset / f"{self.nombre}.json"


def listar_videos(
    datos: Path = DATOS, datasets: Sequence[str] = DATASETS_VALIDACION
) -> list[Video]:
    videos: list[Video] = []
    if "urfd" in datasets:
        videos += _videos_urfd(datos)
    if "caucafall" in datasets:
        videos += _videos_caucafall(datos)
    if "gmdcsa24" in datasets:
        videos += videos_gmdcsa24(datos)
    if "upfall" in datasets:
        videos += videos_upfall(datos)
    if "mcfd" in datasets:
        videos += videos_mcfd(datos)
    return videos


def _videos_urfd(datos: Path) -> list[Video]:
    videos = []
    for ruta in sorted((datos / "urfd").glob("*-cam0.mp4")):
        nombre = ruta.name.removesuffix("-cam0.mp4")
        es_caida = nombre.startswith("fall")
        actividad = "caída" if es_caida else "actividad diaria"
        # URFD MP4 files have the depth image on the left and the RGB image on the right.
        videos.append(Video("urfd", nombre, ruta, es_caida, actividad, "urfd", (320, 0, 320, 240)))
    return videos


def _videos_caucafall(datos: Path) -> list[Video]:
    videos = []
    for ruta in sorted((datos / "caucafall").glob("Subject.*/*.avi")):
        sujeto, actividad = ruta.parent.name, ruta.stem
        nombre = f"{sujeto}-{actividad}".replace(" ", "_")
        videos.append(
            Video("caucafall", nombre, ruta, actividad.startswith("Fall"), actividad, sujeto)
        )
    return videos


# GMDCSA24 labels each clip in Subject N/{Fall,ADL}.csv: "Classes" holds intervals such as
# "Falling (BW)[1.5 to 5]; Standing[0 to 1.5]". The fall onset is the start of the first one.
_INICIO_CAIDA = re.compile(r"Fall(?:ing)?\s*\(?\s*[A-Z]*\s*\)?\s*\[\s*([\d.]+)")
_DIRECCION = re.compile(r"Fall(?:ing)?\s*\(\s*(FW|BW|SW)")
_INTERVALO = re.compile(r"([A-Za-z]+)\s*(?:\([^\[]*)?\[\s*([\d.]+)")


def se_levanta_gmdcsa24(clases: str, inicio: float | None) -> bool | None:
    """Whether a non-fall activity is labelled to start after the fall onset."""
    if inicio is None:
        return None
    return any(
        not nombre.startswith("Fall") and float(desde) > inicio
        for nombre, desde in _INTERVALO.findall(clases)
    )


def actividad_gmdcsa24(es_caida: bool, descripcion: str, clases: str) -> str:
    """Activity group of a GMDCSA24 clip, from its description (keyword rules, in order).

    Falls are grouped by the direction label (FW, BW, SW); daily activities by what the
    person does that the classifier could confuse with a fall.
    """
    d = descripcion.lower()
    if es_caida:
        direccion = _DIRECCION.search(clases)
        nombres = {"FW": "forward", "BW": "backward", "SW": "sideways"}
        return "fall " + (nombres[direccion.group(1)] if direccion else "unlabelled direction")
    if "sleeping" in d:
        return (
            "lying down on / getting up from the floor"
            if "floor" in d
            else ("lying down on / getting up from the bed")
        )
    if any(k in d for k in ("push-up", "exercis", "yoga")):
        return "exercise (push-ups, bending, arms)"
    if "pick" in d:
        return "picking up an object (mostly from the floor)"
    if "ground" in d or "floor" in d:
        return "sitting on / getting up from the floor"
    if any(k in d for k in ("sitting", "bed", "chair")) or "Sitting" in clases:
        return "sitting on a bed or chair"
    return "walking or standing"


def videos_gmdcsa24(datos: Path = DATOS) -> list[Video]:
    """The 160 GMDCSA24 clips: the folder (Fall or ADL) is the ground truth of each video."""
    videos = []
    raiz = datos / GMDCSA24
    for carpeta in sorted(raiz.glob("Subject */")):
        sujeto = "S" + carpeta.name.removeprefix("Subject ").strip()
        for clase in ("Fall", "ADL"):
            etiquetas: dict[str, tuple[str, str, str]] = {}
            ruta_csv = carpeta / f"{clase}.csv"
            if ruta_csv.exists():
                with ruta_csv.open(encoding="utf-8", newline="") as archivo:
                    for fila in list(csv.reader(archivo))[1:]:
                        if len(fila) >= 6:
                            descripcion = ",".join(fila[4:-1]).strip()
                            etiquetas[fila[0].strip()] = (descripcion, fila[-1], fila[2].strip())
            for ruta in sorted((carpeta / clase).glob("*.mp4")):
                es_caida = clase == "Fall"
                descripcion, clases, condicion = etiquetas.get(ruta.name, ("", "", ""))
                encontrado = _INICIO_CAIDA.search(clases) if es_caida else None
                inicio = float(encontrado.group(1)) if encontrado else None
                videos.append(
                    Video(
                        "gmdcsa24",
                        f"{sujeto}-{clase}-{ruta.stem}",
                        ruta,
                        es_caida,
                        actividad_gmdcsa24(es_caida, descripcion, clases),
                        f"gmdcsa24-{sujeto}",
                        inicio_caida=inicio,
                        detalle=descripcion,
                        condicion=condicion,
                        se_levanta=se_levanta_gmdcsa24(clases, inicio) if es_caida else None,
                    )
                )
    return videos


# UP-Fall (Martínez-Villaseñor et al., 2019, table 5): activity id → description. 1–5 are falls.
ACTIVIDADES_UPFALL = {
    1: "falling forward using hands",
    2: "falling forward using knees",
    3: "falling backwards",
    4: "falling sideward",
    5: "falling sitting in empty chair",
    6: "walking",
    7: "standing",
    8: "sitting",
    9: "picking up an object",
    10: "jumping",
    11: "laying",
}
CAMARAS_UPFALL = {1: "lateral view", 2: "frontal view"}  # both 1.82 m above the floor
_CARPETA_UPFALL = re.compile(r"^Subject(\d+)Activity(\d+)Trial(\d+)Camera(\d)$")
_FOTOGRAMA_UPFALL = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d_\d\d_\d\d)\.(\d+)\.png$")


def videos_upfall(datos: Path = DATOS) -> list[Video]:
    """UP-Fall camera recordings: one folder per ``SubjectXActivityYTrialZCameraW`` zip.

    The activity id is the ground truth of each recording (1–5 falls, the rest ADL); the
    subject is the group and the trial (subject, activity, trial) is shared by both cameras.
    """
    videos = []
    for carpeta in sorted((datos / UPFALL).iterdir() if (datos / UPFALL).is_dir() else []):
        encontrado = _CARPETA_UPFALL.match(carpeta.name)
        if not carpeta.is_dir() or encontrado is None:
            continue
        sujeto, actividad, intento, camara = (int(x) for x in encontrado.groups())
        ensayo = f"S{sujeto:02d}-A{actividad:02d}-T{intento}"
        videos.append(
            Video(
                "upfall",
                f"{ensayo}-C{camara}",
                carpeta,
                actividad <= 5,
                ACTIVIDADES_UPFALL.get(actividad, f"activity {actividad}"),
                f"upfall-S{sujeto:02d}",
                detalle=f"activity {actividad}, camera {camara}",
                camara=f"camera {camara} ({CAMARAS_UPFALL.get(camara, '?')})",
                ensayo=ensayo,
            )
        )
    return videos


def fotogramas_upfall(carpeta: Path) -> list[tuple[float, Path]]:
    """PNG frames of an UP-Fall recording with their instant in s, from the file names.

    The names are capture timestamps (``2018-07-04T12_04_17.738369.png``); the instants are
    relative to the first frame. Other files (such as a duplicated ``… - copi.png``) are ignored.
    """
    marcas = []
    for ruta in carpeta.iterdir():
        encontrado = _FOTOGRAMA_UPFALL.match(ruta.name)
        if encontrado:
            segundos = datetime.strptime(encontrado.group(1), "%Y-%m-%dT%H_%M_%S").timestamp()
            marcas.append((segundos + float("0." + encontrado.group(2)), ruta))
    marcas.sort()
    return [(t - marcas[0][0], ruta) for t, ruta in marcas]


# Multiple Cameras Fall Dataset (Auvinet et al., 2010, technical report 1350, with the erratum of
# Feng and Meunier, 2025). The AVI headers say 120 fps, but the recordings run at about 30 fps
# (docs/validation.md, section 8.1), so the instants are frame / 30.
FPS_MCFD = 30.0
# Figure 3: delay in frames of each camera (1–8) per scenario; the cameras are synchronized by
# the end of the recording. Scenario 5, camera 5: 18 (erratum). They match the frame counts of
# the files for scenarios 1–23; scenario 24 (no fall) differs and is not used for timing.
RETARDOS_MCFD: dict[int, tuple[int, ...]] = {
    1: (3, 3, 8, 4, 23, 6, 6, 0),
    2: (25, 40, 0, 16, 18, 33, 33, 6),
    3: (12, 16, 8, 16, 35, 20, 20, 0),
    4: (72, 79, 78, 0, 68, 82, 83, 56),
    5: (17, 24, 5, 11, 18, 26, 28, 0),
    6: (0, 100, 106, 90, 89, 103, 104, 89),
    7: (28, 14, 16, 0, 1, 17, 18, 20),
    8: (92, 79, 0, 81, 64, 81, 82, 56),
    9: (18, 9, 1, 19, 13, 11, 12, 0),
    10: (14, 15, 19, 33, 12, 17, 19, 0),
    11: (23, 4, 20, 14, 0, 6, 7, 12),
    12: (21, 6, 13, 8, 0, 3, 7, 0),
    13: (16, 33, 0, 7, 27, 27, 36, 13),
    14: (49, 36, 38, 0, 29, 29, 7, 14),
    15: (15, 19, 19, 15, 34, 40, 23, 0),
    16: (23, 29, 0, 2, 12, 9, 3, 3),
    17: (21, 26, 15, 0, 10, 0, 29, 18),
    18: (99, 105, 86, 0, 84, 108, 109, 77),
    19: (19, 27, 16, 19, 5, 29, 0, 20),
    20: (25, 9, 3, 10, 10, 4, 5, 0),
    21: (20, 30, 22, 3, 8, 33, 32, 0),
    22: (0, 46, 51, 41, 53, 46, 47, 34),
    23: (31, 52, 52, 45, 54, 60, 50, 0),
    24: (3, 36, 7, 0, 37, 10, 33, 1),
}
POSICIONES_MCFD = {
    1: "walking, standing up",
    2: "falling",
    3: "lying on the ground",
    4: "crouching",
    5: "moving down",
    6: "moving up",
    7: "sitting",
    8: "lying on a sofa",
    9: "moving horizontally",
}
# Section 4.3: reference camera and (first frame, last frame, position code) of each period, in
# the frames of the reference camera. Erratum applied: reference cameras "11" and "10" are 8 and
# 7, and the periods of scenarios 2, 7, 8, 14 and 18 are corrected.
ETIQUETAS_MCFD: dict[int, tuple[int, tuple[tuple[int, int, int], ...]]] = {
    1: (8, ((874, 1011, 1), (1012, 1079, 6), (1080, 1108, 2), (1109, 1285, 3))),
    2: (4, ((308, 394, 1), (395, 425, 2), (426, 600, 3))),
    3: (8, ((380, 590, 1), (591, 625, 2), (626, 784, 3))),
    4: (
        6,
        ((230, 287, 1), (288, 314, 2), (315, 380, 3), (381, 600, 6), (601, 638, 2), (639, 780, 3)),
    ),
    5: (8, ((288, 310, 1), (311, 336, 2), (337, 450, 3))),
    6: (1, ((325, 582, 1), (583, 629, 2), (630, 750, 3))),
    7: (6, ((330, 490, 1), (491, 520, 2), (521, 680, 3))),
    8: (4, ((144, 350, 1), (351, 380, 2), (381, 520, 3))),
    9: (
        8,
        ((310, 472, 1), (473, 505, 5), (506, 576, 7), (577, 627, 6), (628, 651, 2), (652, 760, 3)),
    ),
    10: (8, ((315, 461, 1), (462, 511, 5), (512, 530, 2), (531, 680, 3))),
    11: (7, ((378, 463, 1), (464, 489, 2), (490, 600, 3))),
    12: (8, ((355, 604, 1), (605, 653, 2), (654, 770, 3))),
    13: (
        4,
        (
            (301, 430, 1),
            (431, 476, 5),
            (477, 525, 7),
            (526, 636, 5),
            (637, 717, 8),
            (718, 780, 6),
            (781, 822, 6),
            (823, 863, 2),
            (864, 960, 3),
        ),
    ),
    14: (
        6,
        (
            (372, 590, 1),
            (591, 620, 5),
            (621, 929, 8),
            (930, 969, 6),
            (970, 1019, 6),
            (1020, 1060, 2),
            (1061, 1115, 3),
        ),
    ),
    15: (
        8,
        ((363, 486, 1), (487, 530, 5), (531, 630, 7), (631, 754, 6), (755, 787, 2), (788, 870, 3)),
    ),
    16: (
        4,
        (
            (380, 455, 1),
            (456, 488, 5),
            (489, 530, 4),
            (531, 568, 6),
            (569, 629, 5),
            (630, 645, 4),
            (646, 670, 6),
            (671, 731, 5),
            (732, 817, 7),
            (818, 890, 6),
            (891, 940, 2),
            (941, 1000, 3),
        ),
    ),
    17: (
        6,
        (
            (251, 315, 1),
            (316, 340, 5),
            (341, 361, 4),
            (362, 388, 6),
            (389, 410, 5),
            (411, 430, 4),
            (431, 460, 6),
            (461, 531, 5),
            (532, 620, 7),
            (621, 729, 6),
            (730, 770, 2),
            (771, 860, 3),
        ),
    ),
    18: (
        6,
        ((301, 480, 1), (481, 520, 5), (521, 655, 7), (656, 684, 6), (685, 710, 2), (711, 740, 3)),
    ),
    19: (7, ((255, 498, 1), (499, 600, 2), (601, 770, 3))),
    20: (8, ((301, 544, 1), (545, 672, 2), (673, 800, 3))),
    21: (
        8,
        ((408, 537, 1), (538, 608, 5), (609, 794, 7), (795, 863, 6), (864, 901, 2), (902, 1040, 3)),
    ),
    22: (
        1,
        ((317, 586, 1), (587, 685, 5), (686, 737, 7), (738, 766, 6), (767, 808, 2), (809, 930, 3)),
    ),
    23: (
        8,
        (
            (393, 662, 1),
            (663, 688, 5),
            (689, 710, 4),
            (711, 744, 6),
            (745, 1519, 1),
            (1520, 1595, 2),
            (1596, 1661, 6),
            (1662, 1730, 1),
            (1731, 1769, 5),
            (1770, 1839, 4),
            (1840, 1886, 6),
            (1887, 2645, 1),
            (2646, 2698, 5),
            (2699, 2958, 8),
            (2959, 3035, 6),
            (3036, 3156, 1),
            (3157, 3237, 5),
            (3238, 3416, 8),
            (3417, 3573, 6),
            (3574, 3614, 2),
            (3615, 3745, 6),
            (3746, 3795, 5),
            (3796, 4042, 4),
            (4043, 4105, 6),
            (4106, 4204, 1),
            (4205, 4264, 5),
            (4265, 4440, 7),
            (4441, 4527, 6),
            (4528, 5200, 1),
        ),
    ),
    24: (
        6,
        (
            (350, 974, 1),
            (975, 1315, 1),
            (1316, 1351, 5),
            (1352, 1414, 4),
            (1415, 1450, 6),
            (1451, 1750, 1),
            (1751, 1805, 5),
            (1806, 1844, 4),
            (1845, 1884, 6),
            (1885, 2490, 1),
            (2491, 2514, 5),
            (2515, 2563, 4),
            (2564, 2587, 6),
            (2588, 3040, 1),
            (3041, 3077, 5),
            (3078, 3125, 6),
            (3126, 3243, 1),
            (3244, 3353, 1),
            (3354, 3401, 5),
            (3402, 3500, 4),
        ),
    ),
}
ESCENARIOS_CAIDA_MCFD = range(1, 23)  # 23 and 24 are described as confounding events only


@dataclass(frozen=True, slots=True)
class PeriodoMcfd:
    desde: float  # s, in the camera's own timeline (frame / FPS_MCFD)
    hasta: float
    codigo: int


def periodos_mcfd(escenario: int, camara: int) -> list[PeriodoMcfd]:
    """The labelled periods of a scenario moved to the frames of ``camara``.

    The cameras end together, so frame ``f`` of the reference camera is frame
    ``f - delay[reference] + delay[camara]`` of the other one.
    """
    referencia, periodos = ETIQUETAS_MCFD[escenario]
    retardos = RETARDOS_MCFD[escenario]
    desfase = retardos[camara - 1] - retardos[referencia - 1]
    return [
        PeriodoMcfd((a + desfase) / FPS_MCFD, (b + 1 + desfase) / FPS_MCFD, codigo)
        for a, b, codigo in periodos
    ]


def caidas_mcfd(periodos: Sequence[PeriodoMcfd]) -> list[tuple[float, float]]:
    """Fall windows ``(onset, end)``: a ``falling`` period and the ``lying on the ground`` ones
    right after it. They end with the labels: after the last labelled frame the actor often gets
    up and other people walk in, unlabelled."""
    ventanas = []
    for i, p in enumerate(periodos):
        if p.codigo != 2:
            continue
        fin, j = p.hasta, i + 1
        while j < len(periodos) and periodos[j].codigo == 3:
            fin, j = periodos[j].hasta, j + 1
        ventanas.append((p.desde, fin))
    return ventanas


def videos_mcfd(datos: Path = DATOS) -> list[Video]:
    """The 24 scenarios × 8 cameras: scenarios 1–22 hold a fall, 23 and 24 none.

    One actor performs every scenario, so the whole dataset is one group (as URFD).
    """
    videos = []
    for escenario in range(1, 25):
        for camara in range(1, 9):
            ruta = datos / MCFD / f"chute{escenario:02d}" / f"cam{camara}.avi"
            if not ruta.exists():
                continue
            es_caida = escenario in ESCENARIOS_CAIDA_MCFD
            caidas = [p for p in periodos_mcfd(escenario, camara) if p.codigo == 2]
            videos.append(
                Video(
                    "mcfd",
                    f"chute{escenario:02d}-cam{camara}",
                    ruta,
                    es_caida,
                    f"scenario {escenario}",
                    "mcfd",
                    inicio_caida=caidas[0].desde if es_caida and caidas else None,
                    detalle=" → ".join(
                        POSICIONES_MCFD[c]
                        for i, c in enumerate(x[2] for x in ETIQUETAS_MCFD[escenario][1])
                        if i == 0 or c != ETIQUETAS_MCFD[escenario][1][i - 1][2]
                    ),
                    camara=f"camera {camara}",
                    ensayo=f"chute{escenario:02d}",
                    fps_fuente=FPS_MCFD,
                )
            )
    return videos


# ------------------------------------------------------------------------------ extraction


def fuente_validacion(video: Video) -> Iterator[tuple[float, Callable[[], Any]]]:
    """Every frame of the source with its instant in s, and a function that decodes it.

    Video files: frame index / frame rate (``video.fps_fuente`` overrides a wrong header).
    UP-Fall folders: the capture timestamps in the file names, which are not evenly spaced.
    The image is decoded only for the frames the sampling keeps.
    """
    import cv2

    if video.ruta.is_dir():
        for instante, ruta in fotogramas_upfall(video.ruta):

            def leer(ruta: Path = ruta) -> Any:
                return cv2.imread(str(ruta), cv2.IMREAD_COLOR)

            yield instante, leer
        return
    captura = cv2.VideoCapture(str(video.ruta))
    fps_fuente = video.fps_fuente or captura.get(cv2.CAP_PROP_FPS) or 30.0
    indice = 0
    try:
        while captura.grab():
            yield indice / fps_fuente, lambda: captura.retrieve()[1]
            indice += 1
    finally:
        captura.release()


def fotogramas_validacion(
    video: Video, fps: float, modelo: str, modo: str = "video", jpeg: bool = True
) -> Iterator[tuple[float, Any, Pose | None]]:
    """The validation pipeline, frame by frame: (instant in s, image sent to MediaPipe, pose).

    Sampling by time at ``fps`` with the agent's ``Muestreador`` (on a constant-rate file it
    keeps the same frames as before; after a gap in the timestamps it restarts its grid, as
    the agent does with a webcam that stalls), RGB crop, 480p, JPEG quality 80 and MediaPipe
    in ``modo``. ``scripts/comparar_pipelines.py`` and the parity test check the agent
    against this.
    """
    import cv2

    from te_tengo_deteccion.pose.service import crear_landmarker, detectar

    # One landmarker per video: in VIDEO mode, timestamps must increase within the video.
    landmarker = crear_landmarker(modelo, modo=modo)
    muestreador = Muestreador(fps)
    try:
        for instante, decodificar in fuente_validacion(video):
            if not muestreador.tomar(instante):
                continue
            imagen = decodificar()
            if imagen is None:
                break
            if video.recorte:
                x, y, w, h = video.recorte
                imagen = imagen[y : y + h, x : x + w]
            alto, ancho = imagen.shape[:2]
            if alto > ALTO_MAX:
                imagen = cv2.resize(imagen, (round(ancho * ALTO_MAX / alto / 2) * 2, ALTO_MAX))
            if jpeg:  # same as the agent: JPEG at quality 80
                _, comprimida = cv2.imencode(
                    ".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPEG]
                )
                imagen = cv2.imdecode(comprimida, cv2.IMREAD_COLOR)
            ms = round(instante * 1000) if modo == "video" else None
            yield instante, imagen, detectar(landmarker, imagen, ms)
    finally:
        landmarker.close()


def _extraer(video: Video, fps: float, modelo: str, modo: str, variante: str, jpeg: bool) -> str:
    fotogramas: list[list[Any]] = []
    ancho, alto = 0, 0
    for instante, imagen, pose in fotogramas_validacion(video, fps, modelo, modo, jpeg):
        alto, ancho = imagen.shape[:2]
        puntos = None
        if pose is not None:
            puntos = [
                [round(lm.x, 5), round(lm.y, 5), round(lm.visibilidad, 3)] for lm in pose.landmarks
            ]
        fotogramas.append([round(instante, 4), puntos])
    destino = video.cache(variante)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({"fps": fps, "ancho": ancho, "alto": alto, "fotogramas": fotogramas}),
        encoding="utf-8",
    )
    return video.nombre


def nombre_variante(
    modelo: Path, modo: str, fps: float, jpeg: bool, pipeline: str = "validacion"
) -> str:
    """Cache folder. ``pipeline="agente"``: poses produced by the desktop agent's capture loop
    (``scripts/comparar_pipelines.py --guardar``) instead of ``extraer``."""
    sufijo = "-jpeg" if jpeg else ""
    sufijo += "" if pipeline == "validacion" else f"-{pipeline}"
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
    for dataset in sorted({r[0].dataset for r in resultados}, key=DATASETS.index):
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
        p.add_argument(
            "--datasets",
            nargs="+",
            choices=DATASETS,
            default=list(DATASETS_VALIDACION),
            help="Datasets a usar (por defecto, los de calibración: urfd caucafall)",
        )
    p_ext.add_argument("--procesos", type=int, default=6)
    p_ext.add_argument("--rehacer", action="store_true")
    p_eval.add_argument(
        "--pipeline",
        choices=["validacion", "agente"],
        default="validacion",
        help="Poses de `extraer` o del bucle del agente (comparar_pipelines.py --guardar)",
    )
    p_eval.add_argument("--velocidad-min", type=float, help="Umbral fijo (sin calibrar)")
    p_eval.add_argument("--barrer", nargs=3, type=float, metavar=("DESDE", "HASTA", "PASO"))
    p_eval.add_argument("--persistencia", type=float, default=None, help="persistencia_erguido_s")
    p_eval.add_argument("--salida", type=Path, default=RESULTADOS / "reporte.md")
    args = parser.parse_args()

    videos = listar_videos(DATOS, args.datasets)
    if not videos:
        print(
            "No hay videos. Ejecuta: uv run python scripts/descargar_datasets.py", file=sys.stderr
        )
        return 1
    pipeline = getattr(args, "pipeline", "validacion")
    variante = nombre_variante(args.modelo, args.modo, args.fps, not args.sin_jpeg, pipeline)
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
            f"Faltan poses de {len(faltan)} videos. Ejecuta primero: "
            + (
                "evaluar.py extraer"
                if pipeline == "validacion"
                else "comparar_pipelines.py --todos --guardar"
            ),
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

        n_grupos = len({v.grupo for v in videos})
        texto += ["", f"## 2. Validación dejando un grupo fuera ({n_grupos} grupos)", ""]
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
