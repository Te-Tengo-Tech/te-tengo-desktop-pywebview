"""The three OAuth endpoints of the PC link (``docs/AGENT_CONTRACT.md``, "PC link"; ADR 0009).

They follow the RFCs, not the rest of the contract: requests are
``application/x-www-form-urlencoded``, responses snake_case JSON, errors
``{"error", "error_description"}`` (RFC 6749 §5.2), and no bearer token is sent.

* ``pedir_codigo``: device authorization (RFC 8628 §3.1) → ``CodigoVinculacion``.
* ``canjear``: the token endpoint with the device code (RFC 8628 §3.4) → ``TokensPc`` or
  ``RechazoOAuthError`` (``authorization_pending``, ``slow_down``, ``access_denied``,
  ``expired_token``, ``invalid_grant``).
* ``renovar``: the token endpoint with the refresh token (RFC 6749 §6); the answer carries a
  **new** refresh token, and the old one must never be presented again (RFC 9700 §4.14.2).
* ``revocar``: RFC 7009; revoking the refresh token unlinks the PC (CA-31.3).

Secrets: ``device_code``, the access token and the refresh token are never logged nor shown
(``repr=False``); the ``user_code`` is not secret (the PC shows it in large type).
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from te_tengo_captura.backend.cliente import API_VERSION, TIMEOUT
from te_tengo_captura.backend.errores import ErrorBackendError, SinConexionError

logger = logging.getLogger(__name__)

CLIENT_ID = "te-tengo-captura"
RUTA_VINCULACION = "/api/agente/vinculacion"
RUTA_TOKEN = "/api/agente/token"
RUTA_REVOCACION = "/api/agente/token/revocacion"
GRANT_DISPOSITIVO = "urn:ietf:params:oauth:grant-type:device_code"
GRANT_RENOVACION = "refresh_token"


class RechazoOAuthError(ErrorBackendError):
    """An RFC 6749 §5.2 error: ``codigo`` is the ``error`` field (``slow_down`` …)."""


@dataclass(frozen=True, slots=True)
class CodigoVinculacion:
    """RFC 8628 §3.2: what the PC shows (``user_code``, the QR of ``verification_uri_complete``)."""

    device_code: str = field(repr=False)
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


@dataclass(frozen=True, slots=True)
class TokensPc:
    """The PC's tokens: a 1 h access token and a refresh token that rotates on every use."""

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_in: int
    pc_id: str
    hogar_id: str


class ClienteOAuth:
    def __init__(self, api_url: str, transporte: httpx.BaseTransport | None = None) -> None:
        self._http = httpx.Client(
            base_url=api_url,
            headers={"Api-Version": API_VERSION},
            timeout=TIMEOUT,
            transport=transporte,
        )

    def pedir_codigo(
        self,
        nombre_pc: str,
        sistema_operativo: str,
        version_agente: str,
        id_instalacion: str | None = None,
    ) -> CodigoVinculacion:
        campos = {
            "client_id": CLIENT_ID,
            "nombre_pc": nombre_pc,
            "sistema_operativo": sistema_operativo,
            "version_agente": version_agente,
        }
        if id_instalacion is not None:
            campos["id_instalacion"] = id_instalacion
        datos = self._formulario(RUTA_VINCULACION, campos)
        try:
            return CodigoVinculacion(
                device_code=str(datos["device_code"]),
                user_code=str(datos["user_code"]),
                verification_uri=str(datos["verification_uri"]),
                verification_uri_complete=str(datos["verification_uri_complete"]),
                expires_in=int(datos["expires_in"]),
                interval=int(datos.get("interval", 5)),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ErrorBackendError(f"Respuesta inesperada al pedir el código: {error}") from None

    def canjear(self, device_code: str) -> TokensPc:
        """One poll of the device code: the tokens, or ``RechazoOAuthError`` while not approved."""
        return self._tokens(
            {"grant_type": GRANT_DISPOSITIVO, "device_code": device_code, "client_id": CLIENT_ID}
        )

    def renovar(self, refresh_token: str) -> TokensPc:
        return self._tokens(
            {"grant_type": GRANT_RENOVACION, "refresh_token": refresh_token, "client_id": CLIENT_ID}
        )

    def revocar(
        self, refresh_token: str, datos_locales_borrados: bool = False, motivo: str | None = None
    ) -> None:
        campos = {
            "token": refresh_token,
            "token_type_hint": "refresh_token",
            "client_id": CLIENT_ID,
        }
        if datos_locales_borrados:
            campos["datos_locales_borrados"] = "true"
        if motivo:
            campos["motivo"] = motivo
        self._formulario(RUTA_REVOCACION, campos, cuerpo=False)

    def cerrar(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------ internals

    def _tokens(self, campos: dict[str, str]) -> TokensPc:
        datos = self._formulario(RUTA_TOKEN, campos)
        try:
            return TokensPc(
                access_token=str(datos["access_token"]),
                refresh_token=str(datos["refresh_token"]),
                expires_in=int(datos["expires_in"]),
                pc_id=str(datos["pc_id"]),
                hogar_id=str(datos["hogar_id"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ErrorBackendError(f"Respuesta inesperada de los tokens: {error}") from None

    def _formulario(self, ruta: str, campos: dict[str, str], cuerpo: bool = True) -> Any:
        try:
            respuesta = self._http.post(ruta, data=campos)
        except httpx.TransportError as error:
            raise SinConexionError(
                f"Sin conexión con el backend (POST {ruta}): {type(error).__name__}"
            ) from None
        if respuesta.is_error:
            codigo = None
            try:
                problema = respuesta.json()
                if isinstance(problema, dict):
                    codigo = problema.get("error")
            except ValueError:
                pass
            mensaje = f"POST {ruta} → {respuesta.status_code} {codigo or ''}".strip()
            if codigo and respuesta.status_code in (400, 401):
                raise RechazoOAuthError(mensaje, respuesta.status_code, str(codigo))
            raise ErrorBackendError(mensaje, respuesta.status_code)
        if not cuerpo:
            return None
        try:
            return respuesta.json()
        except ValueError:
            raise ErrorBackendError(f"Respuesta inesperada de POST {ruta}") from None
