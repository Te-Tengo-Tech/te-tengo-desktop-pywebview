"""Request and response bodies of the agent contract (camelCase JSON, ISO-8601 UTC times)."""

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from pydantic.alias_generators import to_camel

from te_tengo_deteccion.clasificacion.estados import TipoEvento


class _Cuerpo(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

    def json_api(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


def iso_utc(instante: datetime) -> str:
    """``2026-10-07T15:04:31.250Z``: ISO-8601 in UTC with milliseconds, as in the contract."""
    return instante.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class MotivoCaptura(StrEnum):
    SIN_CONSENTIMIENTO = "SIN_CONSENTIMIENTO"
    EN_PAUSA = "EN_PAUSA"


class SolicitudRegistro(_Cuerpo):
    credencial_instalacion: str
    nombre_habitacion: str
    version_agente: str


class Registro(_Cuerpo):
    camara_id: str
    hogar_id: str
    token: str
    expira_en: datetime
    nombre_habitacion: str


class EstadoCaptura(_Cuerpo):
    captura_permitida: bool
    motivo: MotivoCaptura | None = None
    pausada_hasta: datetime | None = None
    nombre_habitacion: str


class Senal(_Cuerpo):
    webcam_conectada: bool
    deteccion_confiable: bool
    version_agente: str


class EventoAgente(_Cuerpo):
    """Detected event; ``evento_id`` is a UUID v7 and makes resending safe."""

    evento_id: str
    tipo: TipoEvento
    ocurrido_en: datetime
    parametros: dict[str, float] = {}

    @field_serializer("ocurrido_en")
    def _serializar_instante(self, instante: datetime) -> str:
        return iso_utc(instante)

    @field_serializer("parametros")
    def _serializar_parametros(self, parametros: dict[str, float]) -> dict[str, float]:
        # JSON has no infinity: a person lying flat can give an infinite width/height ratio.
        return {nombre: valor for nombre, valor in parametros.items() if math.isfinite(valor)}


class EventoRecibido(_Cuerpo):
    evento_id: str
    alerta_id: str | None = None


class SolicitudClip(_Cuerpo):
    content_type: str = "video/mp4"
    tamano_bytes: int


class SubidaClip(_Cuerpo):
    url_subida: str
    cabeceras: dict[str, str] = {}
    expira_en: datetime


class ConfiguracionRemota(_Cuerpo):
    version_agente: str
    umbrales: dict[str, Any] = {}


class ModoVista(StrEnum):
    """What the live view shows (``docs/AGENT_CONTRACT.md``, "Live view")."""

    VIDEO = "VIDEO"
    VIDEO_CON_POSTURA = "VIDEO_CON_POSTURA"
    SOLO_POSTURA = "SOLO_POSTURA"


class OrdenTransmision(_Cuerpo):
    """A text message of the control channel ``/api/agente/transmision``.

    ``{"transmitir": true, "urlPublicacion", "usuario", "clave", "modo"?}`` starts publishing,
    ``{"transmitir": false}`` stops it, ``{"modo": …}`` alone changes the mode and
    ``{"preparar": true}`` asks for the pre-warm (the app opened the camera screen). Unknown
    fields are ignored, so an agent that does not know a message does nothing with it.
    ``clave`` is the publish token: never logged.
    """

    transmitir: bool | None = None
    preparar: bool | None = None
    url_publicacion: str | None = None
    usuario: str | None = None
    clave: str | None = Field(default=None, repr=False)
    modo: ModoVista | None = None
