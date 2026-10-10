"""The agent without its UI: builds the components, runs their threads and derives the state.

Threads (AGENTS.md): pywebview owns the main thread; the capture loop (with MediaPipe), the
heartbeat, the outbox sender, the state notifier, the live view publisher and its control
channel each run in a worker thread. The UI gets
the state through ``suscribir`` and the bridge, never by reading globals.
"""

import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, tzinfo
from functools import partial
from pathlib import Path

from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.transmision import CanalTransmision
from te_tengo_captura.captura.bucle import BucleCaptura, HiloCaptura
from te_tengo_captura.captura.en_vivo import TransmisionEnVivo
from te_tengo_captura.captura.fuentes import Captador, FuenteVideo
from te_tengo_captura.captura.pose import Estimador
from te_tengo_captura.config import Configuracion
from te_tengo_captura.envios.cola import ColaEnvios, EnviadorPendientes
from te_tengo_captura.estado import Entradas, EstadoAgente, derivar
from te_tengo_captura.latido import HiloLatido, Latido, Salud
from te_tengo_captura.umbrales_remotos import ActualizadorUmbrales
from te_tengo_deteccion.clips.codificar import codificar_mp4

logger = logging.getLogger(__name__)

INTERVALO_ESTADO_S = 1.0  # the window's countdown and «hace N s» move every second


class Agente:
    def __init__(
        self,
        config: Configuracion,
        cliente: ClienteBackend,
        fuente: FuenteVideo,
        estimador: Estimador,
        directorio_datos: Path,
        version: str,
        reloj_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
        zona: tzinfo | None = None,
        codificar: Callable[[list[tuple[float, bytes]]], bytes] | None = None,
        vista_en_vivo: bool = False,
    ) -> None:
        """``vista_en_vivo`` opens the live view's control channel to ``config.api_url``; it is
        off for ``--backend-falso`` and the tests, which have no WebSocket server. ``codificar``
        defaults to ``codificar_mp4`` with its temporary file in the outbox's clip directory."""
        self.config = config
        self.version = version
        self._cliente = cliente
        self._reloj_utc = reloj_utc
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
            permitida=self.latido.captura_permitida,
            fps=config.vista_en_vivo.fps,
            marca_tiempo=config.vista_en_vivo.marca_tiempo,
        )
        self.captador = Captador(fuente, al_leer=self.en_vivo.ofrecer)
        self.bucle = BucleCaptura(
            self.captador,
            estimador,
            config.clasificacion,
            self.cola,
            permitida=self.latido.captura_permitida,
            al_encolar=self._al_encolar,
            codificar=codificar or partial(codificar_mp4, directorio=self.cola.directorio_clips),
            reloj_utc=reloj_utc,
            en_vivo=self.en_vivo,
        )
        self._canal = (
            CanalTransmision(cliente, config.api_url, self.en_vivo) if vista_en_vivo else None
        )
        self._enviador = EnviadorPendientes(self.cola, cliente)
        self.umbrales = ActualizadorUmbrales(
            cliente, config.clasificacion, self.bucle.actualizar_umbrales, version
        )
        self._hilo_captura = HiloCaptura(self.bucle)
        self._hilo_latido = HiloLatido(self.latido)
        self._oyentes: list[Callable[[EstadoAgente], None]] = []
        self._detenido = threading.Event()
        self._hilo_estado = threading.Thread(target=self._notificar, name="estado", daemon=True)

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
        self._hilo_estado.start()

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
        self._cliente.cerrar()
        logger.info("Te Tengo Captura detenido")

    def secretos(self) -> list[str]:
        return [*self._cliente.secretos(), *self.en_vivo.secretos()]

    # ------------------------------------------------------------------ state

    def suscribir(self, oyente: Callable[[EstadoAgente], None]) -> None:
        """``oyente`` gets the state every second (window, tray); it runs in a worker thread."""
        self._oyentes.append(oyente)

    def estado(self) -> EstadoAgente:
        latido = self.latido
        nombre = (
            latido.estado.nombre_habitacion
            if latido.estado is not None and latido.estado.nombre_habitacion
            else self.config.camara.nombre_habitacion
        )
        entradas = Entradas(
            webcam_conectada=self.bucle.webcam_conectada,
            en_linea=latido.en_linea,
            consentimiento=not latido.sin_consentimiento(),
            pausada_hasta=latido.pausada_hasta(),
            segundos_desde_envio=self._segundos_desde_envio(),
            segundos_para_reintento=latido.segundos_para_reintento(),
            nombre_habitacion=nombre,
        )
        return derivar(entradas, self.config, self.version, self._zona)

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

    def reintentar_ahora(self) -> bool:
        """«Reintentar ahora»: a heartbeat right now, and the outbox right after."""
        self.latido.reintentar_ahora()
        self.latido.latir()
        self._enviador.reintentar_ahora()
        return self.latido.en_linea is True

    # ------------------------------------------------------------------ internals

    def _webcam_respondio(self) -> bool:
        return self.captador.conectada is True

    def _salud(self) -> Salud:
        return Salud(self.bucle.webcam_conectada, self.bucle.deteccion_confiable)

    def _segundos_desde_envio(self) -> int:
        ultimos = [self.latido.ultimo_contacto]
        if self.cola.ultimo_envio is not None:
            ultimos.append(datetime.fromtimestamp(self.cola.ultimo_envio, UTC))
        conocidos = [u for u in ultimos if u is not None]
        if not conocidos:
            return 0
        return max(0, int((self._reloj_utc() - max(conocidos)).total_seconds()))

    def _al_latir(self) -> None:
        # A new capture state may open or close the gate: let the capture thread check it now.
        self._hilo_captura.despertar()
        if self.latido.en_linea:
            self._enviador.notificar()

    def _al_encolar(self) -> None:
        self._enviador.notificar()

    def _notificar(self) -> None:
        while not self._detenido.wait(INTERVALO_ESTADO_S):
            self.publicar_estado()

    def publicar_estado(self) -> None:
        estado = self.estado()
        for oyente in list(self._oyentes):
            try:
                oyente(estado)
            except Exception:
                logger.exception("Error al mostrar el estado")
