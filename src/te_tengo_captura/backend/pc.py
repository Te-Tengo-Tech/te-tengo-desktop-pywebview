"""The linked PC's own endpoints (``docs/AGENT_CONTRACT.md``, "PC link"), with its access token.

* ``GET /api/agente/pc``: the household and who approved the link (D-28.4).
* ``POST /api/agente/pc/senal`` every 30 s: keeps the PC «En línea» in the app even with no
  camera in use (CA-30.2).
* ``DELETE /api/agente/pc``: «Desvincular esta PC» (CA-31.3), with ``datosLocalesBorrados`` when
  the person also deleted the data saved on the PC (CA-31.6).

A ``401 SESION_EXPIRADA`` renews the session once and retries; a ``401 PC_DESVINCULADA`` tells
the session the PC left the household. Tokens are never logged.
"""

import logging
from typing import Any, Protocol

import httpx

from te_tengo_captura.backend.cliente import (
    API_VERSION,
    TIMEOUT,
    error_de_respuesta,
    leer_modelo,
)
from te_tengo_captura.backend.errores import (
    NoAutorizadoError,
    PcDesvinculadaError,
    SinConexionError,
)
from te_tengo_captura.backend.modelos import PcDelAgente, SenalPc

logger = logging.getLogger(__name__)

RUTA_PC = "/api/agente/pc"
RUTA_SENAL_PC = "/api/agente/pc/senal"


class Sesion(Protocol):
    def token_vigente(self) -> str: ...

    def renovar_token(self, rechazado: str) -> str: ...

    def desvincular(self, motivo: str) -> None: ...


class ClientePc:
    def __init__(
        self, api_url: str, sesion: Sesion, transporte: httpx.BaseTransport | None = None
    ) -> None:
        self._sesion = sesion
        self._http = httpx.Client(
            base_url=api_url,
            headers={"Api-Version": API_VERSION},
            timeout=TIMEOUT,
            transport=transporte,
        )

    def pc(self) -> PcDelAgente:
        return leer_modelo(PcDelAgente, self.autenticado("GET", RUTA_PC))

    def senal(self, version_agente: str, sistema_operativo: str) -> PcDelAgente:
        cuerpo = SenalPc(version_agente=version_agente, sistema_operativo=sistema_operativo)
        respuesta = self.autenticado("POST", RUTA_SENAL_PC, json=cuerpo.json_api())
        return leer_modelo(PcDelAgente, respuesta)

    def desvincular(self, datos_locales_borrados: bool) -> None:
        parametros = {"datosLocalesBorrados": "true"} if datos_locales_borrados else None
        self.autenticado("DELETE", RUTA_PC, params=parametros)

    def cerrar(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------ internals

    def autenticado(
        self, metodo: str, ruta: str, json: Any = None, params: dict[str, str] | None = None
    ) -> httpx.Response:
        token = self._sesion.token_vigente()
        try:
            return self._enviar(metodo, ruta, token, json, params)
        except NoAutorizadoError:
            logger.info("Token de la PC rechazado en %s; se renueva", ruta)
            token = self._sesion.renovar_token(token)
            return self._enviar(metodo, ruta, token, json, params)

    def _enviar(
        self,
        metodo: str,
        ruta: str,
        token: str,
        json: Any = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            respuesta = self._http.request(
                metodo,
                ruta,
                json=json,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.TransportError as error:
            raise SinConexionError(
                f"Sin conexión con el backend ({metodo} {ruta}): {type(error).__name__}"
            ) from None
        if respuesta.is_error:
            fallo = error_de_respuesta(metodo, ruta, respuesta)
            if isinstance(fallo, PcDesvinculadaError):
                self._sesion.desvincular("PC_DESVINCULADA")
            raise fallo
        return respuesta
