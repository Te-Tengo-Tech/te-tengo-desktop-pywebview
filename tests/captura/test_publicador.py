from pathlib import Path

import av
import numpy as np
import pytest

from te_tengo_captura.captura.publicador import PublicadorPyAV


def test_codifica_h264_de_baja_latencia(tmp_path: Path) -> None:
    destino = tmp_path / "vivo.mkv"
    publicador = PublicadorPyAV(str(destino))
    for i in range(20):  # 2.5 s at 8 fps
        imagen = np.full((480, 640, 3), i * 10, dtype=np.uint8)
        publicador.publicar(imagen, 100.0 + i / 8)  # instants of a webcam's monotonic clock
    publicador.cerrar()
    publicador.cerrar()  # idempotent

    with av.open(str(destino)) as contenedor:
        flujo = contenedor.streams.video[0]
        assert flujo.codec_context.name == "h264"
        assert (flujo.codec_context.width, flujo.codec_context.height) == (640, 480)
        assert len(contenedor.streams.audio) == 0
        paquetes = [p for p in contenedor.demux(flujo) if p.size]
    assert len(paquetes) == 20  # zerolatency: every frame comes out, none held back
    claves = [i for i, p in enumerate(paquetes) if p.is_keyframe]
    assert claves == [0, 8, 16]  # one keyframe per second
    tiempos = [float(p.pts * p.time_base) for p in paquetes if p.pts is not None]
    assert tiempos[0] == pytest.approx(0.0)
    assert tiempos[-1] == pytest.approx(19 / 8, abs=0.01)


def test_un_servidor_inalcanzable_falla_al_publicar() -> None:
    publicador = PublicadorPyAV("rtsp://127.0.0.1:9/camaras/x")
    with pytest.raises(Exception, match=r".+"):
        publicador.publicar(np.zeros((480, 640, 3), dtype=np.uint8), 0.0)
    publicador.cerrar()
