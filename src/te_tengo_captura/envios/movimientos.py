"""The movements lane of a camera's outbox: its 5-minute files to the cloud (US-37).

* **Lowest priority** (CA-37.2): ``ColaEnvios`` only runs this lane when no event and no clip is
  due, and it has its own backoff, so a slow upload never delays an alert.
* **Only with the cloud on** (CA-37.1): ``AlmacenLocal`` asks ``GET /api/agente/movimientos/estado``
  at start and every 5 minutes; this lane uploads only while it says ``guardarEnLaNube``. A ``409
  SIN_CONSENTIMIENTO_DE_MOVIMIENTOS`` or ``MOVIMIENTOS_EN_LA_NUBE_DESACTIVADOS`` stops the lane and
  asks again at once.
* **Offline** (CA-37.3): the files wait in the local folder, encrypted, and the index remembers
  which ones the cloud does not have; they go out oldest first when the connection returns.
* **Steps** (contract, "Movement data"): ``POST /api/agente/movimientos`` with the plaintext's
  size, SHA-256 and rows → ``PUT`` to the pre-signed URL with exactly the headers it came with →
  ``POST …/{archivoId}/confirmacion``. ``409 ARCHIVO_YA_SUBIDO`` and ``422
  MOVIMIENTOS_FUERA_DEL_PLAZO`` drop the file from the queue; ``409 ARCHIVO_NO_SUBIDO`` at the
  confirmation uploads it again; ``400`` drops it (logged: it would never be accepted).
* **Light file** (US-39, contract steps 4–6): right after its Parquet file, the light replay
  file the app draws: ``POST …/{archivoId}/ligero`` → ``PUT`` → ``POST …/ligero/confirmacion``.
  A Parquet file already in the index (``409 ARCHIVO_YA_SUBIDO``) hands its ``archivoId`` so a
  light file that failed before is uploaded on the next pass. ``409 ARCHIVO_YA_SUBIDO`` of the
  light file, a ``404`` (an API without these paths, or a file deleted meanwhile) or a ``400``
  drop only the light file; a temporary failure keeps both on disk for the next pass.
* **Afterwards:** a file only written for the cloud (the local switch is off) is deleted; the
  others stay for their local period.
"""

import hashlib
import logging
from collections.abc import Callable
from typing import Protocol

from te_tengo_captura.almacen.gestor import AlmacenLocal
from te_tengo_captura.almacen.indice import Archivo
from te_tengo_captura.almacen.puntos import contar_filas, instante_ms
from te_tengo_captura.backend.errores import (
    ArchivoNoSubidoError,
    ArchivoYaSubidoError,
    ErrorBackendError,
    FueraDelPlazoError,
    SinPermisoDeMovimientosError,
)
from te_tengo_captura.backend.modelos import (
    SolicitudLigero,
    SolicitudMovimientos,
    SubidaClip,
    SubidaMovimientos,
)

logger = logging.getLogger(__name__)


class RemitenteMovimientos(Protocol):
    """The part of ``ClienteBackend`` this lane uses."""

    def solicitar_subida_movimientos(
        self, solicitud: SolicitudMovimientos
    ) -> SubidaMovimientos: ...

    def subir_archivo(
        self, url: str, cabeceras: dict[str, str], datos: bytes, que: str
    ) -> None: ...

    def confirmar_movimientos(self, archivo_id: str) -> None: ...

    def solicitar_subida_ligero(
        self, archivo_id: str, solicitud: SolicitudLigero
    ) -> SubidaClip: ...

    def confirmar_ligero(self, archivo_id: str) -> None: ...


class CarrilMovimientos:
    def __init__(self, almacen: AlmacenLocal, camara_id: Callable[[], str | None]) -> None:
        self._almacen = almacen
        self._camara_id = camara_id

    def pendientes(self) -> list[Archivo]:
        """The files this lane would upload now (none while the cloud is off)."""
        camara_id = self._camara_id()
        if not camara_id or not self._almacen.sube_movimientos:
            return []
        return self._almacen.pendientes_de_subir(camara_id)

    def subir(self, remitente: RemitenteMovimientos) -> int:
        """Uploads the pending files in order; raises the first failure that may pass later."""
        subidos = 0
        for archivo in self.pendientes():
            if not self._almacen.sube_movimientos:
                break
            if self._subir(remitente, archivo):
                subidos += 1
        return subidos

    def _subir(self, remitente: RemitenteMovimientos, archivo: Archivo) -> bool:
        datos = self._almacen.leer(archivo)
        if datos is None:
            self._almacen.olvidar(archivo)
            return False
        solicitud = SolicitudMovimientos(
            desde=instante_ms(archivo.desde_ms),
            hasta=instante_ms(archivo.hasta_ms),
            tamano_bytes=len(datos),
            sha256=hashlib.sha256(datos).hexdigest(),
            fotogramas=contar_filas(datos),
        )
        try:
            subida = remitente.solicitar_subida_movimientos(solicitud)
        except ArchivoYaSubidoError as error:
            logger.info("Movimientos %s: ya estaban en la nube", archivo.ruta)
            archivo_id = error.cuerpo.get("archivoId")
            if isinstance(archivo_id, str):
                self._subir_ligero(remitente, archivo, archivo_id)
            self._almacen.terminar_subida(archivo)
            return False
        except FueraDelPlazoError as error:
            logger.info("Movimientos %s: no se suben (%s)", archivo.ruta, error.codigo)
            self._almacen.terminar_subida(archivo)
            return False
        except SinPermisoDeMovimientosError:
            self._sin_permiso()
            raise
        except ErrorBackendError as error:
            if error.reintentable:
                raise
            logger.error("Movimientos %s rechazados: %s", archivo.ruta, error)
            self._almacen.terminar_subida(archivo)
            return False
        remitente.subir_archivo(
            subida.url_subida, subida.cabeceras, datos, "el archivo de movimientos"
        )
        try:
            remitente.confirmar_movimientos(subida.archivo_id)
        except ArchivoNoSubidoError as error:
            raise ErrorBackendError(f"El almacenamiento no tiene el archivo: {error}") from None
        except SinPermisoDeMovimientosError:
            self._sin_permiso()
            raise
        self._subir_ligero(remitente, archivo, subida.archivo_id)
        self._almacen.terminar_subida(archivo)
        logger.info("Movimientos subidos: %s (%d bytes)", archivo.ruta, len(datos))
        return True

    def _subir_ligero(
        self, remitente: RemitenteMovimientos, archivo: Archivo, archivo_id: str
    ) -> None:
        """Steps 4-6. Raises a failure that may pass later (both files wait for the next pass)."""
        datos = self._almacen.leer_ligero(archivo)
        if datos is None:
            return  # written by an older version, or damaged: the Parquet file goes alone
        solicitud = SolicitudLigero(
            tamano_bytes=len(datos), sha256=hashlib.sha256(datos).hexdigest()
        )
        try:
            subida = remitente.solicitar_subida_ligero(archivo_id, solicitud)
        except ArchivoYaSubidoError:
            return
        except SinPermisoDeMovimientosError:
            self._sin_permiso()
            raise
        except ErrorBackendError as error:
            if error.reintentable:
                raise
            logger.warning("Movimientos ligeros %s no se suben: %s", archivo.ruta, error)
            return
        remitente.subir_archivo(
            subida.url_subida, subida.cabeceras, datos, "el archivo ligero de movimientos"
        )
        try:
            remitente.confirmar_ligero(archivo_id)
        except ArchivoNoSubidoError as error:
            if error.estado == 404:  # deleted meanwhile
                return
            raise ErrorBackendError(f"El almacenamiento no tiene el ligero: {error}") from None
        except SinPermisoDeMovimientosError:
            self._sin_permiso()
            raise
        except ErrorBackendError as error:
            if error.reintentable:
                raise
            logger.warning("Movimientos ligeros %s rechazados: %s", archivo.ruta, error)

    def _sin_permiso(self) -> None:
        logger.warning("La nube ya no acepta movimientos: se consulta el permiso")
        self._almacen.pedir_permiso()
