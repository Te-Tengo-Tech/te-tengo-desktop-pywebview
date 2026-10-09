"""Runs the agent without its window and tray icon (``--sin-interfaz``).

For machines without a display, such as the API's end-to-end test in CI: the capture loop, the
heartbeat, the outbox sender and the threshold updater run as usual, but pywebview and pystray
are never imported. The agent stops on Ctrl+C or SIGTERM. With no window, every change of the
derived state is logged instead.
"""

import logging
import signal
import threading
from collections.abc import Callable
from types import FrameType

from te_tengo_captura.agente import Agente
from te_tengo_captura.estado import EstadoAgente

logger = logging.getLogger(__name__)

ESPERA_S = 0.5  # how often the main thread checks the stop flag (signals interrupt it on POSIX)


class RegistroDeEstado:
    """Logs the window's situation each time it changes."""

    def __init__(self) -> None:
        self._anterior: str | None = None

    def __call__(self, estado: EstadoAgente) -> None:
        situacion = estado.situacion.value
        if situacion != self._anterior:
            self._anterior = situacion
            logger.info("Estado del agente: %s", situacion)


def ejecutar(agente: Agente, detener: threading.Event | None = None) -> None:
    """Starts the agent and blocks until ``detener`` is set, Ctrl+C or SIGTERM."""
    parar = detener or threading.Event()
    anteriores = _atender_senales(parar)
    agente.suscribir(RegistroDeEstado())
    try:
        agente.iniciar()
        logger.info("Sin interfaz: el agente corre hasta Ctrl+C o SIGTERM")
        while not parar.wait(ESPERA_S):
            pass
    finally:
        agente.detener()
        for senal, manejador in anteriores.items():
            signal.signal(senal, manejador)


ManejadorSenal = Callable[[int, FrameType | None], object] | int | signal.Handlers | None


def _atender_senales(parar: threading.Event) -> dict[signal.Signals, ManejadorSenal]:
    """Ctrl+C and SIGTERM set ``parar``; only possible from the main thread."""
    if threading.current_thread() is not threading.main_thread():
        return {}

    def al_recibir(numero: int, _marco: FrameType | None) -> None:
        logger.info("Señal %s recibida: se detiene el agente", signal.Signals(numero).name)
        parar.set()

    anteriores: dict[signal.Signals, ManejadorSenal] = {}
    for senal in (signal.SIGINT, signal.SIGTERM):
        anteriores[senal] = signal.signal(senal, al_recibir)
    return anteriores
