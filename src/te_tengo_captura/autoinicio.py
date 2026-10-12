"""Start with the system (the PC must stay on with Te Tengo running).

On Windows the packaged agent writes a per-user ``Run`` registry entry on startup, so it starts
when the user signs in; the entry is updated if the program moved. Nothing is written when
running from source (``uv run``) or on macOS and Linux, where the project team installs a
LaunchAgent or an autostart ``.desktop`` file instead (``docs/INSTALLATION.md``).
"""

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CLAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOMBRE = "TeTengoCaptura"
# The files the project team installs on macOS and Linux (docs/INSTALLATION.md, section 10).
LAUNCH_AGENT = Path("Library/LaunchAgents/pe.tetengo.captura.plist")
AUTOSTART_LINUX = Path(".config/autostart/te-tengo-captura.desktop")


def comando() -> str | None:
    """The command to register: the packaged executable, or ``None`` when run from source."""
    if not getattr(sys, "frozen", False):
        return None
    return f'"{sys.executable}"'


def registrar(winreg: Any = None, plataforma: str = sys.platform) -> bool:
    """Creates or updates the ``Run`` entry; ``True`` if it is in place."""
    valor = comando()
    if plataforma != "win32" or valor is None:
        return False
    if winreg is None:
        import winreg as winreg_  # type: ignore[import-not-found,unused-ignore]

        winreg = winreg_
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_RUN, 0, winreg.KEY_ALL_ACCESS) as clave:
            try:
                actual, _ = winreg.QueryValueEx(clave, NOMBRE)
            except FileNotFoundError:
                actual = None
            if actual != valor:
                winreg.SetValueEx(clave, NOMBRE, 0, winreg.REG_SZ, valor)
                logger.info("Inicio con Windows registrado: %s", valor)
    except OSError as error:
        logger.warning("No se pudo registrar el inicio con Windows: %s", error)
        return False
    return True


def quitar(winreg: Any = None, plataforma: str = sys.platform, inicio: Path | None = None) -> bool:
    """«Restablecer esta PC» and uninstall: the agent no longer starts with the system.

    Windows: deletes the ``Run`` entry; macOS: the LaunchAgent; Linux: the autostart file.
    ``True`` if something was removed. ``inicio`` is the home folder (tests)."""
    if plataforma == "win32":
        if winreg is None:
            import winreg as winreg_  # type: ignore[import-not-found,unused-ignore]

            winreg = winreg_
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, CLAVE_RUN, 0, winreg.KEY_ALL_ACCESS
            ) as clave:
                winreg.DeleteValue(clave, NOMBRE)
        except FileNotFoundError:
            return False
        except OSError as error:
            logger.warning("No se pudo quitar el inicio con Windows: %s", error)
            return False
        logger.info("Inicio con Windows quitado")
        return True
    carpeta = inicio or Path.home()
    archivo = carpeta / (LAUNCH_AGENT if plataforma == "darwin" else AUTOSTART_LINUX)
    try:
        archivo.unlink()
    except FileNotFoundError:
        return False
    except OSError as error:
        logger.warning("No se pudo quitar el inicio con el sistema: %s", error)
        return False
    logger.info("Inicio con el sistema quitado (%s)", archivo)
    return True
