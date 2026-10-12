"""A stand-in for the ``pystray`` module: records the icon, its menu and notifications."""

from collections.abc import Callable
from types import ModuleType
from typing import Any


class MenuItem:
    def __init__(
        self,
        texto: str | Callable[[Any], str],
        accion: Callable[[], Any],
        default: bool = False,
        visible: bool | Callable[[Any], bool] = True,
    ) -> None:
        self._texto, self.accion, self.default, self._visible = texto, accion, default, visible

    @property
    def text(self) -> str:
        return self._texto(self) if callable(self._texto) else self._texto

    @property
    def visible(self) -> bool:
        return self._visible(self) if callable(self._visible) else self._visible


class Menu:
    def __init__(self, *items: MenuItem) -> None:
        self.items = items


class Icon:
    def __init__(
        self, nombre: str, icon: Any = None, title: str = "", menu: Menu | None = None
    ) -> None:
        self.name, self.icon, self.title, self.menu = nombre, icon, title, menu
        self.notificaciones: list[tuple[str, str]] = []
        self.corriendo = False
        self.menus_actualizados = 0

    def update_menu(self) -> None:
        self.menus_actualizados += 1

    def run_detached(self) -> None:
        self.corriendo = True

    def notify(self, mensaje: str, titulo: str | None = None) -> None:
        self.notificaciones.append((titulo or "", mensaje))

    def stop(self) -> None:
        self.corriendo = False


class PystrayFalso(ModuleType):
    def __init__(self) -> None:
        super().__init__("pystray")
        self.iconos: list[Icon] = []
        self.Menu = Menu
        self.MenuItem = MenuItem

    def Icon(self, *args: Any, **kwargs: Any) -> Icon:  # noqa: N802 (pystray's name)
        icono = Icon(*args, **kwargs)
        self.iconos.append(icono)
        return icono
