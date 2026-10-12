"""Version numbers compared numerically, MAJOR.MINOR.PATCH, ignoring any suffix (contract)."""

import re

_NUMEROS = re.compile(r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def numeros(version: str) -> tuple[int, int, int]:
    """``"0.5.0-rc.1"`` → ``(0, 5, 0)``; ``"1.2"`` → ``(1, 2, 0)``. ``ValueError`` if it has no
    leading number."""
    coincidencia = _NUMEROS.match(version)
    if coincidencia is None:
        raise ValueError(f"Versión no válida: {version!r}")
    mayor, menor, parche = coincidencia.groups()
    return int(mayor), int(menor or 0), int(parche or 0)


def es_mas_nueva(version: str, que: str) -> bool:
    """``version`` is newer than ``que``; an unreadable version is never newer."""
    try:
        return numeros(version) > numeros(que)
    except ValueError:
        return False
