"""Heartbeat and capture state (US-07, US-05, US-22; ``docs/AGENT_CONTRACT.md``).

Every ``INTERVALO_S`` seconds the agent sends ``POST /api/agente/senal`` with the webcam and
detection state; the answer is the capture state (consent, pause, room name). A change of the
webcam state is reported at once, so the backend marks the camera disconnected without waiting
for missed heartbeats (CA-07.2) and online again as soon as it is back (CA-07.3).

Offline (implementation choice): retries back off 2, 4, 8, 16 s and then every 30 s; the window
shows the countdown and «Reintentar ahora» retries at once.

The last capture state is stored on disk so a restart without internet keeps honouring it. With
no known state, capture stays blocked (CA-05.2). A pause ends on its own at ``pausadaHasta``
even before the backend confirms it (CA-22.3).
"""

import json
import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from te_tengo_captura.backend.errores import CredencialInvalidaError, ErrorBackendError
from te_tengo_captura.backend.modelos import EstadoCaptura, MotivoCaptura

logger = logging.getLogger(__name__)

INTERVALO_S = 30.0
REINTENTO_BASE_S = 2.0
REINTENTO_MAXIMO_S = 30.0
REVISION_WEBCAM_S = 1.0


class Senalador(Protocol):
    def senal(self, webcam_conectada: bool, deteccion_confiable: bool) -> EstadoCaptura: ...


@dataclass(frozen=True, slots=True)
class Salud:
    """What the heartbeat reports about the capture side."""

    webcam_conectada: bool
    deteccion_confiable: bool


class Latido:
    def __init__(
        self,
        cliente: Senalador,
        salud: Callable[[], Salud],
        archivo_estado: Path,
        reloj: Callable[[], float] = time.monotonic,
        reloj_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
        al_cambiar: Callable[[], None] = lambda: None,
    ) -> None:
        self._cliente = cliente
        self._salud = salud
        self._archivo = archivo_estado
        self._reloj = reloj
        self._reloj_utc = reloj_utc
        self._al_cambiar = al_cambiar
        self._candado = threading.Lock()
        self._fallos = 0
        self._proximo = 0.0
        self._ultima_salud: Salud | None = None
        self.en_linea: bool | None = None  # None until the first heartbeat answers
        self.credencial_invalida = False
        self.ultimo_contacto: datetime | None = None
        self.estado: EstadoCaptura | None = self._leer_estado()

    # ------------------------------------------------------------------ queries

    def captura_permitida(self) -> bool:
        estado = self.estado
        if estado is None:
            return False
        if estado.captura_permitida:
            return True
        return (
            estado.motivo is MotivoCaptura.EN_PAUSA
            and estado.pausada_hasta is not None
            and self._reloj_utc() >= estado.pausada_hasta
        )

    def pausada_hasta(self) -> datetime | None:
        estado = self.estado
        if (
            estado is None
            or self.captura_permitida()
            or estado.motivo is not MotivoCaptura.EN_PAUSA
        ):
            return None
        return estado.pausada_hasta

    def sin_consentimiento(self) -> bool:
        estado = self.estado
        return estado is None or (
            not estado.captura_permitida and estado.motivo is not MotivoCaptura.EN_PAUSA
        )

    def segundos_para_reintento(self) -> int:
        """Countdown shown as «reintentando en N s» while offline."""
        if self.en_linea is not False:
            return 0
        return max(0, math.ceil(self._proximo - self._reloj()))

    def espera(self) -> float:
        return max(0.0, self._proximo - self._reloj())

    # ------------------------------------------------------------------ actions

    def toca(self) -> bool:
        """A heartbeat is due: on schedule, or because the webcam state changed."""
        return self.espera() == 0 or self._salud() != self._ultima_salud

    def latir(self) -> None:
        salud = self._salud()
        with self._candado:
            self._ultima_salud = salud
            try:
                estado = self._cliente.senal(salud.webcam_conectada, salud.deteccion_confiable)
            except ErrorBackendError as error:
                self._fallo(error)
            else:
                self._exito(estado)
        self._al_cambiar()

    def reintentar_ahora(self) -> None:
        self._proximo = 0.0

    # ------------------------------------------------------------------ internals

    def _exito(self, estado: EstadoCaptura) -> None:
        if self.en_linea is False:
            logger.info("Conexión con Te Tengo restablecida")
        self.en_linea, self.credencial_invalida, self._fallos = True, False, 0
        self.ultimo_contacto = self._reloj_utc()
        self._proximo = self._reloj() + INTERVALO_S
        if estado != self.estado:
            logger.info(
                "Estado de captura: permitida=%s motivo=%s hasta=%s habitación=%s",
                estado.captura_permitida,
                estado.motivo,
                estado.pausada_hasta,
                estado.nombre_habitacion,
            )
            self.estado = estado
            self._guardar_estado(estado)

    def _fallo(self, error: ErrorBackendError) -> None:
        self._fallos += 1
        self.credencial_invalida = isinstance(error, CredencialInvalidaError)
        if self.en_linea is not False:
            logger.warning("Sin conexión con Te Tengo: %s", error)
        self.en_linea = False
        espera = min(REINTENTO_MAXIMO_S, REINTENTO_BASE_S * 2 ** (self._fallos - 1))
        self._proximo = self._reloj() + espera

    def _leer_estado(self) -> EstadoCaptura | None:
        try:
            return EstadoCaptura.model_validate(json.loads(self._archivo.read_text("utf-8")))
        except FileNotFoundError:
            return None
        except (OSError, ValueError, ValidationError) as error:
            logger.warning("Estado de captura guardado ilegible (%s); se ignora", error)
            return None

    def _guardar_estado(self, estado: EstadoCaptura) -> None:
        try:
            self._archivo.parent.mkdir(parents=True, exist_ok=True)
            temporal = self._archivo.with_suffix(".tmp")
            temporal.write_text(json.dumps(estado.json_api()), encoding="utf-8")
            temporal.replace(self._archivo)
        except OSError as error:
            logger.warning("No se pudo guardar el estado de captura: %s", error)


class HiloLatido:
    """Sends heartbeats from a worker thread; checks the webcam state every second."""

    def __init__(self, latido: Latido) -> None:
        self._latido = latido
        self._detenido = threading.Event()
        self._despertar = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="latido", daemon=True)

    def iniciar(self) -> None:
        self._hilo.start()

    def reintentar_ahora(self) -> None:
        self._latido.reintentar_ahora()
        self._despertar.set()

    def detener(self, espera_s: float = 5.0) -> None:
        self._detenido.set()
        self._despertar.set()
        if self._hilo.is_alive():
            self._hilo.join(espera_s)

    def _correr(self) -> None:
        while not self._detenido.is_set():
            if self._latido.toca():
                try:
                    self._latido.latir()
                except Exception:
                    logger.exception("Error inesperado en el latido")
            self._despertar.wait(min(REVISION_WEBCAM_S, self._latido.espera()))
            self._despertar.clear()
