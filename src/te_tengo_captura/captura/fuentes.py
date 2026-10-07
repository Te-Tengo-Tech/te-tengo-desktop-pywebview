"""Video sources and the frame preparation used by the validation.

* ``FuenteWebcam``: the household USB webcam (``cv2.VideoCapture(indice)``).
* ``FuenteArchivo``: a video file, for demos and tests (its instants come from the file).
* ``FuenteFalsa``: generated frames, with switchable disconnection, for tests.

``Captador`` applies the same processing as the validation (``docs/validation.md``, section 2):
downscale to 480p, sample by time at 8 fps and compress as JPEG with quality 80; the pose is then
estimated on the JPEG-decoded image. It also detects a disconnected webcam (read failures for
``SEGUNDOS_DESCONEXION``) and reopens it on its own or when «Buscar de nuevo» is pressed.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)

Imagen = npt.NDArray[np.uint8]

ALTO_MAX = 480
FPS = 8.0
CALIDAD_JPEG = 80
# Implementation choices: how long reads may fail before the webcam counts as disconnected, and
# how often a disconnected webcam is reopened.
SEGUNDOS_DESCONEXION = 3.0
SEGUNDOS_REAPERTURA = 2.0


class FuenteVideo(Protocol):
    def abrir(self) -> bool:
        """Opens the source; ``False`` if it is not available."""
        ...

    def leer(self) -> tuple[float, Imagen] | None:
        """Next frame with its instant in seconds (increasing), or ``None`` if the read failed."""
        ...

    def cerrar(self) -> None: ...


@dataclass(frozen=True, slots=True)
class Fotograma:
    instante: float  # seconds, increasing
    jpeg: bytes
    imagen: Imagen  # the JPEG-decoded image the pose is estimated on

    @property
    def instante_ms(self) -> int:
        return round(self.instante * 1000)


# ------------------------------------------------------------------ sources


class FuenteWebcam:
    def __init__(self, indice: int, reloj: Callable[[], float] = time.monotonic) -> None:
        self._indice = indice
        self._reloj = reloj
        self._captura: Any = None

    def abrir(self) -> bool:
        import cv2

        self.cerrar()
        captura = cv2.VideoCapture(self._indice)
        if not captura.isOpened():
            captura.release()
            return False
        self._captura = captura
        return True

    def leer(self) -> tuple[float, Imagen] | None:
        if self._captura is None:
            return None
        ok, imagen = self._captura.read()
        if not ok or imagen is None:
            return None
        return self._reloj(), imagen

    def cerrar(self) -> None:
        if self._captura is not None:
            self._captura.release()
            self._captura = None


class FuenteArchivo:
    """Video file. With ``repetir`` it loops, shifting the instants so they keep increasing.

    With ``tiempo_real`` (demos with ``--video``) each frame waits until its instant, like a
    webcam; tests leave it off and read as fast as possible.
    """

    def __init__(self, ruta: Path, repetir: bool = False, tiempo_real: bool = False) -> None:
        self._ruta = ruta
        self._repetir = repetir
        self._tiempo_real = tiempo_real
        self._inicio: float | None = None
        self._captura: Any = None
        self._fps = 30.0
        self._indice = 0
        self._desfase = 0.0
        self.agotada = False

    def abrir(self) -> bool:
        import cv2

        self.cerrar()
        captura = cv2.VideoCapture(str(self._ruta))
        if not captura.isOpened():
            captura.release()
            return False
        self._captura = captura
        self._fps = captura.get(cv2.CAP_PROP_FPS) or 30.0
        return True

    def leer(self) -> tuple[float, Imagen] | None:
        if self._captura is None:
            return None
        ok, imagen = self._captura.read()
        if not ok or imagen is None:
            if not self._repetir or self._indice == 0:
                self.agotada = True
                return None
            import cv2

            self._desfase += self._indice / self._fps
            self._indice = 0
            self._captura.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, imagen = self._captura.read()
            if not ok or imagen is None:
                return None
        instante = self._desfase + self._indice / self._fps
        self._indice += 1
        if self._tiempo_real:
            ahora = time.monotonic()
            self._inicio = ahora if self._inicio is None else self._inicio
            if (adelanto := self._inicio + instante - ahora) > 0:
                time.sleep(adelanto)
        return instante, imagen

    def cerrar(self) -> None:
        if self._captura is not None:
            self._captura.release()
            self._captura = None


class FuenteFalsa:
    """Generated grey frames every ``paso`` seconds; ``conectada = False`` simulates unplugging."""

    def __init__(self, ancho: int = 640, alto: int = 480, paso: float = 1 / 30) -> None:
        self._forma = (alto, ancho, 3)
        self._paso = paso
        self._n = 0
        self.conectada = True
        self.abierta = False
        self.aperturas = 0

    def abrir(self) -> bool:
        self.aperturas += 1
        self.abierta = self.conectada
        return self.abierta

    def leer(self) -> tuple[float, Imagen] | None:
        if not (self.abierta and self.conectada):
            return None
        instante = self._n * self._paso
        self._n += 1
        return instante, np.full(self._forma, (self._n * 7) % 256, dtype=np.uint8)

    def cerrar(self) -> None:
        self.abierta = False


# ------------------------------------------------------------------ processing


def preparar(imagen: Imagen, instante: float) -> Fotograma:
    """480p (even width), JPEG quality 80 and decoding, exactly as in the validation."""
    import cv2

    alto, ancho = imagen.shape[:2]
    if alto > ALTO_MAX:
        imagen = cast(
            Imagen, cv2.resize(imagen, (round(ancho * ALTO_MAX / alto / 2) * 2, ALTO_MAX))
        )
    ok, comprimida = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPEG])
    decodificada = cv2.imdecode(comprimida, cv2.IMREAD_COLOR) if ok else None
    if decodificada is None:
        raise ValueError("No se pudo comprimir el fotograma")
    return Fotograma(instante, comprimida.tobytes(), cast(Imagen, decodificada))


class Muestreador:
    """Takes one frame every ``1/fps`` seconds of the source's time, like the validation.

    On a constant-rate source this picks the same frames as ``scripts/evaluar.py``. After a gap
    longer than one period (a live webcam that stalled) it restarts the grid instead of letting
    a burst of frames through.
    """

    def __init__(self, fps: float = FPS) -> None:
        self._periodo = 1 / fps
        self._siguiente: float | None = None

    def tomar(self, instante: float) -> bool:
        if self._siguiente is None or instante > self._siguiente + self._periodo:
            self._siguiente = instante
        if instante + 1e-9 < self._siguiente:
            return False
        self._siguiente += self._periodo
        return True

    def reiniciar(self) -> None:
        self._siguiente = None


class Captador:
    """Reads the source, detects disconnection and reconnection, and yields prepared frames."""

    def __init__(
        self,
        fuente: FuenteVideo,
        reloj: Callable[[], float] = time.monotonic,
        fps: float = FPS,
        segundos_desconexion: float = SEGUNDOS_DESCONEXION,
        segundos_reapertura: float = SEGUNDOS_REAPERTURA,
    ) -> None:
        self._fuente = fuente
        self._reloj = reloj
        self._muestreador = Muestreador(fps)
        self._desconexion = segundos_desconexion
        self._reapertura = segundos_reapertura
        self._abierta = False
        self._proxima_apertura = 0.0
        self._fallando_desde: float | None = None
        # None until the webcam is first opened (capture may not be allowed yet).
        self.conectada: bool | None = None

    def leer(self) -> Fotograma | None:
        """One read. ``None`` when there is no frame to process yet (skipped, failed or closed)."""
        ahora = self._reloj()
        if not self._abierta:
            if ahora < self._proxima_apertura:
                return None
            self._abierta = self._fuente.abrir()
            if not self._abierta:
                self._marcar_desconectada(ahora)
                return None
            self._fallando_desde = ahora  # counts as failing until the first frame arrives
        lectura = self._fuente.leer()
        if lectura is None:
            if self._fallando_desde is None:
                self._fallando_desde = ahora
            elif ahora - self._fallando_desde >= self._desconexion:
                self._fuente.cerrar()
                self._abierta = False
                self._marcar_desconectada(ahora)
            return None
        self._fallando_desde = None
        if self.conectada is not True:
            logger.info("Webcam conectada")
            self.conectada = True
        instante, imagen = lectura
        if not self._muestreador.tomar(instante):
            return None
        return preparar(imagen, instante)

    def espera(self) -> float:
        """Seconds the caller may sleep before the next ``leer`` is useful."""
        if self._abierta:
            return 0.0
        return max(0.0, self._proxima_apertura - self._reloj())

    def buscar_de_nuevo(self) -> None:
        """«Buscar de nuevo»: close and reopen the webcam on the next read."""
        self._fuente.cerrar()
        self._abierta = False
        self._proxima_apertura = 0.0
        self._muestreador.reiniciar()

    def cerrar(self) -> None:
        self._fuente.cerrar()
        self._abierta = False

    def _marcar_desconectada(self, ahora: float) -> None:
        if self.conectada is not False:
            logger.warning("Webcam desconectada")
        self.conectada = False
        self._proxima_apertura = ahora + self._reapertura
        self._muestreador.reiniciar()
