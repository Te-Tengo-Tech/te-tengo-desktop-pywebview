"""Live view on demand (US-23): what the capture loop feeds and what the control channel drives.

The API asks for the live view over the control channel (``backend/transmision.py``) with the
``urlPublicacion`` of the camera's path in the streaming service (MediaMTX), the publish
credentials and the mode. ``TransmisionEnVivo`` then publishes the webcam as H.264 at its own
frame rate (``fps``, 15 by default), independent of the 8 fps detection sampling: ``Captador``
hands it every frame the webcam delivers (``ofrecer``) and it keeps one per ``1/fps`` slot,
downscaled to 480p in its worker. The capture loop hands it the pose of each detection frame
(``anotar_pose``); the skeleton of the modes that need it is drawn from the latest one
(``captura/postura.py``). The classifier's input does not change.

Rules:

* **Never slow the capture loop.** ``ofrecer`` only puts the frame in a small queue
  (``CAPACIDAD`` frames); when the publisher falls behind the oldest frame is dropped. Resizing,
  drawing, encoding and the network run in the ``en-vivo`` worker thread.
* **Hard gates** (CA-23.4): frames only flow while capture is allowed, because the loop only
  reads the webcam then. When capture stops being allowed the loop calls ``suspender`` and the
  worker also checks the gate itself, so the publisher is closed at once; ``{"transmitir":
  false}`` closes it too. A disconnected webcam produces no frames (CA-23.3).
* **Pre-warm without sending video** (``preparar``, the app opened the camera screen): for up to
  ``PREPARACION_S`` the worker gets everything local ready: PyAV, FFmpeg and libx264 loaded and
  run once on a plain grey picture (``calentar_codificador``), the webcam's frames flowing at the
  live rate with only the newest one kept in memory, and the publish host resolved again if a
  previous live view gave it. **No frame leaves the PC before ``transmitir``**: nothing is
  connected to the streaming service (the publish URL and token only come with ``transmitir``,
  and an RTSP publish session cannot be opened without announcing a stream), and no camera frame
  is encoded. No TLS connection is opened early either: FFmpeg's RTSP client opens its own and
  cannot adopt one, so it would only be thrown away. The publication's own encoder is created on
  ``transmitir`` (a few milliseconds once warm), because FFmpeg builds the stream description
  from it. On ``transmitir`` the newest frame (if fresh) is published at once. The warm state
  is dropped when it times out, on ``suspender`` or a closed gate (pause, consent revoked) and on
  ``detener``.
* **Retries** (implementation choice): if the streaming service cannot be reached the worker
  drops frames and tries again after 1 s, doubling up to 30 s, while the request lasts.
* **Debug overlay** (``marca_tiempo``, off by default): the wall-clock time of the capture, in
  milliseconds since the epoch, drawn on every published picture to measure glass-to-glass
  latency.
* **Secrets:** the publish token is never logged, nor the URL that carries it.
"""

import contextlib
import logging
import queue
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlsplit

from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.captura.fuentes import Imagen, a_480p
from te_tengo_captura.captura.postura import componer
from te_tengo_captura.captura.publicador import (
    FPS_VIVO,
    Publicador,
    PublicadorPyAV,
    calentar_codificador,
    url_con_credenciales,
)
from te_tengo_deteccion.pose.schemas import Pose

logger = logging.getLogger(__name__)

CAPACIDAD = 2  # frames waiting for the publisher (about 130 ms at 15 fps)
REVISION_S = 0.2  # how often the idle worker checks the gate, the request and the warm state
PREPARACION_S = 60.0  # how long a «preparar» keeps the warm state
FRESCURA_S = 0.25  # the newest warm frame is published on «transmitir» only if this recent
REINTENTO_INICIAL_S = 1.0
REINTENTO_MAXIMO_S = 30.0


class TransmisorEnVivo(Protocol):
    """The live view as the capture loop sees it."""

    @property
    def activo(self) -> bool:
        """A family member asked for the live view, or the app is about to (pre-warm)."""
        ...

    def ofrecer(self, instante: float, imagen: Imagen) -> None:
        """A frame as the webcam delivered it; must not block the capture loop."""
        ...

    def anotar_pose(self, pose: Pose | None) -> None:
        """The pose of the latest detection frame (``None``: nobody seen)."""
        ...

    def suspender(self) -> None:
        """Capture is no longer allowed (or restarts): stop publishing now."""
        ...


class TransmisorNulo:
    """No live view (``--backend-falso`` and tests)."""

    activo = False

    def ofrecer(self, instante: float, imagen: Imagen) -> None:
        pass

    def anotar_pose(self, pose: Pose | None) -> None:
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
    instante: float  # its slot on the live view's constant-rate grid (seconds)
    imagen: Imagen  # as the webcam delivered it; never modified
    recibido: float  # ``reloj`` when it arrived
    pared: float  # wall-clock time when it arrived (debug overlay)


class Ritmo:
    """Picks frames for a constant ``fps`` from a faster webcam and numbers them on the grid.

    A frame is taken when it reaches its slot's time, with ``TOLERANCIA`` of a period of
    margin, so a 30 fps webcam gives every other frame however its timestamps jitter, and the
    grid advances exactly one period per frame taken: the published rate stays ``fps`` on
    average for any faster source. After a gap (a stalled webcam) the slots nobody filled are
    skipped, so the timestamps keep up with the real time.
    """

    TOLERANCIA = 0.25

    def __init__(self, fps: float) -> None:
        self._periodo = 1 / fps
        self._origen: float | None = None
        self._siguiente = 0  # number of the next slot

    def tomar(self, instante: float) -> int | None:
        """The slot number of the frame at ``instante``, or ``None`` to skip it."""
        limite = 0.0
        if self._origen is not None:
            limite = self._origen + self._siguiente * self._periodo
        if self._origen is None or instante < limite - 2 * self._periodo:  # first, or clock reset
            self._origen, self._siguiente, limite = instante, 0, instante
        if instante < limite - self.TOLERANCIA * self._periodo:
            return None
        if instante > limite + self._periodo:
            self._siguiente = round((instante - self._origen) / self._periodo)
        numero = self._siguiente
        self._siguiente += 1
        return numero

    def reiniciar(self) -> None:
        self._origen = None


def marcar_tiempo(imagen: Imagen, pared: float) -> Imagen:
    """A copy of ``imagen`` with ``pared`` in epoch milliseconds in its top-left corner."""
    import cv2

    lienzo = imagen.copy()
    texto = str(round(pared * 1000))
    escala = max(0.5, imagen.shape[0] / 480)
    grosor = max(1, round(2 * escala))
    (ancho, alto), base = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, grosor)
    margen = round(6 * escala)
    cv2.rectangle(lienzo, (0, 0), (ancho + 2 * margen, alto + base + 2 * margen), (0, 0, 0), -1)
    cv2.putText(
        lienzo,
        texto,
        (margen, alto + margen),
        cv2.FONT_HERSHEY_SIMPLEX,
        escala,
        (255, 255, 255),
        grosor,
        cv2.LINE_AA,
    )
    return lienzo


def _resolver(host: str, puerto: int) -> None:
    try:
        socket.getaddrinfo(host, puerto, type=socket.SOCK_STREAM)
    except OSError as error:
        logger.debug("Vista en vivo: no se pudo resolver el servidor (%s)", type(error).__name__)


class TransmisionEnVivo:
    """``TransmisorEnVivo`` for the capture loop and ``ReceptorTransmision`` for the channel."""

    def __init__(
        self,
        permitida: Callable[[], bool],
        abrir_publicador: Callable[[str, float], Publicador] = PublicadorPyAV,
        fps: float = FPS_VIVO,
        marca_tiempo: bool = False,
        calentar: Callable[[int, int, float], None] = calentar_codificador,
        resolver: Callable[[str, int], None] | None = None,
        capacidad: int = CAPACIDAD,
        preparacion_s: float = PREPARACION_S,
        reintento_inicial_s: float = REINTENTO_INICIAL_S,
        reintento_maximo_s: float = REINTENTO_MAXIMO_S,
        reloj: Callable[[], float] = time.monotonic,
        reloj_pared: Callable[[], float] = time.time,
    ) -> None:
        self._permitida = permitida
        self._abrir_publicador = abrir_publicador
        self._fps = fps
        self._marca_tiempo = marca_tiempo
        self._calentar = calentar
        self._resolver = resolver or self._resolver_en_otro_hilo
        self._preparacion_s = preparacion_s
        self._reintento_inicial = reintento_inicial_s
        self._reintento_maximo = reintento_maximo_s
        self._reloj = reloj
        self._reloj_pared = reloj_pared
        # ``None`` wakes the worker up (a new request may publish the newest warm frame).
        self._cola: queue.Queue[_Elemento | None] = queue.Queue(maxsize=capacidad)
        self._candado = threading.Lock()
        self._solicitud: Solicitud | None = None
        self._preparada_hasta: float | None = None
        self._modo = ModoVista.VIDEO
        self._generacion = 0  # changes whenever the frames held so far must be dropped
        self._sesion = 0  # changes whenever the current publisher must be closed
        self._pose: Pose | None = None
        self._host: tuple[str, int] | None = None  # of the last publish URL, for pre-warm
        # Capture thread state.
        self._ritmo = Ritmo(fps)
        # Worker thread state.
        self._publicador: Publicador | None = None
        self._sesion_publicador = -1
        self._ultimo: _Elemento | None = None  # newest frame while warm
        self._calentado = False
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
    def fps(self) -> float:
        return self._fps

    @property
    def modo(self) -> ModoVista:
        return self._modo

    @property
    def publicando(self) -> bool:
        """The streaming service is receiving the frames right now."""
        return self._publicando

    @property
    def preparada(self) -> bool:
        """Pre-warm is on: no request yet and not timed out."""
        hasta = self._preparada_hasta
        return self._solicitud is None and hasta is not None and self._reloj() < hasta

    # ------------------------------------------------------------------ control channel

    def preparar(self) -> None:
        """``{"preparar":true}``: get everything local ready for up to ``preparacion_s``."""
        with self._candado:
            if self._solicitud is not None:
                return  # already live
            nueva = self._preparada_hasta is None
            self._preparada_hasta = self._reloj() + self._preparacion_s
            host = self._host
        if host is not None:
            self._resolver(*host)
        if nueva:
            logger.info("Vista en vivo: preparada (%.0f s)", self._preparacion_s)

    def transmitir(self, url: str, usuario: str | None, clave: str | None, modo: ModoVista) -> None:
        partes = urlsplit(url)
        with self._candado:
            self._solicitud = Solicitud(url, usuario, clave)
            self._modo = modo
            self._preparada_hasta = None
            self._sesion += 1
            self._fallos = 0
            self._proximo_intento = 0.0
            if partes.hostname:
                puerto = partes.port or (322 if partes.scheme == "rtsps" else 554)
                self._host = (partes.hostname, puerto)
        if self._ultimo is not None:
            self._despertar()  # publish the newest warm frame now, not with the next one
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
            preparada = self._preparada_hasta is not None
            self._solicitud = None
            self._preparada_hasta = None
            self._modo = ModoVista.VIDEO
            self._generacion += 1
            self._sesion += 1
            self._pose = None
        self._vaciar()
        if habia:
            logger.info("Vista en vivo detenida")
        elif preparada:
            logger.info("Vista en vivo: preparación descartada")

    # ------------------------------------------------------------------ capture loop

    @property
    def activo(self) -> bool:
        return self._solicitud is not None or self.preparada

    def ofrecer(self, instante: float, imagen: Imagen) -> None:
        if not self.activo:
            self._ritmo.reiniciar()
            return
        numero = self._ritmo.tomar(instante)
        if numero is None:
            return
        self._poner(
            _Elemento(
                self._generacion, numero / self._fps, imagen, self._reloj(), self._reloj_pared()
            )
        )

    def anotar_pose(self, pose: Pose | None) -> None:
        self._pose = pose

    def suspender(self) -> None:
        self._descartar("captura no permitida")
        self._vaciar()

    def _descartar(self, motivo: str, solo_si_preparada: bool = False) -> None:
        """Drops the frames held so far, the latest pose and the warm state."""
        with self._candado:
            preparada = self._solicitud is None and self._preparada_hasta is not None
            if solo_si_preparada and not preparada:
                return
            self._generacion += 1
            self._preparada_hasta = None
            self._pose = None
        if preparada:
            logger.info("Vista en vivo: preparación descartada (%s)", motivo)

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
            elemento = self._cola.get(timeout=espera_s)
        except queue.Empty:
            elemento = None
        ahora = self._reloj()
        with self._candado:
            hasta = self._preparada_hasta
            if self._solicitud is None and hasta is not None and ahora >= hasta:
                self._preparada_hasta = None
                self._generacion += 1
                self._pose = None
                logger.info("Vista en vivo: preparación vencida")
            solicitud, modo, generacion = self._solicitud, self._modo, self._generacion
            sesion, preparada = self._sesion, self._preparada_hasta is not None
        permitida = self._permitida()
        if self._publicador is not None and (
            solicitud is None or not permitida or sesion != self._sesion_publicador
        ):
            self._cerrar_publicador()
        if not permitida and preparada:
            self._descartar("captura no permitida", solo_si_preparada=True)
        if not permitida or (solicitud is None and not preparada):
            self._ultimo = None  # the warm frame is dropped with the warm state
            return
        if elemento is not None and elemento.generacion == generacion:
            self._ultimo = elemento
        pendiente = self._ultimo
        if pendiente is None or pendiente.generacion != generacion:
            self._ultimo = None
            return
        if solicitud is None:
            self._calentar_una_vez(pendiente.imagen)  # warm: nothing is encoded nor sent
            return
        self._ultimo = None
        if elemento is None and ahora - pendiente.recibido > FRESCURA_S:
            return  # a warm frame too old to be live
        if self._publicador is None and ahora < self._proximo_intento:
            return  # waiting to retry: the frame is dropped
        self._publicar(solicitud, modo, sesion, pendiente)

    def _publicar(
        self, solicitud: Solicitud, modo: ModoVista, sesion: int, elemento: _Elemento
    ) -> None:
        imagen = componer(a_480p(elemento.imagen), self._pose, modo)
        if self._marca_tiempo:
            imagen = marcar_tiempo(imagen, elemento.pared)
        try:
            if self._publicador is None:
                url = url_con_credenciales(solicitud.url, solicitud.usuario, solicitud.clave)
                self._publicador = self._abrir_publicador(url, self._fps)
                self._sesion_publicador = sesion
            self._publicador.publicar(imagen, elemento.instante)
        except Exception as error:
            self._fallo(error)
            return
        self.publicados += 1
        self._fallos = 0
        if not self._publicando:
            self._publicando = True
            logger.info("Vista en vivo: publicando a %.0f fps", self._fps)

    def _calentar_una_vez(self, imagen: Imagen) -> None:
        if self._calentado:
            return
        self._calentado = True  # once per process: what it loads stays loaded
        alto, ancho = imagen.shape[:2]
        if alto > 480:
            ancho, alto = round(ancho * 480 / alto / 2) * 2, 480
        inicio = time.perf_counter()
        try:
            self._calentar(ancho // 2 * 2, alto // 2 * 2, self._fps)
        except Exception as error:
            logger.warning("Vista en vivo: no se pudo preparar el codificador (%s)", error)
            return
        logger.info(
            "Vista en vivo: codificador listo en %.0f ms", (time.perf_counter() - inicio) * 1000
        )

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
        self._sesion_publicador = -1
        if self._publicando:
            self._publicando = False
            logger.info("Vista en vivo: publicación cerrada")
        if publicador is not None:
            try:
                publicador.cerrar()
            except Exception as error:
                logger.debug("Vista en vivo: error al cerrar (%s)", type(error).__name__)

    def _poner(self, elemento: _Elemento | None) -> None:
        try:
            self._cola.put_nowait(elemento)
        except queue.Full:
            # Behind: drop the oldest frame, a live view wants the newest one.
            try:
                if self._cola.get_nowait() is not None:
                    self.descartados += 1
            except queue.Empty:
                pass
            try:
                self._cola.put_nowait(elemento)
            except queue.Full:
                if elemento is not None:
                    self.descartados += 1

    def _despertar(self) -> None:
        with contextlib.suppress(queue.Full):  # frames are waiting: the worker is awake anyway
            self._cola.put_nowait(None)

    def _vaciar(self) -> None:
        while True:
            try:
                self._cola.get_nowait()
            except queue.Empty:
                return

    @staticmethod
    def _resolver_en_otro_hilo(host: str, puerto: int) -> None:
        # The OS resolver may block for seconds: never in the channel's or the worker's thread.
        threading.Thread(
            target=_resolver, args=(host, puerto), name="en-vivo-dns", daemon=True
        ).start()
