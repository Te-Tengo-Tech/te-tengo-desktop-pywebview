"""Runs the agent with its windows and tray icon: pywebview owns the main thread until «Salir».

Startup: the splash shows the real startup steps, then the status window appears. Closing or
minimizing the window hides it to the tray (the first time with a system notification); the
tray menu opens it again, downloads a new version or looks for one (US-43), or asks to exit:
«Salir» stops fall detection, so the window asks to confirm it first. To install an update the
updater calls ``salir`` once the installer started (no question). «Restablecer esta PC» and, on a
Mac, «Desinstalar» (the reset, then the app bundle goes to the Trash) live in «Avanzado ›
Acerca de».

The exit is bounded (``salida.py``): ``salir`` returns at once, so the bridge call that asked for
it hands its value back to the page before the window closes; the window closes a moment later,
pywebview's main loop ends and the tray and the agent stop; a watchdog ends the process if that
takes longer than 8 s. On a Mac, Cmd+Q, the app menu and the Dock ask the same question
(``macos.py``); logging out or shutting down, on a Mac or on Windows (``windows.py``), exits
without asking.
"""

import logging
import os
import sys
import tempfile
import threading
import time
from collections.abc import MutableMapping
from pathlib import Path

from te_tengo_captura.actualizaciones.actualizador import Plataforma
from te_tengo_captura.bandeja.avisos import Avisos
from te_tengo_captura.bandeja.icono import EN_MACOS, IconoBandeja
from te_tengo_captura.bandeja.iconos import icono
from te_tengo_captura.coordinador import Coordinador, EstadoVentana
from te_tengo_captura.salida import Salida
from te_tengo_captura.ui import arranque
from te_tengo_captura.ui.puente import Acciones, Puente
from te_tengo_captura.ui.ventana import VentanaEstado

logger = logging.getLogger(__name__)

CIERRE_S = 0.3  # after «Salir», the bridge call returns its value before the window closes
EN_WINDOWS = sys.platform == "win32"


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


def icono_de_ventana(ruta_icono: Path, plataforma: str = sys.platform) -> str | None:
    """``webview.start``'s ``icon``: the window icon on Linux (GTK and Qt) only:
    pywebview's WinForms backend loads it with ``System.Drawing.Icon``, which rejects a PNG with
    an unhandled .NET exception that ends the process at startup; Windows uses the .exe's icon."""
    return str(ruta_icono) if plataforma.startswith("linux") else None


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
    def __init__(
        self,
        agente: Coordinador,
        salida: Salida | None = None,
        cierre_s: float = CIERRE_S,
        salir_tras: float | None = None,
    ) -> None:
        self._agente = agente
        self.salida = salida or Salida()
        self._cierre_s = cierre_s
        self._salir_tras = salir_tras  # ``--salir-tras``: the smoke test of the exit
        self._saliendo = False
        self._detenida = False
        self._candado_salida = threading.Lock()
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
            from te_tengo_captura.ui import macos

            mostrar_icono_en_el_dock(ruta_icono)
            self._icono.iniciar()  # AppKit: from the main thread, before its event loop starts
            try:
                macos.interceptar_salida(self.pedir_salir, self._apagar, lambda: self._saliendo)
            except Exception:  # a pywebview that changed: quitting still works from the tray
                logger.warning("No se pudo preguntar antes de salir con Cmd+Q", exc_info=True)
        try:
            webview.start(self._iniciar, icon=icono_de_ventana(ruta_icono))
        finally:
            self.salida.vigilar()  # whatever ended the main loop, the exit is bounded from here
            self._detener()

    def _detener(self) -> None:
        """Stops the tray icon and the agent, once; a failure in one never skips the other."""
        with self._candado_salida:
            if self._detenida:
                return
            self._detenida = True
        try:
            self._icono.detener()
        except Exception:
            logger.exception("No se pudo quitar el ícono de la bandeja")
        try:
            self._agente.detener()
        except Exception:
            logger.exception("No se pudo detener el agente al salir")

    def abrir(self) -> None:
        self._ventana.mostrar()
        self._avisos.ventana_mostrada()

    def ocultar(self) -> None:
        self._ventana.ocultar()

    def pedir_salir(self) -> None:
        """«Salir» in the tray (or Cmd+Q, the app menu, the Dock on a Mac): the window opens and
        asks to confirm it."""
        if self._saliendo:
            return
        logger.info("Salir pedido: la ventana pide confirmarlo")
        self._desde_la_bandeja("salir")

    def salir(self) -> None:
        """«Salir» confirmed in the window (a bridge thread) or the updater's installer started.

        Returns at once: the window closes ``cierre_s`` later, from another thread, so the bridge
        call that asked for it returns first (a call still waiting when the window is gone never
        returns). Then pywebview's main loop ends and ``ejecutar`` stops everything."""
        if not self._empezar_salida():
            return
        logger.info("Salir: se detiene la detección de caídas")
        cierre = threading.Timer(self._cierre_s, self._ventana.destruir)
        cierre.daemon = True
        cierre.start()

    def _apagar(self) -> None:
        """The system logs out or shuts down: no question. On a Mac the app terminates right
        after this returns (``NSTerminateLater``); on Windows the forms are already closing."""
        if not self._empezar_salida():
            return
        if EN_MACOS:
            self._detener_agente_al_apagar()

    def _detener_agente_al_apagar(self) -> None:
        # The tray icon goes with the process (AppKit only from the main thread, which is busy).
        with self._candado_salida:
            if self._detenida:
                return
            self._detenida = True
        try:
            self._agente.detener()
        except Exception:
            logger.exception("No se pudo detener el agente al apagar")

    def _empezar_salida(self) -> bool:
        with self._candado_salida:
            if self._saliendo:
                return False
            self._saliendo = True
        self.salida.vigilar()
        self._ventana.preparar_salida()
        return True

    def _desinstalar(self) -> dict[str, object]:
        """«Desinstalar» on a Mac: there is no uninstaller for an ``.app``."""
        resultado: dict[str, object] = dict(self._agente.restablecer("desinstalada"))
        if not resultado.get("ok"):
            return resultado
        papelera = mover_a_la_papelera(paquete_de_la_app())
        resultado["papelera"] = papelera
        if papelera:
            despedida = threading.Timer(3.0, self.salir)  # the window says goodbye first
            despedida.daemon = True
            despedida.start()
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
        if EN_WINDOWS:
            from te_tengo_captura.ui import windows

            windows.permitir_apagado(self._ventana.nativa, self._apagar)
        self._agente.publicar_estado()
        if self._salir_tras is not None:
            prueba = threading.Timer(self._salir_tras, self._probar_salida)
            prueba.daemon = True
            prueba.start()

    def _probar_salida(self) -> None:
        """``--salir-tras``: the tray's «Salir», then the window's «Salir» through the bridge."""
        logger.info("Prueba de salida: «Salir» en la bandeja y en la ventana")
        self.pedir_salir()
        time.sleep(1.0)
        self._ventana.confirmar_salida()


def ejecutar(agente: Coordinador) -> None:
    Aplicacion(agente).ejecutar()
