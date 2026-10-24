"""macOS: every way to quit goes through «¿Salir de Te Tengo Captura?», and logging out or shutting
down quits at once.

pywebview's Cocoa backend has two quit paths of its own, neither of which asked first:
- the app menu's «Quit» (Cmd+Q) and the Dock's «Quit» send ``terminate:``; its app delegate then
  fires the window's ``closing`` event, which hides the window to the tray (``ventana.py``), so
  «Quit» only hid the window;
- Cmd+Q typed while the web view has the focus reaches ``WebKitHost.keyDown_``, which stops the
  Cocoa main loop directly, without the question.

``interceptar_salida`` replaces both methods (PyObjC ``classAddMethods``) once, before
``webview.start``. A quit the person asked for opens the window and asks (``pedir``, called off
the main thread, because it waits for the page). A quit the system asks for (log out, restart,
shut down: the Apple event's ``why?`` attribute) answers ``NSTerminateLater``, stops the agent
in a worker thread (``apagar``) and then lets the app terminate, so it never delays the log out.

PyObjC and pywebview are imported inside the functions, so this module loads anywhere.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

NS_TERMINATE_CANCEL, NS_TERMINATE_NOW, NS_TERMINATE_LATER = 0, 1, 2


def _codigo(texto: str) -> int:
    return int.from_bytes(texto.encode("ascii"), "big")


# kAEQuitReason values (AERegistry.h): log out, restart and shut down, with or without a dialog.
RAZON_DE_SALIDA = _codigo("why?")
RAZONES_DEL_SISTEMA = frozenset(
    _codigo(c) for c in ("logo", "rlgo", "rrst", "rsdn", "rest", "shut")
)
TECLA_Q = "q"


def decidir(razon: int | None) -> int:
    """The answer to ``applicationShouldTerminate:``.

    The system logging out or shutting down terminates later (once the agent stopped). A quit the
    person asked for is cancelled: the window asks first, and «Salir» there ends the app.
    """
    if razon in RAZONES_DEL_SISTEMA:
        return NS_TERMINATE_LATER
    return NS_TERMINATE_CANCEL


def razon_actual() -> int | None:
    """The ``why?`` of the Apple event being handled (``quit`` from loginwindow), if any."""
    try:
        from Foundation import NSAppleEventManager

        evento = NSAppleEventManager.sharedAppleEventManager().currentAppleEvent()
        if evento is None:
            return None
        razon = evento.attributeDescriptorForKeyword_(RAZON_DE_SALIDA)
        return int(razon.enumCodeValue()) if razon is not None else None
    except Exception:  # an unexpected event shape: treat it as a quit the person asked for
        logger.debug("No se pudo leer la razón de la salida", exc_info=True)
        return None


def es_cmd_q(modificadores: int, caracteres: str | None, mascara_cmd: int) -> bool:
    return bool(modificadores & mascara_cmd) and (caracteres or "").lower() == TECLA_Q


def _en_otro_hilo(accion: Callable[[], None], nombre: str) -> None:
    threading.Thread(target=accion, name=nombre, daemon=True).start()


def interceptar_salida(
    pedir: Callable[[], None],
    apagar: Callable[[], None],
    saliendo: Callable[[], bool],
) -> None:
    """Routes macOS's quit paths to ``pedir`` (the question) or, when the system logs out or
    shuts down, to ``apagar`` followed by the app's termination."""
    import AppKit
    from PyObjCTools import AppHelper
    from webview.platforms.cocoa import BrowserView

    def application_should_terminate(_delegado: object, app: object) -> int:
        respuesta = decidir(razon_actual())
        if respuesta == NS_TERMINATE_LATER:
            logger.info("El sistema cierra la sesión o se apaga: se detiene la detección")

            def apagar_y_responder() -> None:
                try:
                    apagar()
                finally:
                    AppHelper.callAfter(
                        AppKit.NSApplication.sharedApplication().replyToApplicationShouldTerminate_,
                        True,
                    )

            _en_otro_hilo(apagar_y_responder, "apagado")
        elif not saliendo():
            _en_otro_hilo(pedir, "pedir-salir")
        return respuesta

    original_tecla = BrowserView.WebKitHost.__dict__["keyDown_"].callable

    def key_down(vista: object, evento: object) -> None:
        if es_cmd_q(
            int(evento.modifierFlags()),  # type: ignore[attr-defined]
            evento.charactersIgnoringModifiers(),  # type: ignore[attr-defined]
            int(AppKit.NSCommandKeyMask),
        ):
            if not saliendo():
                _en_otro_hilo(pedir, "pedir-salir")
            return
        original_tecla(vista, evento)

    _reemplazar(
        BrowserView.AppDelegate, "applicationShouldTerminate_", application_should_terminate
    )
    _reemplazar(BrowserView.WebKitHost, "keyDown_", key_down)


def _reemplazar(clase: Any, nombre: str, funcion: Callable[..., Any]) -> None:
    """Replaces a method pywebview defined in Python, keeping its Objective-C signature."""
    import objc

    original = clase.__dict__[nombre]
    objc.classAddMethods(
        clase,
        [objc.selector(funcion, selector=original.selector, signature=original.signature)],
    )
