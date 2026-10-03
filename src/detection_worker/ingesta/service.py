"""Procesamiento de los fotogramas de una cámara.

Flujo: ingesta → pose → clasificación → eventos y clips.
"""

import asyncio
import logging
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

from detection_worker.clasificacion.estados import ClasificadorCinematico, TipoEvento
from detection_worker.clips.service import AlmacenClips
from detection_worker.eventos.client import PublicadorEventos
from detection_worker.eventos.schemas import EventoDetectado
from detection_worker.ingesta import protocolo
from detection_worker.ingesta.buffer import BufferClip, Clip
from detection_worker.pose.service import EstimadorPose

logger = logging.getLogger(__name__)

# Eventos que llevan clip de 6 s antes y 6 s después (US-16, US-17 y US-18).
EVENTOS_CON_CLIP = frozenset({TipoEvento.CAIDA, TipoEvento.MOVIMIENTO_INESTABLE})


class ProcesadorCamara:
    """Atiende la conexión de un Agente de captura (una cámara)."""

    def __init__(
        self,
        camara_id: str,
        estimador: EstimadorPose,
        clasificador: ClasificadorCinematico,
        publicador: PublicadorEventos,
        almacen: AlmacenClips,
        buffer: BufferClip | None = None,
    ) -> None:
        self._camara_id = camara_id
        self._estimador = estimador
        self._clasificador = clasificador
        self._publicador = publicador
        self._almacen = almacen
        self._buffer = buffer or BufferClip()
        self._tareas: set[asyncio.Task[None]] = set()

    async def procesar(self, mensaje: bytes) -> list[EventoDetectado]:
        """Procesa un mensaje del agente y devuelve los eventos publicados."""
        instante_ms, jpeg = protocolo.decodificar(mensaje)
        instante = instante_ms / 1000
        for clip in self._buffer.agregar(instante, jpeg):
            self._en_segundo_plano(self._guardar_clip(clip))

        pose = await self._estimador.estimar(jpeg)
        publicados = []
        for evento in self._clasificador.actualizar(instante, pose):
            detectado = EventoDetectado(
                evento_id=uuid4().hex,
                camara_id=self._camara_id,
                tipo=evento.tipo,
                ocurrido_en=datetime.fromtimestamp(evento.instante, UTC),
                parametros=evento.parametros,
            )
            if evento.tipo in EVENTOS_CON_CLIP:
                self._buffer.marcar_evento(detectado.evento_id, evento.instante)
            await self._publicar(detectado)
            publicados.append(detectado)
        return publicados

    async def cerrar(self) -> None:
        if self._tareas:
            await asyncio.gather(*self._tareas, return_exceptions=True)

    async def _publicar(self, evento: EventoDetectado) -> None:
        try:
            await self._publicador.publicar(evento)
        except httpx.HTTPError:
            logger.exception("No se pudo publicar el evento %s", evento.evento_id)

    async def _guardar_clip(self, clip: Clip) -> None:
        try:
            clave = await self._almacen.guardar(self._camara_id, clip)
            await self._publicador.asociar_clip(clip.evento_id, clave)
        except Exception:
            logger.exception("No se pudo guardar el clip del evento %s", clip.evento_id)

    def _en_segundo_plano(self, corrutina: Coroutine[Any, Any, None]) -> None:
        tarea = asyncio.create_task(corrutina)
        self._tareas.add(tarea)
        tarea.add_done_callback(self._tareas.discard)
