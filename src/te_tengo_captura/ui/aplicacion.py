"""Runs the agent with its window: pywebview owns the main thread until the user exits."""

import logging

from te_tengo_captura.agente import Agente
from te_tengo_captura.ui.puente import Puente
from te_tengo_captura.ui.ventana import VentanaEstado

logger = logging.getLogger(__name__)


def ejecutar(agente: Agente) -> None:
    import webview

    ventana: VentanaEstado | None = None

    def ocultar() -> None:
        if ventana is not None:
            ventana.ocultar()

    puente = Puente(
        estado=lambda: agente.estado().a_json(),
        ocultar=ocultar,
        buscar_webcam=agente.buscar_webcam,
        reintentar_ahora=agente.reintentar_ahora,
    )
    ventana = VentanaEstado(puente, oculta=False)
    agente.suscribir(ventana.actualizar)
    try:
        webview.start(agente.iniciar)
    finally:
        agente.detener()
