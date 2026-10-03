"""Prueba de integración con el modelo real de MediaPipe (``make modelo`` para descargarlo)."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from detection_worker.pose.service import MediaPipeEstimador

MODELO = Path("models/pose_landmarker_lite.task")

requiere_modelo = pytest.mark.skipif(
    not MODELO.is_file(), reason="Falta el modelo: ejecuta `make modelo`"
)


@pytest.mark.integracion
@requiere_modelo
async def test_imagen_sin_personas_no_devuelve_pose() -> None:
    estimador = MediaPipeEstimador(MODELO)
    try:
        ok, jpeg = cv2.imencode(".jpg", np.zeros((480, 640, 3), dtype=np.uint8))
        assert ok
        assert await estimador.estimar(jpeg.tobytes()) is None
    finally:
        estimador.cerrar()


def test_falla_si_no_existe_el_modelo(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        MediaPipeEstimador(tmp_path / "no-existe.task")
