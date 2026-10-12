"""«Vincular esta PC» (US-28): the RFC 8628 device flow as a state machine (screen D-28.1).

1. Ask for a code (``POST /api/agente/vinculacion``) and show it: the QR of
   ``verification_uri_complete``, the ``user_code`` in large type and the countdown of
   ``expires_in`` (CA-28.1, CA-28.2).
2. Poll ``POST /api/agente/token`` every ``interval`` seconds:
   * ``authorization_pending``: keep polling;
   * ``slow_down``: add 5 s to the interval, for good (RFC 8628 §3.5);
   * ``access_denied``: «No reconozco esta PC» in the app → screen D-28.5, until «Mostrar otro
     código» (CA-28.4);
   * ``expired_token`` or ``invalid_grant``, or the countdown ran out: ask for a new code on its
     own and say «Código nuevo · el anterior venció» (CA-28.3);
   * the tokens: linked (``al_vincular``).
3. Without internet, or when Te Tengo does not answer, the card says so and retries every
   ``REINTENTO_S`` seconds (the prototype's «Reintentamos en 0:25» [implementation choice]);
   «Reintentar ahora» retries at once. A code that is still valid when the connection returns
   is shown again, so a phone that already scanned it can still approve it.

The ``device_code`` is a secret: it is kept in memory only, never shown, logged or written.
"""

import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from te_tengo_captura.backend.errores import ErrorBackendError, SinConexionError
from te_tengo_captura.vinculacion.oauth import (
    ClienteOAuth,
    CodigoVinculacion,
    RechazoOAuthError,
    TokensPc,
)

logger = logging.getLogger(__name__)

REINTENTO_S = 25.0
AUMENTO_SLOW_DOWN_S = 5.0
ESPERA_MAXIMA_S = 1.0  # the thread wakes up at least every second (countdown, «Reintentar ahora»)


class Fase(StrEnum):
    PIDIENDO = "pidiendo"  # asking for a code
    CODIGO = "codigo"  # showing the code, waiting for the approval
    SIN_INTERNET = "sin_internet"
    SIN_SERVIDOR = "sin_servidor"  # Te Tengo did not answer
    RECHAZADA = "rechazada"  # «No reconozco esta PC»
    VINCULADA = "vinculada"


@dataclass(frozen=True, slots=True)
class EstadoVinculacion:
    fase: Fase
    codigo: str | None = None  # «KQWT-MXHD»
    url: str | None = None  # verification_uri, shown without the scheme
    url_completa: str | None = None  # verification_uri_complete: the QR
    segundos: int = 0  # until the code expires
    renovado: bool = False  # a new code replaced an expired one
    reintento: int = 0  # seconds until the next attempt when offline


class Vinculador:
    def __init__(
        self,
        oauth: ClienteOAuth,
        nombre_pc: str,
        sistema_operativo: str,
        version_agente: str,
        al_vincular: Callable[[TokensPc], None],
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self._oauth = oauth
        self._nombre = nombre_pc
        self._sistema = sistema_operativo
        self._version = version_agente
        self._al_vincular = al_vincular
        self._reloj = reloj
        self._candado = threading.Lock()
        self._fase = Fase.PIDIENDO
        self._codigo: CodigoVinculacion | None = None
        self._vence = 0.0
        self._intervalo = 5.0
        self._proximo = 0.0
        self._renovado = False

    # ------------------------------------------------------------------ queries

    @property
    def fase(self) -> Fase:
        return self._fase

    def estado(self) -> EstadoVinculacion:
        with self._candado:
            ahora = self._reloj()
            codigo = self._codigo if self._fase is Fase.CODIGO else None
            reintento = (
                max(0, math.ceil(self._proximo - ahora))
                if self._fase in (Fase.SIN_INTERNET, Fase.SIN_SERVIDOR)
                else 0
            )
            return EstadoVinculacion(
                fase=self._fase,
                codigo=codigo.user_code if codigo else None,
                url=_sin_esquema(codigo.verification_uri) if codigo else None,
                url_completa=codigo.verification_uri_complete if codigo else None,
                segundos=max(0, math.ceil(self._vence - ahora)) if codigo else 0,
                renovado=self._renovado if codigo else False,
                reintento=reintento,
            )

    # ------------------------------------------------------------------ actions

    def reintentar_ahora(self) -> None:
        with self._candado:
            if self._fase in (Fase.SIN_INTERNET, Fase.SIN_SERVIDOR):
                self._proximo = 0.0

    def otro_codigo(self) -> None:
        """«Mostrar otro código» after a rejection."""
        with self._candado:
            if self._fase is Fase.RECHAZADA:
                self._fase, self._codigo, self._renovado, self._proximo = (
                    Fase.PIDIENDO,
                    None,
                    False,
                    0.0,
                )

    def paso(self) -> float:
        """One step; returns how long the thread may wait before the next one."""
        with self._candado:
            ahora = self._reloj()
            fase = self._fase
            if fase in (Fase.RECHAZADA, Fase.VINCULADA):
                return ESPERA_MAXIMA_S
            if ahora < self._proximo:
                return min(ESPERA_MAXIMA_S, self._proximo - ahora)
            if self._codigo is not None and ahora >= self._vence:
                logger.info("El código de vinculación venció; se pide otro")
                self._codigo, self._renovado = None, True
            if self._codigo is None:
                self._pedir(ahora)
            else:
                self._sondear(ahora)
            return min(ESPERA_MAXIMA_S, max(0.0, self._proximo - self._reloj()))

    # ------------------------------------------------------------------ internals

    def _pedir(self, ahora: float) -> None:
        try:
            codigo = self._oauth.pedir_codigo(self._nombre, self._sistema, self._version)
        except ErrorBackendError as error:
            self._sin_conexion(error, ahora)
            return
        self._codigo = codigo
        self._fase = Fase.CODIGO
        self._vence = ahora + codigo.expires_in
        self._intervalo = float(max(1, codigo.interval))
        self._proximo = ahora + self._intervalo
        logger.info(
            "Código para vincular esta PC: %s (vence en %d min) · %s",
            codigo.user_code,
            codigo.expires_in // 60,
            codigo.verification_uri_complete,
        )

    def _sondear(self, ahora: float) -> None:
        codigo = self._codigo
        assert codigo is not None
        try:
            tokens = self._oauth.canjear(codigo.device_code)
        except RechazoOAuthError as error:
            self._error_oauth(error.codigo or "", ahora)
            return
        except ErrorBackendError as error:
            self._sin_conexion(error, ahora)
            return
        self._fase = Fase.VINCULADA
        self._codigo = None
        logger.info("Esta PC quedó vinculada (pc %s)", tokens.pc_id)
        self._al_vincular(tokens)

    def _error_oauth(self, codigo: str, ahora: float) -> None:
        if codigo == "authorization_pending":
            self._fase = Fase.CODIGO
            self._proximo = ahora + self._intervalo
        elif codigo == "slow_down":
            self._fase = Fase.CODIGO
            self._intervalo += AUMENTO_SLOW_DOWN_S
            self._proximo = ahora + self._intervalo
            logger.info("Vinculación: más despacio; sondeo cada %.0f s", self._intervalo)
        elif codigo == "access_denied":
            self._fase, self._codigo = Fase.RECHAZADA, None
            logger.info("La vinculación fue rechazada en la app («No reconozco esta PC»)")
        elif codigo in ("expired_token", "invalid_grant"):
            logger.info("El código de vinculación ya no sirve (%s); se pide otro", codigo)
            self._codigo, self._renovado = None, True
            self._pedir(ahora)
        else:
            self._sin_conexion(ErrorBackendError(codigo, 400, codigo), ahora)

    def _sin_conexion(self, error: ErrorBackendError, ahora: float) -> None:
        fase = Fase.SIN_INTERNET if isinstance(error, SinConexionError) else Fase.SIN_SERVIDOR
        if self._fase is not fase:
            logger.warning("Vinculación: %s (%s)", fase.value, error)
        self._fase = fase
        # A code still valid when the connection returns is polled again and shown (``paso``).
        self._proximo = ahora + REINTENTO_S


class HiloVinculacion:
    """Runs ``Vinculador.paso`` in a worker thread until it is linked or stopped."""

    def __init__(self, vinculador: Vinculador) -> None:
        self._vinculador = vinculador
        self._detenido = threading.Event()
        self._despertar = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="vinculacion", daemon=True)

    def iniciar(self) -> None:
        self._hilo.start()

    def despertar(self) -> None:
        self._despertar.set()

    def detener(self, espera_s: float = 5.0) -> None:
        self._detenido.set()
        self._despertar.set()
        if self._hilo.is_alive() and self._hilo is not threading.current_thread():
            self._hilo.join(espera_s)

    def _correr(self) -> None:
        while not self._detenido.is_set():
            try:
                espera = self._vinculador.paso()
            except Exception:
                logger.exception("Error inesperado al vincular la PC")
                espera = ESPERA_MAXIMA_S
            if self._vinculador.fase is Fase.VINCULADA:
                return
            self._despertar.wait(espera)
            self._despertar.clear()


def _sin_esquema(url: str) -> str:
    """``https://app.tetengo.reqsai.tech/vincular`` → ``app.tetengo.reqsai.tech/vincular``."""
    return url.split("://", 1)[-1].rstrip("/")
