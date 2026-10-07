"""Remote thresholds: ``GET /api/agente/configuracion`` (``docs/AGENT_CONTRACT.md``).

Applied at startup and every hour (implementation choice; 5 minutes after a failure). Each remote
field is checked on its own against ``Umbrales``: unknown fields and invalid values are logged
and ignored, and missing fields keep the local values of the installation file. The result is
always computed from the local values, so a field the backend stops sending goes back to its
local value. The speed threshold can never be removed: the classifier needs it.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any, Protocol

from pydantic import ValidationError

from te_tengo_captura.backend.errores import ErrorBackendError
from te_tengo_captura.backend.modelos import ConfiguracionRemota
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

logger = logging.getLogger(__name__)

INTERVALO_S = 3600.0
REINTENTO_S = 300.0


class FuenteConfiguracion(Protocol):
    def configuracion(self) -> ConfiguracionRemota: ...


def combinar(locales: Umbrales, remotos: dict[str, Any]) -> Umbrales:
    """The local thresholds with every valid remote field applied."""
    resultado = locales
    for campo, valor in remotos.items():
        if campo not in Umbrales.model_fields:
            logger.warning("Umbral remoto desconocido ignorado: %s", campo)
            continue
        try:
            candidato = Umbrales.model_validate({**resultado.model_dump(), campo: valor})
        except ValidationError as error:
            detalle = error.errors()[0]["msg"]
            logger.warning("Umbral remoto inválido ignorado: %s=%r (%s)", campo, valor, detalle)
            continue
        if not candidato.calibrado:
            logger.warning("Umbral remoto ignorado: %s no puede quedar sin valor", campo)
            continue
        resultado = candidato
    return resultado


class ActualizadorUmbrales:
    def __init__(
        self,
        fuente: FuenteConfiguracion,
        locales: Umbrales,
        aplicar: Callable[[Umbrales], None],
        version_local: str,
    ) -> None:
        self._fuente = fuente
        self._locales = locales
        self._aplicar = aplicar
        self._version = version_local
        self.vigentes = locales
        self._detenido = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="umbrales", daemon=True)

    def actualizar(self) -> bool:
        """One fetch; ``True`` if the backend answered."""
        try:
            remota = self._fuente.configuracion()
        except ErrorBackendError as error:
            logger.info("Configuración remota no disponible: %s", error)
            return False
        if remota.version_agente != self._version:
            logger.info(
                "Versión del agente publicada: %s (esta: %s)", remota.version_agente, self._version
            )
        nuevos = combinar(self._locales, remota.umbrales)
        if nuevos != self.vigentes:
            logger.info("Umbrales actualizados desde el backend: %s", nuevos.model_dump())
            self.vigentes = nuevos
            self._aplicar(nuevos)
        return True

    def iniciar(self) -> None:
        self._hilo.start()

    def detener(self, espera_s: float = 5.0) -> None:
        self._detenido.set()
        if self._hilo.is_alive():
            self._hilo.join(espera_s)

    def _correr(self) -> None:
        while not self._detenido.is_set():
            try:
                espera = INTERVALO_S if self.actualizar() else REINTENTO_S
            except Exception:
                logger.exception("Error inesperado al leer la configuración remota")
                espera = REINTENTO_S
            self._detenido.wait(espera)
