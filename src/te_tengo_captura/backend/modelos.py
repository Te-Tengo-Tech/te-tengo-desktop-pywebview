"""Request and response bodies of the agent contract (camelCase JSON, ISO-8601 UTC times)."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer
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
