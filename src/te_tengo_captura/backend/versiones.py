"""``GET /api/versiones`` (``docs/AGENT_CONTRACT.md``, "Updates (US-43)"): the latest published
Te Tengo Captura per system, its installer and SHA-256.

The path is public: it is called **without** any ``Authorization`` header, so a PC whose token
expired, or one that is not linked yet, still learns about updates (the API answers ``401`` to an
expired bearer token even on a public path). An older backend without the path (``404``) and a
network failure both mean "no information" (``None``); only the person pressing «Buscar
actualizaciones» is told about the missing internet.
"""

import logging

import httpx

from te_tengo_captura.backend.cliente import API_VERSION, TIMEOUT, leer_modelo
from te_tengo_captura.backend.errores import ErrorBackendError, SinConexionError
from te_tengo_captura.backend.modelos import VersionesPublicadas

logger = logging.getLogger(__name__)

RUTA_VERSIONES = "/api/versiones"


class ClienteVersiones:
    def __init__(self, api_url: str, transporte: httpx.BaseTransport | None = None) -> None:
        self._http = httpx.Client(
            base_url=api_url,
            headers={"Api-Version": API_VERSION},
            timeout=TIMEOUT,
            transport=transporte,
        )

    def versiones(self) -> VersionesPublicadas | None:
        """The published versions; ``None`` when the backend does not have the path (``404``).

        Raises ``SinConexionError`` without internet and ``ErrorBackendError`` on other errors."""
        try:
            respuesta = self._http.get(RUTA_VERSIONES)
        except httpx.TransportError as error:
            raise SinConexionError(
                f"Sin conexión con el backend (GET {RUTA_VERSIONES}): {type(error).__name__}"
            ) from None
        if respuesta.status_code == 404:
            logger.info("El backend no publica versiones (GET %s → 404)", RUTA_VERSIONES)
            return None
        if respuesta.is_error:
            raise ErrorBackendError(
                f"GET {RUTA_VERSIONES} → {respuesta.status_code}", respuesta.status_code
            )
        return leer_modelo(VersionesPublicadas, respuesta)

    def cerrar(self) -> None:
        self._http.close()
