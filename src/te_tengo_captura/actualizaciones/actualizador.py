"""Updates of Te Tengo Captura on this PC (US-43; contract "Updates (US-43)").

**Checking (CA-43.1).** ``GET /api/versiones`` at startup and then once a day, and when the
person chooses «Buscar actualizaciones» (Avanzado › Acerca de, or the tray menu). Without
internet the next try is an hour later (implementation choice: the «next check»); detection is
never stopped. The PC reads the channel of its system: ``windows`` or ``mac``.

**A new version** shows the band «Hay una versión nueva (X)» with «Qué cambió» and «Descargar»
(Windows) or «Ir a la descarga» (Mac, or a Windows channel without ``url``/``sha256``), a coral
dot on the tray icon and on «Acerca de», the tray menu item, and one system notice per version
(``marcar_notificada`` keeps the version announced, so publishing it again never repeats it).
Below ``versionMinima`` the band says «Actualiza Te Tengo para seguir recibiendo alertas»
(CA-43.8); detection goes on.

**Windows (CA-43.2).** «Descargar» → «Descargando la versión X…» with its percentage and
«Cancelar» → «Verificando la descarga…» (SHA-256, ``descarga.py``) → «Reiniciando para
actualizar…» → the installer runs silently and opens the new version (``instalador.py``) and
this process exits. A failure keeps the current version and offers «Reintentar».

**Never during an alert or a live view (CA-43.9).** ``bloqueo`` tells whether a fall alert is in
progress (``"alerta"``) or a live view, its pre-warm or a camera preview is open (``"vivo"``).
Download and verification go on; the restart waits («Se actualizará cuando termine la alerta»)
and continues on its own when it ends.

**Automatically (CA-43.7).** «Actualizar automáticamente» is on by default and only on Windows:
between 03:00 and 06:00 local time (``VENTANA_AUTOMATICA``: a PC asleep at 03:00 still updates if
it wakes before 06:00, never in the day) a new version is downloaded, verified and installed when
nothing blocks it, at most once per night. Changing it goes to the activity log (the coordinator).

**macOS (CA-43.3).** Nothing is downloaded or installed: «Ir a la descarga» opens
``paginaDescargas`` in the browser and the window explains the three steps.

Settings and memory live in ``actualizaciones.json`` in the data folder (the switch, the version
announced, the last check and the last version that ran, which tells the next start that the
program was updated, also by hand, for ``PC_ACTUALIZADA``).
"""

import json
import logging
import shutil
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from datetime import date, datetime, timedelta, tzinfo
from datetime import time as hora
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx

from te_tengo_captura.actualizaciones import descarga, instalador
from te_tengo_captura.actualizaciones.comparar import es_mas_nueva
from te_tengo_captura.backend.errores import ErrorBackendError, SinConexionError
from te_tengo_captura.backend.modelos import VersionesPublicadas, VersionPublicada

logger = logging.getLogger(__name__)

ARCHIVO = "actualizaciones.json"
CARPETA = "actualizaciones"
INTERVALO_BUSQUEDA = timedelta(days=1)  # CA-43.1
REINTENTO_BUSQUEDA = timedelta(hours=1)  # without internet: the next check
HORA_AUTOMATICA = hora(3, 0)  # CA-43.7
VENTANA_AUTOMATICA = timedelta(hours=3)
FRESCURA_AUTOMATICA = timedelta(hours=1)  # an older check is repeated before installing at night
ESPERA_REINICIO_S = 1.5  # «Reiniciando para actualizar…» is seen before the window closes
TICK_S = 1.0
DMG_PREDETERMINADO = "te-tengo-captura.dmg"  # docs/RELEASES.md: the landing's stable name


class Plataforma(StrEnum):
    WINDOWS = "windows"
    MAC = "mac"


class Estado(StrEnum):
    """The band's states (``u.st`` of the prototype)."""

    DESCARGANDO = "dl"
    VERIFICANDO = "verify"
    REINICIANDO = "restart"
    ESPERANDO = "wait"
    SIN_INTERNET = "net"
    FALLO = "fail"
    ALTERADA = "bad"
    SIN_ESPACIO = "disk"


OCUPADO = frozenset({Estado.DESCARGANDO, Estado.VERIFICANDO, Estado.REINICIANDO})


def plataforma_actual() -> Plataforma | None:
    if sys.platform == "win32":
        return Plataforma.WINDOWS
    if sys.platform == "darwin":
        return Plataforma.MAC
    return None  # Linux: no published channel


def en_madrugada(ahora: datetime) -> date | None:
    """The night whose automatic update window (03:00 to 06:00) contains ``ahora``."""
    inicio = datetime.combine(ahora.date(), HORA_AUTOMATICA, ahora.tzinfo)
    return inicio.date() if inicio <= ahora < inicio + VENTANA_AUTOMATICA else None


def proxima_madrugada(ahora: datetime) -> datetime:
    """The next 03:00 strictly after ``ahora`` (local wall-clock time)."""
    hoy = datetime.combine(ahora.date(), HORA_AUTOMATICA, ahora.tzinfo)
    return hoy if ahora < hoy else hoy + timedelta(days=1)


def _sin_esquema(url: str) -> str:
    return url.split("://", 1)[-1].rstrip("/")


def _en_hilo(accion: Callable[[], None]) -> None:
    threading.Thread(target=accion, name="actualizacion", daemon=True).start()


class Actualizador:
    def __init__(
        self,
        version: str,
        directorio: Path,
        versiones: Callable[[], VersionesPublicadas | None],
        plataforma: Plataforma | None = None,
        reloj: Callable[[], datetime] = datetime.now,
        zona: tzinfo | None = None,
        bloqueo: Callable[[], str | None] = lambda: None,
        bajar: Callable[..., descarga.Descarga] = descarga.descargar,
        lanzar: Callable[[Path], None] = instalador.lanzar,
        abrir_navegador: Callable[[str], object] = webbrowser.open,
        transporte: httpx.BaseTransport | None = None,
        uso: descarga.UsoDisco = shutil.disk_usage,
        en_hilo: Callable[[Callable[[], None]], None] = _en_hilo,
        esperar: Callable[[float], None] = time.sleep,
    ) -> None:
        """``reloj`` gives the local wall-clock time (naive, no DST in Peru); ``bloqueo`` tells
        whether an alert (``"alerta"``) or a live view or preview (``"vivo"``) is open."""
        self.version = version
        self.plataforma = plataforma
        self._directorio = directorio
        self._versiones = versiones
        self._reloj = reloj
        self._zona = zona
        self._bloqueo = bloqueo
        self._bajar = bajar
        self._lanzar = lanzar
        self._abrir_navegador = abrir_navegador
        self._transporte = transporte
        self._uso = uso
        self._en_hilo = en_hilo
        self._esperar = esperar
        self.al_salir: Callable[[], None] = lambda: None  # the application exits (installer)
        self._candado = threading.RLock()
        self._cancelada = threading.Event()
        self._detenido = threading.Event()
        self._hilo: threading.Thread | None = None
        self._publicadas: VersionesPublicadas | None = None
        self.estado: Estado | None = None
        self.porcentaje = 0
        self.espera: str | None = None
        self.faltan_bytes = 0
        self.buscando = False
        self._listo: Path | None = None
        self._proxima_busqueda: datetime | None = None
        self._noche_automatica: date | None = None
        self.actualizada_a: str | None = None  # this start follows an update (window notice)
        datos = self._leer()
        self._automatica = bool(datos.get("automatica", True))
        self._notificada = datos.get("notificada")
        self.ultima_busqueda: datetime | None = _fecha(datos.get("ultimaBusqueda"))
        self._ultima_version = datos.get("ultimaVersion")
        # The installer started by the previous run opened this one (the splash says so).
        self.terminando = instalador.leer_marca(directorio) is not None

    # ------------------------------------------------------------------ lifecycle

    def iniciar(self) -> None:
        self._terminar_actualizacion()
        self._hilo = threading.Thread(target=self._correr, name="actualizaciones", daemon=True)
        self._hilo.start()

    def detener(self) -> None:
        self._detenido.set()
        self._cancelada.set()
        hilo = self._hilo
        if hilo is not None and hilo.is_alive() and hilo is not threading.current_thread():
            hilo.join(1.0)  # a daemon: a check in flight never delays the exit

    def registrar_version(self) -> tuple[str, str] | None:
        """At startup: ``(anterior, actual)`` when this version is newer than the last one that
        ran here (an update, automatic or by hand), once; the coordinator logs it
        (``PC_ACTUALIZADA``)."""
        anterior = self._ultima_version
        if anterior != self.version:
            self._ultima_version = self.version
            self._guardar()
        if isinstance(anterior, str) and es_mas_nueva(self.version, anterior):
            self.actualizada_a = self.version
            return anterior, self.version
        return None

    # ------------------------------------------------------------------ what was published

    @property
    def canal(self) -> VersionPublicada | None:
        publicadas = self._publicadas
        if publicadas is None or self.plataforma is None:
            return None
        return publicadas.windows if self.plataforma is Plataforma.WINDOWS else publicadas.mac

    @property
    def nueva(self) -> VersionPublicada | None:
        """The published version when it is newer than this one."""
        canal = self.canal
        return canal if canal is not None and es_mas_nueva(canal.version, self.version) else None

    @property
    def debajo_de_la_minima(self) -> bool:
        """CA-43.8: the backend no longer supports this version."""
        canal = self.canal
        minima = canal.version_minima if canal is not None else None
        return minima is not None and es_mas_nueva(minima, self.version)

    @property
    def se_descarga(self) -> bool:
        """Windows with an installer and its SHA-256; otherwise «Ir a la descarga»."""
        nueva = self.nueva
        return (
            self.plataforma is Plataforma.WINDOWS
            and nueva is not None
            and bool(nueva.url)
            and bool(nueva.sha256)
        )

    @property
    def automatica(self) -> bool:
        """«Actualizar automáticamente» in force: only on Windows (CA-43.7)."""
        return self.plataforma is Plataforma.WINDOWS and self._automatica

    def actualizacion_automatica(self) -> bool | None:
        """For the PC's heartbeat: ``None`` (omitted) on a system without updates."""
        return None if self.plataforma is None else self.automatica

    def aviso_pendiente(self) -> str | None:
        """The new version for the system notice, unless an alert or a live view is open."""
        nueva = self.nueva
        if nueva is None or self.estado is Estado.REINICIANDO or self._bloqueo():
            return None
        return nueva.version

    # ------------------------------------------------------------------ actions

    def buscar(self) -> dict[str, Any]:
        """Asks ``GET /api/versiones``; ``ok`` is false only without internet."""
        ahora = self._reloj()
        with self._candado:
            if self.plataforma is None:  # no published channel for this system
                self._proxima_busqueda = ahora + INTERVALO_BUSQUEDA
                return {"ok": True, "nueva": False, "version": self.version}
            if self.buscando:
                return {"ok": True, "nueva": self.nueva is not None, "version": self.version}
            self.buscando = True
        try:
            publicadas = self._versiones()
        except SinConexionError as error:
            logger.info("Sin internet: no se pudo buscar una versión nueva (%s)", error)
            with self._candado:
                self.buscando = False
                self._proxima_busqueda = ahora + REINTENTO_BUSQUEDA
            return {"ok": False, "nueva": self.nueva is not None, "version": self.version}
        except ErrorBackendError as error:
            logger.warning("No se pudo saber la última versión: %s", error)
            publicadas = self._publicadas  # no information: what was known stays
        with self._candado:
            self.buscando = False
            self._publicadas = publicadas
            self.ultima_busqueda = ahora
            self._proxima_busqueda = ahora + INTERVALO_BUSQUEDA
            nueva = self.nueva
        self._guardar()
        if nueva is not None:
            logger.info("Hay una versión nueva: %s (instalada %s)", nueva.version, self.version)
        return {"ok": True, "nueva": nueva is not None, "version": self.version}

    def descargar(self) -> dict[str, Any]:
        """«Descargar» (Windows) or «Ir a la descarga»."""
        if self.nueva is None:
            return {"ok": False}
        if not self.se_descarga:
            return self.ir_a_la_descarga()
        with self._candado:
            if self.estado in OCUPADO or (self.estado is Estado.ESPERANDO and self._listo):
                return {"ok": True}
            self.estado, self.porcentaje, self.faltan_bytes = Estado.DESCARGANDO, 0, 0
            self._cancelada.clear()
        self._en_hilo(self._descargar_e_instalar)
        return {"ok": True}

    def cancelar(self) -> dict[str, Any]:
        """«Cancelar»: «Descarga cancelada. Sigues con la versión Y.»"""
        with self._candado:
            if self.estado is not Estado.DESCARGANDO:
                return {"ok": False, "version": self.version}
            self._cancelada.set()
            self.estado, self.porcentaje = None, 0
        return {"ok": True, "version": self.version}

    def ir_a_la_descarga(self) -> dict[str, Any]:
        """Opens ``paginaDescargas`` in the browser (Mac, CA-43.3)."""
        publicadas, canal = self._publicadas, self.canal
        pagina = publicadas.pagina_descargas if publicadas else None
        url = pagina or (canal.url if canal else None)
        if not url:
            return {"ok": False}
        try:
            self._abrir_navegador(url)
        except Exception:  # the browser is best effort; the page is shown in the window
            logger.warning("No se pudo abrir el navegador", exc_info=True)
        return {"ok": True, "pagina": _sin_esquema(url)}

    def cambiar_automatica(self, activar: bool) -> bool:
        with self._candado:
            self._automatica = bool(activar)
        self._guardar()
        if activar:
            logger.info("Actualización automática: la próxima a las %s", HORA_AUTOMATICA)
        return self._automatica

    def marcar_notificada(self, version: str) -> bool:
        """``True`` the first time ``version`` is announced (one system notice per version)."""
        with self._candado:
            if self._notificada == version:
                return False
            self._notificada = version
        self._guardar()
        return True

    # ------------------------------------------------------------------ scheduler

    def paso(self) -> None:
        """One turn of the scheduler (every second): the daily check, a restart that waited,
        the night's automatic update."""
        ahora = self._reloj()
        if self._proxima_busqueda is None or ahora >= self._proxima_busqueda:
            self.buscar()
        self._reanudar()
        self._automatica_de_noche(ahora)

    def _correr(self) -> None:
        while not self._detenido.is_set():
            try:
                self.paso()
            except Exception:
                logger.exception("Error inesperado en las actualizaciones")
            self._detenido.wait(TICK_S)

    def _automatica_de_noche(self, ahora: datetime) -> None:
        noche = en_madrugada(ahora)
        if noche is None or not self.automatica or self._noche_automatica == noche:
            return
        if self.estado in OCUPADO or self.estado is Estado.ESPERANDO or self._bloqueo():
            return  # CA-43.7: no alert in progress and no live view open
        if self.ultima_busqueda is None or ahora - self.ultima_busqueda > FRESCURA_AUTOMATICA:
            self.buscar()
        if not self.se_descarga:
            return
        self._noche_automatica = noche
        logger.info("Actualización automática de madrugada a la versión %s", self._version_nueva())
        self.descargar()

    def _reanudar(self) -> None:
        with self._candado:
            if self.estado is not Estado.ESPERANDO:
                return
            motivo = self._bloqueo()
            if motivo:
                self.espera = motivo
                return
        logger.info("Terminó la alerta o la vista en vivo: se instala la versión nueva")
        self._reiniciar()

    # ------------------------------------------------------------------ download and install

    def _descargar_e_instalar(self) -> None:
        nueva = self.nueva
        if nueva is None or not nueva.url or not nueva.sha256:
            with self._candado:
                self.estado = None
            return
        destino = self._directorio / CARPETA / f"te-tengo-captura-{nueva.version}-setup.exe"

        def progreso(pct: int) -> None:
            self.porcentaje = pct

        def verificando() -> None:
            with self._candado:
                if self.estado is Estado.DESCARGANDO:
                    self.estado = Estado.VERIFICANDO

        resultado = self._bajar(
            nueva.url,
            nueva.sha256,
            destino,
            tamano=nueva.tamano_bytes,
            al_progreso=progreso,
            al_verificar=verificando,
            cancelada=self._cancelada,
            transporte=self._transporte,
            uso=self._uso,
        )
        with self._candado:
            if resultado.resultado is descarga.Resultado.CANCELADA or self._detenido.is_set():
                self.estado, self.porcentaje = None, 0
                return
            if resultado.resultado is not descarga.Resultado.LISTA or resultado.archivo is None:
                self.estado = Estado(resultado.resultado.value)
                self.faltan_bytes = resultado.faltan_bytes
                return
            self._listo = resultado.archivo
            motivo = self._bloqueo()
            if motivo:
                logger.info("Versión %s verificada: espera (%s)", nueva.version, motivo)
                self.estado, self.espera = Estado.ESPERANDO, motivo
                return
        self._reiniciar()

    def _reiniciar(self) -> None:
        with self._candado:
            archivo, nueva = self._listo, self._version_nueva()
            if archivo is None or nueva is None:
                self.estado = None
                return
            self.estado, self.espera = Estado.REINICIANDO, None
        try:
            instalador.guardar_marca(self._directorio, self.version, nueva, archivo)
            self._lanzar(archivo)
        except OSError as error:
            logger.error("No se pudo iniciar el instalador: %s", error)
            archivo.unlink(missing_ok=True)
            (self._directorio / instalador.ARCHIVO_MARCA).unlink(missing_ok=True)
            with self._candado:
                self._listo, self.estado = None, Estado.FALLO
            return
        self._esperar(ESPERA_REINICIO_S)
        logger.info("Se cierra Te Tengo Captura para instalar la versión %s", nueva)
        self.al_salir()

    def _terminar_actualizacion(self) -> None:
        """The previous run started the installer: delete it and its marker (Inno Setup's log
        stays for the diagnostic). A download left by a closed run is deleted too."""
        marca = instalador.leer_marca(self._directorio)
        if marca is not None:
            if marca.get("hacia") == self.version:
                logger.info("Actualización terminada: versión %s", self.version)
            else:
                logger.warning(
                    "La versión %s no se instaló; sigue la %s", marca.get("hacia"), self.version
                )
            (self._directorio / instalador.ARCHIVO_MARCA).unlink(missing_ok=True)
        for archivo in (self._directorio / CARPETA).glob("*"):
            if archivo.name != instalador.ARCHIVO_LOG and archivo.is_file():
                archivo.unlink(missing_ok=True)

    def _version_nueva(self) -> str | None:
        nueva = self.nueva
        return nueva.version if nueva is not None else None

    # ------------------------------------------------------------------ window

    def a_json(self) -> dict[str, Any]:
        """``upd`` of the window's state: the band, «Acerca de» and the dialogs."""
        nueva, canal = self.nueva, self.canal
        publicadas = self._publicadas
        pagina = publicadas.pagina_descargas if publicadas else None
        mac = self.plataforma is Plataforma.MAC
        dmg = DMG_PREDETERMINADO
        if mac and canal is not None and canal.url and canal.url.lower().endswith(".dmg"):
            dmg = canal.url.rstrip("/").rsplit("/", 1)[-1]
        publicada = (
            nueva.publicada_en.astimezone(self._zona).strftime("%d/%m/%Y")
            if nueva is not None and nueva.publicada_en is not None
            else None
        )
        return {
            "os": self.plataforma.value if self.plataforma else None,
            "ver": self.version,
            "latest": nueva.version if nueva is not None else None,
            "minima": self.debajo_de_la_minima,
            "notes": list(nueva.notas) if nueva is not None else [],
            "date": publicada,
            "mb": descarga.megas(nueva.tamano_bytes)
            if nueva is not None and nueva.tamano_bytes
            else None,
            "download": self.se_descarga,
            "page": _sin_esquema(pagina) if pagina else None,
            "dmg": dmg,
            "st": self.estado.value if self.estado else None,
            "pct": self.porcentaje,
            "why": self.espera,
            "ready": self._listo is not None and self.estado is Estado.ESPERANDO,
            "free": descarga.megas(self.faltan_bytes) if self.faltan_bytes else None,
            "drive": _unidad(self._directorio),
            "checking": self.buscando,
            "last": self._texto_busqueda(),
            "auto": self.automatica,
            "updated": self.actualizada_a,
        }

    def _texto_busqueda(self) -> str | None:
        """«hoy 10:30» (prototype); another day «22/09 10:30» (adapted, docs/BLOCKERS.md)."""
        ultima = self.ultima_busqueda
        if ultima is None:
            return None
        if ultima.date() == self._reloj().date():
            return f"hoy {ultima:%H:%M}"
        return f"{ultima:%d/%m %H:%M}"

    # ------------------------------------------------------------------ storage

    def _leer(self) -> dict[str, Any]:
        try:
            datos = json.loads((self._directorio / ARCHIVO).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return datos if isinstance(datos, dict) else {}

    def _guardar(self) -> None:
        datos = {
            "automatica": self._automatica,
            "notificada": self._notificada,
            "ultimaBusqueda": self.ultima_busqueda.isoformat() if self.ultima_busqueda else None,
            "ultimaVersion": self._ultima_version,
        }
        try:
            self._directorio.mkdir(parents=True, exist_ok=True)
            (self._directorio / ARCHIVO).write_text(json.dumps(datos), encoding="utf-8")
        except OSError as error:
            logger.warning("No se pudo guardar %s: %s", ARCHIVO, error)


def _fecha(valor: object) -> datetime | None:
    if not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


def _unidad(directorio: Path) -> str:
    """«C:» on Windows: the disk of the download folder («Libera 90 MB en el disco C:.»)."""
    unidad = directorio.drive or Path(directorio).resolve().drive
    return unidad or "C:"
