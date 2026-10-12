"""Runs the verified Windows installer silently and lets it open the new version (CA-43.2).

The agent starts the Inno Setup installer (``packaging/te-tengo-captura.iss``) as a detached
process and then exits:

    <installer> /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /RELANZAR
                /LOG=<data>\\actualizaciones\\instalacion.log

* ``/VERYSILENT /SUPPRESSMSGBOXES /NORESTART``: no wizard, no message box, never a reboot.
* ``/RELANZAR`` (this project's parameter): the installer first waits until this agent has
  exited (it holds the named mutex ``MUTEX`` while it runs, ``instancia.py``), then replaces the
  program in ``%LOCALAPPDATA%\\Programs\\TeTengoCaptura`` and opens it again. Without it the
  installer behaves as before (interactive installs are unchanged).
* ``/LOG``: Inno Setup's log, for the diagnostic.

The installer only replaces the program folder: ``config.toml`` (``%APPDATA%\\TeTengoCaptura``),
the data folder (``%LOCALAPPDATA%\\TeTengoCaptura``: outbox, cameras, movements, activity) and
the PC's tokens (Windows Credential Manager) are never touched, so the link, the cameras and the
data stay.

Before starting it, ``ARCHIVO_MARCA`` records the versions; the next start finds it, says
«Terminando la actualización…» on the splash, and deletes the installer.
"""

import json
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from te_tengo_captura.instancia import MUTEX

__all__ = ["MUTEX", "comando", "guardar_marca", "lanzar", "leer_marca"]

logger = logging.getLogger(__name__)

PARAMETROS = ("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/RELANZAR")
ARCHIVO_MARCA = "actualizacion.json"
ARCHIVO_LOG = "instalacion.log"
# Windows process creation flags (``subprocess`` only defines them on Windows).
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
BANDERAS = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def comando(instalador: Path) -> list[str]:
    return [str(instalador), *PARAMETROS, f"/LOG={instalador.parent / ARCHIVO_LOG}"]


def lanzar(instalador: Path, popen: Callable[..., Any] = subprocess.Popen) -> None:
    """Starts the installer detached from this process, which exits right after."""
    popen(
        comando(instalador),
        creationflags=BANDERAS,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(instalador.parent),
    )
    logger.info("Instalador iniciado en silencio: %s", instalador.name)


def guardar_marca(directorio: Path, desde: str, hacia: str, instalador: Path) -> None:
    datos = {"desde": desde, "hacia": hacia, "instalador": str(instalador)}
    (directorio / ARCHIVO_MARCA).write_text(json.dumps(datos), encoding="utf-8")


def leer_marca(directorio: Path) -> dict[str, str] | None:
    try:
        datos = json.loads((directorio / ARCHIVO_MARCA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {str(k): str(v) for k, v in datos.items()} if isinstance(datos, dict) else None
