"""Processing of the frames of one camera.

Flow: ingestion → pose → classification → events and clips.
"""

import asyncio
import logging
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

from detection_worker.clips.service import AlmacenClips
from detection_worker.eventos.client import PublicadorEventos
from detection_worker.eventos.schemas import EventoDetectado
from detection_worker.ingesta import protocolo
from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clips.buffer import BufferClip, Clip
from te_tengo_deteccion.pose.service import EstimadorPose

logger = logging.getLogger(__name__)

# Events that are sent as alerts and carry a clip; the others are notices without video.
EVENTOS_CON_CLIP = frozenset({TipoEvento.CAIDA, TipoEvento.MOVIMIENTO_INESTABLE})


class ProcesadorCamara:
    """Handles the connection of one Capture Agent (one camera)."""

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
        """Processes a message from the agent and returns the published events."""
        instante_ms, jpeg = protocolo.decodificar(mensaje)
        instante = instante_ms / 1000
        for clip in self._buffer.agregar(instante, jpeg):
            self._en_segundo_plano(self._guardar_clip(clip))

        pose = await self._estimador.estimar(jpeg, self._camara_id, instante_ms)
        publicados = []
        for evento in self._clasificador.actualizar(instante, pose):
            detectado = EventoDetectado(
                evento_id=uuid4().hex,
                camara_id=self._camara_id,
                tipo=evento.tipo,
                ocurrido_en=datetime.fromtimestamp(evento.instante, UTC),
                parametros=evento.parametros,
            )
            logger.info(
                "Evento detectado: %s en %s %s",
                evento.tipo.value,
                self._camara_id,
                evento.parametros,
            )
            if evento.tipo in EVENTOS_CON_CLIP:
                self._buffer.marcar_evento(detectado.evento_id, evento.instante)
            await self._publicar(detectado)
            publicados.append(detectado)
        return publicados

    async def cerrar(self) -> None:
        if self._tareas:
            await asyncio.gather(*self._tareas, return_exceptions=True)
        await self._estimador.liberar(self._camara_id)

    async def _publicar(self, evento: EventoDetectado) -> None:
        try:
            await self._publicador.publicar(evento)
        except httpx.HTTPError as error:
            # No full traceback: with the backend down, the log would fill up with noise.
            logger.warning(
                "No se pudo publicar el evento %s (%s): %s",
                evento.tipo.value,
                evento.evento_id,
                error,
            )

    async def _guardar_clip(self, clip: Clip) -> None:
        try:
            clave = await self._almacen.guardar(self._camara_id, clip)
            await self._publicador.asociar_clip(clip.evento_id, clave)
        except Exception as error:
            logger.error("No se pudo guardar el clip del evento %s: %s", clip.evento_id, error)

    def _en_segundo_plano(self, corrutina: Coroutine[Any, Any, None]) -> None:
        tarea = asyncio.create_task(corrutina)
        self._tareas.add(tarea)
        tarea.add_done_callback(self._tareas.discard)
