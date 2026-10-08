"""Control channel of the live view: the WebSocket ``/api/agente/transmision``.

``docs/AGENT_CONTRACT.md`` ("Live view"): the agent keeps one WebSocket open with its camera
token in the handshake (``Authorization: Bearer``) and receives **text JSON only**:

* ``{"transmitir": true, "urlPublicacion", "usuario", "clave", "modo"?}``: start publishing;
* ``{"modo": "VIDEO_CON_POSTURA"}``: change the mode during a transmission;
* ``{"transmitir": false}``: stop publishing.

The URL is the API's (``api_url``) with ``ws://`` or ``wss://``. A ``401`` in the handshake
registers the camera again (contract, "Token expiry"). Any other failure, or a closed
connection, retries after 1 s doubling up to 30 s (implementation choice), reset after a
connection opens. When the connection is lost the live view stops: the API sends
``transmitir: true`` again on reconnect if someone is still watching, and a stream nobody can
stop is worse for privacy than a short cut. Neither the token nor the publish token is logged.
"""

import json
import logging
import threading
from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit

from pydantic import ValidationError

from te_tengo_captura.backend.cliente import API_VERSION
from te_tengo_captura.backend.errores import ErrorBackendError
from te_tengo_captura.backend.modelos import ModoVista, OrdenTransmision

logger = logging.getLogger(__name__)

# websockets logs the handshake headers (with the bearer token) at DEBUG.
logging.getLogger("websockets").setLevel(logging.WARNING)

RUTA_TRANSMISION = "/api/agente/transmision"
REINTENTO_INICIAL_S = 1.0
REINTENTO_MAXIMO_S = 30.0
TIMEOUT_APERTURA_S = 10.0
INTERVALO_PING_S = 20.0


class FuenteToken(Protocol):
    def token_vigente(self) -> str: ...

    def renovar_token(self, rechazado: str) -> str: ...


class ReceptorTransmision(Protocol):
    def transmitir(
        self, url: str, usuario: str | None, clave: str | None, modo: ModoVista
    ) -> None: ...

    def cambiar_modo(self, modo: ModoVista) -> None: ...

    def detener(self) -> None: ...


def url_websocket(api_url: str) -> str:
    """``https://host/base`` → ``wss://host/base/api/agente/transmision``."""
    partes = urlsplit(api_url.rstrip("/"))
    esquema = "wss" if partes.scheme == "https" else "ws"
    return urlunsplit(partes._replace(scheme=esquema, path=partes.path + RUTA_TRANSMISION))


def _conectar(url: str, token: str) -> Any:
    from websockets.sync.client import connect

    return connect(
        url,
        additional_headers={"Authorization": f"Bearer {token}", "Api-Version": API_VERSION},
        open_timeout=TIMEOUT_APERTURA_S,
        ping_interval=INTERVALO_PING_S,
        ping_timeout=INTERVALO_PING_S,
        max_size=64 * 1024,
    )


class CanalTransmision:
    def __init__(
        self,
        cliente: FuenteToken,
        api_url: str,
        receptor: ReceptorTransmision,
        conectar: Callable[[str, str], Any] = _conectar,
        reintento_inicial_s: float = REINTENTO_INICIAL_S,
        reintento_maximo_s: float = REINTENTO_MAXIMO_S,
    ) -> None:
        self._cliente = cliente
        self._url = url_websocket(api_url)
        self._receptor = receptor
        self._conectar = conectar
        self._reintento_inicial = reintento_inicial_s
        self._reintento_maximo = reintento_maximo_s
        self._fallos = 0
        self._conexion: Any = None
        self._candado = threading.Lock()
        self.conectado = False
        self._detenido = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="transmision", daemon=True)

    def iniciar(self) -> None:
        self._hilo.start()

    def detener(self, espera_s: float = 5.0) -> None:
        self._detenido.set()
        with self._candado:
            conexion = self._conexion
        if conexion is not None:
            conexion.close()
        if self._hilo.is_alive():
            self._hilo.join(espera_s)

    # ------------------------------------------------------------------ internals

    def _correr(self) -> None:
        while not self._detenido.is_set():
            espera = self.conectar_una_vez()
            if espera > 0:
                self._detenido.wait(espera)

    def conectar_una_vez(self) -> float:
        """One connection until it closes; returns how long to wait before the next one."""
        from websockets.exceptions import InvalidStatus

        token: str | None = None
        try:
            token = self._cliente.token_vigente()
            self._atender(token)
        except InvalidStatus as error:
            estado = error.response.status_code
            if estado == 401 and token is not None:
                logger.info("Canal de vista en vivo: token rechazado; se registra de nuevo")
                try:
                    self._cliente.renovar_token(token)
                except ErrorBackendError as registro:
                    return self._fallo(f"registro: {registro}")
                if self._fallos == 0:
                    self._fallos = 1
                    return 0.0  # retry once at once with the new token
            return self._fallo(f"HTTP {estado}")
        except ErrorBackendError as error:
            return self._fallo(str(error))
        except Exception as error:
            # Network errors, timeouts, handshake failures and closed connections.
            return self._fallo(type(error).__name__)
        finally:
            self._cerrado()
        return 0.0 if self._detenido.is_set() else self._fallo("conexión cerrada")

    def _atender(self, token: str) -> None:
        with self._conectar(self._url, token) as conexion:
            with self._candado:
                self._conexion = conexion
            if self._detenido.is_set():
                return
            self.conectado = True
            self._fallos = 0
            logger.info("Canal de vista en vivo conectado")
            for mensaje in conexion:
                self.atender_mensaje(mensaje)

    def atender_mensaje(self, mensaje: str | bytes) -> None:
        if isinstance(mensaje, bytes):
            logger.warning("Canal de vista en vivo: mensaje binario ignorado")
            return
        try:
            orden = OrdenTransmision.model_validate(json.loads(mensaje))
        except (ValueError, ValidationError) as error:
            # Never echo the message: it may carry the publish token.
            logger.warning(
                "Canal de vista en vivo: mensaje inválido ignorado (%s)", type(error).__name__
            )
            return
        if orden.transmitir is True:
            if not orden.url_publicacion:
                logger.warning("Canal de vista en vivo: «transmitir» sin urlPublicacion")
                return
            self._receptor.transmitir(
                orden.url_publicacion, orden.usuario, orden.clave, orden.modo or ModoVista.VIDEO
            )
        elif orden.transmitir is False:
            self._receptor.detener()
        elif orden.modo is not None:
            self._receptor.cambiar_modo(orden.modo)

    def _cerrado(self) -> None:
        with self._candado:
            self._conexion = None
        if self.conectado:
            self.conectado = False
            logger.info("Canal de vista en vivo cerrado")
        self._receptor.detener()

    def _fallo(self, motivo: str) -> float:
        self._fallos += 1
        espera = min(self._reintento_maximo, self._reintento_inicial * 2.0 ** (self._fallos - 1))
        nivel = logging.WARNING if self._fallos == 1 else logging.DEBUG
        logger.log(
            nivel, "Canal de vista en vivo sin conexión (%s); reintento en %.0f s", motivo, espera
        )
        return espera
