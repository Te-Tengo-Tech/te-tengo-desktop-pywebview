"""A stand-in for the ``webview`` module: records what the UI asks pywebview to do."""

from collections.abc import Callable
from types import ModuleType
from typing import Any


class Evento:
    def __init__(self) -> None:
        self.manejadores: list[Callable[[], Any]] = []

    def __iadd__(self, manejador: Callable[[], Any]) -> "Evento":
        self.manejadores.append(manejador)
        return self

    def disparar(self) -> list[Any]:
        return [m() for m in self.manejadores]


class Eventos:
    def __init__(self) -> None:
        self.loaded = Evento()
        self.closing = Evento()
        self.shown = Evento()


class VentanaFalsa:
    def __init__(self, titulo: str, url: str | None, **opciones: Any) -> None:
        self.titulo, self.url, self.opciones = titulo, url, opciones
        self.events = Eventos()
        self.visible = not opciones.get("hidden", False)
        self.scripts: list[str] = []
        self.destruida = False
        self.movida: tuple[int, int] | None = None

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def restore(self) -> None:
        pass

    def move(self, x: int, y: int) -> None:
        self.movida = (x, y)

    def evaluate_js(self, script: str) -> None:
        self.scripts.append(script)

    def destroy(self) -> None:
        self.destruida = True


class WebviewFalso(ModuleType):
    def __init__(self) -> None:
        super().__init__("webview")
        self.ventanas: list[VentanaFalsa] = []
        self.iniciado = False
        self.opciones: dict[str, Any] = {}
        self.screens: list[Any] = []

    def create_window(self, titulo: str, url: str | None = None, **opciones: Any) -> VentanaFalsa:
        ventana = VentanaFalsa(titulo, url, **opciones)
        self.ventanas.append(ventana)
        return ventana

    def start(
        self, func: Callable[..., Any] | None = None, args: Any = None, **opciones: Any
    ) -> None:
        self.iniciado = True
        self.opciones = opciones
        for ventana in self.ventanas:
            ventana.events.loaded.disparar()
        if func is not None:
            func(*(args or ()))
