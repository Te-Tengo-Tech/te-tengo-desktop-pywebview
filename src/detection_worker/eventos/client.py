"""Adaptador hacia el Backend API del sistema (Spring Boot)."""

import logging
from typing import Protocol

import httpx

from detection_worker.eventos.schemas import EventoDetectado

logger = logging.getLogger(__name__)

RUTA_EVENTOS = "/internal/v1/eventos"
RUTA_CLIPS = "/internal/v1/eventos/{evento_id}/clip"


class PublicadorEventos(Protocol):
    async def publicar(self, evento: EventoDetectado) -> None: ...

    async def asociar_clip(self, evento_id: str, clave: str) -> None: ...

    async def cerrar(self) -> None: ...


class BackendPublicador:
    def __init__(self, url_base: str, token: str, timeout_s: float = 5.0) -> None:
        self._cliente = httpx.AsyncClient(
            base_url=url_base,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_s,
        )

    async def publicar(self, evento: EventoDetectado) -> None:
        respuesta = await self._cliente.post(RUTA_EVENTOS, json=evento.model_dump(mode="json"))
        respuesta.raise_for_status()
        logger.info("Evento publicado", extra={"evento": evento.tipo, "camara": evento.camara_id})

    async def asociar_clip(self, evento_id: str, clave: str) -> None:
        respuesta = await self._cliente.put(
            RUTA_CLIPS.format(evento_id=evento_id), json={"clave": clave}
        )
        respuesta.raise_for_status()

    async def cerrar(self) -> None:
        await self._cliente.aclose()
