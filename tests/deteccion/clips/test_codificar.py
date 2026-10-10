import io
import struct
from pathlib import Path

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


def cajas(video: bytes) -> list[str]:
    """Types of the MP4's top-level boxes, in order."""
    tipos, posicion = [], 0
    while posicion + 8 <= len(video):
        tamano, tipo = struct.unpack(">I4s", video[posicion : posicion + 8])
        tipos.append(tipo.decode("latin-1"))
        assert tamano >= 8  # no 64-bit or to-the-end boxes in a small clip
        posicion += tamano
    assert posicion == len(video)
    return tipos


def test_mp4_normal_con_el_indice_al_principio() -> None:
    # Safari/AVPlayer and ExoPlayer seek poorly in a fragmented MP4 without an index.
    tipos = cajas(codificar_mp4(fotogramas(96, 640, 480, 0.125)))
    assert tipos[0] == "ftyp"
    assert "moof" not in tipos
    assert "mfra" not in tipos
    assert tipos.count("moov") == 1
    assert tipos.count("mdat") == 1
    assert tipos.index("moov") < tipos.index("mdat")


def test_perfil_constrained_baseline_sin_fotogramas_b() -> None:
    with av.open(io.BytesIO(codificar_mp4(fotogramas(16, 64, 48, 0.125))), mode="r") as contenedor:
        flujo = contenedor.streams.video[0]
        assert flujo.codec_context.profile == "Constrained Baseline"
        assert not flujo.codec_context.has_b_frames


def instantes_clave(video: bytes) -> list[float]:
    with av.open(io.BytesIO(video), mode="r") as contenedor:
        flujo = contenedor.streams.video[0]
        assert flujo.time_base is not None
        return [
            float(paquete.pts * flujo.time_base)
            for paquete in contenedor.demux(flujo)
            if paquete.is_keyframe and paquete.pts is not None
        ]


def test_un_fotograma_clave_cada_medio_segundo() -> None:
    # Every frame changes brightness (a scene cut): keyframes stay on the fixed grid anyway.
    claves = instantes_clave(codificar_mp4(fotogramas(97, 640, 480, 0.125)))
    assert claves == pytest.approx([i * 0.5 for i in range(25)])


def test_fotograma_clave_cada_medio_segundo_a_otra_tasa() -> None:
    claves = instantes_clave(codificar_mp4(fotogramas(61, 64, 48, 0.1)))  # 10 fps, GOP 5
    assert claves == pytest.approx([i * 0.5 for i in range(13)])


def test_duracion_igual_al_intervalo_del_clip() -> None:
    with av.open(io.BytesIO(codificar_mp4(fotogramas(97, 64, 48, 0.125))), mode="r") as contenedor:
        flujo = contenedor.streams.video[0]
        assert flujo.duration is not None
        assert flujo.time_base is not None
        # 12 s from the first frame to the last, plus the last frame's 1/8 s.
        assert float(flujo.duration * flujo.time_base) == pytest.approx(12.125)
        assert flujo.frames == 97


def test_se_decodifica_desde_el_inicio_y_tras_saltar_a_la_mitad() -> None:
    video = codificar_mp4(fotogramas(97, 64, 48, 0.125))
    with av.open(io.BytesIO(video), mode="r") as contenedor:
        primero = next(contenedor.decode(video=0))
        assert primero.key_frame
        assert primero.time == pytest.approx(0.0)
    with av.open(io.BytesIO(video), mode="r") as contenedor:
        flujo = contenedor.streams.video[0]
        assert flujo.time_base is not None
        contenedor.seek(round(6.2 / flujo.time_base), stream=flujo)
        cuadros = list(contenedor.decode(flujo))
        # Lands on the keyframe at 6.0 s, not back at the start of the clip.
        assert cuadros[0].key_frame
        assert cuadros[0].time == pytest.approx(6.0)
        assert len(cuadros) == 49
        assert cuadros[-1].to_ndarray(format="bgr24").shape == (48, 64, 3)


def test_no_deja_archivos_en_el_directorio(tmp_path: Path) -> None:
    codificar_mp4(fotogramas(4, 64, 48, 0.125), directorio=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_borra_el_temporal_si_falla(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fallar(ruta: str, **_: object) -> None:
        Path(ruta).write_bytes(b"a medias")
        raise ValueError("sin espacio")

    monkeypatch.setattr(av, "open", fallar)
    with pytest.raises(ErrorCodificacionError, match="sin espacio"):
        codificar_mp4(fotogramas(4, 64, 48, 0.125), directorio=tmp_path)
    assert list(tmp_path.iterdir()) == []
