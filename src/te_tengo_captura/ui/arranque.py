"""Splash window (screen 00): 480 × 300, frameless, centered, in ``--morado``.

The progress follows the real startup (``BOOT_STEPS`` of the prototype): «Iniciando…» while
the agent's threads start, «Abriendo la webcam configurada…» until the webcam answers (or capture
turns out not to be allowed yet), «Conectando con Te Tengo…» until the first heartbeat answers.
Each step has a time limit so a missing webcam or internet never blocks the window. Steps keep
the prototype's cadence as a minimum (``proto.js``: 22 % at 0.08 s, 54 % at 0.72 s, 86 % at
1.34 s, 100 % at 1.82 s, fade out at 2.06 s), so the symbol finishes assembling before the
status window appears even when the real steps are instant.
"""

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from te_tengo_captura.agente import Agente
from te_tengo_captura.ui.ventana import FONDO_ARRANQUE, WEB

ANCHO, ALTO = 480, 300
DURACION_MINIMA_S = 2.06  # fade out starts; the splash is gone at about 2.2 s
SALIDA_S = 0.2  # .boot.out animation
LIMITE_PASO_S = 5.0


@dataclass(frozen=True, slots=True)
class Paso:
    porcentaje: int
    indice_texto: int  # index in BOOT_STEPS
    listo: Callable[[], bool]
    desde_s: float = 0.0  # not shown before this time since the start (prototype cadence)
    limite_s: float = LIMITE_PASO_S


def pasos(agente: Agente) -> list[Paso]:
    def webcam_resuelta() -> bool:
        # Opened (or failed to open), or not opened because capture is not allowed.
        latido = agente.latido
        no_permitida = latido.en_linea is not None and not latido.captura_permitida()
        return agente.captador.conectada is not None or no_permitida

    return [
        Paso(22, 0, lambda: True, desde_s=0.08),
        Paso(54, 1, webcam_resuelta, desde_s=0.72),
        Paso(86, 2, lambda: agente.latido.en_linea is not None, desde_s=1.34),
        Paso(100, 2, lambda: True, desde_s=1.82),
    ]


def recorrer(
    pasos_: list[Paso],
    mostrar: Callable[[int, int], None],
    reloj: Callable[[], float] = time.monotonic,
    esperar: Callable[[float], None] = time.sleep,
    intervalo_s: float = 0.1,
) -> None:
    """Shows each step once the previous one is ready (or hit its limit) and not before its
    time in the prototype's cadence; returns after at least the minimum time."""
    inicio = reloj()
    for paso in pasos_:
        if (antes := inicio + paso.desde_s - reloj()) > 0:
            esperar(antes)
        mostrar(paso.porcentaje, paso.indice_texto)
        limite = reloj() + paso.limite_s
        while not paso.listo() and reloj() < limite:
            esperar(intervalo_s)
    if (resto := inicio + DURACION_MINIMA_S - reloj()) > 0:
        esperar(resto)


class VentanaArranque:
    def __init__(self, version: str) -> None:
        import webview

        self._version = version
        self._cargada = threading.Event()
        ventana = webview.create_window(
            "Te Tengo Captura",
            str(WEB / "arranque.html"),
            width=ANCHO,
            height=ALTO,
            resizable=False,
            frameless=True,
            easy_drag=False,
            background_color=FONDO_ARRANQUE,
        )
        if ventana is None:
            raise RuntimeError("pywebview no pudo crear la ventana de arranque")
        self._ventana: Any = ventana
        self._ventana.events.loaded += self._cargada.set

    def esperar_carga(self, limite_s: float = 5.0) -> bool:
        return self._cargada.wait(limite_s)

    def mostrar(self, porcentaje: int, indice_texto: int) -> None:
        argumentos = json.dumps([porcentaje, indice_texto, self._version])[1:-1]
        self._ventana.evaluate_js(f"window.ttg && window.ttg.arranque({argumentos})")

    def cerrar(self, esperar: Callable[[float], None] = time.sleep) -> None:
        self._ventana.evaluate_js("window.ttg && window.ttg.arranqueFin()")
        esperar(SALIDA_S)
        self._ventana.destroy()
