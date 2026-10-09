from itertools import pairwise
from pathlib import Path

import av
import numpy as np
import pytest

from te_tengo_captura.captura.publicador import PublicadorPyAV, calentar_codificador


def test_codifica_h264_de_baja_latencia_compatible_con_webrtc(tmp_path: Path) -> None:
    destino = tmp_path / "vivo.mkv"
    publicador = PublicadorPyAV(str(destino))
    for i in range(20):  # 1.33 s at 15 fps
        imagen = np.full((480, 640, 3), i * 10, dtype=np.uint8)
        publicador.publicar(imagen, 100.0 + i / 15)  # instants of a webcam's monotonic clock
    publicador.cerrar()
    publicador.cerrar()  # idempotent

    with av.open(str(destino)) as contenedor:
        flujo = contenedor.streams.video[0]
        assert flujo.codec_context.name == "h264"
        assert flujo.codec_context.profile == "Constrained Baseline"  # WebRTC in every browser
        assert (flujo.codec_context.width, flujo.codec_context.height) == (640, 480)
        assert len(contenedor.streams.audio) == 0
        paquetes = [p for p in contenedor.demux(flujo) if p.size]
        cuadros = [c for p in paquetes for c in p.decode()]
    assert len(paquetes) == 20  # zerolatency: every frame comes out, none held back
    claves = [i for i, p in enumerate(paquetes) if p.is_keyframe]
    assert claves == [0, 8, 16]  # the first frame, then one keyframe every half second
    assert {int(c.pict_type) for c in cuadros} == {1, 2}  # I and P frames, no B-frames
    tiempos = [float(p.pts * p.time_base) for p in paquetes if p.pts is not None]
    assert tiempos[0] == pytest.approx(0.0)
    assert tiempos[-1] == pytest.approx(19 / 15, abs=0.01)


def test_cada_publicacion_empieza_con_un_cuadro_clave(tmp_path: Path) -> None:
    for n in range(2):
        destino = tmp_path / f"vivo-{n}.mkv"
        publicador = PublicadorPyAV(str(destino))
        for i in range(5):
            publicador.publicar(np.full((240, 320, 3), 40 * n + i, dtype=np.uint8), 7.0 + i / 15)
        publicador.cerrar()
        with av.open(str(destino)) as contenedor:
            paquetes = [p for p in contenedor.demux(contenedor.streams.video[0]) if p.size]
        assert [p.is_keyframe for p in paquetes] == [True, False, False, False, False]


def test_calentar_el_codificador_no_escribe_nada(tmp_path: Path) -> None:
    calentar_codificador(640, 480)
    calentar_codificador(854, 480, fps=10)
    assert list(tmp_path.iterdir()) == []


def test_marca_los_cuadros_a_ritmo_constante_aunque_la_captura_oscile(tmp_path: Path) -> None:
    # Frames picked from a jittery webcam: the real intervals wobble around 1/15 s.
    destino = tmp_path / "vivo.mkv"
    publicador = PublicadorPyAV(str(destino))
    generador = np.random.default_rng(3)
    for i in range(30):
        instante = 50.0 + i / 15 + generador.uniform(-0.01, 0.01)
        publicador.publicar(np.full((240, 320, 3), i * 8, dtype=np.uint8), instante)
    publicador.cerrar()

    with av.open(str(destino)) as contenedor:
        flujo = contenedor.streams.video[0]
        tiempos = sorted(
            float(p.pts * p.time_base)
            for p in contenedor.demux(flujo)
            if p.size and p.pts is not None
        )
    intervalos = {round(b - a, 3) for a, b in pairwise(tiempos)}
    assert intervalos <= {
        0.066,
        0.067,
    }  # constant parts, as Apple's low-latency HLS player requires


def test_un_hueco_de_la_webcam_deja_ranuras_vacias(tmp_path: Path) -> None:
    destino = tmp_path / "vivo.mkv"
    publicador = PublicadorPyAV(str(destino), fps=10)
    for instante in (0.0, 0.1, 0.2, 1.2, 1.3, 1.3):  # 1 s without frames, then a repeated slot
        publicador.publicar(np.zeros((240, 320, 3), dtype=np.uint8), instante)
    publicador.cerrar()

    with av.open(str(destino)) as contenedor:
        flujo = contenedor.streams.video[0]
        tiempos = sorted(
            round(float(p.pts * p.time_base), 2)
            for p in contenedor.demux(flujo)
            if p.size and p.pts is not None
        )
    assert tiempos == [0.0, 0.1, 0.2, 1.2, 1.3, 1.4]


def test_un_servidor_inalcanzable_falla_al_publicar() -> None:
    publicador = PublicadorPyAV("rtsp://127.0.0.1:9/camaras/x")
    with pytest.raises(Exception, match=r".+"):
        publicador.publicar(np.zeros((480, 640, 3), dtype=np.uint8), 0.0)
    publicador.cerrar()
