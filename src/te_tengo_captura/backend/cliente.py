"""HTTP client of the agent contract (``docs/AGENT_CONTRACT.md``, version 1).

It is synchronous and thread-safe: the capture loop, the heartbeat and the outbox call it from
their own worker threads. The camera token is obtained by registering with the installation
credential and renewed on any ``401`` other than ``CREDENCIAL_INVALIDA``. Neither the credential
nor the token, nor the pre-signed upload URL, is ever logged.
"""

import logging
import threading
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from te_tengo_captura.backend.errores import (
    POR_CODIGO,
    ErrorBackendError,
    NoAutorizadoError,
    SinConexionError,
)
from te_tengo_captura.backend.modelos import (
    ConfiguracionRemota,
    EstadoCaptura,
    EventoAgente,
    EventoRecibido,
    Registro,
    Senal,
    SolicitudClip,
    SolicitudRegistro,
    SubidaClip,
)

logger = logging.getLogger(__name__)

_Modelo = TypeVar("_Modelo", bound=BaseModel)

# httpx logs every request URL at INFO, and the clip upload URL carries its signature.
for _nombre in ("httpx", "httpcore"):
    logging.getLogger(_nombre).setLevel(logging.WARNING)

API_VERSION = "1"
RUTA_REGISTRO = "/api/agente/camaras/registro"
RUTA_ESTADO = "/api/agente/estado-captura"
RUTA_SENAL = "/api/agente/senal"
RUTA_EVENTOS = "/api/agente/eventos"
RUTA_CLIP = "/api/agente/eventos/{evento_id}/clip"
RUTA_CONFIGURACION = "/api/agente/configuracion"

# Seconds; a clip upload carries about 1 MB, so it gets a longer write timeout.
TIMEOUT = httpx.Timeout(10.0, connect=5.0)
TIMEOUT_SUBIDA = httpx.Timeout(10.0, connect=5.0, write=60.0)


class ClienteBackend:
    def __init__(
        self,
        api_url: str,
        credencial_instalacion: str,
        nombre_habitacion: str,
        version_agente: str,
        transporte: httpx.BaseTransport | None = None,
    ) -> None:
        self._credencial = credencial_instalacion
        self._nombre_habitacion = nombre_habitacion
        self._version = version_agente
        self._http = httpx.Client(
            base_url=api_url,
            headers={"Api-Version": API_VERSION},
            timeout=TIMEOUT,
            transport=transporte,
        )
        # A separate client without base headers for the pre-signed storage URL.
        self._almacen = httpx.Client(timeout=TIMEOUT_SUBIDA, transport=transporte)
        self._candado = threading.Lock()
        # Heartbeat, outbox and thresholds share the client: only one of them registers at a time.
        self._candado_registro = threading.Lock()
        self._registro: Registro | None = None

    @property
    def registro(self) -> Registro | None:
        return self._registro

    def secretos(self) -> list[str]:
        """Values that must never appear in a log (for the log filter)."""
        token = self._token()
        return [self._credencial, *([token] if token else [])]

    # ------------------------------------------------------------------ contract

    def registrar(self) -> Registro:
        """Registers the camera and keeps the new token (CA-06.1)."""
        cuerpo = SolicitudRegistro(
            credencial_instalacion=self._credencial,
            nombre_habitacion=self._nombre_habitacion,
            version_agente=self._version,
        )
        respuesta = self._enviar("POST", RUTA_REGISTRO, json=cuerpo.json_api())
        registro = _leer(Registro, respuesta)
        with self._candado:
            self._registro = registro
        logger.info("Cámara registrada: %s (%s)", registro.camara_id, registro.nombre_habitacion)
        return registro

    def estado_captura(self) -> EstadoCaptura:
        return _leer(EstadoCaptura, self._autenticado("GET", RUTA_ESTADO))

    def senal(self, webcam_conectada: bool, deteccion_confiable: bool) -> EstadoCaptura:
        cuerpo = Senal(
            webcam_conectada=webcam_conectada,
            deteccion_confiable=deteccion_confiable,
            version_agente=self._version,
        )
        return _leer(EstadoCaptura, self._autenticado("POST", RUTA_SENAL, json=cuerpo.json_api()))

    def publicar_evento(self, evento: EventoAgente) -> tuple[EventoRecibido, bool]:
        """Publishes an event. Returns the response and whether it was a duplicate (``200``)."""
        respuesta = self._autenticado("POST", RUTA_EVENTOS, json=evento.json_api())
        return _leer(EventoRecibido, respuesta), respuesta.status_code == 200

    def solicitar_subida_clip(self, evento_id: str, tamano_bytes: int) -> SubidaClip:
        cuerpo = SolicitudClip(tamano_bytes=tamano_bytes)
        ruta = RUTA_CLIP.format(evento_id=evento_id)
        return _leer(SubidaClip, self._autenticado("POST", ruta, json=cuerpo.json_api()))

    def subir_clip(self, subida: SubidaClip, mp4: bytes) -> None:
        """``PUT`` of the MP4 to the pre-signed URL, with the headers the backend returned."""
        try:
            respuesta = self._almacen.put(subida.url_subida, content=mp4, headers=subida.cabeceras)
        except httpx.TransportError as error:
            raise SinConexionError(
                f"Sin conexión al subir el clip: {type(error).__name__}"
            ) from None
        if respuesta.is_error:
            raise ErrorBackendError(
                f"El almacenamiento rechazó el clip ({respuesta.status_code})",
                respuesta.status_code,
            )

    def configuracion(self) -> ConfiguracionRemota:
        return _leer(ConfiguracionRemota, self._autenticado("GET", RUTA_CONFIGURACION))

    def token_vigente(self) -> str:
        """The camera token, registering first if there is none (control channel handshake)."""
        return self._token() or self._registrar_si_hace_falta(rechazado=None)

    def renovar_token(self, rechazado: str) -> str:
        """A ``401`` outside this client (the control channel): register again once."""
        return self._registrar_si_hace_falta(rechazado=rechazado)

    def cerrar(self) -> None:
        self._http.close()
        self._almacen.close()

    # ------------------------------------------------------------------ internals

    def _autenticado(self, metodo: str, ruta: str, json: Any = None) -> httpx.Response:
        token = self.token_vigente()
        try:
            return self._enviar(metodo, ruta, json=json, token=token)
        except NoAutorizadoError:
            # The token expired or was revoked: register again once (contract, "Token expiry").
            logger.info("Token rechazado en %s; se registra de nuevo", ruta)
            token = self._registrar_si_hace_falta(rechazado=token)
            return self._enviar(metodo, ruta, json=json, token=token)

    def _registrar_si_hace_falta(self, rechazado: str | None) -> str:
        """Registers unless another thread already got a token other than the rejected one."""
        with self._candado_registro:
            actual = self._token()
            if actual is not None and actual != rechazado:
                return actual
            return self.registrar().token

    def _token(self) -> str | None:
        with self._candado:
            return self._registro.token if self._registro else None

    def _enviar(
        self, metodo: str, ruta: str, json: Any = None, token: str | None = None
    ) -> httpx.Response:
        cabeceras = {"Authorization": f"Bearer {token}"} if token else None
        try:
            respuesta = self._http.request(metodo, ruta, json=json, headers=cabeceras)
        except httpx.TransportError as error:
            raise SinConexionError(
                f"Sin conexión con el backend ({metodo} {ruta}): {type(error).__name__}"
            ) from None
        if respuesta.is_error:
            raise _error(metodo, ruta, respuesta)
        return respuesta


def _error(metodo: str, ruta: str, respuesta: httpx.Response) -> ErrorBackendError:
    codigo: str | None = None
    detalle = ""
    try:
        problema = respuesta.json()
        if isinstance(problema, dict):
            codigo = problema.get("codigo")
            detalle = str(problema.get("detail") or problema.get("title") or "")
    except ValueError:
        pass
    mensaje = f"{metodo} {ruta} → {respuesta.status_code} {codigo or ''} {detalle}".strip()
    if codigo in POR_CODIGO:
        return POR_CODIGO[codigo](mensaje, respuesta.status_code, codigo)
    if respuesta.status_code == 401:
        return NoAutorizadoError(mensaje, 401, codigo)
    return ErrorBackendError(mensaje, respuesta.status_code, codigo)


def _leer(modelo: type[_Modelo], respuesta: httpx.Response) -> _Modelo:
    try:
        return modelo.model_validate(respuesta.json())
    except (ValueError, ValidationError) as error:
        raise ErrorBackendError(
            f"Respuesta inesperada del backend ({respuesta.request.url.path}): {error}",
            respuesta.status_code,
        ) from None
