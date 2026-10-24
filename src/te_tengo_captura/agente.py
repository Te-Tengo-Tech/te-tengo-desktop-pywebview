"""One camera's agent: builds the components, runs their threads and derives the state.

The same agent runs an installation's camera (configured by the project team in ``config.toml``)
and each camera in use of a linked PC (``camaras.SupervisorCamaras``, US-29): its own heartbeat,
outbox, capture loop with its own MediaPipe landmarker (monotonic timestamps per stream), clips,
live view and control channel, with the camera's own token.

Threads (AGENTS.md): pywebview owns the main thread; the capture loop (with MediaPipe), the
heartbeat, the outbox sender, the live view publisher and its control channel each run in a
worker thread. ``coordinador.Coordinador`` runs the state notifier and gives the UI the state
through subscriptions and the bridge, never through globals.
"""

import contextlib
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta, tzinfo
from functools import partial
from pathlib import Path

from te_tengo_captura.actualizaciones.alerta import SeguimientoAlerta
from te_tengo_captura.almacen.gestor import AlmacenLocal, GrabadorCamara
from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.modelos import EstadoMovimientos, ModoVista
from te_tengo_captura.backend.transmision import CanalTransmision
from te_tengo_captura.captura.bucle import Analisis, BucleCaptura, HiloCaptura
from te_tengo_captura.captura.en_vivo import TransmisionEnVivo
from te_tengo_captura.captura.fuentes import Captador, FuenteVideo, Imagen
from te_tengo_captura.captura.pose import Estimador
from te_tengo_captura.captura.vista_previa import VistaPreviaLocal
from te_tengo_captura.config import Configuracion, VistaEnVivo
from te_tengo_captura.diario import Narrador
from te_tengo_captura.envios.cola import ColaEnvios, EnviadorPendientes
from te_tengo_captura.envios.movimientos import CarrilMovimientos
from te_tengo_captura.estado import (
    CamaraEntradas,
    DatosPc,
    Entradas,
    EstadoAgente,
    Hogar,
    Webcam,
    derivar,
)
from te_tengo_captura.latido import HiloLatido, Latido, Salud
from te_tengo_captura.sistema import nombre_pc, sistema_operativo
from te_tengo_captura.umbrales_remotos import ActualizadorUmbrales
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.clips.codificar import codificar_mp4

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AjustesCamara:
    """What one camera's agent needs to know about itself."""

    api_url: str
    nombre_habitacion: str  # until the backend says otherwise (the app renames it)
    nombre_webcam: str
    clasificacion: Umbrales
    vista_en_vivo: VistaEnVivo
    dispositivo_id: str | None = None  # a linked PC's webcam (OS unique id)
    elegida_desde: str | None = None  # "app" or "pc" (CA-29.10)


def ajustes_de_instalacion(config: Configuracion) -> AjustesCamara:
    return AjustesCamara(
        api_url=config.api_url,
        nombre_habitacion=config.camara.nombre_habitacion,
        nombre_webcam=config.webcam.nombre,
        clasificacion=config.clasificacion,
        vista_en_vivo=config.vista_en_vivo,
    )


class Agente:
    def __init__(
        self,
        config: Configuracion | AjustesCamara,
        cliente: ClienteBackend,
        fuente: FuenteVideo,
        estimador: Estimador,
        directorio_datos: Path,
        version: str,
        reloj_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
        zona: tzinfo | None = None,
        codificar: Callable[[list[tuple[float, bytes]]], bytes] | None = None,
        vista_en_vivo: bool = False,
        al_desvincular: Callable[[str], None] | None = None,
        almacen: AlmacenLocal | None = None,
    ) -> None:
        """``vista_en_vivo`` opens the live view's control channel to ``config.api_url``; it is
        off for ``--backend-falso`` and the tests, which have no WebSocket server. ``codificar``
        defaults to ``codificar_mp4`` with its temporary file in the outbox's clip directory.
        ``al_desvincular`` hears that the installation's PC was removed from the household in the
        app (``401 PC_DESVINCULADA`` or ``{"desvincular":true}``, US-31); capture stops at once."""
        ajustes = ajustes_de_instalacion(config) if isinstance(config, Configuracion) else config
        self.ajustes = ajustes
        self.version = version
        self._cliente = cliente
        self._reloj_utc = reloj_utc
        self._al_desvincular = al_desvincular
        self._bloqueada = False  # the PC left the household: never capture again
        cliente.al_desvincular = self._desvinculada
        self._zona = zona
        directorio_datos.mkdir(parents=True, exist_ok=True)
        self.cola = ColaEnvios(directorio_datos)
        self.latido = Latido(
            cliente,
            self._salud,
            directorio_datos / "estado_captura.json",
            reloj_utc=reloj_utc,
            al_cambiar=self._al_latir,
        )
        self.en_vivo = TransmisionEnVivo(
            permitida=self._permitida,
            fps=ajustes.vista_en_vivo.fps,
            marca_tiempo=ajustes.vista_en_vivo.marca_tiempo,
        )
        self.vista_previa = VistaPreviaLocal()
        self.captador = Captador(fuente, al_leer=self._al_leer)
        self.bucle = BucleCaptura(
            self.captador,
            estimador,
            ajustes.clasificacion,
            self.cola,
            permitida=self._permitida,
            al_encolar=self._al_encolar,
            codificar=codificar or partial(codificar_mp4, directorio=self.cola.directorio_clips),
            reloj_utc=reloj_utc,
            en_vivo=self.en_vivo,
        )
        self._canal = (
            CanalTransmision(
                cliente, ajustes.api_url, self.en_vivo, al_desvincular=self._desvinculada
            )
            if vista_en_vivo
            else None
        )
        self._enviador = EnviadorPendientes(self.cola, cliente)
        self.umbrales = ActualizadorUmbrales(
            cliente, ajustes.clasificacion, self.bucle.actualizar_umbrales, version
        )
        self._hilo_captura = HiloCaptura(self.bucle)
        self._hilo_latido = HiloLatido(self.latido)
        instalacion = config if isinstance(config, Configuracion) else None
        self._hogar = Hogar(
            instalacion.vivienda.nombre_adulto_mayor if instalacion else "",
            instalacion.vivienda.direccion if instalacion else "",
        )
        self._pc = DatosPc(
            nombre=nombre_pc(),
            sistema=sistema_operativo(),
            programa=f"Te Tengo Captura {version}",
            instalada_el=instalacion.instalada_el.strftime("%d/%m/%Y") if instalacion else None,
        )
        self._detenido = threading.Event()
        self.narrador = Narrador(
            camara=lambda: self.clave_camara,
            habitacion=lambda: self.nombre_habitacion,
            dispositivo=lambda: self.ajustes.nombre_webcam,
            reloj=time.monotonic,
        )
        # A fall detected and not yet over: updates wait for it (US-43, CA-43.9).
        self.alerta = SeguimientoAlerta()
        self.bucle.observadores.append(self._analizado)
        # Local storage (US-38) and the cloud (US-36, US-37): this camera's recorder, once its
        # camera id is known, and the movements lane of its outbox.
        self._almacen: AlmacenLocal | None = None
        self._grabador: GrabadorCamara | None = None
        self._eventos: dict[str, datetime] = {}  # eventoId → when, for the clip's landmarks
        self.bucle.al_clip.append(self._clip)
        if almacen is not None:
            self.conectar_almacen(almacen)

    # ------------------------------------------------------------------ lifecycle

    def iniciar(self) -> None:
        logger.info("Te Tengo Captura %s iniciando", self.version)
        self._hilo_latido.iniciar()
        self._enviador.iniciar()
        self.en_vivo.iniciar()
        self._hilo_captura.iniciar()
        if self._canal is not None:
            self._canal.iniciar()
        self.umbrales.iniciar()

    def detener(self) -> None:
        self._detenido.set()
        self.umbrales.detener()
        if self._canal is not None:
            self._canal.detener()
        self._hilo_captura.detener()
        self.en_vivo.cerrar()
        self._hilo_latido.detener()
        self._enviador.detener()
        self.cola.cerrar()
        if self._almacen is not None:
            for lista in (self._almacen.al_movimientos, self._almacen.al_cambiar_permiso):
                with contextlib.suppress(ValueError):
                    lista.remove(self._hay_movimientos)
            if self._grabador is not None:
                self._almacen.soltar_camara(self._cliente.camara_id or "")
        self._cliente.cerrar()
        logger.info("Te Tengo Captura detenido")

    def secretos(self) -> list[str]:
        return [*self._cliente.secretos(), *self.en_vivo.secretos()]

    # ------------------------------------------------------------------ state

    def camara(self) -> CamaraEntradas:
        """This camera as the window's state sees it (one row of «Estado»). The notifier calls
        it every second, so it also tells the advanced mode's log about connection changes."""
        latido = self.latido
        self.narrador.estado(self.bucle.webcam_conectada, latido.en_linea, latido.pausada_hasta())
        return CamaraEntradas(
            clave=self.clave_camara,
            nombre_habitacion=self.nombre_habitacion,
            dispositivo=self.ajustes.nombre_webcam,
            webcam_conectada=self.bucle.webcam_conectada,
            pausada_hasta=latido.pausada_hasta(),
            en_vivo_desde=self.en_vivo.solicitada_desde,
            elegida_desde=self.ajustes.elegida_desde,
        )

    @property
    def nombre_habitacion(self) -> str:
        estado = self.latido.estado
        if estado is not None and estado.nombre_habitacion:
            return estado.nombre_habitacion
        return self.ajustes.nombre_habitacion

    def estado(self) -> EstadoAgente:
        latido = self.latido
        camara = self.camara()
        webcam = Webcam(
            clave=camara.clave,
            nombre=self.ajustes.nombre_webcam,
            dispositivo_id=self.ajustes.dispositivo_id,
            nombre_habitacion=camara.nombre_habitacion,
            conectada=camara.webcam_conectada,
            esqueleto=True,
        )
        entradas = Entradas(
            camaras=(camara,),
            en_linea=latido.en_linea,
            consentimiento=not latido.sin_consentimiento(),
            segundos_para_reintento=latido.segundos_para_reintento(),
            webcams=(webcam,),
        )
        return derivar(entradas, self._hogar, self._pc, self.version, self._zona)

    @property
    def clave_camara(self) -> str:
        """The camera's id once registered (``instalacion`` before): the window's key for it."""
        return self._cliente.camara_id or "instalacion"

    # ------------------------------------------------------------------ bridge actions

    def buscar_webcam(self, espera_s: float = 3.0) -> bool:
        """«Buscar de nuevo»: reopen the webcam and wait a moment for it to answer."""
        self.bucle.buscar_webcam()
        self._hilo_captura.despertar()
        limite = time.monotonic() + espera_s
        while not self._webcam_respondio():
            if time.monotonic() >= limite or self._detenido.wait(0.1):
                return self._webcam_respondio()
        return True

    def vista_previa_jpeg(self, clave: str, modo: ModoVista = ModoVista.VIDEO) -> bytes | None:
        """The newest frame of the camera for the «Cámaras» tab, only on this PC."""
        return self.vista_previa.jpeg(modo) if clave == self.clave_camara else None

    def reintentar_ahora(self) -> bool:
        """«Reintentar ahora»: a heartbeat right now, and the outbox right after."""
        self.latido.reintentar_ahora()
        self.latido.latir()
        self._enviador.reintentar_ahora()
        return self.latido.en_linea is True

    # ------------------------------------------------------------------ internals

    def bloquear(self) -> None:
        """Never capture again (the camera left its room or the PC left the household)."""
        self._bloqueada = True
        self._hilo_captura.despertar()

    def renombrar(self, nombre_habitacion: str) -> None:
        """The owner renamed the room or moved the camera (the heartbeat confirms it)."""
        if nombre_habitacion != self.ajustes.nombre_habitacion:
            self.ajustes = replace(self.ajustes, nombre_habitacion=nombre_habitacion)

    def medidores(self) -> dict[str, object]:
        """The «Medidores» of this camera (CA-32.3), with the reason when there is nothing to
        measure (CA-32.4)."""
        m = self.narrador.medicion
        latido = self.latido
        if not self.bucle.webcam_conectada:
            motivo = "desconectada"
        elif latido.pausada_hasta() is not None:
            motivo = "pausa"
        elif latido.estado is not None and latido.sin_consentimiento():
            motivo = "consentimiento"
        elif not m.persona or not self.bucle.activa:
            motivo = "sin_persona"
        else:
            motivo = None
        pausa = latido.pausada_hasta()
        return {
            "motivo": motivo,
            "pausa": pausa.astimezone(self._zona).strftime("%H:%M") if pausa else None,
            "fps": round(self.bucle.fps, 1),
            "demora": round(self.bucle.demora, 3),
            "persona": m.persona,
            "m1": m.m1,
            "m2": m.m2,
            "m3": m.m3,
            "cabezaBajoPies": m.cabeza_bajo_pies,
            "umbralV": m.umbral_v,
            "umbralAngulo": m.umbral_angulo,
            "umbralRazon": m.umbral_razon,
            "umbralVisibilidad": m.umbral_visibilidad,
            "fase": m.fase,
            "ventana": m.ventana if m.ventana is not None else m.ventana_total,
            "ventanaTotal": m.ventana_total,
            "suelo": m.suelo,
            "confirmacion": m.confirmacion,
            "visibilidad": m.visibilidad,
            "esqueleto": {k: list(v) for k, v in m.esqueleto.items()},
        }

    def _analizado(self, analisis: Analisis) -> None:
        self.vista_previa.anotar_pose(analisis.pose)
        self.narrador.analizado(
            analisis.fotograma.instante, analisis.pose, analisis.clasificador, analisis.eventos
        )
        self.alerta.observar(evento.tipo for evento in analisis.detectados)
        for evento in analisis.detectados:
            self._eventos[evento.evento_id] = evento.ocurrido_en
            while len(self._eventos) > 32:
                self._eventos.pop(next(iter(self._eventos)))
        grabador = self._grabador_listo()
        if grabador is not None:
            grabador.analizado(analisis)

    def conectar_almacen(self, almacen: AlmacenLocal) -> None:
        """An installation's storage is the coordinator's (it exists before the agent)."""
        self._almacen = almacen
        self.cola.carril_movimientos = CarrilMovimientos(almacen, lambda: self._cliente.camara_id)
        almacen.al_movimientos.append(self._hay_movimientos)
        almacen.al_cambiar_permiso.append(self._hay_movimientos)

    def _hay_movimientos(self, *_: object) -> None:
        """A new movement file, or the cloud turned on: the outbox looks again."""
        self._enviador.notificar()

    def estado_movimientos(self) -> EstadoMovimientos:
        return self._cliente.estado_movimientos()

    def _grabador_listo(self) -> "GrabadorCamara | None":
        if self._grabador is None and self._almacen is not None:
            camara_id = self._cliente.camara_id
            if camara_id:
                self._grabador = self._almacen.para_camara(camara_id)
                self._grabador.al_puntos_clip = self._puntos_clip
        return self._grabador

    def _clip(self, evento_id: str, mp4: bytes) -> None:
        grabador = self._grabador_listo()
        if grabador is not None:
            ocurrido_en = self._eventos.get(evento_id) or self._reloj_utc() - timedelta(seconds=6)
            grabador.clip(evento_id, ocurrido_en, mp4)

    def _puntos_clip(self, evento_id: str, parquet: bytes, ligero: bytes) -> None:
        """The landmarks of the clip's 12 s (US-36), Parquet and light: uploaded after the clip."""
        self.cola.agregar_puntos_clip(evento_id, parquet, ligero)
        self._enviador.notificar()

    def _permitida(self) -> bool:
        return not self._bloqueada and self.latido.captura_permitida()

    def _desvinculada(self, motivo: str) -> None:
        """The PC left the household: stop capturing at once (CA-31.1), then tell the owner."""
        if self._bloqueada:
            return
        self._bloqueada = True
        self._hilo_captura.despertar()
        logger.warning("Esta cámara se quitó (%s): se detiene la captura", motivo)
        if self._al_desvincular is not None:
            self._al_desvincular(motivo)

    def _al_leer(self, instante: float, imagen: Imagen) -> None:
        self.en_vivo.ofrecer(instante, imagen)
        self.vista_previa.ofrecer(instante, imagen)

    def _webcam_respondio(self) -> bool:
        return self.captador.conectada is True

    def _salud(self) -> Salud:
        return Salud(self.bucle.webcam_conectada, self.bucle.deteccion_confiable)

    def _al_latir(self) -> None:
        # A new capture state may open or close the gate: let the capture thread check it now.
        self._hilo_captura.despertar()
        if self.latido.en_linea:
            self._enviador.notificar()

    def _al_encolar(self) -> None:
        self._enviador.notificar()
