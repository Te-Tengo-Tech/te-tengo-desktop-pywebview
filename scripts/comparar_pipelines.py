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
import sys
import tempfile
from collections.abc import Callable
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

    instante_ms: int
    forma: tuple[int, ...]
    tipo: str
    pose: bool
    visibilidades: tuple[float, ...]
    fase: str
    eventos: tuple[str, ...]


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
                round(instante * 1000),
                tuple(imagen.shape),
                f"{imagen.dtype} BGR",
                pose is not None,
                _visibilidades(pose),
                clasificador.fase.value,
                tuple(e.tipo.value for e in eventos),
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
            registros.append(
                Registro(ms, forma, tipo, pose is not None, _visibilidades(pose), fase, nombres)
            )
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


def _texto(r: Registro | None) -> str:
    if r is None:
        return "—"
    vis = " ".join(f"{v:.2f}" for v in r.visibilidades) if r.pose else "sin pose"
    eventos = f" [{' '.join(r.eventos)}]" if r.eventos else ""
    return f"{'x'.join(map(str, r.forma))} {r.tipo} {vis:<29} {r.fase}{eventos}"


def comparar(nombre: str, caminos: dict[str, list[Registro]], resumen: bool) -> bool:
    base = caminos["validacion"]
    iguales = True
    print(f"\n== {nombre}")
    for camino, registros in caminos.items():
        poses = sum(r.pose for r in registros)
        eventos = [(r.instante_ms, e) for r in registros for e in r.eventos]
        mismos = [(r.instante_ms, r.pose, r.fase, r.eventos) for r in registros] == [
            (r.instante_ms, r.pose, r.fase, r.eventos) for r in base
        ]
        iguales = iguales and (mismos or camino == "agente-mp4v")
        marca = "" if camino == "validacion" else (" = validacion" if mismos else " ≠ validacion")
        print(f"  {camino:<11} pose en {poses}/{len(registros)} · eventos {eventos}{marca}")
    if resumen:
        return iguales
    filas = max(len(r) for r in caminos.values())
    print(f"  {'ms':>6} | " + " | ".join(caminos))
    for i in range(filas):
        actuales = [r[i] if i < len(r) else None for r in caminos.values()]
        ms = next(r.instante_ms for r in actuales if r is not None)
        claves = {
            None if r is None else (r.instante_ms, r.pose, r.fase, r.eventos) for r in actuales
        }
        distinto = len(claves) > 1
        print(f"{'*' if distinto else ' '} {ms:>6} | " + " | ".join(_texto(r) for r in actuales))
    return iguales


def main() -> int:
    a = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    a.add_argument("videos", nargs="+", help="Nombres como en evaluar.py (fall-01, adl-01, …)")
    a.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    a.add_argument("--recodificado", action="store_true", help="Añade el clip recortado con mp4v")
    a.add_argument("--resumen", action="store_true", help="Solo el resumen de cada video")
    args = a.parse_args()
    if not args.modelo.is_file():
        print(f"Falta el modelo {args.modelo}. Ejecuta: make modelo", file=sys.stderr)
        return 1
    videos = {v.nombre: v for v in evaluar.listar_videos()}
    faltan = [n for n in args.videos if n not in videos]
    if faltan:
        print(f"No están en datos/: {', '.join(faltan)}", file=sys.stderr)
        return 1
    umbrales = Umbrales(**UMBRALES_CALIBRADOS)  # the agent's thresholds without overrides
    iguales = True
    with tempfile.TemporaryDirectory() as temporal:
        for nombre in args.videos:
            video = videos[nombre]
            caminos = {
                "validacion": por_validacion(video, args.modelo, umbrales),
                "agente": por_agente(video.ruta, video.recorte, args.modelo, umbrales),
            }
            if args.recodificado:
                clip = recodificar_mp4v(video, Path(temporal) / f"{nombre}-rgb.mp4")
                caminos["agente-mp4v"] = por_agente(clip, None, args.modelo, umbrales)
            iguales = comparar(nombre, caminos, args.resumen) and iguales
    print("\nLos caminos coinciden." if iguales else "\nLos caminos NO coinciden.")
    return 0 if iguales else 1


if __name__ == "__main__":
    sys.exit(main())
