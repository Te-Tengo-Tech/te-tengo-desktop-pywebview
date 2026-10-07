import io

import av
import cv2
import numpy as np
import pytest

from te_tengo_deteccion.clips.codificar import ErrorCodificacionError, codificar_mp4


def fotogramas(n: int, ancho: int, alto: int, paso: float) -> list[tuple[float, bytes]]:
    resultado = []
    for i in range(n):
        ok, jpeg = cv2.imencode(".jpg", np.full((alto, ancho, 3), i * 20 % 256, dtype=np.uint8))
        assert ok
        resultado.append((i * paso, jpeg.tobytes()))
    return resultado


def abrir(video: bytes) -> tuple[str, str, int, int, int, float]:
    with av.open(io.BytesIO(video), mode="r") as contenedor:
        flujo = contenedor.streams.video[0]
        cuadros = len(list(contenedor.decode(flujo)))
        return (
            flujo.codec_context.name,
            flujo.codec_context.pix_fmt or "",
            flujo.codec_context.width,
            flujo.codec_context.height,
            cuadros,
            float(flujo.average_rate or 0),
        )


def test_codifica_jpeg_a_mp4_h264() -> None:
    video = codificar_mp4(fotogramas(96, 640, 480, 0.125))  # 12 s at 8 fps, like a real clip
    assert video[4:8] == b"ftyp"
    codec, pix_fmt, ancho, alto, cuadros, fps = abrir(video)
    assert (codec, pix_fmt, ancho, alto, cuadros) == ("h264", "yuv420p", 640, 480, 96)
    assert fps == pytest.approx(8.0)


def test_codifica_ancho_impar_de_webcam_16_9() -> None:
    _, _, ancho, alto, cuadros, _ = abrir(codificar_mp4(fotogramas(6, 853, 480, 0.125)))
    assert (ancho, alto, cuadros) == (852, 480, 6)


def test_rechaza_clip_de_un_solo_fotograma() -> None:
    with pytest.raises(ValueError, match="dos fotogramas"):
        codificar_mp4([(0.0, b"\xff\xd8")])


def test_fotograma_invalido() -> None:
    with pytest.raises(ErrorCodificacionError):
        codificar_mp4([(0.0, b"no"), (0.1, b"jpeg")])


def test_mismo_instante_usa_5_fps() -> None:
    *_, cuadros, fps = abrir(codificar_mp4(fotogramas(3, 64, 48, 0.0)))
    assert cuadros == 3
    assert fps == pytest.approx(5.0)


def test_fotogramas_de_distinto_tamano_se_ajustan_al_primero() -> None:
    mezcla = [*fotogramas(3, 640, 480, 0.125), (0.5, fotogramas(1, 320, 240, 0)[0][1])]
    _, _, ancho, alto, cuadros, _ = abrir(codificar_mp4(mezcla))
    assert (ancho, alto, cuadros) == (640, 480, 4)
