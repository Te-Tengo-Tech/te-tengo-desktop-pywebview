"""A linked PC (US-28, US-30, US-31): its session, heartbeat, control channel and webcams.

The installation agent (``agente.py``) is one camera configured by the project team. A linked
PC instead has its own identity: it was approved by the household's owner in the app and holds
an access token and a rotating refresh token in the OS credential store
(``vinculacion/sesion.py``). This module runs what belongs to the PC itself:

* **Heartbeat** (``LatidoPc``): ``POST /api/agente/pc/senal`` every ``INTERVALO_S`` with the
  agent's version and system keeps the PC «En línea» in the app even with no camera in use
  (CA-30.2). The answer (``PcDelAgente``: household, approver, consent) is kept in ``pc.json``
  in the data folder (names only, no secret), so the window can show them offline. Offline, it
  retries after 2, 4, 8, 16 s and then every 30 s, like the cameras' heartbeat.
* **Control channel** with the PC's own token: it hears ``{"desvincular":true}`` even with no
  camera in use (CA-31.1).
* **Webcams**: the ones the PC detects (``captura/dispositivos.py``), by their stable OS id, for
  «Detectamos 3 cámaras» and the «Cámaras» tab.
* **Unlink from the PC** (CA-31.3, CA-31.6): ``DELETE /api/agente/pc``; if the API cannot be
  reached, the refresh token is revoked instead (RFC 7009, works without a valid access token);
  if that fails too, the refresh token is kept as a pending revocation and sent as soon as
  there is internet, so the family is told even when the PC was offline.
"""

import json
import logging
import math
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, tzinfo
from pathlib import Path

from pydantic import ValidationError

from te_tengo_captura.backend.errores import ErrorBackendError, PcDesvinculadaError
from te_tengo_captura.backend.modelos import ModoVista, PcDelAgente
from te_tengo_captura.backend.pc import ClientePc
from te_tengo_captura.backend.transmision import CanalTransmision
from te_tengo_captura.captura.dispositivos import Dispositivo, listar_dispositivos
from te_tengo_captura.estado import DatosPc, Entradas, EstadoAgente, Hogar, Webcam, derivar
from te_tengo_captura.sistema import nombre_pc, sistema_operativo
from te_tengo_captura.vinculacion.credenciales import AlmacenCredenciales, RevocacionPendiente
from te_tengo_captura.vinculacion.oauth import ClienteOAuth
from te_tengo_captura.vinculacion.sesion import SesionPc

logger = logging.getLogger(__name__)

INTERVALO_S = 30.0
REINTENTO_BASE_S = 2.0
REINTENTO_MAXIMO_S = 30.0
ARCHIVO_PC = "pc.json"


class LatidoPc:
    """The PC's heartbeat and the last ``PcDelAgente`` it got."""

    def __init__(
        self,
        cliente: ClientePc,
        version: str,
        archivo: Path,
        reloj: Callable[[], float] = time.monotonic,
        reloj_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
        al_contactar: Callable[[], None] = lambda: None,
    ) -> None:
        self._cliente = cliente
        self._version = version
        self._al_contactar = al_contactar
        self._ultimo_aviso_contacto: float | None = None
        self._sistema = sistema_operativo()
        self._archivo = archivo
        self._reloj = reloj
        self._reloj_utc = reloj_utc
        self._fallos = 0
        self._proximo = 0.0
        self.en_linea: bool | None = None
        self.pc: PcDelAgente | None = leer_pc(archivo)

    def espera(self) -> float:
        return max(0.0, self._proximo - self._reloj())

    def segundos_para_reintento(self) -> int:
        if self.en_linea is not False:
            return 0
        return max(0, math.ceil(self._proximo - self._reloj()))

    def reintentar_ahora(self) -> None:
        self._proximo = 0.0

    def latir(self) -> None:
        try:
            pc = self._cliente.senal(self._version, self._sistema)
        except PcDesvinculadaError:
            raise
        except ErrorBackendError as error:
            self._fallos += 1
            if self.en_linea is not False:
                logger.warning("Sin conexión con Te Tengo (PC): %s", error)
            self.en_linea = False
            espera = min(REINTENTO_MAXIMO_S, REINTENTO_BASE_S * 2 ** (self._fallos - 1))
            self._proximo = self._reloj() + espera
            return
        if self.en_linea is False:
            logger.info("Conexión con Te Tengo restablecida (PC)")
        self.en_linea, self._fallos = True, 0
        ahora = self._reloj()
        self._proximo = ahora + INTERVALO_S
        if self._ultimo_aviso_contacto is None or ahora - self._ultimo_aviso_contacto >= 3600:
            self._ultimo_aviso_contacto = ahora  # the last contact, for the 90 days (CA-28.7)
            self._al_contactar()
        if pc != self.pc:
            self.pc = pc
            guardar_pc(self._archivo, pc)


def leer_pc(archivo: Path) -> PcDelAgente | None:
    try:
        return PcDelAgente.model_validate(json.loads(archivo.read_text("utf-8")))
    except FileNotFoundError:
        return None
    except (OSError, ValueError, ValidationError):
        return None


def guardar_pc(archivo: Path, pc: PcDelAgente) -> None:
    try:
        archivo.parent.mkdir(parents=True, exist_ok=True)
        temporal = archivo.with_suffix(".tmp")
        temporal.write_text(json.dumps(pc.json_api()), encoding="utf-8")
        temporal.replace(archivo)
    except OSError as error:
        logger.warning("No se pudo guardar los datos de la PC: %s", error)


class _SinVistaEnVivo:
    """The PC's own channel carries no live view for a camera in use (previews: US-29)."""

    def transmitir(self, url: str, usuario: str | None, clave: str | None, modo: ModoVista) -> None:
        logger.info("Canal de la PC: vista previa no disponible todavía")

    def cambiar_modo(self, modo: ModoVista) -> None:
        pass

    def preparar(self) -> None:
        pass

    def detener(self) -> None:
        pass


class AgentePc:
    def __init__(
        self,
        api_url: str,
        sesion: SesionPc,
        cliente: ClientePc,
        oauth: ClienteOAuth,
        almacen: AlmacenCredenciales,
        directorio_datos: Path,
        version: str,
        listar: Callable[[], list[Dispositivo]] = listar_dispositivos,
        canal: bool = True,
        zona: tzinfo | None = None,
        al_contactar: Callable[[], None] = lambda: None,
    ) -> None:
        self.version = version
        self.sesion = sesion
        self._cliente = cliente
        self._oauth = oauth
        self._almacen = almacen
        self._directorio = directorio_datos
        self._listar = listar
        self._zona = zona
        self.latido = LatidoPc(
            cliente, version, directorio_datos / ARCHIVO_PC, al_contactar=al_contactar
        )
        self._dispositivos: list[Dispositivo] | None = None
        self._canal = (
            CanalTransmision(
                sesion,
                api_url,
                _SinVistaEnVivo(),
                al_desvincular=sesion.desvincular,
                nombre="Canal de la PC",
            )
            if canal
            else None
        )
        self._detenido = threading.Event()
        self._despertar = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="latido-pc", daemon=True)

    # ------------------------------------------------------------------ lifecycle

    def iniciar(self) -> None:
        logger.info(
            "Te Tengo Captura %s iniciando (PC vinculada %s)", self.version, self.sesion.pc_id
        )
        threading.Thread(target=self.buscar_webcams, name="webcams", daemon=True).start()
        self._hilo.start()
        if self._canal is not None:
            self._canal.iniciar()

    def detener(self) -> None:
        self._detenido.set()
        self._despertar.set()
        if self._canal is not None:
            self._canal.detener()
        if self._hilo.is_alive() and self._hilo is not threading.current_thread():
            self._hilo.join(5.0)
        self._cliente.cerrar()

    def secretos(self) -> list[str]:
        return self.sesion.secretos()

    # ------------------------------------------------------------------ state

    @property
    def webcams_listadas(self) -> bool:
        return self._dispositivos is not None

    @property
    def dispositivos(self) -> list[Dispositivo]:
        return list(self._dispositivos or [])

    def estado(self) -> EstadoAgente:
        pc = self.latido.pc
        webcams = tuple(
            Webcam(
                clave=d.dispositivo_id,
                nombre=d.nombre,
                dispositivo_id=d.dispositivo_id,
                nombre_habitacion=None,
            )
            for d in self.dispositivos
        )
        entradas = Entradas(
            camaras=(),
            en_linea=self.latido.en_linea,
            consentimiento=pc.consentimiento_vigente if pc is not None else True,
            segundos_para_reintento=self.latido.segundos_para_reintento(),
            webcams=webcams,
            vinculada=True,
            webcams_detectadas=len(webcams) if self._dispositivos is not None else None,
        )
        return derivar(entradas, self.hogar(), self.datos_pc(), self.version, self._zona)

    def hogar(self) -> Hogar:
        pc = self.latido.pc
        return Hogar(pc.nombre_adulto_mayor if pc is not None else "", "")

    def datos_pc(self) -> DatosPc:
        pc = self.latido.pc
        return DatosPc(
            nombre=pc.nombre if pc is not None else nombre_pc(),
            sistema=sistema_operativo(),
            programa=f"Te Tengo Captura {self.version}",
            vinculada_por=(pc.vinculada_por or "") if pc is not None else None,
            vinculada_el=(
                pc.vinculada_en.astimezone(self._zona).strftime("%d/%m/%Y")
                if pc is not None
                else None
            ),
        )

    # ------------------------------------------------------------------ bridge actions

    def buscar_webcams(self) -> bool:
        try:
            self._dispositivos = self._listar()
        except Exception:
            logger.exception("No se pudieron listar las webcams")
            self._dispositivos = []
        logger.info("Webcams detectadas: %d", len(self._dispositivos))
        return bool(self._dispositivos)

    def reintentar_ahora(self) -> bool:
        self.latido.reintentar_ahora()
        self._despertar.set()
        try:
            self.latido.latir()
        except PcDesvinculadaError:
            return False
        return self.latido.en_linea is True

    def desvincular(self, datos_locales_borrados: bool) -> bool:
        """«Desvincular esta PC»; ``True`` if the API heard it now, ``False`` if it is pending."""
        try:
            self._cliente.desvincular(datos_locales_borrados)
            logger.info("Esta PC se desvinculó desde la PC")
            return True
        except PcDesvinculadaError:
            return True  # already removed from the app
        except ErrorBackendError as error:
            logger.warning("No se pudo desvincular con la API (%s); se revoca el token", error)
        refresh = self.sesion.refresh_token()
        try:
            self._oauth.revocar(refresh, datos_locales_borrados)
            logger.info("Esta PC se desvinculó revocando su token")
            return True
        except ErrorBackendError as error:
            logger.warning("Desvinculación pendiente de enviar (%s)", error)
            self._almacen.guardar_revocacion(RevocacionPendiente(refresh, datos_locales_borrados))
            return False

    # ------------------------------------------------------------------ internals

    def _correr(self) -> None:
        while not self._detenido.is_set():
            if self.latido.espera() == 0:
                try:
                    self.latido.latir()
                except PcDesvinculadaError:
                    return
                except Exception:
                    logger.exception("Error inesperado en el latido de la PC")
            self._despertar.wait(min(1.0, self.latido.espera()))
            self._despertar.clear()


def enviar_revocacion_pendiente(almacen: AlmacenCredenciales, oauth: ClienteOAuth) -> bool:
    """Sends a revocation left pending by an offline unlink; ``True`` once nothing is pending."""
    pendiente = almacen.leer_revocacion()
    if pendiente is None:
        return True
    try:
        oauth.revocar(pendiente.refresh_token, pendiente.datos_locales_borrados)
    except ErrorBackendError as error:
        logger.info("La desvinculación sigue pendiente de enviar (%s)", error)
        return False
    almacen.borrar_revocacion()
    logger.info("Desvinculación pendiente enviada")
    return True
