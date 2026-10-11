"""Typed errors of the backend: one exception per ``ProblemDetail.codigo`` the agent handles."""

from typing import Any


class ErrorBackendError(RuntimeError):
    """The backend answered with an error, or could not be reached."""

    def __init__(
        self,
        mensaje: str,
        estado: int | None = None,
        codigo: str | None = None,
        cuerpo: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo
        self.cuerpo = cuerpo or {}  # the ProblemDetail, e.g. 409 AMBIENTE_OCUPADO's camera

    @property
    def reintentable(self) -> bool:
        """Network failures, ``429`` and ``5xx`` may succeed later; other errors will not."""
        return self.estado is None or self.estado == 429 or self.estado >= 500


class SinConexionError(ErrorBackendError):
    """No response: no internet, DNS failure, timeout or connection refused."""


class CredencialInvalidaError(ErrorBackendError):
    """``401 CREDENCIAL_INVALIDA``: the installation credential was rejected."""


class NoAutorizadoError(ErrorBackendError):
    """``401`` even after registering again."""


class PcDesvinculadaError(ErrorBackendError):
    """``401 PC_DESVINCULADA``: the PC (or the installation's PC) left the household (US-31).

    The agent stops capturing, deletes its credentials and shows the link code (CA-31.1)."""


class SesionExpiradaError(ErrorBackendError):
    """``401 SESION_EXPIRADA``: the token expired; a linked PC renews it once."""


class CapturaNoPermitidaError(ErrorBackendError):
    """``409 CAPTURA_NO_PERMITIDA``: consent is missing or the camera is paused."""


class EventoNoEncontradoError(ErrorBackendError):
    """``404 EVENTO_NO_ENCONTRADO``: the clip refers to an event the backend does not have."""


POR_CODIGO: dict[str, type[ErrorBackendError]] = {
    "CREDENCIAL_INVALIDA": CredencialInvalidaError,
    "PC_DESVINCULADA": PcDesvinculadaError,
    "CAPTURA_NO_PERMITIDA": CapturaNoPermitidaError,
    "EVENTO_NO_ENCONTRADO": EventoNoEncontradoError,
}
