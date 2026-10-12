"""The PC's tokens in the operating system's credential store (change request 2.1).

Windows Credential Manager, the macOS Keychain or the Linux Secret Service, through
``keyring``: never in files. Three entries under the service ``TeTengoCaptura``:

* ``pc-renovacion``: the refresh token with the PC's and household's ids;
* ``pc-acceso``: the access token and when it expires;
* ``pc-revocacion-pendiente``: a refresh token the PC must still revoke because it was unlinked
  from the PC while offline (US-31); it is sent as soon as there is internet;
* ``pc-instalacion``: the PC's installation id, a UUID generated once and sent with every link
  code request (``id_instalacion``), so the app can say «Esta PC ya está vinculada». It is not a
  credential and survives unlinking: ``borrar`` keeps it.

Each value is small JSON (Windows limits a credential to 2560 bytes). The refresh token is
written before the access token, so a crash between both leaves a renewable state. Nothing here
is ever logged.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)

SERVICIO = "TeTengoCaptura"
CUENTA_RENOVACION = "pc-renovacion"
CUENTA_ACCESO = "pc-acceso"
CUENTA_REVOCACION = "pc-revocacion-pendiente"
CUENTA_INSTALACION = "pc-instalacion"


class Llavero(Protocol):
    """The part of ``keyring`` the agent uses (a fake in the tests)."""

    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


class AlmacenNoDisponibleError(RuntimeError):
    """The OS credential store cannot be used (e.g. no Secret Service on a headless Linux)."""


@dataclass(frozen=True, slots=True)
class CredencialesPc:
    access_token: str = field(repr=False)
    expira_en: float  # Unix time
    refresh_token: str = field(repr=False)
    pc_id: str
    hogar_id: str


@dataclass(frozen=True, slots=True)
class RevocacionPendiente:
    refresh_token: str = field(repr=False)
    datos_locales_borrados: bool


def llavero_del_sistema() -> Llavero:
    import keyring

    return keyring.get_keyring()


class AlmacenCredenciales:
    def __init__(self, llavero: Llavero | None = None) -> None:
        self._llavero = llavero

    def _sistema(self) -> Llavero:
        if self._llavero is None:
            self._llavero = llavero_del_sistema()
        return self._llavero

    @property
    def llavero(self) -> Llavero:
        """The credential store itself: the local data key lives there too (US-38)."""
        return self._sistema()

    # ------------------------------------------------------------------ tokens

    def leer(self) -> CredencialesPc | None:
        renovacion = self._leer_json(CUENTA_RENOVACION)
        if renovacion is None:
            return None
        acceso = self._leer_json(CUENTA_ACCESO) or {}
        try:
            return CredencialesPc(
                access_token=str(acceso.get("access_token", "")),
                expira_en=float(acceso.get("expira_en", 0.0)),
                refresh_token=str(renovacion["refresh_token"]),
                pc_id=str(renovacion["pc_id"]),
                hogar_id=str(renovacion["hogar_id"]),
            )
        except (KeyError, TypeError, ValueError):
            logger.warning("Credenciales de la PC ilegibles en el almacén del sistema; se ignoran")
            return None

    def guardar(self, credenciales: CredencialesPc) -> None:
        self._escribir(
            CUENTA_RENOVACION,
            {
                "refresh_token": credenciales.refresh_token,
                "pc_id": credenciales.pc_id,
                "hogar_id": credenciales.hogar_id,
            },
        )
        self._escribir(
            CUENTA_ACCESO,
            {"access_token": credenciales.access_token, "expira_en": credenciales.expira_en},
        )

    def borrar(self) -> None:
        for cuenta in (CUENTA_ACCESO, CUENTA_RENOVACION):
            self._borrar(cuenta)

    # ------------------------------------------------------------------ installation id

    def id_instalacion(self) -> str:
        """The PC's installation id; generated and stored the first time."""
        datos = self._leer_json(CUENTA_INSTALACION)
        if datos is not None:
            try:
                return str(uuid.UUID(str(datos["id"])))
            except (KeyError, ValueError):
                logger.warning("Id de instalación ilegible; se genera otro")
        nuevo = str(uuid.uuid4())
        self._escribir(CUENTA_INSTALACION, {"id": nuevo})
        return nuevo

    # ------------------------------------------------------------------ pending revocation

    def leer_revocacion(self) -> RevocacionPendiente | None:
        datos = self._leer_json(CUENTA_REVOCACION)
        if datos is None or "refresh_token" not in datos:
            return None
        return RevocacionPendiente(
            str(datos["refresh_token"]), bool(datos.get("datos_locales_borrados", False))
        )

    def guardar_revocacion(self, pendiente: RevocacionPendiente) -> None:
        self._escribir(
            CUENTA_REVOCACION,
            {
                "refresh_token": pendiente.refresh_token,
                "datos_locales_borrados": pendiente.datos_locales_borrados,
            },
        )

    def borrar_revocacion(self) -> None:
        self._borrar(CUENTA_REVOCACION)

    # ------------------------------------------------------------------ internals

    def _leer_json(self, cuenta: str) -> dict[str, Any] | None:
        try:
            texto = self._sistema().get_password(SERVICIO, cuenta)
        except Exception as error:
            raise AlmacenNoDisponibleError(type(error).__name__) from None
        if not texto:
            return None
        try:
            datos = json.loads(texto)
        except ValueError:
            return None
        return datos if isinstance(datos, dict) else None

    def _escribir(self, cuenta: str, datos: dict[str, Any]) -> None:
        try:
            self._sistema().set_password(SERVICIO, cuenta, json.dumps(datos))
        except Exception as error:
            raise AlmacenNoDisponibleError(type(error).__name__) from None

    def _borrar(self, cuenta: str) -> None:
        try:
            self._sistema().delete_password(SERVICIO, cuenta)
        except Exception:
            # PasswordDeleteError when it did not exist; any other failure leaves nothing usable.
            logger.debug("Nada que borrar en %s/%s", SERVICIO, cuenta)


class LlaveroEnMemoria:
    """A credential store that forgets everything on exit (tests and ``--backend-falso``)."""

    def __init__(self) -> None:
        self._valores: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self._valores.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._valores[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        self._valores.pop((service_name, username), None)
