"""Runs the agent with its windows and tray icon: pywebview owns the main thread until «Salir».

Startup: the splash shows the real startup steps, then the status window appears. Closing or
minimizing the window hides it to the tray (the first time with a system notification); the
tray menu opens it again or exits.
"""

import logging
import os
import tempfile
from collections.abc import MutableMapping
from pathlib import Path

from te_tengo_captura.agente import Agente
from te_tengo_captura.bandeja.avisos import Avisos
from te_tengo_captura.bandeja.icono import EN_MACOS, IconoBandeja
from te_tengo_captura.bandeja.iconos import icono
from te_tengo_captura.ui import arranque
from te_tengo_captura.ui.puente import Puente
from te_tengo_captura.ui.ventana import VentanaEstado

logger = logging.getLogger(__name__)


def quitar_qt_de_opencv(entorno: MutableMapping[str, str] = os.environ) -> None:
    """On Linux, importing ``cv2`` points Qt at the plugins bundled with OpenCV, which cannot
    load pywebview's Qt backend. Drop those variables so Qt uses its own plugins."""
    for variable in ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_FONTDIR"):
        valor = entorno.get(variable, "")
        if f"{os.sep}cv2{os.sep}" in valor:
            del entorno[variable]


def guardar_icono(carpeta: Path | None = None) -> Path:
    """Writes the brand app icon as a PNG for the window and the Dock, and returns its path."""
    ruta = (carpeta or Path(tempfile.gettempdir())) / "te-tengo-captura.png"
    icono(None, 512).save(ruta)
    return ruta


def mostrar_icono_en_el_dock(ruta: Path) -> None:
    """macOS: an unpackaged run shows Python's icon in the Dock; use the brand icon instead."""
    from AppKit import NSApplication, NSImage

    imagen = NSImage.alloc().initWithContentsOfFile_(str(ruta))
    if imagen is not None:
        NSApplication.sharedApplication().setApplicationIconImage_(imagen)


class Aplicacion:
    def __init__(self, agente: Agente) -> None:
        self._agente = agente
        self._icono = IconoBandeja(abrir=self.abrir, salir=self.salir)
        self._avisos = Avisos(agente.config, self._icono.notificar)
        puente = Puente(
            estado=lambda: agente.estado().a_json(),
            ocultar=self.ocultar,
            buscar_webcam=agente.buscar_webcam,
            reintentar_ahora=agente.reintentar_ahora,
        )
        self._inicio = arranque.VentanaArranque(agente.version)
        self._ventana = VentanaEstado(puente, al_ocultar=self._al_ocultar, oculta=True)
        agente.suscribir(self._ventana.actualizar)
        agente.suscribir(self._icono.actualizar)
        agente.suscribir(self._avisos.estado)

    def ejecutar(self) -> None:
        import webview

        quitar_qt_de_opencv()
        ruta_icono = guardar_icono()
        if EN_MACOS:
            mostrar_icono_en_el_dock(ruta_icono)
            self._icono.iniciar()  # AppKit: from the main thread, before its event loop starts
        try:
            # ``icon`` sets the window icon on Linux (GTK and Qt); Windows uses the .exe's icon.
            webview.start(self._iniciar, icon=str(ruta_icono))
        finally:
            self._icono.detener()
            self._agente.detener()

    def abrir(self) -> None:
        self._ventana.mostrar()
        self._avisos.ventana_mostrada()

    def ocultar(self) -> None:
        self._ventana.ocultar()

    def salir(self) -> None:
        logger.info("Salir desde la bandeja")
        self._ventana.destruir()

    def _al_ocultar(self) -> None:
        self._avisos.ventana_oculta(self._agente.estado())

    def _iniciar(self) -> None:
        if not EN_MACOS:
            self._icono.iniciar()
        self._inicio.esperar_carga()
        pasos = arranque.pasos(self._agente)
        self._inicio.mostrar(pasos[0].porcentaje, pasos[0].indice_texto)
        self._agente.iniciar()
        arranque.recorrer(pasos, self._inicio.mostrar)
        self._inicio.cerrar()
        self.abrir()
        self._agente.publicar_estado()


def ejecutar(agente: Agente) -> None:
    Aplicacion(agente).ejecutar()
