"""A bounded exit: once the person confirmed «Salir» (or the system shuts down), the process ends
within a few seconds, whatever is still running.

Python waits for every non-daemon thread before it exits. Our worker threads are daemons, but
pywebview runs each JS bridge call in a non-daemon thread that hands the result back to the page
with ``evaluate_js``; once the window is gone that call never returns (on macOS it waits for the
Cocoa main loop, which has already stopped), so the interpreter hung in ``threading._shutdown``
and macOS marked the app «not responding». Two guards:

- ``terminar``: at the end of ``main``, after the agent stopped and the single-instance lock was
  released, wait up to ``GRACIA_S`` for the remaining non-daemon threads, then log which ones are
  still alive and end the process with ``os._exit``.
- ``vigilar``: from the moment the exit starts, a daemon watchdog ends the process with
  ``os._exit`` if it is still alive after ``LIMITE_S`` (stopping the agent got stuck), after
  logging every thread's stack.

Both flush the logs first. ``os._exit`` releases the instance lock and the Windows named mutex with
the process, so the installer waiting for it (``/RELANZAR``) goes on.
"""

import contextlib
import logging
import sys
import threading
import time
import traceback
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

LIMITE_S = 8.0  # the whole exit, from «Salir» to the end of the process
GRACIA_S = 2.0  # waiting for stray non-daemon threads once everything was stopped


def hilos_pendientes() -> list[threading.Thread]:
    """The alive non-daemon threads Python would wait for, except this one and the main one."""
    actual, principal = threading.current_thread(), threading.main_thread()
    return [
        h
        for h in threading.enumerate()
        if h.is_alive() and not h.daemon and h is not actual and h is not principal
    ]


def describir_hilos(hilos: list[threading.Thread] | None = None) -> str:
    """Each thread's name and where it is, for the log (no secrets: only file names and lines)."""
    marcos = sys._current_frames()
    partes = []
    for hilo in threading.enumerate() if hilos is None else hilos:
        marco = marcos.get(hilo.ident or -1)
        pila = "".join(traceback.format_stack(marco, limit=6)) if marco is not None else ""
        partes.append(f"- {hilo.name}{' (daemon)' if hilo.daemon else ''}\n{pila}")
    return "\n".join(partes)


def vaciar_registros() -> None:
    for manejador in logging.getLogger().handlers:
        with contextlib.suppress(Exception):  # a broken handler never blocks the exit
            manejador.flush()


def _forzar(codigo: int) -> None:
    import os

    os._exit(codigo)


class Salida:
    def __init__(
        self,
        limite_s: float = LIMITE_S,
        gracia_s: float = GRACIA_S,
        forzar: Callable[[int], Any] = _forzar,
        reloj: Callable[[], float] = time.monotonic,
        pendientes: Callable[[], list[threading.Thread]] = hilos_pendientes,
    ) -> None:
        self._limite_s, self._gracia_s = limite_s, gracia_s
        self._pendientes = pendientes
        self._forzar, self._reloj = forzar, reloj
        self._inicio: float | None = None
        self._vigia: threading.Thread | None = None
        self._candado = threading.Lock()
        self._fin = threading.Event()  # tests: stops the watchdog without ending the process

    @property
    def iniciada(self) -> bool:
        return self._inicio is not None

    def vigilar(self) -> None:
        """The exit started: from now on the process ends within ``limite_s`` (idempotent)."""
        with self._candado:
            if self._vigia is not None:
                return
            self._inicio = self._reloj()
            self._vigia = threading.Thread(target=self._vigilar, name="salida", daemon=True)
            self._vigia.start()

    def terminar(self, codigo: int = 0) -> None:
        """The end of ``main``: returns if nothing would keep the process alive, otherwise waits
        up to ``gracia_s`` for those threads and ends the process."""
        limite = self._reloj() + self._gracia_s
        for hilo in self._pendientes():
            hilo.join(max(0.0, limite - self._reloj()))
        pendientes = self._pendientes()
        if self._inicio is not None:
            logger.info("Salida completa en %.1f s", self._reloj() - self._inicio)
        if not pendientes:
            return
        logger.warning(
            "Se cierra sin esperar a %d hilo(s) que no terminaron: %s",
            len(pendientes),
            ", ".join(h.name for h in pendientes),
        )
        logger.debug("Hilos al salir:\n%s", describir_hilos(pendientes))
        vaciar_registros()
        self._forzar(codigo)

    def detener_vigilancia(self) -> None:
        self._fin.set()

    def _vigilar(self) -> None:
        if self._fin.wait(self._limite_s):
            return
        logger.error(
            "La salida tardó más de %.0f s; se cierra el programa. Hilos:\n%s",
            self._limite_s,
            describir_hilos(),
        )
        vaciar_registros()
        self._forzar(1)
