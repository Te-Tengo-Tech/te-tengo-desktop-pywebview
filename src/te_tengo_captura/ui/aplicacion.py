"""Runs the agent with its windows: pywebview owns the main thread until the user exits.

Startup: the splash shows the real startup steps, then the status window appears.
"""

import logging

from te_tengo_captura.agente import Agente
from te_tengo_captura.ui import arranque
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
    inicio = arranque.VentanaArranque(agente.version)
    ventana = VentanaEstado(puente, oculta=True)
    agente.suscribir(ventana.actualizar)

    def iniciar() -> None:
        inicio.esperar_carga()
        pasos = arranque.pasos(agente)
        inicio.mostrar(pasos[0].porcentaje, pasos[0].indice_texto)
        agente.iniciar()
        arranque.recorrer(pasos, inicio.mostrar)
        inicio.cerrar()
        assert ventana is not None
        ventana.mostrar()
        agente.publicar_estado()

    try:
        webview.start(iniciar)
    finally:
        agente.detener()
