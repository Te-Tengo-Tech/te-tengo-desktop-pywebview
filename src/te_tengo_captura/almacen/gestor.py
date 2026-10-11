"""What the PC keeps (US-38) and only with the movement consent (US-35): «Almacenamiento».

* **The folder** is the person's choice (by default ``Datos`` in the platform's data directory,
  e.g. ``%LOCALAPPDATA%\\TeTengoCaptura\\Datos``); «Cambiar carpeta» moves everything in a
  background thread while detection goes on (CA-38.1).
* **Per type** (CA-38.1): movements (body landmarks, never images), continuous video and the
  clips of the alerts, each with a switch and a period (7 días … «Nunca borrar»), plus a space
  limit. Defaults follow the prototype: movements on for 90 days, clips on and never deleted,
  continuous video **off** (CA-38.2), a 50 GB limit.
* **Movements** (``puntos.py``): every analysed frame of a camera, the 33 points quantized with
  the classifier's θ, P, v, phase and event, one Parquet+zstd file per camera every 5 minutes.
  Only with the movement consent (``GET /api/agente/movimientos/estado``, at start and every 5
  minutes, CA-35.3); when it is revoked nothing more is stored and the window asks whether to
  delete what this PC kept (CA-35.4).
* **Continuous video** (CA-38.2): the 480p, 8 fps frames the classifier sees, H.264 in 10-minute
  fragmented MP4 segments, encrypted as they are written; never uploaded.
* **Clips:** a local copy of each alert's 12-second clip (the upload copy is the outbox's).
* **Encryption at rest** (CA-38.4): every file is AES-256-GCM (``cifrado.py``) with a key kept in
  the OS credential store; no plaintext touches the disk.
* **The space limit** (CA-38.3): before each file, the oldest video and then the oldest
  movements are deleted to make room (clips only by their period); if there is still no room,
  or the folder is gone or the disk is full (CA-38.5), the file is skipped and the window says
  what to check. **Detection never waits for storage**: the capture thread only queues rows and
  frames; a writer thread per camera encodes, encrypts and writes them, dropping frames when it
  is behind.
* **The index** (``indice.py``, SQLite in the folder) knows every file by camera, type and time:
  retention, the space limit, the replay (US-39) and the cloud upload (US-37) only read it.
"""

import contextlib
import json
import logging
import queue
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

from te_tengo_captura.almacen.cifrado import (
    AlmacenCredenciales,
    ClaveDatos,
    EscritorCifrado,
    cifrar_bytes,
)
from te_tengo_captura.almacen.indice import IndiceArchivos, TipoArchivo
from te_tengo_captura.almacen.puntos import FilaMovimiento, TramoCerrado, TramoMovimientos, a_ms
from te_tengo_captura.almacen.retencion import (
    Politica,
    ReglaTipo,
    aplicar_retencion,
    liberar_espacio,
)
from te_tengo_captura.backend.errores import ErrorBackendError
from te_tengo_captura.backend.modelos import EstadoMovimientos
from te_tengo_captura.captura.bucle import Analisis

logger = logging.getLogger(__name__)

GB = 1_000_000_000
REVISION_PERMISO_S = 300.0  # contract: ask every 5 minutes
REVISION_RETENCION_S = 3600.0
SEGMENTO_VIDEO_S = 600.0  # CA-38.2: 10-minute parts
FPS_VIDEO = 8
COLA_FOTOGRAMAS = 16  # frames waiting for the video writer (2 s): older ones are dropped
CERCA_DEL_LIMITE = 0.9  # «Queda poco espacio» from 90 % of the limit
ARCHIVO_AJUSTES = "almacenamiento.json"
INDICE = "indice.sqlite3"
EXTENSION = ".ttg"


@dataclass(frozen=True, slots=True)
class AjustesAlmacen:
    """The «Almacenamiento» choices (``None`` days: «Nunca borrar»)."""

    carpeta: str | None = None
    movimientos: bool = True
    dias_movimientos: int | None = 90
    video: bool = False
    dias_video: int | None = 7
    clips: bool = True
    dias_clips: int | None = None
    limite_gb: float = 50.0

    def politica(self) -> Politica:
        return Politica(
            movimientos=ReglaTipo(self.movimientos, self.dias_movimientos),
            video=ReglaTipo(self.video, self.dias_video),
            clip=ReglaTipo(self.clips, self.dias_clips),
            limite_bytes=int(self.limite_gb * GB),
        )


def texto_dias(dias: int | None) -> str:
    """«90 días», «1 año», «Nunca borrar» (the prototype's period pills)."""
    if dias is None:
        return "Nunca borrar"
    if dias == 365:
        return "1 año"
    return f"{dias} día" if dias == 1 else f"{dias} días"


@dataclass(frozen=True, slots=True)
class Cambio:
    """One setting changed on this PC, for the activity log (``GUARDADO_LOCAL_CAMBIADO``)."""

    texto: str
    objeto: str
    anterior: str
    nuevo: str


class AlmacenLocal:
    def __init__(
        self,
        directorio_ajustes: Path,
        carpeta_predeterminada: Path,
        llavero: AlmacenCredenciales | None = None,
        reloj_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ruta_ajustes = directorio_ajustes / ARCHIVO_AJUSTES
        self._predeterminada = carpeta_predeterminada
        self._clave = ClaveDatos(llavero)
        self._reloj_utc = reloj_utc
        self._reloj = reloj
        self._candado = threading.RLock()
        self.ajustes = self._leer_ajustes()
        self._indice: IndiceArchivos | None = None
        self.permiso: EstadoMovimientos | None = None
        self._consultar: Callable[[], EstadoMovimientos] | None = None
        self.revocado = False  # the consent ended: the window asks whether to delete (CA-35.4)
        self.problema: str | None = None  # "lleno" (CA-38.5) or "sin_clave"
        self.liberado: str | None = None  # «Borramos el video del 01/10 …» (CA-38.3)
        self.moviendo: float | None = None  # bytes being moved to a new folder
        self.al_movimientos: list[Callable[[str, int], None]] = []  # (camera, index id): US-37
        self._grabadores: dict[str, GrabadorCamara] = {}
        self._detenido = threading.Event()
        self._despertar = threading.Event()
        self._pedir_permiso = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="almacen", daemon=True)

    # ------------------------------------------------------------------ lifecycle

    @property
    def carpeta(self) -> Path:
        return Path(self.ajustes.carpeta) if self.ajustes.carpeta else self._predeterminada

    def iniciar(self, consultar_permiso: Callable[[], EstadoMovimientos] | None) -> None:
        self._consultar = consultar_permiso
        self._abrir_indice()
        self._hilo.start()

    def detener(self) -> None:
        self._detenido.set()
        self._despertar.set()
        with self._candado:
            grabadores, self._grabadores = list(self._grabadores.values()), {}
        for grabador in grabadores:
            grabador.cerrar()
        if self._hilo.is_alive() and self._hilo is not threading.current_thread():
            self._hilo.join(5.0)
        if self._indice is not None:
            self._indice.cerrar()
            self._indice = None

    @property
    def indice(self) -> IndiceArchivos | None:
        return self._indice

    def clave(self) -> bytes | None:
        """The data key from the OS credential store; ``None`` if it cannot be used."""
        try:
            return self._clave.obtener()
        except Exception as error:
            if self.problema != "sin_clave":
                logger.error("No se puede usar la clave de los datos (%s)", type(error).__name__)
            self.problema = "sin_clave"
            return None

    # ------------------------------------------------------------------ cameras

    def para_camara(self, camara_id: str) -> "GrabadorCamara":
        with self._candado:
            grabador = self._grabadores.get(camara_id)
            if grabador is None:
                grabador = GrabadorCamara(self, camara_id)
                self._grabadores[camara_id] = grabador
            return grabador

    def soltar_camara(self, camara_id: str) -> None:
        with self._candado:
            grabador = self._grabadores.pop(camara_id, None)
        if grabador is not None:
            grabador.cerrar()

    def guarda(self, tipo: TipoArchivo) -> bool:
        a = self.ajustes
        if tipo is TipoArchivo.MOVIMIENTOS:
            return a.movimientos and self.puede_movimientos
        if tipo is TipoArchivo.VIDEO:
            return a.video
        return a.clips

    @property
    def puede_movimientos(self) -> bool:
        """Only with the movement consent (CA-35.3)."""
        permiso = self.permiso
        return permiso is not None and permiso.guardar_en_la_pc

    # ------------------------------------------------------------------ writing (writer threads)

    def guardar(
        self,
        tipo: TipoArchivo,
        camara_id: str,
        desde_ms: int,
        hasta_ms: int,
        relativa: str,
        escribir: Callable[[Path, bytes], int],
        tamano_estimado: int,
    ) -> int | None:
        """Makes room, writes one encrypted file and indexes it; ``None`` if it was skipped."""
        clave = self.clave()
        indice = self._indice
        if clave is None or indice is None:
            return None
        if not self._hacer_lugar(tamano_estimado):
            return None
        destino = self.carpeta / relativa
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            tamano = escribir(destino, clave)
        except OSError as error:
            if self.problema != "lleno":
                logger.error("No se pudo guardar en la carpeta de datos: %s", error)
            self.problema = "lleno"
            return None
        if self.problema == "lleno":
            logger.info("La carpeta de datos vuelve a aceptar archivos")
        self.problema = None
        return indice.registrar(
            tipo=tipo,
            camara_id=camara_id,
            desde_ms=desde_ms,
            hasta_ms=hasta_ms,
            ruta=relativa,
            tamano_bytes=tamano,
        )

    def _hacer_lugar(self, necesarios: int) -> bool:
        indice = self._indice
        if indice is None:
            return False
        liberacion = liberar_espacio(
            indice, self.ajustes.politica(), necesarios, self._borrar_archivo
        )
        videos = [b.archivo for b in liberacion.borrados if b.archivo.tipo is TipoArchivo.VIDEO]
        if videos:
            dia = datetime.fromtimestamp(videos[0].desde_ms / 1000, UTC).astimezone()
            self.liberado = f"{dia:%d/%m}"
            logger.info("Se borró el video más antiguo (%s) para liberar espacio", self.liberado)
        if not liberacion.suficiente:
            if self.problema != "limite":
                logger.warning("No hay espacio dentro del límite: no se guarda este archivo")
            return False
        return True

    def _borrar_archivo(self, relativa: str) -> None:
        (self.carpeta / relativa).unlink(missing_ok=True)

    # ------------------------------------------------------------------ settings

    def cambiar(self, **cambios: Any) -> list[Cambio]:
        """Applies the window's changes; returns what changed for the activity log."""
        with self._candado:
            antes = self.ajustes
            despues = replace(antes, **cambios)
            if despues == antes:
                return []
            self.ajustes = despues
            self._guardar_ajustes()
        registro = _cambios(antes, despues)
        self._despertar.set()  # retention and the limit apply now
        return registro

    def mover_carpeta(self, nueva: Path, al_terminar: Callable[[bool], None]) -> None:
        """«Cambiar carpeta»: moves every file while detection goes on."""

        def mover() -> None:
            ok = True
            origen = self.carpeta
            with self._candado:
                uso = sum(self.uso().values())
                self.moviendo = float(uso)
            try:
                nueva.mkdir(parents=True, exist_ok=True)
                if self._indice is not None:
                    self._indice.cerrar()
                    self._indice = None
                for ruta in sorted(origen.rglob("*")) if origen.exists() else []:
                    if ruta.is_file():
                        destino = nueva / ruta.relative_to(origen)
                        destino.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(ruta), str(destino))
                with self._candado:
                    self.ajustes = replace(self.ajustes, carpeta=str(nueva))
                    self._guardar_ajustes()
                shutil.rmtree(origen, ignore_errors=True)
            except OSError as error:
                logger.error("No se pudo mover la carpeta de datos: %s", error)
                ok = False
            finally:
                self._abrir_indice()
                self.moviendo = None
            al_terminar(ok)

        threading.Thread(target=mover, name="mover-carpeta", daemon=True).start()

    # ------------------------------------------------------------------ deleting

    def borrar_tipo(self, tipo: TipoArchivo) -> int:
        """«Borrar» the movements after a revocation (CA-35.4); returns the bytes deleted."""
        indice = self._indice
        if indice is None:
            return 0
        borrados = 0
        for archivo in indice.anteriores_a(tipo, 2**62):
            self._borrar_archivo(archivo.ruta)
            indice.borrar(archivo.id)
            borrados += archivo.tamano_bytes
        self.revocado = False
        return borrados

    def borrar_todo(self) -> None:
        """«Borrar también los datos guardados en esta PC» (CA-31.6): the folder and its key."""
        self.detener()
        shutil.rmtree(self.carpeta, ignore_errors=True)
        try:
            self._clave.borrar()
        except Exception:
            logger.debug("No había clave de datos que borrar")

    def conservar(self) -> None:
        """«Conservar» after a revocation: the files stay, nothing new is stored."""
        self.revocado = False

    # ------------------------------------------------------------------ state

    def uso(self) -> dict[TipoArchivo, int]:
        indice = self._indice
        if indice is None:
            return dict.fromkeys(TipoArchivo, 0)
        uso = indice.uso_por_tipo()
        return {tipo: uso.get(tipo, 0) for tipo in TipoArchivo}

    def estado(self) -> dict[str, Any]:
        """What «Almacenamiento» shows."""
        uso = self.uso()
        total = sum(uso.values())
        limite = int(self.ajustes.limite_gb * GB)
        estado: str | None = None
        if self.moviendo is not None:
            estado = "moviendo"
        elif self.problema in ("lleno", "sin_clave"):
            estado = "lleno"
        elif self.liberado is not None:
            estado = "limite"
        elif total >= CERCA_DEL_LIMITE * limite:
            estado = "cerca"
        permiso = self.permiso
        return {
            "carpeta": str(self.carpeta),
            "uso": {
                "movimientos": uso[TipoArchivo.MOVIMIENTOS],
                "video": uso[TipoArchivo.VIDEO],
                "clips": uso[TipoArchivo.CLIP],
            },
            "limite": limite,
            "estado": estado,
            "liberado": self.liberado,
            "ajustes": asdict(self.ajustes),
            "permisoMovimientos": self.puede_movimientos,
            "nube": permiso.retencion_dias
            if permiso is not None and permiso.guardar_en_la_nube
            else None,
            "revocado": self.revocado,
            "hayVideo": uso[TipoArchivo.VIDEO] > 0,
        }

    # ------------------------------------------------------------------ internals

    def _abrir_indice(self) -> None:
        try:
            self.carpeta.mkdir(parents=True, exist_ok=True)
            self._indice = IndiceArchivos(self.carpeta / INDICE)
        except (OSError, Exception) as error:
            logger.error("No se pudo abrir la carpeta de datos %s: %s", self.carpeta, error)
            self.problema = "lleno"
            self._indice = None

    def _leer_ajustes(self) -> AjustesAlmacen:
        try:
            datos = json.loads(self._ruta_ajustes.read_text(encoding="utf-8"))
            return AjustesAlmacen(
                **{k: v for k, v in datos.items() if k in AjustesAlmacen.__dataclass_fields__}
            )
        except (OSError, ValueError, TypeError):
            return AjustesAlmacen()

    def _guardar_ajustes(self) -> None:
        try:
            self._ruta_ajustes.parent.mkdir(parents=True, exist_ok=True)
            temporal = self._ruta_ajustes.with_suffix(".tmp")
            temporal.write_text(json.dumps(asdict(self.ajustes)), encoding="utf-8")
            temporal.replace(self._ruta_ajustes)
        except OSError as error:
            logger.warning("No se pudieron guardar los ajustes del almacenamiento: %s", error)

    def pedir_permiso(self) -> None:
        """Asks for the movement consent now (the PC or the camera just started), not in 5 min."""
        self._pedir_permiso.set()
        self._despertar.set()

    def revisar_permiso(self) -> None:
        consultar = self._consultar
        if consultar is None:
            return
        try:
            permiso = consultar()
        except ErrorBackendError as error:
            logger.info("No se pudo consultar el permiso de movimientos: %s", error)
            return
        antes = self.puede_movimientos
        self.permiso = permiso
        if antes and not permiso.guardar_en_la_pc:
            logger.warning("Se revocó el permiso de guardar movimientos: no se guardan más")
            self.revocado = TipoArchivo.MOVIMIENTOS in {t for t, b in self.uso().items() if b > 0}

    def _correr(self) -> None:
        proximo_permiso = proxima_retencion = 0.0
        while not self._detenido.is_set():
            ahora = self._reloj()
            if ahora >= proximo_permiso or self._pedir_permiso.is_set():
                self._pedir_permiso.clear()
                self.revisar_permiso()
                proximo_permiso = ahora + REVISION_PERMISO_S
            if ahora >= proxima_retencion or self._despertar.is_set():
                self._despertar.clear()
                indice = self._indice
                if indice is not None:
                    try:
                        aplicar_retencion(
                            indice,
                            self.ajustes.politica(),
                            a_ms(self._reloj_utc()),
                            self._borrar_archivo,
                        )
                        self._hacer_lugar(0)
                    except Exception:
                        logger.exception("Error al aplicar el plazo de los datos guardados")
                proxima_retencion = ahora + REVISION_RETENCION_S
            self._despertar.wait(min(60.0, proximo_permiso - self._reloj()))


def _cambios(antes: AjustesAlmacen, despues: AjustesAlmacen) -> list[Cambio]:
    """«Desde esta PC: …» sentences of the prototype for each changed setting."""
    cambios: list[Cambio] = []
    si_no = {True: "Sí", False: "No"}
    for campo, dias, nombre, objeto in (
        ("movimientos", "dias_movimientos", "los movimientos", "Movimientos"),
        ("video", "dias_video", "el video continuo", "Video continuo"),
        ("clips", "dias_clips", "los clips", "Clips de los avisos"),
    ):
        a, d = getattr(antes, campo), getattr(despues, campo)
        if a != d:
            verbo = "se activó" if d else "se desactivó"
            articulo = "el guardado de " if campo != "video" else ""
            cosa = nombre.replace("los ", "").replace("el ", "") if campo != "video" else nombre
            cambios.append(
                Cambio(
                    f"Desde esta PC: {verbo} {articulo}{cosa}",
                    objeto,
                    si_no[a] + (f", {texto_dias(getattr(antes, dias))}" if a else ""),
                    si_no[d] + (f", {texto_dias(getattr(despues, dias))}" if d else ""),
                )
            )
        a_d, d_d = getattr(antes, dias), getattr(despues, dias)
        if a_d != d_d:
            cambios.append(
                Cambio(
                    f"Desde esta PC: {nombre} {'pasó' if campo == 'video' else 'pasaron'} de "
                    f"{texto_dias(a_d)} a {texto_dias(d_d)}",
                    objeto,
                    texto_dias(a_d),
                    texto_dias(d_d),
                )
            )
    if antes.limite_gb != despues.limite_gb:
        a_t, d_t = f"{antes.limite_gb:g} GB", f"{despues.limite_gb:g} GB"
        cambios.append(
            Cambio(
                f"Desde esta PC: el límite de espacio pasó de {a_t} a {d_t}",
                "Límite de espacio",
                a_t,
                d_t,
            )
        )
    if antes.carpeta != despues.carpeta:
        cambios.append(
            Cambio("Desde esta PC: se cambió la carpeta de los datos", "Carpeta", "", "")
        )
    return cambios


class GrabadorCamara:
    """What one camera stores, written off the capture thread (it only queues)."""

    def __init__(self, almacen: AlmacenLocal, camara_id: str) -> None:
        self._almacen = almacen
        self._camara_id = camara_id
        self._tramo = TramoMovimientos(camara_id)
        self._cola: queue.Queue[tuple[str, Any] | None] = queue.Queue(maxsize=256)
        self._video: _SegmentoVideo | None = None
        self.descartados = 0
        self._hilo = threading.Thread(
            target=self._correr, name=f"guardar-{camara_id[:8]}", daemon=True
        )
        self._hilo.start()

    # ------------------------------------------------------------------ capture thread

    def analizado(self, analisis: Analisis) -> None:
        """A ``BucleCaptura`` observer: queues the movement row and the video frame."""
        almacen = self._almacen
        if almacen.guarda(TipoArchivo.MOVIMIENTOS):
            self._poner(("fila", _fila(analisis)))
        if almacen.guarda(TipoArchivo.VIDEO):
            self._poner(("video", (analisis.ocurrido_en, analisis.fotograma.imagen)))
        elif self._video is not None:
            self._poner(("cerrar_video", None))

    def clip(self, evento_id: str, ocurrido_en: datetime, mp4: bytes) -> None:
        """A local copy of an alert's clip (the outbox keeps its own copy for the upload)."""
        if self._almacen.guarda(TipoArchivo.CLIP):
            self._poner(("clip", (evento_id, ocurrido_en, mp4)))

    def cerrar(self) -> None:
        with contextlib.suppress(queue.Full):
            self._cola.put(None, timeout=1.0)
        self._hilo.join(10.0)

    def _poner(self, elemento: tuple[str, Any]) -> None:
        try:
            self._cola.put_nowait(elemento)
        except queue.Full:
            self.descartados += 1  # behind: storage never slows detection down

    # ------------------------------------------------------------------ writer thread

    def _correr(self) -> None:
        while True:
            elemento = self._cola.get()
            if elemento is None:
                break
            tipo, datos = elemento
            try:
                if tipo == "fila":
                    for tramo in self._tramo.agregar(datos):
                        self._escribir_tramo(tramo)
                elif tipo == "video":
                    self._video_fotograma(*datos)
                elif tipo == "cerrar_video":
                    self._cerrar_video()
                elif tipo == "clip":
                    self._escribir_clip(*datos)
            except Exception:
                logger.exception("Error al guardar datos de la cámara")
        for tramo in self._tramo.cerrar():
            self._escribir_tramo(tramo)
        self._cerrar_video()

    def _escribir_tramo(self, tramo: TramoCerrado) -> None:
        if not self._almacen.puede_movimientos:
            return  # the consent ended while the window was open (CA-35.4)
        momento = tramo.desde
        relativa = (
            f"movimientos/{self._camara_id}/{momento:%Y/%m/%d}/{momento:%H%M%S}.parquet{EXTENSION}"
        )

        def escribir(destino: Path, clave: bytes) -> int:
            cifrado = cifrar_bytes(clave, tramo.datos)
            temporal = destino.with_suffix(".tmp")
            temporal.write_bytes(cifrado)
            temporal.replace(destino)
            return len(cifrado)

        archivo_id = self._almacen.guardar(
            TipoArchivo.MOVIMIENTOS,
            self._camara_id,
            tramo.desde_ms,
            tramo.hasta_ms,
            relativa,
            escribir,
            len(tramo.datos),
        )
        if archivo_id is not None:
            logger.info(
                "Movimientos guardados: %d filas, %d bytes", tramo.n_filas, len(tramo.datos)
            )
            for oyente in list(self._almacen.al_movimientos):
                oyente(self._camara_id, archivo_id)

    def _escribir_clip(self, evento_id: str, ocurrido_en: datetime, mp4: bytes) -> None:
        relativa = f"clips/{self._camara_id}/{ocurrido_en:%Y/%m/%d}/{evento_id}.mp4{EXTENSION}"
        desde = a_ms(ocurrido_en) - 6000

        def escribir(destino: Path, clave: bytes) -> int:
            cifrado = cifrar_bytes(clave, mp4)
            destino.write_bytes(cifrado)
            return len(cifrado)

        self._almacen.guardar(
            TipoArchivo.CLIP, self._camara_id, desde, desde + 12000, relativa, escribir, len(mp4)
        )

    def _video_fotograma(self, ocurrido_en: datetime, imagen: Any) -> None:
        segmento = self._video
        if segmento is not None and segmento.lleno(ocurrido_en):
            self._cerrar_video()
            segmento = None
        if segmento is None:
            clave = self._almacen.clave()
            if clave is None or not self._almacen._hacer_lugar(int(0.06 * GB)):
                return
            segmento = _SegmentoVideo(self._almacen.carpeta, self._camara_id, ocurrido_en, clave)
            self._video = segmento
        segmento.agregar(ocurrido_en, imagen)

    def _cerrar_video(self) -> None:
        segmento, self._video = self._video, None
        if segmento is None:
            return
        cerrado = segmento.cerrar()
        indice = self._almacen.indice
        if cerrado is not None and indice is not None:
            relativa, desde_ms, hasta_ms, tamano = cerrado
            indice.registrar(
                tipo=TipoArchivo.VIDEO,
                camara_id=self._camara_id,
                desde_ms=desde_ms,
                hasta_ms=hasta_ms,
                ruta=relativa,
                tamano_bytes=tamano,
            )


class _SegmentoVideo:
    """A 10-minute H.264 segment, fragmented MP4 written straight into the encrypted file."""

    def __init__(self, carpeta: Path, camara_id: str, inicio: datetime, clave: bytes) -> None:
        import av

        self._inicio = inicio
        self._relativa = f"video/{camara_id}/{inicio:%Y/%m/%d}/{inicio:%H%M%S}.mp4{EXTENSION}"
        destino = carpeta / self._relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        self._escritor = EscritorCifrado(clave, destino)
        self._contenedor: Any = av.open(
            self._escritor,
            mode="w",
            format="mp4",
            options={"movflags": "frag_keyframe+empty_moov+default_base_moof"},
        )
        self._flujo: Any = None
        self._ultimo: datetime = inicio
        self._n = 0

    def lleno(self, ahora: datetime) -> bool:
        return (ahora - self._inicio).total_seconds() >= SEGMENTO_VIDEO_S

    def agregar(self, ahora: datetime, imagen: Any) -> None:
        import av

        alto, ancho = imagen.shape[:2]
        if self._flujo is None:
            flujo = self._contenedor.add_stream("libx264", rate=FPS_VIDEO)
            flujo.width, flujo.height = ancho // 2 * 2, alto // 2 * 2
            flujo.pix_fmt = "yuv420p"
            flujo.time_base = Fraction(1, 1000)
            flujo.options = {"preset": "veryfast", "crf": "28", "g": str(FPS_VIDEO * 2)}
            self._flujo = flujo
        cuadro = av.VideoFrame.from_ndarray(
            imagen[: self._flujo.height, : self._flujo.width], format="bgr24"
        )
        cuadro.pts = max(self._n, int((ahora - self._inicio).total_seconds() * 1000))
        cuadro.time_base = Fraction(1, 1000)
        self._n = cuadro.pts + 1
        for paquete in self._flujo.encode(cuadro):
            self._contenedor.mux(paquete)
        self._ultimo = ahora

    def cerrar(self) -> tuple[str, int, int, int] | None:
        try:
            if self._flujo is not None:
                for paquete in self._flujo.encode():
                    self._contenedor.mux(paquete)
            self._contenedor.close()
            self._escritor.close()
        except Exception:
            logger.exception("No se pudo cerrar el segmento de video")
            self._escritor.abortar()
            return None
        if self._flujo is None:
            self._escritor.abortar()
            return None
        return (
            self._relativa,
            a_ms(self._inicio),
            a_ms(self._ultimo) + 1,
            self._escritor.ruta.stat().st_size,
        )


def _fila(analisis: Analisis) -> FilaMovimiento:
    pose = analisis.pose
    medicion = analisis.clasificador.ultima_medicion
    actual = medicion is not None and medicion.instante == analisis.fotograma.instante
    evento = analisis.eventos[0].tipo if analisis.eventos else None
    return FilaMovimiento(
        t_ms=a_ms(analisis.ocurrido_en),
        landmarks=(
            [(lm.x, lm.y, lm.z, lm.visibilidad) for lm in pose.landmarks]
            if pose is not None
            else None
        ),
        theta=medicion.parametros.angulo_grados if actual and medicion else None,
        p=medicion.parametros.razon_ancho_alto if actual and medicion else None,
        v=medicion.velocidad if actual and medicion else None,
        fase=analisis.clasificador.fase,
        evento=evento,
    )
