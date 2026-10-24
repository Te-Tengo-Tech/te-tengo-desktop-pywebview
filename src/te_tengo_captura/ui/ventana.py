"""The window (tabs Estado · Cámaras): 960 × 640, not resizable, frameless with the prototype's
36 px title bar. Closing or minimizing hides it to the tray; it never stops the agent.

pywebview is imported inside the methods, so this module loads without a display.
"""

import json
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from te_tengo_captura.estado import Mostrable
from te_tengo_captura.ui.puente import Puente

logger = logging.getLogger(__name__)

WEB = Path(__file__).resolve().parent / "web"
ANCHO, ALTO = 960, 640
FONDO = "#FFF7F1"  # --ground (cream), so no white flash before the page paints
FONDO_ARRANQUE = FONDO  # the splash is on cream too (brand kit)


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

    def actualizar(self, estado: Mostrable) -> None:
        if self._cargada.is_set() and not self._saliendo:
            self._ventana.evaluate_js(script_actualizar(estado.a_json()))

    def accion(self, nombre: str) -> None:
        """Runs one of the page's actions (``ttg.accion``), e.g. from the tray menu."""
        if self._cargada.is_set() and not self._saliendo:
            self._ventana.evaluate_js(f"window.ttg && window.ttg.accion({json.dumps(nombre)})")

    def confirmar_salida(self) -> None:
        """Presses the dialog's «Salir» (``--salir-tras``), as the person would."""
        if self._cargada.is_set() and not self._saliendo:
            self._ventana.evaluate_js(
                "(function(b){ b && b.click(); })(document.querySelector('[data-act=\"quitDo\"]'))"
            )

    def elegir_destino(self, nombre: str) -> Path | None:
        """The system's «Guardar como» with ``nombre`` proposed; ``None`` if cancelled."""
        import webview

        elegido = self._ventana.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=nombre, file_types=("Zip (*.zip)",)
        )
        if not elegido:
            return None
        ruta = elegido if isinstance(elegido, str) else elegido[0]
        return Path(ruta)

    def elegir_carpeta(self) -> Path | None:
        """The system's folder dialog; ``None`` if cancelled."""
        import webview

        elegido = self._ventana.create_file_dialog(webview.FOLDER_DIALOG)
        if not elegido:
            return None
        return Path(elegido if isinstance(elegido, str) else elegido[0])

    @property
    def nativa(self) -> Any:
        """The pywebview window (the platform hooks of ``macos.py`` and ``windows.py``)."""
        return self._ventana

    @property
    def saliendo(self) -> bool:
        return self._saliendo

    def preparar_salida(self) -> None:
        """No more scripts for the page: one in flight when the window closes never returns."""
        self._saliendo = True

    def destruir(self) -> None:
        self._saliendo = True
        try:
            self._ventana.destroy()
        except Exception:  # already closed (e.g. by the system's shutdown)
            logger.debug("La ventana ya estaba cerrada", exc_info=True)

    def _al_cerrar(self) -> bool:
        # Alt+F4 or the OS close: hide instead of closing (returning False cancels it).
        if self._saliendo:
            return True
        self.ocultar()
        return False
