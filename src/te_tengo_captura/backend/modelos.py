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
    ``{"preparar": true}`` asks for the pre-warm (the app opened the camera screen) and
    ``{"desvincular": true}`` says the PC left the household (US-31). Unknown
    fields are ignored, so an agent that does not know a message does nothing with it.
    ``clave`` is the publish token: never logged.
    """

    transmitir: bool | None = None
    preparar: bool | None = None
    desvincular: bool | None = None
    # The PC's own channel (US-29): an assignment from the app, «Buscar de nuevo», and the
    # preview of a webcam «sin usar» (``camaraId``/``dispositivoId`` added to a live view message).
    camara: dict[str, Any] | None = None
    buscar_camaras: bool | None = None
    camara_id: str | None = None
    dispositivo_id: str | None = None
    url_publicacion: str | None = None
    usuario: str | None = None
    clave: str | None = Field(default=None, repr=False)
    modo: ModoVista | None = None


class PcDelAgente(_Cuerpo):
    """``GET /api/agente/pc`` and the PC's heartbeat: its household and who approved it."""

    pc_id: str
    hogar_id: str
    nombre: str
    nombre_adulto_mayor: str
    vinculada_en: datetime
    vinculada_por: str | None = None
    consentimiento_vigente: bool


class SenalPc(_Cuerpo):
    version_agente: str
    sistema_operativo: str


class WebcamInventario(_Cuerpo):
    dispositivo_id: str
    nombre_dispositivo: str
    conectada: bool = True


class Inventario(_Cuerpo):
    webcams: list[WebcamInventario]


class CamaraDeLaPc(_Cuerpo):
    """A webcam of a linked PC: its room and per-camera token while in use (US-29)."""

    camara_id: str
    dispositivo_id: str
    nombre_dispositivo: str
    en_uso: bool
    conectada: bool = True
    ambiente_id: str | None = None
    nombre_habitacion: str | None = None
    estado_conexion: str | None = None
    pausada_hasta: datetime | None = None
    token: str | None = Field(default=None, repr=False)
    expira_en: datetime | None = None


class CamaraEnAmbiente(_Cuerpo):
    id: str
    pc_id: str | None = None
    pc_nombre: str | None = None
    nombre_dispositivo: str | None = None
    estado_conexion: str | None = None


class Ambiente(_Cuerpo):
    """A room of the household and the camera in use in it, on this PC or another one."""

    id: str
    nombre: str
    camaras: list[CamaraEnAmbiente] = []


class AsignacionCamara(_Cuerpo):
    """«Elegir aquí» (CA-29.8): a webcam of this PC to a room, by id or by a new name."""

    dispositivo_id: str
    nombre_dispositivo: str
    ambiente_id: str | None = None
    nombre_ambiente: str | None = None

    def json_api(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class EstadoMovimientos(_Cuerpo):
    """``GET /api/agente/movimientos/estado``: may movements be stored, on the PC and in the
    cloud (US-35, US-37)."""

    consentimiento_vigente: bool
    guardar_en_la_pc: bool
    guardar_en_la_nube: bool
    retencion_dias: int | None = None
    version_texto_vigente: str | None = None
