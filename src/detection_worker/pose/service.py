"""Servicio de estimación de pose con MediaPipe Pose Landmarker.

La inferencia es intensiva en CPU. Para no bloquear el bucle de eventos de FastAPI (que recibe
el video por WebSocket), se ejecuta en un proceso aparte (ver docs/adr/0003).
"""

import asyncio
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Protocol

from detection_worker.pose.schemas import Landmark, Pose

# Estado del proceso hijo: un landmarker por proceso, creado una sola vez.
_landmarker: Any = None


class EstimadorPose(Protocol):
    async def estimar(self, jpeg: bytes) -> Pose | None:
        """Devuelve la pose de la persona o ``None`` si el fotograma no tiene a nadie visible."""
        ...

    def cerrar(self) -> None: ...


def crear_landmarker(ruta_modelo: str, confianza_min: float = 0.5) -> Any:
    """Crea el Pose Landmarker de MediaPipe (modelo en ``ruta_modelo``)."""
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions

    opciones = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=ruta_modelo, delegate=BaseOptions.Delegate.CPU),
        # IMAGE: cada fotograma es independiente; tolera reconexiones del agente sin exigir
        # marcas de tiempo crecientes como el modo VIDEO.
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=confianza_min,
        min_pose_presence_confidence=confianza_min,
    )
    return vision.PoseLandmarker.create_from_options(opciones)


def detectar(landmarker: Any, imagen_bgr: Any) -> Pose | None:
    """Estima la pose en una imagen BGR de OpenCV; ``None`` si no hay nadie visible."""
    import cv2
    import mediapipe as mp

    alto, ancho = imagen_bgr.shape[:2]
    rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)
    resultado = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not resultado.pose_landmarks:
        return None
    landmarks = tuple(
        Landmark(lm.x, lm.y, lm.visibility or 0.0) for lm in resultado.pose_landmarks[0]
    )
    return Pose(landmarks, ancho, alto)


def _inicializar(ruta_modelo: str, confianza_min: float) -> None:
    global _landmarker
    _landmarker = crear_landmarker(ruta_modelo, confianza_min)


def _estimar(jpeg: bytes) -> Pose | None:
    import cv2
    import numpy as np

    imagen = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    return None if imagen is None else detectar(_landmarker, imagen)


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

    async def estimar(self, jpeg: bytes) -> Pose | None:
        bucle = asyncio.get_running_loop()
        pose: Pose | None = await bucle.run_in_executor(self._pool, _estimar, jpeg)
        return pose

    def cerrar(self) -> None:
        self._pool.shutdown(cancel_futures=True)
