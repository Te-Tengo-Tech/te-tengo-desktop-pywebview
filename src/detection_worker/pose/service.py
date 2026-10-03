"""Servicio de estimación de pose con MediaPipe Pose Landmarker.

La inferencia es intensiva en CPU. Para no bloquear el bucle de eventos de FastAPI (que recibe
el video por WebSocket), se ejecuta en un proceso aparte (ver docs/adr/0003). Se usa el modo
VIDEO, que sigue a la persona entre fotogramas y la pierde menos durante una caída (docs/adr/0006).
"""

import asyncio
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Protocol

from detection_worker.pose.schemas import Landmark, Pose

# Estado del proceso hijo: un landmarker en modo VIDEO por cámara, con su última marca de tiempo.
_configuracion: tuple[str, float] = ("", 0.5)
_landmarkers: dict[str, tuple[Any, int]] = {}


class EstimadorPose(Protocol):
    async def estimar(self, jpeg: bytes, camara_id: str, instante_ms: int) -> Pose | None:
        """Devuelve la pose de la persona o ``None`` si el fotograma no tiene a nadie visible."""
        ...

    async def liberar(self, camara_id: str) -> None:
        """Libera el seguimiento de una cámara que se desconectó."""
        ...

    def cerrar(self) -> None: ...


def crear_landmarker(ruta_modelo: str, confianza_min: float = 0.5, modo: str = "imagen") -> Any:
    """Crea el Pose Landmarker de MediaPipe (modelo en ``ruta_modelo``).

    ``modo="imagen"`` analiza cada fotograma por separado; ``modo="video"`` sigue a la persona
    entre fotogramas y exige marcas de tiempo crecientes.
    """
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions

    opciones = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=ruta_modelo, delegate=BaseOptions.Delegate.CPU),
        # IMAGE: cada fotograma es independiente; tolera reconexiones del agente sin exigir
        # marcas de tiempo crecientes como el modo VIDEO.
        running_mode=vision.RunningMode.VIDEO if modo == "video" else vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=confianza_min,
        min_pose_presence_confidence=confianza_min,
        min_tracking_confidence=confianza_min,
    )
    return vision.PoseLandmarker.create_from_options(opciones)


def detectar(landmarker: Any, imagen_bgr: Any, instante_ms: int | None = None) -> Pose | None:
    """Estima la pose en una imagen BGR de OpenCV; ``None`` si no hay nadie visible.

    Con un landmarker en modo video, ``instante_ms`` es obligatorio y debe crecer.
    """
    import cv2
    import mediapipe as mp

    alto, ancho = imagen_bgr.shape[:2]
    rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)
    imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    resultado = (
        landmarker.detect(imagen)
        if instante_ms is None
        else landmarker.detect_for_video(imagen, instante_ms)
    )
    if not resultado.pose_landmarks:
        return None
    landmarks = tuple(
        Landmark(lm.x, lm.y, lm.visibility or 0.0) for lm in resultado.pose_landmarks[0]
    )
    return Pose(landmarks, ancho, alto)


def _inicializar(ruta_modelo: str, confianza_min: float) -> None:
    global _configuracion
    _configuracion = (ruta_modelo, confianza_min)


def _estimar(jpeg: bytes, camara_id: str, instante_ms: int) -> Pose | None:
    import cv2
    import numpy as np

    imagen = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        return None
    landmarker, ultimo_ms = _landmarkers.get(camara_id, (None, -1))
    if landmarker is None or instante_ms <= ultimo_ms:
        # El modo VIDEO exige marcas de tiempo crecientes; si el agente se reconectó con un reloj
        # anterior, se empieza un seguimiento nuevo.
        if landmarker is not None:
            landmarker.close()
        landmarker = crear_landmarker(*_configuracion, modo="video")
    _landmarkers[camara_id] = (landmarker, instante_ms)
    return detectar(landmarker, imagen, instante_ms)


def _liberar(camara_id: str) -> None:
    landmarker, _ = _landmarkers.pop(camara_id, (None, -1))
    if landmarker is not None:
        landmarker.close()


class MediaPipeEstimador:
    """Estimador que corre MediaPipe en un proceso dedicado."""

    def __init__(self, ruta_modelo: Path, confianza_min: float = 0.5) -> None:
        if not ruta_modelo.is_file():
            raise FileNotFoundError(
                f"No existe el modelo {ruta_modelo}. Descárgalo con: make modelo"
            )
        self._pool = ProcessPoolExecutor(
            max_workers=1,
            initializer=_inicializar,
            initargs=(str(ruta_modelo), confianza_min),
        )

    async def estimar(self, jpeg: bytes, camara_id: str, instante_ms: int) -> Pose | None:
        bucle = asyncio.get_running_loop()
        pose: Pose | None = await bucle.run_in_executor(
            self._pool, _estimar, jpeg, camara_id, instante_ms
        )
        return pose

    async def liberar(self, camara_id: str) -> None:
        await asyncio.get_running_loop().run_in_executor(self._pool, _liberar, camara_id)

    def cerrar(self) -> None:
        self._pool.shutdown(cancel_futures=True)
