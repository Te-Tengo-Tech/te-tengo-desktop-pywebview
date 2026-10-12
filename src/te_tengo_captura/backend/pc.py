"""The linked PC's own endpoints (``docs/AGENT_CONTRACT.md``, "PC link"), with its access token.

* ``GET /api/agente/pc``: the household and who approved the link (D-28.4).
* ``POST /api/agente/pc/senal`` every 30 s: keeps the PC «En línea» in the app even with no
  camera in use (CA-30.2), with whether «Actualizar automáticamente» is on (US-43, CA-43.7).
* ``DELETE /api/agente/pc``: «Desvincular esta PC» (CA-31.3), with ``datosLocalesBorrados`` when
  the person also deleted the data saved on the PC (CA-31.6).
* The PC's webcams (US-29): ``PUT …/camaras/inventario`` (the whole list it detects),
  ``GET …/camaras`` (after reconnecting), ``POST …/camaras/tokens`` (new per-camera tokens),
  ``GET /api/agente/ambientes`` and, for «Elegir aquí» (CA-29.8), ``PUT``/``DELETE …/camaras``.

A ``401 SESION_EXPIRADA`` renews the session once and retries; a ``401 PC_DESVINCULADA`` tells
the session the PC left the household. Tokens are never logged.
"""

import logging
from typing import Any, Protocol

import httpx

from te_tengo_captura.backend.cliente import (
    API_VERSION,
    RUTA_ESTADO_MOVIMIENTOS,
    TIMEOUT,
    error_de_respuesta,
    leer_modelo,
)
from te_tengo_captura.backend.errores import (
    ErrorBackendError,
    NoAutorizadoError,
    PcDesvinculadaError,
    SinConexionError,
)
from te_tengo_captura.backend.modelos import (
    Ambiente,
    AsignacionCamara,
    CamaraDeLaPc,
    EstadoMovimientos,
    Inventario,
    PcDelAgente,
    SenalPc,
    WebcamInventario,
)

logger = logging.getLogger(__name__)

RUTA_PC = "/api/agente/pc"
RUTA_SENAL_PC = "/api/agente/pc/senal"
RUTA_INVENTARIO = "/api/agente/pc/camaras/inventario"
RUTA_CAMARAS = "/api/agente/pc/camaras"
RUTA_TOKENS = "/api/agente/pc/camaras/tokens"
RUTA_AMBIENTES = "/api/agente/ambientes"
RUTA_ACTIVIDAD = "/api/agente/pc/actividad"


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

    def senal(
        self,
        version_agente: str,
        sistema_operativo: str,
        actualizacion_automatica: bool | None = None,
    ) -> PcDelAgente:
        cuerpo = SenalPc(
            version_agente=version_agente,
            sistema_operativo=sistema_operativo,
            actualizacion_automatica=actualizacion_automatica,
        )
        respuesta = self.autenticado("POST", RUTA_SENAL_PC, json=cuerpo.json_api())
        return leer_modelo(PcDelAgente, respuesta)

    def desvincular(self, datos_locales_borrados: bool) -> None:
        parametros = {"datosLocalesBorrados": "true"} if datos_locales_borrados else None
        self.autenticado("DELETE", RUTA_PC, params=parametros)

    def inventario(self, webcams: list[WebcamInventario]) -> list[CamaraDeLaPc]:
        cuerpo = Inventario(webcams=webcams).json_api()
        return _camaras(self.autenticado("PUT", RUTA_INVENTARIO, json=cuerpo))

    def camaras(self) -> list[CamaraDeLaPc]:
        return _camaras(self.autenticado("GET", RUTA_CAMARAS))

    def tokens_de_camaras(self) -> list[CamaraDeLaPc]:
        return _camaras(self.autenticado("POST", RUTA_TOKENS))

    def ambientes(self) -> list[Ambiente]:
        respuesta = self.autenticado("GET", RUTA_AMBIENTES)
        try:
            return [Ambiente.model_validate(a) for a in respuesta.json()]
        except (ValueError, TypeError) as error:
            raise ErrorBackendError(f"Respuesta inesperada de los ambientes: {error}") from None

    def asignar(self, asignacion: AsignacionCamara) -> CamaraDeLaPc:
        """«Usar esta cámara» from the PC (an upsert by ``dispositivoId``)."""
        respuesta = self.autenticado("PUT", RUTA_CAMARAS, json=asignacion.json_api())
        return leer_modelo(CamaraDeLaPc, respuesta)

    def dejar_de_usar(self, camara_id: str) -> None:
        self.autenticado("DELETE", f"{RUTA_CAMARAS}/{camara_id}")

    def estado_movimientos(self) -> EstadoMovimientos:
        """Whether movements may be stored (US-35, US-37), with the PC's token."""
        return leer_modelo(EstadoMovimientos, self.autenticado("GET", RUTA_ESTADO_MOVIMIENTOS))

    def actividad(self, cambios: list[dict[str, Any]]) -> None:
        """The PC's own changes for the activity log (US-33), also those made offline."""
        self.autenticado("POST", RUTA_ACTIVIDAD, json={"cambios": cambios})

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


def _camaras(respuesta: httpx.Response) -> list[CamaraDeLaPc]:
    try:
        return [CamaraDeLaPc.model_validate(c) for c in respuesta.json()]
    except (ValueError, TypeError) as error:
        raise ErrorBackendError(f"Respuesta inesperada de las cámaras: {error}") from None
