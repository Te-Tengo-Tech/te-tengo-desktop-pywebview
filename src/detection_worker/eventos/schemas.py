from datetime import datetime

from pydantic import BaseModel

from detection_worker.clasificacion.estados import TipoEvento


class EventoDetectado(BaseModel):
    """Evento que se reporta al Backend API del sistema (contrato provisional)."""

    evento_id: str
    camara_id: str
    tipo: TipoEvento
    ocurrido_en: datetime
    parametros: dict[str, float] = {}
    clip: str | None = None
