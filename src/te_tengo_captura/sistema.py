"""What this PC is called and which system it runs, for the window and the PC link (US-28).

The PC link sends both to the API (``nombre_pc``: 1–60 characters, ``sistema_operativo``: up to
60), and the app shows them before «Aprobar» (CA-28.4); the window shows them in «Datos de la
instalación».
"""

import platform
import socket

MAXIMO_NOMBRE = 60
MAXIMO_SISTEMA = 60

# ``platform.win32_edition()`` → how Windows names the edition to people.
_EDICIONES = {
    "Core": "Home",
    "CoreSingleLanguage": "Home",
    "CoreCountrySpecific": "Home",
    "Professional": "Pro",
    "ProfessionalWorkstation": "Pro for Workstations",
    "Enterprise": "Enterprise",
    "Education": "Education",
}


def nombre_pc(nodo: str | None = None) -> str:
    """The computer's name (``Sala-Rosa``), or «PC» when the system does not say."""
    nombre = (nodo if nodo is not None else platform.node() or socket.gethostname()).strip()
    # macOS reports «Sala-Rosa.local»; the household knows it as «Sala-Rosa».
    nombre = nombre.removesuffix(".local").removesuffix(".lan")
    return (nombre or "PC")[:MAXIMO_NOMBRE]


def sistema_operativo() -> str:
    """«Windows 11 Home», «macOS 15.4» or the Linux distribution's name."""
    sistema = platform.system()
    if sistema == "Windows":
        texto = _windows(platform.win32_ver()[1], platform.win32_edition() or "")
    elif sistema == "Darwin":
        texto = f"macOS {platform.mac_ver()[0]}".strip()
    elif sistema == "Linux":
        try:
            texto = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux")
        except OSError:
            texto = "Linux"
    else:
        texto = sistema or "Desconocido"
    return texto[:MAXIMO_SISTEMA]


def _windows(version: str, edicion: str) -> str:
    """Windows 11 still reports version 10.0; its builds start at 22000."""
    try:
        compilacion = int(version.split(".")[2])
    except (IndexError, ValueError):
        compilacion = 0
    nombre = "Windows 11" if compilacion >= 22000 else "Windows 10"
    edicion = _EDICIONES.get(edicion, edicion)
    return f"{nombre} {edicion}".strip()
