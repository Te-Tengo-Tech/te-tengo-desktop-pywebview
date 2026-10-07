"""Pose estimation service with MediaPipe Pose Landmarker.

Inference is CPU-intensive. To avoid blocking the FastAPI event loop (which receives the video
over WebSocket), it runs in a separate process (see docs/adr/0003). VIDEO mode is used, which
tracks the person across frames and loses them less often during a fall (docs/adr/0006).
"""

import asyncio
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Protocol

from detection_worker.pose.schemas import Landmark, Pose

# Child process state: one VIDEO-mode landmarker per camera, with its last timestamp.
_configuracion: tuple[str, float] = ("", 0.5)
_landmarkers: dict[str, tuple[Any, int]] = {}


class EstimadorPose(Protocol):
    async def estimar(self, jpeg: bytes, camara_id: str, instante_ms: int) -> Pose | None:
        """Returns the person's pose, or ``None`` if nobody is visible in the frame."""
        ...

    async def liberar(self, camara_id: str) -> None:
        """Releases the tracking state of a camera that disconnected."""
        ...

    def cerrar(self) -> None: ...


def crear_landmarker(ruta_modelo: str, confianza_min: float = 0.5, modo: str = "imagen") -> Any:
    """Creates the MediaPipe Pose Landmarker (model at ``ruta_modelo``).

    ``modo="imagen"`` analyzes each frame separately; ``modo="video"`` tracks the person across
    frames and requires increasing timestamps.
    """
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions

    opciones = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=ruta_modelo, delegate=BaseOptions.Delegate.CPU),
        # IMAGE: each frame is independent; it tolerates agent reconnections without requiring
        # increasing timestamps, unlike VIDEO mode.
        running_mode=vision.RunningMode.VIDEO if modo == "video" else vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=confianza_min,
        min_pose_presence_confidence=confianza_min,
        min_tracking_confidence=confianza_min,
    )
    return vision.PoseLandmarker.create_from_options(opciones)


def detectar(landmarker: Any, imagen_bgr: Any, instante_ms: int | None = None) -> Pose | None:
    """Estimates the pose in an OpenCV BGR image; ``None`` if nobody is visible.

    With a video-mode landmarker, ``instante_ms`` is required and must increase.
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
        # VIDEO mode requires increasing timestamps; if the agent reconnected with an earlier
        # clock, new tracking is started.
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
    """Estimator that runs MediaPipe in a dedicated process."""

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
