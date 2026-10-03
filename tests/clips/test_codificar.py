import shutil

import cv2
import numpy as np
import pytest

from detection_worker.clips.service import codificar_mp4


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg no está instalado")
def test_codifica_jpeg_a_mp4() -> None:
    fotogramas = []
    for i in range(10):
        imagen = np.full((480, 640, 3), i * 20, dtype=np.uint8)
        ok, jpeg = cv2.imencode(".jpg", imagen)
        assert ok
        fotogramas.append((i * 0.2, jpeg.tobytes()))
    video = codificar_mp4(fotogramas)
    assert video[4:8] == b"ftyp"


def test_rechaza_clip_de_un_solo_fotograma() -> None:
    with pytest.raises(ValueError, match="dos fotogramas"):
        codificar_mp4([(0.0, b"\xff\xd8")])


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg no está instalado")
def test_codifica_ancho_impar_de_webcam_16_9() -> None:
    fotogramas = []
    for i in range(6):
        ok, jpeg = cv2.imencode(".jpg", np.full((480, 853, 3), i * 30, dtype=np.uint8))
        assert ok
        fotogramas.append((i * 0.125, jpeg.tobytes()))
    assert codificar_mp4(fotogramas)[4:8] == b"ftyp"
