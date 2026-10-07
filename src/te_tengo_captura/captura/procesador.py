"""Processing of the frames of the household webcam.

Flow: frame → pose → classification → events and clips. Kept from the retired ingestion
service; T07 turns it into the capture loop with the consent gate and the outbox.
"""

import asyncio
import logging
from collections.abc import Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clips.buffer import BufferClip, Clip
from te_tengo_deteccion.pose.service import EstimadorPose

logger = logging.getLogger(__name__)

# Events that are sent as alerts and carry a clip; the others are notices without video.
EVENTOS_CON_CLIP = frozenset({TipoEvento.CAIDA, TipoEvento.MOVIMIENTO_INESTABLE})


@dataclass(frozen=True, slots=True)
class EventoDetectado:
    """Event ready to be reported to the backend."""

    evento_id: str
    tipo: TipoEvento
    ocurrido_en: datetime
    parametros: dict[str, float] = field(default_factory=dict)


class PublicadorEventos(Protocol):
    async def publicar(self, evento: EventoDetectado) -> None: ...


class DestinoClips(Protocol):
    async def guardar(self, clip: Clip) -> None: ...


class ProcesadorCamara:
    """Turns the frames of one camera into published events and clips."""

    def __init__(
        self,
        camara_id: str,
        estimador: EstimadorPose,
        clasificador: ClasificadorCinematico,
        publicador: PublicadorEventos,
        clips: DestinoClips,
        buffer: BufferClip | None = None,
    ) -> None:
        self._camara_id = camara_id
        self._estimador = estimador
        self._clasificador = clasificador
        self._publicador = publicador
        self._clips = clips
        self._buffer = buffer or BufferClip()
        self._tareas: set[asyncio.Task[None]] = set()

    async def procesar(self, instante_ms: int, jpeg: bytes) -> list[EventoDetectado]:
        """Processes one frame and returns the published events."""
        instante = instante_ms / 1000
        for clip in self._buffer.agregar(instante, jpeg):
            self._en_segundo_plano(self._guardar_clip(clip))

        pose = await self._estimador.estimar(jpeg, self._camara_id, instante_ms)
        publicados = []
        for evento in self._clasificador.actualizar(instante, pose):
            detectado = EventoDetectado(
                evento_id=uuid4().hex,
                tipo=evento.tipo,
                ocurrido_en=datetime.fromtimestamp(evento.instante, UTC),
                parametros=evento.parametros,
            )
            logger.info("Evento detectado: %s %s", evento.tipo.value, evento.parametros)
            if evento.tipo in EVENTOS_CON_CLIP:
                self._buffer.marcar_evento(detectado.evento_id, evento.instante)
            await self._publicador.publicar(detectado)
            publicados.append(detectado)
        return publicados

    async def cerrar(self) -> None:
        if self._tareas:
            await asyncio.gather(*self._tareas, return_exceptions=True)
        await self._estimador.liberar(self._camara_id)

    async def _guardar_clip(self, clip: Clip) -> None:
        try:
            await self._clips.guardar(clip)
        except Exception as error:
            logger.error("No se pudo guardar el clip del evento %s: %s", clip.evento_id, error)

    def _en_segundo_plano(self, corrutina: Coroutine[Any, Any, None]) -> None:
        tarea = asyncio.create_task(corrutina)
        self._tareas.add(tarea)
        tarea.add_done_callback(self._tareas.discard)
