"""Start with the system (the window footer says «Se inicia con Windows»).

On Windows the packaged agent writes a per-user ``Run`` registry entry on startup, so it starts
when the user signs in; the entry is updated if the program moved. Nothing is written when
running from source (``uv run``) or on macOS and Linux, where the project team installs a
LaunchAgent or an autostart ``.desktop`` file instead (``docs/INSTALLATION.md``).
"""

import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

CLAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOMBRE = "TeTengoCaptura"


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
