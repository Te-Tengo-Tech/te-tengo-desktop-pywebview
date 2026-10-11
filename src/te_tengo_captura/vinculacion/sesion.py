"""The linked PC's session: its access token, renewed with the rotating refresh token.

* ``token_vigente`` renews the access token when less than ``MARGEN_S`` remains (1 h tokens
  [implementation choice of the API]); ``renovar_token`` renews after a ``401 SESION_EXPIRADA``
  unless another thread already did.
* Renewals are serialized: each refresh token is presented **once**; the new one replaces it in
  the OS credential store in the same step (RFC 9700 §4.14.2: presenting a used refresh token
  unlinks the PC). If no answer arrived (network failure) the same token is tried again later:
  the agent cannot know whether the server rotated it (``docs/BLOCKERS.md``).
* ``invalid_grant`` (unlinked, reused, or 90 days without renewing) and ``401 PC_DESVINCULADA``
  call ``al_desvincular`` once: the agent stops capturing, deletes the credentials and shows the
  link code (CA-31.1, CA-31.2, CA-28.7).
* ``al_renovar`` callbacks run after each renewal (the cameras' tokens are renewed right after
  the PC's, contract "Cameras of a linked PC").
"""

import logging
import threading
import time
from collections.abc import Callable

from te_tengo_captura.backend.errores import PcDesvinculadaError
from te_tengo_captura.vinculacion.credenciales import (
    AlmacenCredenciales,
    AlmacenNoDisponibleError,
    CredencialesPc,
)
from te_tengo_captura.vinculacion.oauth import ClienteOAuth, RechazoOAuthError, TokensPc

logger = logging.getLogger(__name__)

MARGEN_S = 300.0  # renew five minutes before the access token expires


def credenciales_de(tokens: TokensPc, ahora: float) -> CredencialesPc:
    return CredencialesPc(
        access_token=tokens.access_token,
        expira_en=ahora + tokens.expires_in,
        refresh_token=tokens.refresh_token,
        pc_id=tokens.pc_id,
        hogar_id=tokens.hogar_id,
    )


class SesionPc:
    def __init__(
        self,
        oauth: ClienteOAuth,
        almacen: AlmacenCredenciales,
        credenciales: CredencialesPc,
        al_desvincular: Callable[[str], None],
        reloj: Callable[[], float] = time.time,
    ) -> None:
        self._oauth = oauth
        self._almacen = almacen
        self._credenciales = credenciales
        self._al_desvincular = al_desvincular
        self._reloj = reloj
        self._candado = threading.Lock()
        self._desvinculada = False
        self._sin_guardar = False
        self.al_renovar: list[Callable[[], None]] = []
        self.ultima_renovacion: float | None = None

    @property
    def pc_id(self) -> str:
        return self._credenciales.pc_id

    @property
    def hogar_id(self) -> str:
        return self._credenciales.hogar_id

    @property
    def desvinculada(self) -> bool:
        return self._desvinculada

    def secretos(self) -> list[str]:
        c = self._credenciales
        return [s for s in (c.access_token, c.refresh_token) if s]

    def refresh_token(self) -> str:
        return self._credenciales.refresh_token

    # ------------------------------------------------------------------ tokens

    def token_vigente(self) -> str:
        with self._candado:
            self._comprobar()
            if not self._credenciales.access_token or (
                self._credenciales.expira_en - self._reloj() < MARGEN_S
            ):
                self._renovar()
            return self._credenciales.access_token

    def renovar_token(self, rechazado: str) -> str:
        """After a ``401``: renew unless another thread already got a new token."""
        with self._candado:
            self._comprobar()
            if self._credenciales.access_token != rechazado:
                return self._credenciales.access_token
            self._renovar()
            return self._credenciales.access_token

    def desvincular(self, motivo: str) -> None:
        """The PC left the household (``desvincular``, ``PC_DESVINCULADA``, ``invalid_grant``)."""
        if self._desvinculada:
            return
        self._desvinculada = True
        logger.warning("Esta PC se quitó de la vivienda (%s)", motivo)
        self._al_desvincular(motivo)

    # ------------------------------------------------------------------ internals

    def _comprobar(self) -> None:
        if self._desvinculada:
            raise PcDesvinculadaError("La PC ya no está vinculada", 401, "PC_DESVINCULADA")

    def _renovar(self) -> None:
        try:
            tokens = self._oauth.renovar(self._credenciales.refresh_token)
        except RechazoOAuthError as error:
            if error.codigo == "invalid_grant":
                self.desvincular("invalid_grant")
                raise PcDesvinculadaError(str(error), 401, "PC_DESVINCULADA") from None
            raise
        self._credenciales = credenciales_de(tokens, self._reloj())
        self.ultima_renovacion = self._reloj()
        try:
            self._almacen.guardar(self._credenciales)
            self._sin_guardar = False
        except AlmacenNoDisponibleError as error:
            # The new token lives in memory; a restart now would present the old one.
            self._sin_guardar = True
            logger.error("No se pudo guardar el token renovado (%s)", error)
        logger.info("Tokens de la PC renovados")
        for oyente in list(self.al_renovar):
            try:
                oyente()
            except Exception:
                logger.exception("Error tras renovar los tokens de la PC")
