"""Live view on demand (US-23): what the capture loop feeds and what the control channel drives.

The API asks for the live view over the control channel (``backend/transmision.py``) with the
``urlPublicacion`` of the camera's path in the streaming service (MediaMTX), the publish
credentials and the mode. ``TransmisionEnVivo`` then publishes the frames the capture loop
already processes (480p, about 8 fps) as H.264, drawn for the mode (``captura/postura.py``).

Rules:

* **Never slow the capture loop.** ``enviar`` only puts the frame and its pose in a small queue
  (``CAPACIDAD`` frames); when the publisher falls behind the oldest frame is dropped. Drawing,
  encoding and the network run in the ``en-vivo`` worker thread.
* **Hard gates** (CA-23.4): frames only flow while capture is allowed, because the loop only
  reads the webcam then. When capture stops being allowed the loop calls ``suspender`` and the
  worker also checks the gate itself, so the publisher is closed at once; ``{"transmitir":
  false}`` closes it too. A disconnected webcam produces no frames (CA-23.3).
* **Retries** (implementation choice): if the streaming service cannot be reached the worker
  drops frames and tries again after 1 s, doubling up to 30 s, while the request lasts.
* **Secrets:** the publish token is never logged, nor the URL that carries it.
"""

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.captura.fuentes import Fotograma
from te_tengo_captura.captura.postura import componer
from te_tengo_captura.captura.publicador import Publicador, PublicadorPyAV, url_con_credenciales
from te_tengo_deteccion.pose.schemas import Pose

logger = logging.getLogger(__name__)

CAPACIDAD = 2  # frames waiting for the publisher (a quarter of a second at 8 fps)
REVISION_S = 0.2  # how often the idle worker checks the gate and the request
REINTENTO_INICIAL_S = 1.0
REINTENTO_MAXIMO_S = 30.0


class TransmisorEnVivo(Protocol):
    """The live view as the capture loop sees it."""

    @property
    def activo(self) -> bool:
        """A family member asked for the live view."""
        ...

    def enviar(self, fotograma: Fotograma, pose: Pose | None) -> None:
        """A processed frame and its pose; must not block the capture loop."""
        ...

    def suspender(self) -> None:
        """Capture is no longer allowed (or restarts): stop publishing now."""
        ...


class TransmisorNulo:
    """No live view (``--backend-falso`` and tests)."""

    activo = False

    def enviar(self, fotograma: Fotograma, pose: Pose | None) -> None:
        pass

    def suspender(self) -> None:
        pass


@dataclass(frozen=True, slots=True)
class Solicitud:
    url: str
    usuario: str | None
    clave: str | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class _Elemento:
    generacion: int
    fotograma: Fotograma
    pose: Pose | None


class TransmisionEnVivo:
    """``TransmisorEnVivo`` for the capture loop and ``ReceptorTransmision`` for the channel."""

    def __init__(
        self,
        permitida: Callable[[], bool],
        abrir_publicador: Callable[[str], Publicador] = PublicadorPyAV,
        capacidad: int = CAPACIDAD,
        reintento_inicial_s: float = REINTENTO_INICIAL_S,
        reintento_maximo_s: float = REINTENTO_MAXIMO_S,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self._permitida = permitida
        self._abrir_publicador = abrir_publicador
        self._reintento_inicial = reintento_inicial_s
        self._reintento_maximo = reintento_maximo_s
        self._reloj = reloj
        self._cola: queue.Queue[_Elemento] = queue.Queue(maxsize=capacidad)
        self._candado = threading.Lock()
        self._solicitud: Solicitud | None = None
        self._modo = ModoVista.VIDEO
        self._generacion = 0  # changes whenever the current publisher must be closed
        # Worker thread state.
        self._publicador: Publicador | None = None
        self._generacion_publicador = -1
        self._publicando = False
        self._fallos = 0
        self._proximo_intento = 0.0
        self.descartados = 0  # frames dropped because the publisher was behind
        self.publicados = 0
        self._cerrado = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="en-vivo", daemon=True)

    # ------------------------------------------------------------------ lifecycle

    def iniciar(self) -> None:
        self._hilo.start()

    def cerrar(self, espera_s: float = 5.0) -> None:
        self.detener()
        self._cerrado.set()
        if self._hilo.is_alive():
            self._hilo.join(espera_s)
        else:
            self._cerrar_publicador()

    def secretos(self) -> list[str]:
        solicitud = self._solicitud
        return [solicitud.clave] if solicitud is not None and solicitud.clave else []

    @property
    def modo(self) -> ModoVista:
        return self._modo

    @property
    def publicando(self) -> bool:
        """The streaming service is receiving the frames right now."""
        return self._publicando

    # ------------------------------------------------------------------ control channel

    def transmitir(self, url: str, usuario: str | None, clave: str | None, modo: ModoVista) -> None:
        with self._candado:
            self._solicitud = Solicitud(url, usuario, clave)
            self._modo = modo
            self._generacion += 1
            self._fallos = 0
            self._proximo_intento = 0.0
        self._vaciar()
        logger.info("Vista en vivo solicitada (modo %s)", modo.value)

    def cambiar_modo(self, modo: ModoVista) -> None:
        with self._candado:
            cambio = modo is not self._modo
            self._modo = modo
        if cambio:
            logger.info("Vista en vivo: modo %s", modo.value)

    def detener(self) -> None:
        with self._candado:
            habia = self._solicitud is not None
            self._solicitud = None
            self._modo = ModoVista.VIDEO
            self._generacion += 1
        self._vaciar()
        if habia:
            logger.info("Vista en vivo detenida")

    # ------------------------------------------------------------------ capture loop

    @property
    def activo(self) -> bool:
        return self._solicitud is not None

    def enviar(self, fotograma: Fotograma, pose: Pose | None) -> None:
        elemento = _Elemento(self._generacion, fotograma, pose)
        try:
            self._cola.put_nowait(elemento)
        except queue.Full:
            # Behind: drop the oldest frame, a live view wants the newest one.
            try:
                self._cola.get_nowait()
                self.descartados += 1
            except queue.Empty:
                pass
            try:
                self._cola.put_nowait(elemento)
            except queue.Full:
                self.descartados += 1

    def suspender(self) -> None:
        with self._candado:
            self._generacion += 1
        self._vaciar()

    # ------------------------------------------------------------------ worker

    def _correr(self) -> None:
        try:
            while not self._cerrado.is_set():
                self.procesar_siguiente(REVISION_S)
        finally:
            self._cerrar_publicador()

    def procesar_siguiente(self, espera_s: float) -> None:
        """One step of the worker: waits up to ``espera_s`` for a frame and publishes it."""
        try:
            elemento: _Elemento | None = self._cola.get(timeout=espera_s)
        except queue.Empty:
            elemento = None
        with self._candado:
            solicitud, modo, generacion = self._solicitud, self._modo, self._generacion
        permitida = self._permitida()
        if self._publicador is not None and (
            solicitud is None or not permitida or generacion != self._generacion_publicador
        ):
            self._cerrar_publicador()
        if elemento is None or solicitud is None or not permitida:
            return
        if elemento.generacion != generacion:
            return  # queued before a stop or a new request
        if self._publicador is None and self._reloj() < self._proximo_intento:
            return  # waiting to retry: the frame is dropped
        imagen = componer(elemento.fotograma.imagen, elemento.pose, modo)
        try:
            if self._publicador is None:
                url = url_con_credenciales(solicitud.url, solicitud.usuario, solicitud.clave)
                self._publicador = self._abrir_publicador(url)
                self._generacion_publicador = generacion
            self._publicador.publicar(imagen, elemento.fotograma.instante)
        except Exception as error:
            self._fallo(error)
            return
        self.publicados += 1
        self._fallos = 0
        if not self._publicando:
            self._publicando = True
            logger.info("Vista en vivo: publicando")

    def _fallo(self, error: Exception) -> None:
        self._fallos += 1
        espera = min(self._reintento_maximo, self._reintento_inicial * 2.0 ** (self._fallos - 1))
        self._proximo_intento = self._reloj() + espera
        # Only the type and errno text: FFmpeg's messages include the URL with the token.
        detalle = getattr(error, "strerror", None) or ""
        logger.warning(
            "Vista en vivo: no se pudo publicar (%s %s); reintento en %.0f s",
            type(error).__name__,
            detalle,
            espera,
        )
        self._cerrar_publicador()

    def _cerrar_publicador(self) -> None:
        publicador, self._publicador = self._publicador, None
        self._generacion_publicador = -1
        if self._publicando:
            self._publicando = False
            logger.info("Vista en vivo: publicación cerrada")
        if publicador is not None:
            try:
                publicador.cerrar()
            except Exception as error:
                logger.debug("Vista en vivo: error al cerrar (%s)", type(error).__name__)

    def _vaciar(self) -> None:
        while True:
            try:
                self._cola.get_nowait()
            except queue.Empty:
                return
