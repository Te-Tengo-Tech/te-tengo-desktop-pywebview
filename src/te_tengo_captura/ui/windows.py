"""Windows: signing out, restarting or shutting down (and «Finalizar tarea») close the app at once.

Windows sends ``WM_QUERYENDSESSION`` to every window; WinForms answers it by closing the forms
with ``CloseReason.WindowsShutDown``. pywebview turns that ``FormClosing`` into the window's
``closing`` event, which hides the window to the tray and cancels the close (``ventana.py``), so
the app would block the shutdown («Esta aplicación impide apagar»). ``permitir_apagado`` adds a
second ``FormClosing`` handler, which runs after pywebview's: for those reasons it lets the form
close and calls ``apagar`` (the exit without the question). The last form closing ends
pywebview's main loop and ``Aplicacion.ejecutar`` stops the agent.

pythonnet and pywebview are imported inside the function, so this module loads anywhere.
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# System.Windows.Forms.CloseReason
RAZONES_DEL_SISTEMA = frozenset({"WindowsShutDown", "TaskManagerClosing"})


def es_cierre_del_sistema(razon: object) -> bool:
    return str(razon) in RAZONES_DEL_SISTEMA


def permitir_apagado(ventana: Any, apagar: Callable[[], None]) -> bool:
    """Hooks the shutdown on the form of ``ventana`` (a shown pywebview window); ``False`` if the
    backend is not WinForms."""
    try:
        from webview.platforms.winforms import BrowserView
    except Exception:
        return False
    formulario = BrowserView.instances.get(ventana.uid)
    if formulario is None:
        return False

    def al_cerrar(_emisor: object, argumentos: Any) -> None:
        if es_cierre_del_sistema(argumentos.CloseReason):
            logger.info("Windows cierra la sesión o se apaga: se detiene la detección")
            apagar()
            argumentos.Cancel = False

    formulario.FormClosing += al_cerrar
    return True
