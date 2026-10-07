"""Capture loop: frame → MediaPipe → ``ClasificadorCinematico`` → events and clips → outbox.

It runs in a worker thread (``HiloCaptura``). Rules (AGENTS.md):

* **Consent and pauses are hard gates** (CA-05.2, CA-22.1): while capture is not allowed the
  webcam is closed, so no frame is read, classified or buffered. When it turns false the clip
  buffer is dropped and the classifier and the tracker are reset; when it turns true again the
  webcam is reopened and capture resumes on its own (CA-22.3).
* **Never lose an event:** each event gets a UUID v7 ``eventoId`` and goes to the outbox first.
* **Clips** (CA-18.1): for the events in ``EVENTOS_CON_CLIP`` the frames from 6 s before to 6 s
  after are encoded as MP4 off the loop thread and queued for upload. If encoding fails, the
  event has already been queued and is sent without its clip (CA-18.2).
"""

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import partial
from typing import Protocol

from te_tengo_captura.backend.modelos import EventoAgente
from te_tengo_captura.captura.fuentes import Captador
from te_tengo_captura.captura.pose import Estimador
from te_tengo_captura.ids import uuid7
from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.clips.buffer import BufferClip, Clip
from te_tengo_deteccion.clips.codificar import codificar_mp4

logger = logging.getLogger(__name__)

# Events that are sent as alerts and carry a clip; the others are notices without video.
EVENTOS_CON_CLIP = frozenset({TipoEvento.CAIDA, TipoEvento.MOVIMIENTO_INESTABLE})


class Bandeja(Protocol):
    """The part of the outbox the loop writes to."""

    def agregar_evento(self, evento: EventoAgente) -> None: ...

    def agregar_clip(self, evento_id: str, mp4: bytes) -> None: ...


def _en_otro_hilo() -> Callable[[Callable[[], None]], object]:
    ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="clips")
    return ejecutor.submit


class BucleCaptura:
    def __init__(
        self,
        captador: Captador,
        estimador: Estimador,
        umbrales: Umbrales,
        bandeja: Bandeja,
        permitida: Callable[[], bool],
        al_encolar: Callable[[], None] = lambda: None,
        codificar: Callable[[list[tuple[float, bytes]]], bytes] = codificar_mp4,
        ejecutar_clip: Callable[[Callable[[], None]], object] | None = None,
        reloj_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = uuid7,
    ) -> None:
        self._captador = captador
        self._estimador = estimador
        self._umbrales = umbrales
        self._bandeja = bandeja
        self._permitida = permitida
        self._al_encolar = al_encolar
        self._codificar = codificar
        self._ejecutar_clip = ejecutar_clip or _en_otro_hilo()
        self._reloj_utc = reloj_utc
        self._generar_id = generar_id
        self._clasificador = ClasificadorCinematico(umbrales)
        self._buffer = BufferClip()
        self._activa = False
        self._buscar = threading.Event()
        self.deteccion_confiable = True

    @property
    def activa(self) -> bool:
        """Capture is allowed and running."""
        return self._activa

    @property
    def webcam_conectada(self) -> bool:
        """Last known state; a webcam not opened yet (capture not allowed) is not «lost»."""
        return self._captador.conectada is not False

    def actualizar_umbrales(self, umbrales: Umbrales) -> None:
        """New thresholds (remote configuration): applied with a fresh classifier."""
        self._umbrales = umbrales
        self._clasificador = ClasificadorCinematico(umbrales)

    def buscar_webcam(self) -> None:
        """«Buscar de nuevo» from another thread: the reopen happens on the capture thread."""
        self._buscar.set()

    def paso(self) -> list[EventoAgente]:
        """Processes at most one frame and returns the events queued for it."""
        if not self._permitida():
            if self._activa:
                self._detener()
            return []
        if not self._activa:
            logger.info("Captura permitida: se abre la webcam")
            self._activa = True
        if self._buscar.is_set():
            self._buscar.clear()
            self._captador.buscar_de_nuevo()
        fotograma = self._captador.leer()
        if fotograma is None:
            return []
        for clip in self._buffer.agregar(fotograma.instante, fotograma.jpeg):
            self._ejecutar_clip(partial(self._guardar_clip, clip))

        pose = self._estimador.estimar(fotograma.imagen, fotograma.instante_ms)
        if pose is not None:
            self.deteccion_confiable = True
        ocurrido_en = self._reloj_utc()
        encolados = []
        for evento in self._clasificador.actualizar(fotograma.instante, pose):
            if evento.tipo is TipoEvento.DETECCION_NO_CONFIABLE:
                self.deteccion_confiable = False
            detectado = EventoAgente(
                evento_id=self._generar_id(),
                tipo=evento.tipo,
                ocurrido_en=ocurrido_en,
                parametros=evento.parametros,
            )
            self._bandeja.agregar_evento(detectado)
            logger.info("Evento detectado: %s %s", evento.tipo.value, detectado.evento_id)
            if evento.tipo in EVENTOS_CON_CLIP:
                self._buffer.marcar_evento(detectado.evento_id, evento.instante)
            encolados.append(detectado)
        if encolados:
            self._al_encolar()
        return encolados

    def espera(self) -> float:
        """Seconds the thread may wait before the next useful ``paso``."""
        return self._captador.espera() if self._activa else 0.5

    def cerrar(self) -> None:
        self._detener()
        self._estimador.cerrar()

    def _detener(self) -> None:
        if self._activa:
            logger.info("Captura detenida: se cierra la webcam y se descarta el buffer")
        self._activa = False
        self._captador.cerrar()
        self._buffer = BufferClip()
        self._clasificador = ClasificadorCinematico(self._umbrales)
        self._estimador.reiniciar()
        self.deteccion_confiable = True

    def _guardar_clip(self, clip: Clip) -> None:
        try:
            mp4 = self._codificar(clip.fotogramas)
            self._bandeja.agregar_clip(clip.evento_id, mp4)
        except Exception as error:
            logger.error("Clip del evento %s no disponible: %s", clip.evento_id, error)
            return
        self._al_encolar()


class HiloCaptura:
    """Runs ``BucleCaptura`` in a worker thread until ``detener``."""

    def __init__(self, bucle: BucleCaptura) -> None:
        self._bucle = bucle
        self._detenido = threading.Event()
        self._despertar = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="captura", daemon=True)

    def iniciar(self) -> None:
        self._hilo.start()

    def despertar(self) -> None:
        """The capture state changed: check the gate now."""
        self._despertar.set()

    def detener(self, espera_s: float = 5.0) -> None:
        self._detenido.set()
        self._despertar.set()
        if self._hilo.is_alive():
            self._hilo.join(espera_s)

    def _correr(self) -> None:
        try:
            while not self._detenido.is_set():
                self._bucle.paso()
                if (espera := self._bucle.espera()) > 0:
                    self._despertar.wait(espera)
                    self._despertar.clear()
        finally:
            self._bucle.cerrar()
