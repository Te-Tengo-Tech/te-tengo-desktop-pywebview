"""The pystray tray icon: status dot, tooltip and menu.

The menu texts «Abrir Te Tengo Captura» and «Salir» are placeholders until the team confirms
them (``docs/BLOCKERS.md``): the prototype shows the icon but not its menu. «Abrir…» is the
default item, so a click on the icon opens the window.
"""

import logging
from collections.abc import Callable
from typing import Any

from te_tengo_captura.bandeja.iconos import icono
from te_tengo_captura.estado import EstadoAgente, Notificacion

logger = logging.getLogger(__name__)

TEXTO_ABRIR = "Abrir Te Tengo Captura"
TEXTO_SALIR = "Salir"


def descripcion(estado: EstadoAgente) -> str:
    """Tooltip, as the ``title`` of the tray button in the prototype."""
    return f"Te Tengo Captura · {estado.bandeja.etiqueta}"


class IconoBandeja:
    def __init__(self, abrir: Callable[[], None], salir: Callable[[], None]) -> None:
        import pystray

        self._punto: str | None = None
        self._icono: Any = pystray.Icon(
            "te-tengo-captura",
            icon=icono("ok"),
            title="Te Tengo Captura",
            menu=pystray.Menu(
                pystray.MenuItem(TEXTO_ABRIR, lambda: abrir(), default=True),
                pystray.MenuItem(TEXTO_SALIR, lambda: salir()),
            ),
        )

    def iniciar(self) -> None:
        # Detached: pywebview owns the main thread.
        self._icono.run_detached()

    def actualizar(self, estado: EstadoAgente) -> None:
        if estado.bandeja.k != self._punto:
            self._punto = estado.bandeja.k
            self._icono.icon = icono(self._punto)
        titulo = descripcion(estado)
        if self._icono.title != titulo:
            self._icono.title = titulo

    def notificar(self, aviso: Notificacion) -> None:
        try:
            self._icono.notify(aviso.texto, aviso.titulo)
        except Exception:  # notifications are best effort (not every desktop supports them)
            logger.warning("No se pudo mostrar la notificación del sistema", exc_info=True)

    def detener(self) -> None:
        self._icono.stop()
