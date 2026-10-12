"""The pystray tray icon: status dot, tooltip and menu.

The menu follows the prototype's tray menu (screen 68, US-43): «Abrir Te Tengo Captura», with a
new version «Descargar la versión X» (Mac: «Ir a la descarga de la versión X») and «Buscar
actualizaciones»; «Salir» opens the window and asks to confirm it, because it stops fall detection
(draft copy, ``docs/BLOCKERS.md``).
«Abrir…» is the default item, so a click on the icon opens the window. A new version adds a
coral dot to the icon and «· versión nueva X» to the tooltip.
"""

import logging
import sys
from collections.abc import Callable
from typing import Any

from te_tengo_captura.bandeja.iconos import icono
from te_tengo_captura.estado import Mostrable, Notificacion

logger = logging.getLogger(__name__)

TEXTO_ABRIR = "Abrir Te Tengo Captura"
TEXTO_SALIR = "Salir"
TEXTO_BUSCAR = "Buscar actualizaciones"


def texto_descarga(version: str, mac: bool) -> str:
    return f"{'Ir a la descarga de la' if mac else 'Descargar la'} versión {version}"


# macOS: AppKit status items may only be touched from the main thread, which pywebview owns.
EN_MACOS = sys.platform == "darwin"


def _en_hilo_principal(accion: Callable[[], None]) -> None:
    if EN_MACOS:
        from PyObjCTools import AppHelper

        AppHelper.callAfter(accion)
    else:
        accion()


def descripcion(estado: Mostrable) -> str:
    """Tooltip, as the ``title`` of the tray button in the prototype."""
    return f"Te Tengo Captura · {estado.bandeja.etiqueta}"


class IconoBandeja:
    def __init__(
        self,
        abrir: Callable[[], None],
        salir: Callable[[], None],
        descargar: Callable[[], None] = lambda: None,
        buscar: Callable[[], None] = lambda: None,
    ) -> None:
        import pystray

        self._punto: str | None = None
        self._version: str | None = None  # a new version of the program (US-43)
        self._mac = False
        self._icono: Any = pystray.Icon(
            "te-tengo-captura",
            icon=icono("ok"),
            title="Te Tengo Captura",
            menu=pystray.Menu(
                pystray.MenuItem(TEXTO_ABRIR, lambda: abrir(), default=True),
                pystray.MenuItem(
                    lambda _item: texto_descarga(self._version or "", self._mac),
                    lambda: descargar(),
                    visible=lambda _item: self._version is not None,
                ),
                pystray.MenuItem(TEXTO_BUSCAR, lambda: buscar()),
                pystray.MenuItem(TEXTO_SALIR, lambda: salir()),
            ),
        )

    def iniciar(self) -> None:
        # Detached: pywebview owns the main thread and runs its event loop. On macOS this must be
        # called from the main thread, before ``webview.start``.
        self._icono.run_detached()

    def version_nueva(self, version: str | None, mac: bool = False) -> None:
        """A new version to download (the coral dot and the menu item), or ``None``."""
        if (version, mac) == (self._version, self._mac):
            return
        self._version, self._mac = version, mac

        def aplicar() -> None:
            if self._punto is not None:
                self._icono.icon = icono(self._punto, version_nueva=version is not None)
            self._icono.update_menu()

        _en_hilo_principal(aplicar)

    def actualizar(self, estado: Mostrable) -> None:
        punto, titulo = estado.bandeja.k, descripcion(estado)
        if self._version is not None:
            titulo += f" · versión nueva {self._version}"

        def aplicar() -> None:
            if punto != self._punto:
                self._punto = punto
                self._icono.icon = icono(punto, version_nueva=self._version is not None)
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
