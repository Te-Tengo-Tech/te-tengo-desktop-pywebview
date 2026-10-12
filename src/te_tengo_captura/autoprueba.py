"""``--autoprueba``: checks that a build has everything it needs, without a webcam or a display.

Used as the smoke test of the packaged app in CI: the MediaPipe model loads and runs, a clip is
encoded, the live view encodes H.264 and has its RTSP muxer and WebSocket client, pywebview and
pystray import, the web assets are present, the OS credential store is reachable through keyring
(not on Linux CI, which has no Secret Service), the PC link's QR is drawn, the webcam listing
loads and a movements file is written, encrypted, decrypted and read back (pyarrow, cryptography).
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
    from te_tengo_captura.captura.publicador import PublicadorPyAV, calentar_codificador

    if "rtsp" not in av.formats_available:
        raise RuntimeError("PyAV no tiene RTSP")
    with tempfile.TemporaryDirectory() as directorio:
        destino = Path(directorio) / "vivo.mkv"
        calentar_codificador(640, 480)
        publicador = PublicadorPyAV(str(destino))
        negro = np.zeros((480, 640, 3), dtype=np.uint8)
        for i in range(15):
            publicador.publicar(componer(negro, None, ModoVista.SOLO_POSTURA), i / 15)
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


def _vinculacion() -> None:
    import sys

    from te_tengo_captura.captura.dispositivos import listar_dispositivos
    from te_tengo_captura.vinculacion.qr import codigo_qr

    if codigo_qr("https://app.tetengo.reqsai.tech/vincular?codigo=KQWT-MXHD").modulos < 21:
        raise RuntimeError("el QR no se generó")
    if sys.platform in ("win32", "darwin"):
        import keyring

        nombre = type(keyring.get_keyring()).__module__
        if "fail" in nombre or "null" in nombre:
            raise RuntimeError(f"sin almacén de credenciales del sistema ({nombre})")
    listar_dispositivos()  # no webcam in CI: an empty list, but the OS libraries load


def _almacenamiento() -> None:
    import os
    from datetime import UTC, datetime

    from te_tengo_captura.almacen.cifrado import cifrar_bytes, descifrar_bytes
    from te_tengo_captura.almacen.puntos import (
        FilaMovimiento,
        TramoMovimientos,
        a_ms,
        leer_parquet,
    )

    tramo = TramoMovimientos("autoprueba")
    inicio = a_ms(datetime(2026, 9, 23, tzinfo=UTC))
    for i in range(16):
        tramo.agregar(FilaMovimiento(inicio + i * 125, [(0.5, 0.5, 0.0, 0.9)] * 33))
    [cerrado] = tramo.cerrar()
    clave = os.urandom(32)
    _, filas = leer_parquet(descifrar_bytes(clave, cifrar_bytes(clave, cerrado.datos)))
    if len(filas) != 16:
        raise RuntimeError("el archivo de movimientos no se leyó completo")


def ejecutar(ruta_modelo: Path) -> int:
    pruebas: list[tuple[str, Callable[[], None]]] = [
        ("modelo de pose", lambda: _modelo(ruta_modelo)),
        ("clip MP4", _clip),
        ("vista en vivo", _vista_en_vivo),
        ("interfaz", _interfaz),
        ("vinculación", _vinculacion),
        ("almacenamiento", _almacenamiento),
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
