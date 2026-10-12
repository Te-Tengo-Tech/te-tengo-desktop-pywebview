"""Persistent outbox: events and clips survive restarts and offline periods.

Events are written here first and sent afterwards, so none is lost (AGENTS.md). Delivery rules:

* **Lanes:** urgent events (``URGENTES``: the fall, its confirmation, the unstable movement and
  the recovery), the other events, the clips (with the landmarks of each clip, US-36, after it)
  and the movement files (US-37, ``movimientos.py``) are sent in four lanes, in that order, each
  with its own backoff, so a failure in one never delays another: a failing clip upload never
  holds back an event, and a new fall goes out at once even while the other lanes wait. The
  movements lane only runs when no event or clip is due.
* **Order:** within a lane, events go out in the order they were detected; a clip goes out only
  once its event was accepted, because the backend needs the event to issue the upload URL.
* **Idempotency:** the backend answers ``200`` to a repeated ``eventoId``; that counts as
  delivered, so resending after a lost response is safe.
* **Backoff** (implementation choice): after a failure that may succeed later (no connection,
  ``429``, ``5xx``) a lane waits ``min(tope, 2 s × 2^(n-1))`` after its n-th failure in a row,
  with *equal jitter* (half fixed, half random) so many households do not retry in lockstep after
  an outage. ``tope`` is 300 s for the other events and the clips, and ``ESPERA_MAXIMA_URGENTE_S``
  (5 s) for urgent events, so a pending fall goes out within seconds of the connection coming
  back; a newly queued urgent event is tried at once. A clip upload that fails for any reason
  backs off the clip lane only. A success resets its lane's wait; «Reintentar ahora» skips every
  wait.
* **Rejections:** an event the backend refuses for good (``409 CAPTURA_NO_PERMITIDA``, ``400``)
  is kept as ``rechazado`` for diagnosis and not retried. A clip is discarded after
  ``MAX_INTENTOS_CLIP`` failed uploads or when its event was rejected (CA-18.2: the event is
  still sent without the clip).
* **Privacy:** the clip file is deleted after a successful upload or when it is discarded, and
  clip files the database does not know are deleted at startup. A clip's landmarks
  (``<eventoId>.puntos.parquet``, and the same rows in the light replay format the app draws,
  ``<eventoId>.puntos.ttmov``, uploaded right after it) follow the same rules; without the
  movement consent they are never made, and a ``409 SIN_CONSENTIMIENTO_DE_MOVIMIENTOS``
  discards them. An API without the light file's path (``404`` without ``codigo``) gets the
  Parquet file only.
"""

import json
import logging
import random
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from te_tengo_captura.almacen.ligero import ruta_ligera
from te_tengo_captura.backend.errores import (
    ErrorBackendError,
    EventoNoEncontradoError,
    SinPermisoDeMovimientosError,
)
from te_tengo_captura.backend.modelos import EventoAgente, EventoRecibido, SubidaClip
from te_tengo_deteccion.clasificacion.estados import TipoEvento

if TYPE_CHECKING:
    from te_tengo_captura.envios.movimientos import CarrilMovimientos, RemitenteMovimientos

logger = logging.getLogger(__name__)

ESPERA_BASE_S = 2.0
ESPERA_MAXIMA_S = 300.0
ESPERA_MAXIMA_URGENTE_S = 5.0
MAX_INTENTOS_CLIP = 10

# Events a family member must hear about now: never behind another lane's backoff.
URGENTES = frozenset(
    {
        TipoEvento.CAIDA,
        TipoEvento.CAIDA_CONFIRMADA,
        TipoEvento.MOVIMIENTO_INESTABLE,
        TipoEvento.RECUPERACION,
    }
)

_CLIPS_LISTOS = (
    "SELECT c.evento_id, c.archivo, c.intentos FROM clips c "
    "LEFT JOIN eventos e ON e.evento_id = c.evento_id "
    "WHERE e.estado IS NULL OR e.estado = 'rechazado' ORDER BY c.creado_en"
)

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS eventos (
    orden INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id TEXT NOT NULL UNIQUE,
    cuerpo TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    intentos INTEGER NOT NULL DEFAULT 0,
    ultimo_error TEXT
);
CREATE TABLE IF NOT EXISTS clips (
    evento_id TEXT PRIMARY KEY,
    archivo TEXT NOT NULL,
    intentos INTEGER NOT NULL DEFAULT 0,
    creado_en INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS puntos (
    evento_id TEXT PRIMARY KEY,
    archivo TEXT NOT NULL,
    intentos INTEGER NOT NULL DEFAULT 0,
    creado_en INTEGER NOT NULL
);
"""

# A clip's landmarks go after its event was accepted and its clip left the queue.
_PUNTOS_LISTOS = (
    "SELECT p.evento_id, p.archivo, p.intentos FROM puntos p "
    "LEFT JOIN eventos e ON e.evento_id = p.evento_id "
    "LEFT JOIN clips c ON c.evento_id = p.evento_id "
    "WHERE (e.estado IS NULL OR e.estado = 'rechazado') AND c.evento_id IS NULL "
    "ORDER BY p.creado_en"
)


class Remitente(Protocol):
    """The part of ``ClienteBackend`` the outbox uses."""

    def publicar_evento(self, evento: EventoAgente) -> tuple[EventoRecibido, bool]: ...

    def solicitar_subida_clip(self, evento_id: str, tamano_bytes: int) -> SubidaClip: ...

    def subir_clip(self, subida: SubidaClip, mp4: bytes) -> None: ...

    def solicitar_subida_puntos_clip(self, evento_id: str) -> SubidaClip: ...

    def solicitar_subida_puntos_clip_ligero(self, evento_id: str) -> SubidaClip: ...

    def subir_archivo(
        self, url: str, cabeceras: dict[str, str], datos: bytes, que: str
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class Resumen:
    """Result of one pass over the outbox."""

    eventos_enviados: int
    clips_subidos: int
    pendientes: int
    error: ErrorBackendError | None  # the first failure that stopped a lane, if any
    movimientos_subidos: int = 0
    movimientos_pendientes: int = 0


class _Espera:
    """Backoff of one lane: exponential, capped at ``tope``, with equal jitter."""

    def __init__(
        self, tope: float, reloj: Callable[[], float], aleatorio: Callable[[], float]
    ) -> None:
        self._tope = tope
        self._reloj = reloj
        self._aleatorio = aleatorio
        self._fallos_seguidos = 0
        self._proximo_intento = 0.0

    def restante(self) -> float:
        return max(0.0, self._proximo_intento - self._reloj())

    def fallo(self) -> None:
        self._fallos_seguidos += 1
        tope = min(self._tope, ESPERA_BASE_S * 2 ** (self._fallos_seguidos - 1))
        self._proximo_intento = self._reloj() + tope / 2 + self._aleatorio() * tope / 2

    def exito(self) -> None:
        self._fallos_seguidos = 0
        self._proximo_intento = 0.0

    def ya(self) -> None:
        """The next attempt is due now; the count of failures stays."""
        self._proximo_intento = 0.0


class ColaEnvios:
    def __init__(
        self,
        directorio: Path,
        reloj: Callable[[], float] = time.time,
        aleatorio: Callable[[], float] = random.random,
    ) -> None:
        self._directorio_clips = directorio / "clips"
        self._directorio_clips.mkdir(parents=True, exist_ok=True)
        self._reloj = reloj
        self._aleatorio = aleatorio
        self._candado = threading.RLock()
        self._db = sqlite3.connect(
            directorio / "envios.sqlite3", check_same_thread=False, isolation_level=None
        )
        self._db.executescript(_ESQUEMA)
        self._urgentes = _Espera(ESPERA_MAXIMA_URGENTE_S, reloj, aleatorio)
        self._otros = _Espera(ESPERA_MAXIMA_S, reloj, aleatorio)
        self._clips = _Espera(ESPERA_MAXIMA_S, reloj, aleatorio)
        self._movimientos = _Espera(ESPERA_MAXIMA_S, reloj, aleatorio)
        self.carril_movimientos: CarrilMovimientos | None = None  # US-37, with local storage
        self.ultimo_envio: float | None = None
        self._limpiar_huerfanos()

    @property
    def directorio_clips(self) -> Path:
        """Where clips wait for their upload (and are encoded, ``codificar_mp4``)."""
        return self._directorio_clips

    # ------------------------------------------------------------------ writing

    def agregar_evento(self, evento: EventoAgente) -> None:
        with self._candado:
            self._db.execute(
                "INSERT OR IGNORE INTO eventos (evento_id, cuerpo) VALUES (?, ?)",
                (evento.evento_id, json.dumps(evento.json_api())),
            )
            if evento.tipo in URGENTES:
                self._urgentes.ya()

    def agregar_clip(self, evento_id: str, mp4: bytes) -> None:
        """Stores the clip file until it is uploaded (the only frames ever kept on disk)."""
        archivo = self._directorio_clips / f"{evento_id}.mp4"
        temporal = archivo.with_suffix(".tmp")
        temporal.write_bytes(mp4)
        temporal.replace(archivo)
        with self._candado:
            self._db.execute(
                "INSERT OR REPLACE INTO clips (evento_id, archivo, creado_en) VALUES (?, ?, ?)",
                (evento_id, archivo.name, int(self._reloj())),
            )

    def agregar_puntos_clip(self, evento_id: str, parquet: bytes, ligero: bytes = b"") -> None:
        """The landmarks of an alert's clip (US-36), uploaded after the clip: the Parquet file and,
        next to it, the light file the app draws."""
        archivo = self._directorio_clips / f"{evento_id}.puntos.parquet"
        for contenido, destino in ((ligero, _ligero(archivo)), (parquet, archivo)):
            if not contenido:
                continue
            temporal = destino.with_suffix(".tmp")
            temporal.write_bytes(contenido)
            temporal.replace(destino)
        with self._candado:
            self._db.execute(
                "INSERT OR REPLACE INTO puntos (evento_id, archivo, creado_en) VALUES (?, ?, ?)",
                (evento_id, archivo.name, int(self._reloj())),
            )

    # ------------------------------------------------------------------ reading

    def eventos_pendientes(self) -> list[str]:
        with self._candado:
            filas = self._db.execute(
                "SELECT evento_id FROM eventos WHERE estado = 'pendiente' ORDER BY orden"
            ).fetchall()
        return [fila[0] for fila in filas]

    def eventos_rechazados(self) -> list[str]:
        with self._candado:
            filas = self._db.execute(
                "SELECT evento_id FROM eventos WHERE estado = 'rechazado' ORDER BY orden"
            ).fetchall()
        return [fila[0] for fila in filas]

    def clips_pendientes(self) -> list[str]:
        with self._candado:
            filas = self._db.execute("SELECT evento_id FROM clips ORDER BY creado_en").fetchall()
        return [fila[0] for fila in filas]

    def puntos_pendientes(self) -> list[str]:
        with self._candado:
            filas = self._db.execute("SELECT evento_id FROM puntos ORDER BY creado_en").fetchall()
        return [fila[0] for fila in filas]

    @property
    def pendientes(self) -> int:
        return (
            len(self.eventos_pendientes())
            + len(self.clips_pendientes())
            + len(self.puntos_pendientes())
        )

    def movimientos_pendientes(self) -> int:
        carril = self.carril_movimientos
        return len(carril.pendientes()) if carril is not None else 0

    def espera(self) -> float:
        """Seconds until the next attempt of a lane with work is due (0 if one is due now)."""
        with self._candado:
            urgentes, otros = self._eventos_por_carril()
            esperas = [
                espera.restante()
                for espera, trabajo in (
                    (self._urgentes, urgentes),
                    (self._otros, otros),
                    (
                        self._clips,
                        self._db.execute(_CLIPS_LISTOS).fetchone()
                        or self._db.execute(_PUNTOS_LISTOS).fetchone(),
                    ),
                    (self._movimientos, self.movimientos_pendientes()),
                )
                if trabajo
            ]
        return min(esperas, default=0.0)

    # ------------------------------------------------------------------ sending

    def reintentar_ahora(self) -> None:
        for espera in (self._urgentes, self._otros, self._clips, self._movimientos):
            espera.ya()

    def enviar(self, remitente: Remitente) -> Resumen:
        """Sends what is due in each lane, in order; a lane stops at its first temporary failure."""
        with self._candado:
            enviados = subidos = 0
            errores: list[ErrorBackendError] = []
            urgentes, otros = self._eventos_por_carril()
            for espera, filas in ((self._urgentes, urgentes), (self._otros, otros)):
                if not filas or espera.restante() > 0:
                    continue
                try:
                    for evento_id, cuerpo in filas:
                        if self._enviar_evento(remitente, evento_id, cuerpo):
                            enviados += 1
                except ErrorBackendError as error:
                    espera.fallo()
                    errores.append(error)
                else:
                    espera.exito()
            if self._clips.restante() == 0:
                try:
                    for evento_id, archivo, intentos in self._db.execute(_CLIPS_LISTOS).fetchall():
                        if self._subir_clip(remitente, evento_id, archivo, intentos):
                            subidos += 1
                    for evento_id, archivo, intentos in self._db.execute(_PUNTOS_LISTOS).fetchall():
                        self._subir_puntos(remitente, evento_id, archivo, intentos)
                except ErrorBackendError as error:
                    self._clips.fallo()
                    errores.append(error)
                else:
                    self._clips.exito()
            pendientes = self.pendientes
            movimientos = self._enviar_movimientos(remitente, errores, pendientes)
            if errores:
                logger.warning("Envío pendiente (%d en cola): %s", pendientes, errores[0])
            return Resumen(
                enviados,
                subidos,
                pendientes,
                errores[0] if errores else None,
                movimientos,
                self.movimientos_pendientes(),
            )

    def cerrar(self) -> None:
        with self._candado:
            self._db.close()

    def _enviar_movimientos(
        self, remitente: Remitente, errores: list[ErrorBackendError], pendientes: int
    ) -> int:
        """The lowest lane: only when nothing else is waiting (CA-37.2)."""
        carril = self.carril_movimientos
        if carril is None or pendientes or self._movimientos.restante() > 0:
            return 0
        try:
            subidos = carril.subir(cast("RemitenteMovimientos", remitente))
        except ErrorBackendError as error:
            self._movimientos.fallo()
            errores.append(error)
            return 0
        self._movimientos.exito()
        if subidos:
            self._exito()
        return subidos

    # ------------------------------------------------------------------ internals

    def _eventos_por_carril(self) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """Pending events in detection order, split into urgent ones and the others."""
        urgentes: list[tuple[str, str]] = []
        otros: list[tuple[str, str]] = []
        for evento_id, cuerpo in self._db.execute(
            "SELECT evento_id, cuerpo FROM eventos WHERE estado = 'pendiente' ORDER BY orden"
        ).fetchall():
            urgente = json.loads(cuerpo).get("tipo") in URGENTES
            (urgentes if urgente else otros).append((evento_id, cuerpo))
        return urgentes, otros

    def _enviar_evento(self, remitente: Remitente, evento_id: str, cuerpo: str) -> bool:
        evento = EventoAgente.model_validate(json.loads(cuerpo))
        self._db.execute(
            "UPDATE eventos SET intentos = intentos + 1 WHERE evento_id = ?", (evento_id,)
        )
        try:
            _, duplicado = remitente.publicar_evento(evento)
        except ErrorBackendError as error:
            if error.reintentable:
                raise
            logger.error("El backend rechazó el evento %s: %s", evento_id, error)
            self._db.execute(
                "UPDATE eventos SET estado = 'rechazado', ultimo_error = ? WHERE evento_id = ?",
                (str(error), evento_id),
            )
            return False
        # Delivered (a duplicate means an earlier attempt already arrived): the row goes away.
        self._db.execute("DELETE FROM eventos WHERE evento_id = ?", (evento_id,))
        self._exito()
        logger.info("Evento %s enviado%s", evento_id, " (ya estaba)" if duplicado else "")
        return True

    def _subir_clip(
        self, remitente: Remitente, evento_id: str, archivo: str, intentos: int
    ) -> bool:
        ruta = self._directorio_clips / archivo
        if evento_id in self.eventos_rechazados():
            self._descartar_clip(evento_id, ruta, "su evento fue rechazado")
            return False
        try:
            mp4 = ruta.read_bytes()
        except OSError:
            self._descartar_clip(evento_id, ruta, "no se encontró el archivo")
            return False
        self._db.execute(
            "UPDATE clips SET intentos = intentos + 1 WHERE evento_id = ?", (evento_id,)
        )
        try:
            subida = remitente.solicitar_subida_clip(evento_id, len(mp4))
            remitente.subir_clip(subida, mp4)
        except EventoNoEncontradoError:
            self._descartar_clip(evento_id, ruta, "el backend no tiene el evento")
            return False
        except ErrorBackendError as error:
            if intentos + 1 >= MAX_INTENTOS_CLIP:
                self._descartar_clip(evento_id, ruta, f"falló {MAX_INTENTOS_CLIP} veces: {error}")
                return False
            raise
        self._descartar_clip(evento_id, ruta, None)
        self._exito()
        return True

    def _subir_puntos(
        self, remitente: Remitente, evento_id: str, archivo: str, intentos: int
    ) -> None:
        ruta = self._directorio_clips / archivo
        try:
            datos = ruta.read_bytes()
        except OSError:
            self._descartar_puntos(evento_id, ruta, "no se encontró el archivo")
            return
        self._db.execute(
            "UPDATE puntos SET intentos = intentos + 1 WHERE evento_id = ?", (evento_id,)
        )
        try:
            subida = remitente.solicitar_subida_puntos_clip(evento_id)
            remitente.subir_archivo(
                subida.url_subida, subida.cabeceras, datos, "los puntos del clip"
            )
            self._subir_puntos_ligeros(remitente, evento_id, _ligero(ruta))
        except (EventoNoEncontradoError, SinPermisoDeMovimientosError) as error:
            self._descartar_puntos(evento_id, ruta, str(error.codigo))
            return
        except ErrorBackendError as error:
            if not error.reintentable or intentos + 1 >= MAX_INTENTOS_CLIP:
                self._descartar_puntos(evento_id, ruta, str(error))
                return
            raise
        self._descartar_puntos(evento_id, ruta, None)
        self._exito()

    def _subir_puntos_ligeros(self, remitente: Remitente, evento_id: str, ruta: Path) -> None:
        """The light file of a clip's landmarks, right after its Parquet file."""
        try:
            datos = ruta.read_bytes()
        except OSError:
            return  # an older version made none
        try:
            subida = remitente.solicitar_subida_puntos_clip_ligero(evento_id)
        except ErrorBackendError as error:
            if error.estado == 404 and error.codigo is None:
                logger.info("El backend no acepta archivos ligeros: solo se sube el Parquet")
                return
            raise
        remitente.subir_archivo(
            subida.url_subida, subida.cabeceras, datos, "los puntos ligeros del clip"
        )

    def _descartar_puntos(self, evento_id: str, ruta: Path, motivo: str | None) -> None:
        ruta.unlink(missing_ok=True)
        _ligero(ruta).unlink(missing_ok=True)
        self._db.execute("DELETE FROM puntos WHERE evento_id = ?", (evento_id,))
        if motivo is None:
            logger.info("Puntos del clip del evento %s subidos", evento_id)
        else:
            logger.warning("Puntos del clip del evento %s descartados: %s", evento_id, motivo)

    def _descartar_clip(self, evento_id: str, ruta: Path, motivo: str | None) -> None:
        ruta.unlink(missing_ok=True)
        self._db.execute("DELETE FROM clips WHERE evento_id = ?", (evento_id,))
        if motivo is None:
            logger.info("Clip del evento %s subido", evento_id)
        else:
            logger.error("Clip del evento %s descartado: %s", evento_id, motivo)

    def _exito(self) -> None:
        self.ultimo_envio = self._reloj()

    def aplazar(self) -> None:
        """One more failure in a row in every lane (an unexpected error of a whole pass)."""
        for espera in (self._urgentes, self._otros, self._clips, self._movimientos):
            espera.fallo()

    def _limpiar_huerfanos(self) -> None:
        conocidos: set[str] = set()
        for (archivo,) in self._db.execute(
            "SELECT archivo FROM clips UNION SELECT archivo FROM puntos"
        ).fetchall():
            conocidos.add(archivo)
            if (ligero := ruta_ligera(archivo)) is not None:
                conocidos.add(ligero)
        for archivo in self._directorio_clips.iterdir():
            if archivo.name not in conocidos:
                archivo.unlink(missing_ok=True)


def _ligero(parquet: Path) -> Path:
    """``<eventoId>.puntos.parquet`` → ``<eventoId>.puntos.ttmov``."""
    return parquet.with_name(ruta_ligera(parquet.name) or f"{parquet.name}.ttmov")


class EnviadorPendientes:
    """Worker thread that empties the outbox: right away when notified, otherwise on backoff."""

    def __init__(
        self,
        cola: ColaEnvios,
        remitente: Remitente,
        al_terminar: Callable[[Resumen], None] | None = None,
    ) -> None:
        self._cola = cola
        self._remitente = remitente
        self._al_terminar = al_terminar
        self._despertar = threading.Event()
        self._detenido = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, name="envios", daemon=True)

    def iniciar(self) -> None:
        self._hilo.start()

    def notificar(self) -> None:
        """New items or «Reintentar ahora»: try at once."""
        self._despertar.set()

    def reintentar_ahora(self) -> None:
        self._cola.reintentar_ahora()
        self.notificar()

    def detener(self, espera_s: float = 5.0) -> None:
        self._detenido.set()
        self._despertar.set()
        if self._hilo.is_alive():
            self._hilo.join(espera_s)

    def _bucle(self) -> None:
        while not self._detenido.is_set():
            self._despertar.clear()
            try:
                resumen = self._cola.enviar(self._remitente)
            except Exception:  # never let the sender die: the next pass may succeed
                logger.exception("Error inesperado al enviar la cola")
                resumen = Resumen(0, 0, self._cola.pendientes, ErrorBackendError("inesperado"))
                self._cola.aplazar()
            if self._al_terminar is not None:
                self._al_terminar(resumen)
            hay = resumen.pendientes or resumen.movimientos_pendientes
            espera = self._cola.espera() if hay else None
            self._despertar.wait(espera)
