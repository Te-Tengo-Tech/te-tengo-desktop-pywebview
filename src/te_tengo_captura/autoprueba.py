"""``--autoprueba``: checks that a build has everything it needs, without a webcam or a display.

Used as the smoke test of the packaged app in CI: the MediaPipe model loads and runs, a clip is
encoded, the live view encodes H.264 and has its RTSP muxer and WebSocket client, pywebview and
pystray import, and the web assets are present.
"""

import logging
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def _modelo(ruta: Path) -> None:
    import numpy as np

    from te_tengo_captura.captura.pose import EstimadorMediaPipe

    estimador = EstimadorMediaPipe(ruta)
    try:
        if estimador.estimar(np.zeros((480, 640, 3), dtype=np.uint8), 0) is not None:
            raise RuntimeError("se detectó una pose en una imagen vacía")
    finally:
        estimador.cerrar()


def _clip() -> None:
    import cv2
    import numpy as np

    from te_tengo_deteccion.clips.codificar import codificar_mp4

    fotogramas = []
    for i in range(4):
        ok, jpeg = cv2.imencode(".jpg", np.full((48, 64, 3), i * 60, dtype=np.uint8))
        if not ok:
            raise RuntimeError("no se pudo comprimir un fotograma")
        fotogramas.append((i * 0.125, jpeg.tobytes()))
    if codificar_mp4(fotogramas)[4:8] != b"ftyp":
        raise RuntimeError("el clip no es un MP4")


def _vista_en_vivo() -> None:
    import tempfile

    import av
    import numpy as np
    from websockets.sync.client import connect  # noqa: F401

    from te_tengo_captura.backend.modelos import ModoVista
    from te_tengo_captura.captura.postura import componer
    from te_tengo_captura.captura.publicador import PublicadorPyAV

    if "rtsp" not in av.formats_available:
        raise RuntimeError("PyAV no tiene RTSP")
    with tempfile.TemporaryDirectory() as directorio:
        destino = Path(directorio) / "vivo.mkv"
        publicador = PublicadorPyAV(str(destino))
        negro = np.zeros((480, 640, 3), dtype=np.uint8)
        for i in range(8):
            publicador.publicar(componer(negro, None, ModoVista.SOLO_POSTURA), i / 8)
        publicador.cerrar()
        if destino.stat().st_size == 0:
            raise RuntimeError("la vista en vivo no se codificó")


def _interfaz() -> None:
    import pystray  # noqa: F401
    import webview  # noqa: F401

    from te_tengo_captura.bandeja.iconos import icono
    from te_tengo_captura.ui.ventana import WEB

    for archivo in ("index.html", "arranque.html", "app.css", "app.js", "fonts/OFL.txt"):
        if not (WEB / archivo).is_file():
            raise RuntimeError(f"falta {archivo}")
    icono("ok")


def ejecutar(ruta_modelo: Path) -> int:
    pruebas: list[tuple[str, Callable[[], None]]] = [
        ("modelo de pose", lambda: _modelo(ruta_modelo)),
        ("clip MP4", _clip),
        ("vista en vivo", _vista_en_vivo),
        ("interfaz", _interfaz),
    ]
    fallidas = 0
    for nombre, prueba in pruebas:
        try:
            prueba()
        except Exception:
            fallidas += 1
            logger.exception("Autoprueba: %s FALLÓ", nombre)
        else:
            logger.info("Autoprueba: %s OK", nombre)
    return 1 if fallidas else 0
