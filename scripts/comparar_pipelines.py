"""Compares, frame by frame, the validation pipeline with the desktop agent's pipeline.

* ``validacion``: ``scripts/evaluar.py extraer`` (``fotogramas_validacion``) and the classifier fed
  with the poses as the cache stores them (rounded), exactly as ``evaluar.py evaluar`` does.
* ``agente``: ``te_tengo_captura`` as it runs: ``FuenteArchivo`` → ``Captador`` (time sampler,
  480p, JPEG 80) → ``EstimadorMediaPipe`` (VIDEO mode) → ``BucleCaptura`` → events. URFD files are
  cropped in memory to their RGB half, the same pixels the validation uses.
* ``agente-mp4v`` (with ``--recodificado``): the agent on the RGB half written to a new MP4 with
  OpenCV's ``mp4v`` codec, as an earlier version of ``docs/INSTALLATION.md`` told users to do.

For each frame it prints the timestamp sent to MediaPipe, the image (shape, dtype, colour order),
whether a pose was found, the visibility of the key landmarks and the classifier phase. It ends
with the events of each path and exits with 1 if the paths differ.

Examples:
    uv run python scripts/comparar_pipelines.py fall-01 fall-03 adl-01
    uv run python scripts/comparar_pipelines.py fall-01 --recodificado --resumen
"""

import argparse
import json
import sys
import tempfile
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import evaluar

from te_tengo_captura.backend.modelos import EventoAgente
from te_tengo_captura.captura.bucle import BucleCaptura
from te_tengo_captura.captura.fuentes import Captador, FuenteArchivo, Imagen
from te_tengo_captura.captura.pose import EstimadorMediaPipe
from te_tengo_captura.config import UMBRALES_CALIBRADOS
from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.schemas import Indice, Landmark, Pose

# Key landmarks: shoulders, hips and ankles (left, right).
CLAVE = (
    Indice.HOMBRO_IZQUIERDO,
    Indice.HOMBRO_DERECHO,
    Indice.CADERA_IZQUIERDA,
    Indice.CADERA_DERECHA,
    Indice.TOBILLO_IZQUIERDO,
    Indice.TOBILLO_DERECHO,
)


@dataclass(frozen=True, slots=True)
class Registro:
    """One frame as MediaPipe and the classifier saw it."""

    instante: float
    instante_ms: int
    forma: tuple[int, ...]
    tipo: str
    pose: bool
    visibilidades: tuple[float, ...]
    fase: str
    eventos: tuple[str, ...]
    puntos: list[list[float]] | None  # landmarks rounded as in the cache of evaluar.py

    @property
    def clave(self) -> tuple[Any, ...]:
        """What must match between paths: the poses as stored for the validation and the
        classifier's phase and events."""
        return (self.instante_ms, self.forma, self.puntos, self.fase, self.eventos)


def _puntos(pose: Pose | None) -> list[list[float]] | None:
    if pose is None:
        return None
    return [[round(lm.x, 5), round(lm.y, 5), round(lm.visibilidad, 3)] for lm in pose.landmarks]


def _visibilidades(pose: Pose | None) -> tuple[float, ...]:
    return () if pose is None else tuple(round(pose.landmarks[i].visibilidad, 2) for i in CLAVE)


def _redondeada(pose: Pose | None) -> Pose | None:
    """The pose as ``evaluar.py extraer`` stores it in the cache."""
    if pose is None:
        return None
    puntos = tuple(
        Landmark(round(lm.x, 5), round(lm.y, 5), round(lm.visibilidad, 3)) for lm in pose.landmarks
    )
    return Pose(puntos, pose.ancho, pose.alto)


# ------------------------------------------------------------------ validation


def por_validacion(
    video: evaluar.Video, modelo: Path, umbrales: Umbrales, fps: float = 8.0
) -> list[Registro]:
    clasificador = ClasificadorCinematico(umbrales)
    registros = []
    for instante, imagen, pose in evaluar.fotogramas_validacion(video, fps, str(modelo)):
        t = round(instante, 4)
        eventos = clasificador.actualizar(t, _redondeada(pose))
        registros.append(
            Registro(
                t,
                round(instante * 1000),
                tuple(imagen.shape),
                f"{imagen.dtype} BGR",
                pose is not None,
                _visibilidades(pose),
                clasificador.fase.value,
                tuple(e.tipo.value for e in eventos),
                _puntos(pose),
            )
        )
    return registros


# ------------------------------------------------------------------ agent


class FuenteRecortada:
    """A ``FuenteVideo`` that hands on only a region of each frame (the URFD RGB half)."""

    def __init__(self, fuente: FuenteArchivo, recorte: tuple[int, int, int, int] | None) -> None:
        self.fuente = fuente
        self._recorte = recorte

    def abrir(self) -> bool:
        return self.fuente.abrir()

    def leer(self) -> tuple[float, Imagen] | None:
        lectura = self.fuente.leer()
        if lectura is None or self._recorte is None:
            return lectura
        x, y, w, h = self._recorte
        instante, imagen = lectura
        return instante, imagen[y : y + h, x : x + w]

    def cerrar(self) -> None:
        self.fuente.cerrar()


class EstimadorRegistrador:
    """Wraps the agent's estimator and records what it is given and what it returns."""

    def __init__(self, estimador: EstimadorMediaPipe) -> None:
        self._estimador = estimador
        self.vistos: list[tuple[int, tuple[int, ...], str, Pose | None]] = []

    def estimar(self, imagen: Imagen, instante_ms: int) -> Pose | None:
        pose = self._estimador.estimar(imagen, instante_ms)
        self.vistos.append((instante_ms, tuple(imagen.shape), f"{imagen.dtype} BGR", pose))
        return pose

    def reiniciar(self) -> None:
        self._estimador.reiniciar()

    def cerrar(self) -> None:
        self._estimador.cerrar()


class _Bandeja:
    def __init__(self) -> None:
        self.eventos: list[EventoAgente] = []

    def agregar_evento(self, evento: EventoAgente) -> None:
        self.eventos.append(evento)

    def agregar_clip(self, evento_id: str, mp4: bytes) -> None:
        pass


def por_agente(
    ruta: Path,
    recorte: tuple[int, int, int, int] | None,
    modelo: Path,
    umbrales: Umbrales,
    estimador: Callable[[Path], EstimadorMediaPipe] = EstimadorMediaPipe,
) -> list[Registro]:
    archivo = FuenteArchivo(ruta)
    registrador = EstimadorRegistrador(estimador(modelo))
    bucle = BucleCaptura(
        Captador(FuenteRecortada(archivo, recorte), reloj=lambda: 0.0),
        registrador,
        umbrales,
        _Bandeja(),
        permitida=lambda: True,
        codificar=lambda fotogramas: b"",
        ejecutar_clip=lambda tarea: None,
    )
    registros = []
    try:
        while not archivo.agotada:
            antes = len(registrador.vistos)
            eventos = bucle.paso()
            if len(registrador.vistos) == antes:
                continue
            ms, forma, tipo, pose = registrador.vistos[-1]
            fase = bucle._clasificador.fase.value
            nombres = tuple(e.tipo.value for e in eventos)
            vis = _visibilidades(pose)
            registro = Registro(
                round(ms / 1000, 4),
                ms,
                forma,
                tipo,
                pose is not None,
                vis,
                fase,
                nombres,
                _puntos(pose),
            )
            registros.append(registro)
    finally:
        bucle.cerrar()
    return registros


def recodificar_mp4v(video: evaluar.Video, destino: Path) -> Path:
    """The RGB half written with ``mp4v``, as the earlier INSTALLATION.md recipe did."""
    import cv2

    origen = cv2.VideoCapture(str(video.ruta))
    fps = origen.get(cv2.CAP_PROP_FPS) or 30.0
    x, y, w, h = video.recorte or (0, 0, 0, 0)
    salida: Any = None
    while True:
        ok, imagen = origen.read()
        if not ok:
            break
        if video.recorte:
            imagen = imagen[y : y + h, x : x + w]
        if salida is None:
            alto, ancho = imagen.shape[:2]
            salida = cv2.VideoWriter(
                str(destino), cv2.VideoWriter.fourcc(*"mp4v"), fps, (ancho, alto)
            )
        salida.write(imagen)
    origen.release()
    if salida is not None:
        salida.release()
    return destino


# ------------------------------------------------------------------ report


def guardar_poses(video: evaluar.Video, variante: str, registros: list[Registro]) -> None:
    """Stores the agent's poses in the cache format of ``evaluar.py`` (``--pipeline agente``)."""
    alto, ancho = registros[-1].forma[:2] if registros else (0, 0)
    fotogramas = [[r.instante, r.puntos] for r in registros]
    destino = video.cache(variante)
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = {"fps": 8.0, "ancho": ancho, "alto": alto, "fotogramas": fotogramas}
    destino.write_text(json.dumps(datos), encoding="utf-8")


def _texto(r: Registro | None) -> str:
    if r is None:
        return "—"
    vis = " ".join(f"{v:.2f}" for v in r.visibilidades) if r.pose else "sin pose"
    eventos = f" [{' '.join(r.eventos)}]" if r.eventos else ""
    return f"{'x'.join(map(str, r.forma))} {r.tipo} {vis:<29} {r.fase}{eventos}"


def comparar(nombre: str, caminos: dict[str, list[Registro]], resumen: bool) -> tuple[bool, str]:
    """Whether the agent matches the validation, and the report of the video."""
    base = [r.clave for r in caminos["validacion"]]
    iguales = True
    lineas = [f"== {nombre}"]
    for camino, registros in caminos.items():
        poses = sum(r.pose for r in registros)
        eventos = [(r.instante_ms, e) for r in registros for e in r.eventos]
        mismos = [r.clave for r in registros] == base
        iguales = iguales and (mismos or camino == "agente-mp4v")
        marca = "" if camino == "validacion" else (" = validacion" if mismos else " ≠ validacion")
        lineas.append(f"  {camino:<11} pose en {poses}/{len(registros)} · eventos {eventos}{marca}")
    if not resumen:
        lineas.append(f"  {'ms':>6} | " + " | ".join(caminos))
        for i in range(max(len(r) for r in caminos.values())):
            actuales = [r[i] if i < len(r) else None for r in caminos.values()]
            ms = next(r.instante_ms for r in actuales if r is not None)
            distinto = len({None if r is None else r.clave for r in actuales}) > 1
            fila = " | ".join(_texto(r) for r in actuales)
            lineas.append(f"{'*' if distinto else ' '} {ms:>6} | {fila}")
    return iguales, "\n".join(lineas)


def comparar_video(
    video: evaluar.Video, modelo: Path, recodificado: bool, resumen: bool, guardar: str | None
) -> tuple[bool, str]:
    umbrales = Umbrales(**UMBRALES_CALIBRADOS)  # the agent's thresholds without overrides
    caminos = {
        "validacion": por_validacion(video, modelo, umbrales),
        "agente": por_agente(video.ruta, video.recorte, modelo, umbrales),
    }
    if recodificado:
        with tempfile.TemporaryDirectory() as temporal:
            clip = recodificar_mp4v(video, Path(temporal) / f"{video.nombre}-rgb.mp4")
            caminos["agente-mp4v"] = por_agente(clip, None, modelo, umbrales)
    if guardar:
        guardar_poses(video, guardar, caminos["agente"])
    return comparar(video.nombre, caminos, resumen)


def main() -> int:
    a = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    a.add_argument("videos", nargs="*", help="Nombres como en evaluar.py (fall-01, adl-01, …)")
    a.add_argument("--todos", action="store_true", help="Todos los videos de datos/ (resumen)")
    a.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    a.add_argument("--recodificado", action="store_true", help="Añade el clip recortado con mp4v")
    a.add_argument("--resumen", action="store_true", help="Solo el resumen de cada video")
    a.add_argument(
        "--guardar",
        action="store_true",
        help="Guarda las poses del agente para `evaluar.py evaluar --pipeline agente`",
    )
    a.add_argument("--procesos", type=int, default=6)
    args = a.parse_args()
    if not args.modelo.is_file():
        print(f"Falta el modelo {args.modelo}. Ejecuta: make modelo", file=sys.stderr)
        return 1
    todos = {v.nombre: v for v in evaluar.listar_videos()}
    nombres = list(todos) if args.todos else args.videos
    faltan = [n for n in nombres if n not in todos]
    if not nombres or faltan:
        print(f"No están en datos/: {', '.join(faltan) or 'ningún video'}", file=sys.stderr)
        return 1
    resumen = args.resumen or args.todos
    guardar = (
        evaluar.nombre_variante(args.modelo, "video", 8.0, True, "agente") if args.guardar else None
    )
    distintos = []
    with ProcessPoolExecutor(args.procesos) as grupo:
        tareas = [
            grupo.submit(comparar_video, todos[n], args.modelo, args.recodificado, resumen, guardar)
            for n in nombres
        ]
        for nombre, tarea in zip(nombres, tareas, strict=True):
            iguales, texto = tarea.result()
            print(texto, flush=True)
            if not iguales:
                distintos.append(nombre)
    print(
        f"\nEl agente coincide con la validación en {len(nombres) - len(distintos)} "
        f"de {len(nombres)} videos."
    )
    if distintos:
        print(f"Distintos: {', '.join(distintos)}")
    return 1 if distintos else 0


if __name__ == "__main__":
    sys.exit(main())
