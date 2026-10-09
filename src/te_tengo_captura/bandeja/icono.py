"""The pystray tray icon: status dot, tooltip and menu.

The menu texts «Abrir Te Tengo Captura» and «Salir» are placeholders until the team confirms
them (``docs/BLOCKERS.md``): the prototype shows the icon but not its menu. «Abrir…» is the
default item, so a click on the icon opens the window.
"""

import logging
import sys
from collections.abc import Callable
from typing import Any

from te_tengo_captura.bandeja.iconos import icono
from te_tengo_captura.estado import EstadoAgente, Notificacion

logger = logging.getLogger(__name__)

TEXTO_ABRIR = "Abrir Te Tengo Captura"
TEXTO_SALIR = "Salir"


# macOS: AppKit status items may only be touched from the main thread, which pywebview owns.
EN_MACOS = sys.platform == "darwin"


def _en_hilo_principal(accion: Callable[[], None]) -> None:
    if EN_MACOS:
        from PyObjCTools import AppHelper

        AppHelper.callAfter(accion)
    else:
        accion()


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
        # Detached: pywebview owns the main thread and runs its event loop. On macOS this must be
        # called from the main thread, before ``webview.start``.
        self._icono.run_detached()

    def actualizar(self, estado: EstadoAgente) -> None:
        punto, titulo = estado.bandeja.k, descripcion(estado)

        def aplicar() -> None:
            if punto != self._punto:
                self._punto = punto
                self._icono.icon = icono(punto)
            if self._icono.title != titulo:
                self._icono.title = titulo

        _en_hilo_principal(aplicar)

    def notificar(self, aviso: Notificacion) -> None:
        def mostrar() -> None:
            try:
                self._icono.notify(aviso.texto, aviso.titulo)
            except Exception:  # notifications are best effort (not every desktop supports them)
                logger.warning("No se pudo mostrar la notificación del sistema", exc_info=True)

        _en_hilo_principal(mostrar)

    def detener(self) -> None:
        self._icono.stop()
