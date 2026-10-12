"""«Restablecer esta PC» and the uninstaller: leave the PC as if Te Tengo had never been installed.

* **The API** hears that the PC left the household, with the reason for the activity log
  (``motivo``: ``restablecida`` or ``desinstalada``, ``docs/AGENT_CONTRACT.md``, "PC link"): the
  family gets push ``PC_DESVINCULADA`` and the app removes the PC. Offline, the in-app reset keeps
  the revocation pending (it is sent when there is internet); the uninstaller cannot, so the app
  shows the PC «Sin conexión» until the owner removes it.
* **The OS credential store** loses the PC's tokens, its installation id (a new one is made on
  the next code: the app sees a new PC) and the key of the local data.
* **The disk** loses ``config.toml``, the data folder (outbox, clips, movements, video, local index,
  activity, updates) and, when uninstalling, the logs.
* **Start with the system** is removed (``autoinicio.quitar``).

``ejecutar`` is the command line (``te-tengo-captura --restablecer``) the Windows uninstaller runs
before it removes the program; the window uses ``Coordinador.restablecer``.
"""

import contextlib
import json
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

from te_tengo_captura import autoinicio
from te_tengo_captura.almacen.gestor import ARCHIVO_AJUSTES
from te_tengo_captura.backend.errores import ErrorBackendError
from te_tengo_captura.vinculacion.credenciales import AlmacenCredenciales, AlmacenNoDisponibleError
from te_tengo_captura.vinculacion.oauth import ClienteOAuth

logger = logging.getLogger(__name__)

Motivo = Literal["restablecida", "desinstalada"]
MOTIVOS: tuple[Motivo, ...] = ("restablecida", "desinstalada")
# Kept while the agent that resets runs: its single-instance lock.
CONSERVAR = frozenset({"instancia.lock", "instancia.json"})


@dataclass(frozen=True, slots=True)
class Resultado:
    vinculada: bool  # there was a linked PC to tell the API about
    avisada: bool  # the API heard it now


def vaciar_carpeta(carpeta: Path, conservar: frozenset[str] = CONSERVAR) -> None:
    """Deletes everything in ``carpeta`` but ``conservar`` (best effort: a file in use stays)."""
    if not carpeta.is_dir():
        return
    for ruta in carpeta.iterdir():
        if ruta.name in conservar:
            continue
        try:
            if ruta.is_dir() and not ruta.is_symlink():
                shutil.rmtree(ruta, ignore_errors=True)
            else:
                ruta.unlink(missing_ok=True)
        except OSError as error:
            logger.warning("No se pudo borrar %s: %s", ruta.name, error)


def carpeta_movida(datos: Path) -> Path | None:
    """The data folder «Cambiar carpeta» moved out of ``datos`` (``almacenamiento.json``)."""
    try:
        ajustes = json.loads((datos / ARCHIVO_AJUSTES).read_text(encoding="utf-8"))
        carpeta = ajustes.get("carpeta") if isinstance(ajustes, dict) else None
    except (OSError, ValueError):
        return None
    return Path(carpeta) if carpeta else None


def borrar_configuracion(ruta: Path) -> None:
    """``config.toml`` (with the installation credential, if any) and its folder if empty."""
    ruta.unlink(missing_ok=True)
    with contextlib.suppress(OSError):  # not empty, or already gone
        ruta.parent.rmdir()


def avisar_a_la_api(
    almacen: AlmacenCredenciales,
    oauth: ClienteOAuth,
    motivo: Motivo,
) -> Resultado:
    """Revokes the PC's refresh token (RFC 7009, no access token needed) with ``motivo``; a
    revocation left pending by an earlier offline unlink is sent too."""
    try:
        credenciales = almacen.leer()
        pendiente = almacen.leer_revocacion()
    except AlmacenNoDisponibleError as error:
        logger.error("El almacén de credenciales no está disponible (%s)", error)
        return Resultado(vinculada=False, avisada=False)
    avisada = True
    if pendiente is not None:
        try:
            oauth.revocar(pendiente.refresh_token, pendiente.datos_locales_borrados, motivo)
        except ErrorBackendError as error:
            logger.warning("No se pudo enviar la desvinculación pendiente (%s)", error)
            avisada = False
    if credenciales is None:
        return Resultado(vinculada=pendiente is not None, avisada=avisada and pendiente is not None)
    try:
        oauth.revocar(credenciales.refresh_token, True, motivo)
        logger.info("Esta PC se desvinculó (%s)", motivo)
    except ErrorBackendError as error:
        logger.warning("Sin conexión con Te Tengo: la PC no se pudo desvincular (%s)", error)
        avisada = False
    return Resultado(vinculada=True, avisada=avisada)


def ejecutar(
    api_url: str,
    almacen: AlmacenCredenciales,
    datos: Path,
    configuracion: Path | None,
    logs: Path | None,
    motivo: Motivo,
    transporte: httpx.BaseTransport | None = None,
    quitar_autoinicio: Callable[[], bool] = autoinicio.quitar,
) -> Resultado:
    """``te-tengo-captura --restablecer``: no window, the agent must not be running."""
    oauth = ClienteOAuth(api_url, transporte)
    try:
        resultado = avisar_a_la_api(almacen, oauth, motivo)
    finally:
        oauth.cerrar()
    try:
        almacen.borrar_todo()
    except AlmacenNoDisponibleError as error:
        logger.error("No se pudieron borrar las credenciales (%s)", error)
    movida = carpeta_movida(datos)
    if movida is not None:
        shutil.rmtree(movida, ignore_errors=True)
    vaciar_carpeta(datos)
    if configuracion is not None:
        borrar_configuracion(configuracion)
    if logs is not None:
        shutil.rmtree(logs, ignore_errors=True)
    quitar_autoinicio()
    return resultado
