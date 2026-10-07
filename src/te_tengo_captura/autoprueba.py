"""``--autoprueba``: checks that a build has everything it needs, without a webcam or a display.

Used as the smoke test of the packaged app in CI: the MediaPipe model loads and runs, a clip is
encoded, pywebview and pystray import, and the web assets are present.
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
