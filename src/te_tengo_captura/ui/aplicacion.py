"""Runs the agent with its windows and tray icon: pywebview owns the main thread until «Salir».

Startup: the splash shows the real startup steps, then the status window appears. Closing or
minimizing the window hides it to the tray (the first time with a system notification); the
tray menu opens it again, downloads a new version or looks for one (US-43), or asks to exit:
«Salir» stops fall detection, so the window asks to confirm it first. To install an update the
updater calls ``salir`` once the installer started (no question). «Restablecer esta PC» and, on a
Mac, «Desinstalar» (the reset, then the app bundle goes to the Trash) live in «Avanzado ›
Acerca de».
"""

import logging
import os
import sys
import tempfile
import threading
from collections.abc import MutableMapping
from pathlib import Path

from te_tengo_captura.actualizaciones.actualizador import Plataforma
from te_tengo_captura.bandeja.avisos import Avisos
from te_tengo_captura.bandeja.icono import EN_MACOS, IconoBandeja
from te_tengo_captura.bandeja.iconos import icono
from te_tengo_captura.coordinador import Coordinador, EstadoVentana
from te_tengo_captura.ui import arranque
from te_tengo_captura.ui.puente import Acciones, Puente
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


def mostrar_en_carpeta(ruta: str) -> None:
    """Opens the file manager on the saved file (Explorer, Finder or the desktop's)."""
    import subprocess

    archivo = Path(ruta)
    if sys.platform == "win32":
        subprocess.Popen(["explorer", f"/select,{archivo}"])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(archivo)])
    else:
        subprocess.Popen(["xdg-open", str(archivo.parent)])


def paquete_de_la_app(ejecutable: str | None = None) -> Path | None:
    """``/Applications/Te Tengo Captura.app`` when running from the packaged app."""
    if ejecutable is None:
        if not getattr(sys, "frozen", False):
            return None
        ejecutable = sys.executable
    for carpeta in Path(ejecutable).parents:
        if carpeta.suffix == ".app":
            return carpeta
    return None


def mover_a_la_papelera(paquete: Path | None) -> bool:
    """macOS: moves the app to the Trash (``NSFileManager``); ``False`` if it could not."""
    if paquete is None or sys.platform != "darwin":
        return False
    try:
        from Foundation import NSURL, NSFileManager

        ok, _url, error = NSFileManager.defaultManager().trashItemAtURL_resultingItemURL_error_(
            NSURL.fileURLWithPath_(str(paquete)), None, None
        )
    except Exception:
        logger.warning("No se pudo mover la app a la Papelera", exc_info=True)
        return False
    if not ok:
        logger.warning("No se pudo mover la app a la Papelera: %s", error)
    return bool(ok)


class Aplicacion:
    def __init__(self, agente: Coordinador) -> None:
        self._agente = agente
        self._icono = IconoBandeja(
            abrir=self.abrir,
            salir=self.pedir_salir,
            descargar=lambda: self._desde_la_bandeja("updGo"),
            buscar=lambda: self._desde_la_bandeja("updCheck"),
        )
        self._avisos = Avisos(self._icono.notificar)
        puente = Puente(
            estado=lambda: agente.estado().a_json(),
            ocultar=self.ocultar,
            buscar_webcam=agente.buscar_webcam,
            reintentar_ahora=agente.reintentar_ahora,
            vista_previa=agente.vista_previa_jpeg,
            modo_vista_previa=agente.cambiar_vista_previa,
            acciones=Acciones(
                otro_codigo=agente.otro_codigo,
                vincular_de_nuevo=agente.vincular_de_nuevo,
                ir_a_estado=agente.ir_a_estado,
                desvincular=agente.desvincular,
                ambientes=agente.ambientes,
                usar_aqui=agente.usar_aqui,
                dejar_de_usar=agente.dejar_de_usar,
                modo_avanzado=agente.cambiar_modo_avanzado,
                registro=agente.registro,
                medidores=agente.medidores,
                actividad=agente.lista_actividad,
                exportar_diagnostico=self._exportar_diagnostico,
                nombre_diagnostico=agente.nombre_diagnostico,
                mostrar_en_carpeta=mostrar_en_carpeta,
                cambiar_almacenamiento=agente.cambiar_almacenamiento,
                cambiar_carpeta=self._cambiar_carpeta,
                borrar_movimientos=agente.borrar_movimientos,
                conservar_movimientos=agente.conservar_movimientos,
                repeticion=agente.repeticion,
                repeticion_ventana=agente.repeticion_ventana,
                repeticion_poses=agente.repeticion_poses,
                repeticion_video=agente.repeticion_video,
                cerrar_repeticion=agente.cerrar_repeticion,
                buscar_actualizaciones=agente.actualizador.buscar,
                descargar_actualizacion=agente.actualizador.descargar,
                cancelar_actualizacion=agente.actualizador.cancelar,
                ir_a_la_descarga=agente.actualizador.ir_a_la_descarga,
                actualizacion_automatica=agente.cambiar_actualizacion_automatica,
                salir=self.salir,
                restablecer=agente.restablecer,
                desinstalar=self._desinstalar,
            ),
        )
        self._inicio = arranque.VentanaArranque(agente.version)
        agente.actualizador.al_salir = self.salir  # the installer opens the new version
        self._ventana = VentanaEstado(puente, al_ocultar=self._al_ocultar, oculta=True)
        agente.suscribir(self._ventana.actualizar)
        agente.suscribir(self._icono.actualizar)
        agente.suscribir(self._avisos.estado)
        agente.suscribir(self._version_nueva)

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

    def pedir_salir(self) -> None:
        """«Salir» in the tray: the window opens and asks to confirm it."""
        self._desde_la_bandeja("salir")

    def salir(self) -> None:
        logger.info("Salir: se detiene la detección de caídas")
        self._ventana.destruir()

    def _desinstalar(self) -> dict[str, object]:
        """«Desinstalar» on a Mac: there is no uninstaller for an ``.app``."""
        resultado: dict[str, object] = dict(self._agente.restablecer("desinstalada"))
        if not resultado.get("ok"):
            return resultado
        papelera = mover_a_la_papelera(paquete_de_la_app())
        resultado["papelera"] = papelera
        if papelera:
            threading.Timer(3.0, self.salir).start()  # the window says goodbye first
        return resultado

    def _exportar_diagnostico(self) -> dict[str, object]:
        destino = self._ventana.elegir_destino(self._agente.nombre_diagnostico())
        if destino is None:
            return {"ok": False, "cancelado": True}
        return self._agente.exportar_diagnostico(destino)

    def _cambiar_carpeta(self) -> dict[str, object]:
        carpeta = self._ventana.elegir_carpeta()
        if carpeta is None:
            return {"ok": False, "cancelado": True}
        return self._agente.cambiar_carpeta(carpeta / "TeTengo" / "Datos")

    def _desde_la_bandeja(self, accion: str) -> None:
        """«Descargar la versión X» or «Buscar actualizaciones» from the tray menu: the window
        opens and does it, as its own buttons do."""
        self.abrir()
        self._ventana.accion(accion)

    def _version_nueva(self, _estado: EstadoVentana) -> None:
        actualizador = self._agente.actualizador
        nueva = actualizador.nueva
        mac = actualizador.plataforma is Plataforma.MAC
        restart = actualizador.estado is not None and actualizador.estado.value == "restart"
        self._icono.version_nueva(nueva.version if nueva and not restart else None, mac)
        self._avisos.version_nueva(
            actualizador.aviso_pendiente(), mac, actualizador.marcar_notificada
        )

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


def ejecutar(agente: Coordinador) -> None:
    Aplicacion(agente).ejecutar()
