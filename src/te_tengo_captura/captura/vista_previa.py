"""The local preview of the «Cámaras» tab (CA-29.8: «La vista previa solo se ve en esta PC»).

The window asks for the newest frame of a camera a few times per second while it shows it. Only
then does ``VistaPreviaLocal`` keep a reference to the newest webcam frame (``ofrecer``, from the
capture thread, before the detection sampling), and only in memory; the frame is downscaled and
compressed to a small JPEG when asked (``jpeg``). Nothing is written to disk or sent anywhere.
When the window stops asking for ``ACTIVA_S`` seconds the frame is dropped. The capture loop only
reads the webcam while capture is allowed, so a camera without consent or paused has no preview.
"""

import threading
import time
from collections.abc import Callable
from typing import Any

from te_tengo_captura.captura.fuentes import Imagen

ACTIVA_S = 2.0  # how long a request keeps frames coming (the window polls every 0.25 s)
FRESCURA_S = 1.0  # an older frame is not shown as «live»
ANCHO = 480
CALIDAD_JPEG = 70


class VistaPreviaLocal:
    def __init__(self, reloj: Callable[[], float] = time.monotonic) -> None:
        self._reloj = reloj
        self._candado = threading.Lock()
        self._pedida_hasta = 0.0
        self._imagen: Imagen | None = None
        self._recibida = 0.0

    @property
    def pedida(self) -> bool:
        return self._reloj() < self._pedida_hasta

    def ofrecer(self, instante: float, imagen: Imagen) -> None:
        """A frame as the webcam delivered it (capture thread): only a reference is kept."""
        if not self.pedida:
            if self._imagen is not None:
                with self._candado:
                    self._imagen = None
            return
        with self._candado:
            self._imagen, self._recibida = imagen, self._reloj()

    def jpeg(self) -> bytes | None:
        """The newest frame as a small JPEG, or ``None`` if there is no fresh one yet."""
        ahora = self._reloj()
        with self._candado:
            self._pedida_hasta = ahora + ACTIVA_S
            imagen, recibida = self._imagen, self._recibida
        if imagen is None or ahora - recibida > FRESCURA_S:
            return None
        return codificar(imagen)


def codificar(imagen: Imagen, ancho: int = ANCHO) -> bytes | None:
    import cv2

    alto_original, ancho_original = imagen.shape[:2]
    pequena: Any = imagen
    if ancho_original > ancho:
        pequena = cv2.resize(imagen, (ancho, round(alto_original * ancho / ancho_original)))
    ok, datos = cv2.imencode(".jpg", pequena, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPEG])
    return datos.tobytes() if ok else None
