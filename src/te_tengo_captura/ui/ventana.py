"""The status window (screens 01–05): 960 × 640, not resizable, frameless with the prototype's
36 px title bar. Closing or minimizing hides it to the tray; it never stops the agent.

pywebview is imported inside the methods, so this module loads without a display.
"""

import json
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from te_tengo_captura.estado import EstadoAgente
from te_tengo_captura.ui.puente import Puente

logger = logging.getLogger(__name__)

WEB = Path(__file__).resolve().parent / "web"
ANCHO, ALTO = 960, 640
FONDO = "#EEF0F4"  # --ground, so no white flash before the page paints
FONDO_ARRANQUE = "#4A2A85"  # --morado


def script_actualizar(datos: dict[str, Any]) -> str:
    """JavaScript that pushes the state to the page (ASCII-only JSON, safe inside a script)."""
    return f"window.ttg && window.ttg.actualizar({json.dumps(datos)})"


class VentanaEstado:
    def __init__(
        self,
        puente: Puente,
        al_ocultar: Callable[[], None] = lambda: None,
        oculta: bool = True,
    ) -> None:
        import webview

        self._al_ocultar = al_ocultar
        self._saliendo = False
        self._cargada = threading.Event()
        ventana = webview.create_window(
            "Te Tengo Captura",
            str(WEB / "index.html"),
            js_api=puente,
            width=ANCHO,
            height=ALTO,
            resizable=False,
            frameless=True,
            easy_drag=False,  # only the title bar drags (.pywebview-drag-region)
            hidden=oculta,
            background_color=FONDO,
        )
        if ventana is None:
            raise RuntimeError("pywebview no pudo crear la ventana")
        self._ventana: Any = ventana
        self._ventana.events.loaded += self._cargada.set
        self._ventana.events.closing += self._al_cerrar

    def mostrar(self) -> None:
        self._ventana.show()
        self._ventana.restore()

    def ocultar(self) -> None:
        self._ventana.hide()
        self._al_ocultar()

    def actualizar(self, estado: EstadoAgente) -> None:
        if self._cargada.is_set() and not self._saliendo:
            self._ventana.evaluate_js(script_actualizar(estado.a_json()))

    def destruir(self) -> None:
        self._saliendo = True
        self._ventana.destroy()

    def _al_cerrar(self) -> bool:
        # Alt+F4 or the OS close: hide instead of closing (returning False cancels it).
        if self._saliendo:
            return True
        self.ocultar()
        return False
