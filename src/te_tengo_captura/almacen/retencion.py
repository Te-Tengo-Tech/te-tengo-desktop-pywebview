"""Retention per type and the disk cap (CA-38.3, CA-38.5).

* **Retention:** a file is deleted once its whole span ended more than the type's days ago;
  ``dias = None`` is «Nunca borrar».
* **Cap:** when what is stored plus what must be written exceeds ``limite_bytes``, the oldest
  video is deleted first and then the oldest movements («borramos primero el video más antiguo y
  luego los movimientos más antiguos»). Clips are never deleted by the cap, only by their
  retention.
* **Never blocks, never raises for lack of space:** detection and alerts must go on, so these
  functions only report what they deleted (for the desktop notice) and whether the space is still
  short; the caller then skips that write. A file the callback fails to delete stays in the index
  and is skipped.

The functions are pure over the index: the filesystem is reached only through ``borrar_archivo``,
which receives the path relative to the data folder.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from te_tengo_captura.almacen.indice import Archivo, IndiceArchivos, TipoArchivo

logger = logging.getLogger(__name__)

UN_DIA_MS = 24 * 60 * 60 * 1000
# Order in which the cap deletes: clips are not in it.
ORDEN_LIBERACION = (TipoArchivo.VIDEO, TipoArchivo.MOVIMIENTOS)
_LOTE = 100

BorrarArchivo = Callable[[str], None]


class MotivoBorrado(StrEnum):
    RETENCION = "retencion"
    ESPACIO = "espacio"


@dataclass(frozen=True, slots=True)
class ReglaTipo:
    """What the family chose for one type: keep it (switch) and for how many days."""

    activo: bool
    dias: int | None  # None: «Nunca borrar»

    def __post_init__(self) -> None:
        if self.dias is not None and self.dias < 0:
            raise ValueError("Los días de retención no pueden ser negativos")


@dataclass(frozen=True, slots=True)
class Politica:
    movimientos: ReglaTipo
    video: ReglaTipo
    clip: ReglaTipo
    limite_bytes: int

    def regla(self, tipo: TipoArchivo) -> ReglaTipo:
        return {
            TipoArchivo.MOVIMIENTOS: self.movimientos,
            TipoArchivo.VIDEO: self.video,
            TipoArchivo.CLIP: self.clip,
        }[tipo]

    def guarda(self, tipo: TipoArchivo) -> bool:
        """Whether new files of this type are written (the switch of CA-38.1)."""
        return self.regla(tipo).activo


@dataclass(frozen=True, slots=True)
class BorradoInfo:
    archivo: Archivo
    motivo: MotivoBorrado


@dataclass(frozen=True, slots=True)
class Liberacion:
    """Outcome of ``liberar_espacio``."""

    borrados: list[BorradoInfo] = field(default_factory=list)
    suficiente: bool = True  # False: even after deleting, the new file does not fit
    faltan_bytes: int = 0


def _borrar(
    indice: IndiceArchivos, archivo: Archivo, motivo: MotivoBorrado, borrar_archivo: BorrarArchivo
) -> BorradoInfo | None:
    try:
        borrar_archivo(archivo.ruta)
    except OSError as error:
        logger.warning("No se pudo borrar %s: %s", archivo.ruta, error)
        return None
    indice.borrar(archivo.id)
    return BorradoInfo(archivo, motivo)


def aplicar_retencion(
    indice: IndiceArchivos, politica: Politica, ahora_ms: int, borrar_archivo: BorrarArchivo
) -> list[BorradoInfo]:
    """Deletes every file older than its type's retention; returns what was deleted."""
    borrados: list[BorradoInfo] = []
    for tipo in TipoArchivo:
        dias = politica.regla(tipo).dias
        if dias is None:
            continue
        for archivo in indice.anteriores_a(tipo, ahora_ms - dias * UN_DIA_MS):
            borrado = _borrar(indice, archivo, MotivoBorrado.RETENCION, borrar_archivo)
            if borrado is not None:
                borrados.append(borrado)
    if borrados:
        logger.info("Retención: %d archivos borrados", len(borrados))
    return borrados


def liberar_espacio(
    indice: IndiceArchivos,
    politica: Politica,
    necesarios_bytes: int,
    borrar_archivo: BorrarArchivo,
) -> Liberacion:
    """Makes room for ``necesarios_bytes`` under the cap, oldest video first, then movements."""
    exceso = sum(indice.uso_por_tipo().values()) + necesarios_bytes - politica.limite_bytes
    if exceso <= 0:
        return Liberacion()
    borrados: list[BorradoInfo] = []
    for tipo in ORDEN_LIBERACION:
        fallidos: set[int] = set()
        while exceso > 0:
            candidatos = [
                a for a in indice.mas_antiguos(tipo, _LOTE + len(fallidos)) if a.id not in fallidos
            ]
            if not candidatos:
                break
            for archivo in candidatos:
                borrado = _borrar(indice, archivo, MotivoBorrado.ESPACIO, borrar_archivo)
                if borrado is None:
                    fallidos.add(archivo.id)
                    continue
                borrados.append(borrado)
                exceso -= archivo.tamano_bytes
                if exceso <= 0:
                    break
    if borrados:
        logger.info("Límite de espacio: %d archivos borrados", len(borrados))
    if exceso > 0:
        logger.warning("Espacio insuficiente: faltan %d bytes", exceso)
    return Liberacion(borrados, exceso <= 0, max(0, exceso))
