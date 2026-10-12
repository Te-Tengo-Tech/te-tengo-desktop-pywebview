"""«Ver qué pasó» on the PC (US-39, CA-39.2): the movements kept here, replayed as a skeleton.

* **Only from this PC's folder** and only with the movement consent (CA-39.4); nothing is sent.
* **A window** of 10 minutes or 1 hour: its events (the fall, the unstable movement and the
  recovery, as the classifier wrote them in each row), its stretches without data and why
  (CA-39.5: nobody in the image, or no capture at all: the PC off or the camera paused) and
  whether continuous video exists for it.
* **Poses** in chunks (the window can hold 28 800 rows): the 13 joints the skeleton draws, in
  image units, and a phase code per row («De pie», «Movimiento inestable», «Posible caída»,
  «En el suelo», «… caída confirmada», «Se levantó»).
* **Video** (CA-39.2): with continuous video kept here, a JPEG of the frame at a time, decoded
  from the encrypted segment in memory. The video never leaves the PC.
* Decrypted files are kept in memory only while the replay is open (a few at a time).
"""

import io
import logging
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, tzinfo
from itertools import pairwise
from typing import Any, cast

from te_tengo_captura.almacen.gestor import AlmacenLocal
from te_tengo_captura.almacen.indice import Archivo, TipoArchivo
from te_tengo_captura.almacen.puntos import FilaMovimiento, instante_ms, leer_parquet
from te_tengo_deteccion.clasificacion.estados import Fase, TipoEvento

logger = logging.getLogger(__name__)

# The skeleton's joints (the same keys as the meters, ``diario.ARTICULACIONES``).
ARTICULACIONES = (
    ("h", 0),
    ("sL", 11),
    ("sR", 12),
    ("eL", 13),
    ("eR", 14),
    ("wL", 15),
    ("wR", 16),
    ("hL", 23),
    ("hR", 24),
    ("kL", 25),
    ("kR", 26),
    ("aL", 27),
    ("aR", 28),
)
VENTANA_MAXIMA_MS = 60 * 60 * 1000
HUECO_MINIMO_MS = 5_000  # shorter stretches without data are not marked
INESTABLE_MS = 4_000  # «Movimiento inestable» around its event
LEVANTO_MS = 12_000  # «Se levantó» after the recovery
ARCHIVOS_EN_MEMORIA = 12

# Phase codes for the window (``rpPose`` of the prototype).
DE_PIE, INESTABLE, POSIBLE_CAIDA, EN_EL_SUELO, CONFIRMADA, SE_LEVANTO = range(6)
MARCAS = {
    TipoEvento.CAIDA: ("caida", "Caída"),
    TipoEvento.MOVIMIENTO_INESTABLE: ("inestable", "Inestable"),
    TipoEvento.RECUPERACION: ("calma", "Se levantó"),
}
SIN_PERSONA = ("Sin persona en la imagen", "Sin persona")
SIN_CAPTURA = ("PC apagada o cámara en pausa", "Sin captura")


@dataclass(frozen=True, slots=True)
class Hueco:
    desde_ms: int
    hasta_ms: int
    motivo: str
    corto: str


class Repeticion:
    def __init__(
        self,
        almacen: AlmacenLocal,
        zona: tzinfo | None = None,
        reloj_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._almacen = almacen
        self._zona = zona
        self._reloj_utc = reloj_utc
        self._candado = threading.Lock()
        self._filas: OrderedDict[int, list[FilaMovimiento]] = OrderedDict()
        self._videos: OrderedDict[int, _LectorVideo] = OrderedDict()

    # ------------------------------------------------------------------ what there is

    @property
    def permitida(self) -> bool:
        """Only with the movement consent (CA-39.4)."""
        return self._almacen.puede_movimientos

    def datos_desde(self, camara_id: str) -> int | None:
        indice = self._almacen.indice
        if indice is None:
            return None
        return indice.disponibles_desde(camara_id, TipoArchivo.MOVIMIENTOS)

    def datos_hasta(self, camara_id: str) -> int | None:
        """End of the newest movements of the camera (epoch ms)."""
        indice = self._almacen.indice
        if indice is None:
            return None
        archivos = indice.en_rango(camara_id, TipoArchivo.MOVIMIENTOS, 0, 2**62)
        return max((a.hasta_ms for a in archivos), default=None)

    def dias(self, camara_id: str) -> list[date]:
        """Days with movements of the camera (in the PC's time zone), newest first."""
        indice = self._almacen.indice
        if indice is None:
            return []
        vistos: set[date] = set()
        for archivo in indice.en_rango(camara_id, TipoArchivo.MOVIMIENTOS, 0, 2**62):
            for borde in (archivo.desde_ms, archivo.hasta_ms - 1):
                vistos.add(self._local(borde).date())
        return sorted(vistos, reverse=True)

    def abrir(self, camara_id: str, desde_ms: int, hasta_ms: int) -> dict[str, Any]:
        """A window: its events, its stretches without data and whether there is video."""
        hasta_ms = min(hasta_ms, desde_ms + VENTANA_MAXIMA_MS)
        filas = self._filas_de(camara_id, desde_ms - 1, hasta_ms)
        eventos = [
            {"t": f.t_ms, "k": MARCAS[f.evento][0], "l": MARCAS[f.evento][1]}
            for f in filas
            if f.evento in MARCAS and desde_ms <= f.t_ms <= hasta_ms
        ]
        return {
            "desde": desde_ms,
            "hasta": hasta_ms,
            "hayDatos": any(f.landmarks is not None for f in filas),
            "eventos": eventos,
            "huecos": [
                {"a": h.desde_ms, "b": h.hasta_ms, "motivo": h.motivo, "corto": h.corto}
                for h in self.huecos(camara_id, desde_ms, hasta_ms)
            ],
            "video": self._hay_video(camara_id, desde_ms, hasta_ms),
        }

    def huecos(self, camara_id: str, desde_ms: int, hasta_ms: int) -> list[Hueco]:
        """Stretches without data (CA-39.5): nobody in the image, or no capture at all."""
        indice = self._almacen.indice
        cubiertos = (
            [
                (a.desde_ms, a.hasta_ms)
                for a in indice.en_rango(camara_id, TipoArchivo.MOVIMIENTOS, desde_ms, hasta_ms)
            ]
            if indice is not None
            else []
        )
        filas = self._filas_de(camara_id, desde_ms, hasta_ms)
        huecos: list[Hueco] = []

        def agregar(a: int, b: int, motivo: tuple[str, str]) -> None:
            a, b = max(a, desde_ms), min(b, hasta_ms)
            if b - a < HUECO_MINIMO_MS:
                return
            if huecos and huecos[-1].corto == motivo[1] and a - huecos[-1].hasta_ms < 2_000:
                huecos[-1] = Hueco(huecos[-1].desde_ms, b, *motivo)
            else:
                huecos.append(Hueco(a, b, *motivo))

        # No file, or a pause inside a file (no rows for a while): no capture.
        momentos = sorted({f.t_ms for f in filas})
        cursor = desde_ms
        for a, b in sorted(cubiertos):
            agregar(cursor, a, SIN_CAPTURA)
            cursor = max(cursor, b)
        agregar(cursor, hasta_ms, SIN_CAPTURA)
        for anterior, siguiente in pairwise(momentos):
            if siguiente - anterior > 2_000:
                agregar(anterior + 1, siguiente, SIN_CAPTURA)
        # Rows without a person.
        inicio: int | None = None
        for fila in filas:
            if fila.landmarks is None:
                inicio = fila.t_ms if inicio is None else inicio
            elif inicio is not None:
                agregar(inicio, fila.t_ms, SIN_PERSONA)
                inicio = None
        if inicio is not None and filas:
            agregar(inicio, filas[-1].t_ms + 1, SIN_PERSONA)
        return sorted(huecos, key=lambda h: h.desde_ms)

    def poses(self, camara_id: str, desde_ms: int, hasta_ms: int) -> dict[str, Any]:
        """The skeleton of each row in ``[desde_ms, hasta_ms]`` and its phase code."""
        contexto = self._filas_de(camara_id, desde_ms - 60_000, hasta_ms)
        fases = _fases(contexto)
        t: list[int] = []
        p: list[list[float] | None] = []
        f: list[int] = []
        for fila, fase in zip(contexto, fases, strict=True):
            if not desde_ms <= fila.t_ms <= hasta_ms:
                continue
            t.append(fila.t_ms)
            f.append(fase)
            if fila.landmarks is None:
                p.append(None)
            else:
                puntos: list[float] = []
                for _, indice in ARTICULACIONES:
                    x, y, _, _ = fila.landmarks[indice]
                    puntos += [round(x, 4), round(y, 4)]
                p.append(puntos)
        return {"t": t, "p": p, "f": f, "claves": [k for k, _ in ARTICULACIONES]}

    def fotograma_video(self, camara_id: str, t_ms: int) -> bytes | None:
        """The continuous video's frame at ``t_ms`` as a JPEG (only on this PC)."""
        indice = self._almacen.indice
        if indice is None:
            return None
        archivos = indice.en_rango(camara_id, TipoArchivo.VIDEO, t_ms, t_ms + 1)
        if not archivos:
            return None
        lector = self._lector(archivos[0])
        return lector.jpeg(t_ms) if lector is not None else None

    def cerrar(self) -> None:
        """Drops what was decrypted for the replay."""
        with self._candado:
            self._filas.clear()
            for lector in self._videos.values():
                lector.cerrar()
            self._videos.clear()

    # ------------------------------------------------------------------ internals

    def _local(self, ms: int) -> datetime:
        return instante_ms(ms).astimezone(self._zona)

    def _hay_video(self, camara_id: str, desde_ms: int, hasta_ms: int) -> bool:
        indice = self._almacen.indice
        return bool(
            indice is not None and indice.en_rango(camara_id, TipoArchivo.VIDEO, desde_ms, hasta_ms)
        )

    def _filas_de(self, camara_id: str, desde_ms: int, hasta_ms: int) -> list[FilaMovimiento]:
        indice = self._almacen.indice
        if indice is None:
            return []
        filas: list[FilaMovimiento] = []
        for archivo in indice.en_rango(camara_id, TipoArchivo.MOVIMIENTOS, desde_ms, hasta_ms + 1):
            filas += [f for f in self._filas_del_archivo(archivo) if desde_ms <= f.t_ms <= hasta_ms]
        return sorted(filas, key=lambda f: f.t_ms)

    def _filas_del_archivo(self, archivo: Archivo) -> list[FilaMovimiento]:
        with self._candado:
            if archivo.id in self._filas:
                self._filas.move_to_end(archivo.id)
                return self._filas[archivo.id]
        datos = self._almacen.leer(archivo)
        try:
            filas = leer_parquet(datos)[1] if datos is not None else []
        except ValueError:
            logger.warning("Archivo de movimientos ilegible: %s", archivo.ruta)
            filas = []
        with self._candado:
            self._filas[archivo.id] = filas
            while len(self._filas) > ARCHIVOS_EN_MEMORIA:
                self._filas.popitem(last=False)
        return filas

    def _lector(self, archivo: Archivo) -> "_LectorVideo | None":
        with self._candado:
            if archivo.id in self._videos:
                self._videos.move_to_end(archivo.id)
                return self._videos[archivo.id]
        datos = self._almacen.leer(archivo)
        if datos is None:
            return None
        try:
            lector = _LectorVideo(datos, archivo.desde_ms)
        except Exception:
            logger.warning("Video ilegible: %s", archivo.ruta)
            return None
        with self._candado:
            self._videos[archivo.id] = lector
            while len(self._videos) > 2:
                self._videos.popitem(last=False)[1].cerrar()
        return lector


def _fases(filas: list[FilaMovimiento]) -> list[int]:
    """The phase code of each row, from the classifier's phase and events."""
    inestables = [f.t_ms for f in filas if f.evento is TipoEvento.MOVIMIENTO_INESTABLE]
    levantadas = [f.t_ms for f in filas if f.evento is TipoEvento.RECUPERACION]
    fases: list[int] = []
    confirmada = False
    for fila in filas:
        if fila.evento is TipoEvento.CAIDA_CONFIRMADA:
            confirmada = True
        if fila.fase is Fase.EN_EL_SUELO:
            fases.append(CONFIRMADA if confirmada else EN_EL_SUELO)
            continue
        confirmada = False
        if fila.fase is Fase.INICIO_CAIDA:
            fases.append(POSIBLE_CAIDA)
        elif any(abs(fila.t_ms - t) < INESTABLE_MS for t in inestables):
            fases.append(INESTABLE)
        elif any(0 <= fila.t_ms - t < LEVANTO_MS for t in levantadas):
            fases.append(SE_LEVANTO)
        else:
            fases.append(DE_PIE)
    return fases


class _LectorVideo:
    """Decodes one decrypted 10-minute segment on demand, forward from the last frame."""

    def __init__(self, mp4: bytes, inicio_ms: int) -> None:
        import av

        self._inicio_ms = inicio_ms
        self._contenedor: Any = cast(Any, av.open(io.BytesIO(mp4)))
        self._flujo: Any = self._contenedor.streams.video[0]
        self._cuadros: Any = None
        self._ultimo: Any = None  # (ms, frame)
        self._candado = threading.Lock()
        # The muxer may shift every timestamp (an encoder delay): the first frame is the start.
        primero = next(self._contenedor.decode(self._flujo), None)
        self._origen_ms = int(primero.time * 1000) if primero is not None and primero.time else 0
        self._contenedor.seek(0)

    def jpeg(self, t_ms: int) -> bytes | None:
        with self._candado:
            cuadro = self._cuadro(t_ms - self._inicio_ms)
            if cuadro is None:
                return None
            import cv2

            ok, datos = cv2.imencode(
                ".jpg", cuadro.to_ndarray(format="bgr24"), [cv2.IMWRITE_JPEG_QUALITY, 80]
            )
            return bytes(datos.tobytes()) if ok else None

    def _cuadro(self, ms: int) -> Any:
        if self._ultimo is None or ms < self._ultimo[0] or ms - self._ultimo[0] > 3_000:
            self._contenedor.seek(
                max(0, ms + self._origen_ms) * 1000, backward=True, any_frame=False
            )
            self._cuadros = self._contenedor.decode(self._flujo)
            self._ultimo = None
        elegido = self._ultimo
        for cuadro in self._cuadros or []:
            momento = (int(cuadro.time * 1000) if cuadro.time is not None else 0) - self._origen_ms
            elegido = (momento, cuadro)
            if momento >= ms:
                break
        self._ultimo = elegido
        return elegido[1] if elegido is not None else None

    def cerrar(self) -> None:
        self._contenedor.close()
