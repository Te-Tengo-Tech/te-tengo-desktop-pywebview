"""Movement files: body landmarks only, never images (US-37, US-38).

One Parquet file (zstd) holds the analyzed frames (about 8 fps) of one camera during one window
of at most 5 minutes aligned to the UTC clock (00:00, 00:05 …). One row per frame, columns in
this order:

* ``t_ms`` int64: instant of the frame, UTC epoch milliseconds;
* ``pose_presente`` bool: MediaPipe found a person in the frame;
* for each of MediaPipe's 33 landmarks ``ii`` = ``00`` … ``32``: ``x{ii}`` uint16, ``y{ii}``
  uint16, ``z{ii}`` int16 and ``v{ii}`` uint8 (visibility), all null when there is no pose;
* ``theta`` float32: angle of the body centre line with the floor, in degrees;
* ``p`` float32: width/height ratio of the body;
* ``v`` float32: hip descent speed, in bodies per second (the three nullable);
* ``fase`` dictionary string: ``normal``, ``inicio_caida`` or ``en_el_suelo``;
* ``evento`` dictionary string, nullable: the event detected on that frame, if any.

**Quantization** (``q`` is the stored integer, ``c`` the MediaPipe value):

* x, y (normalized to the image, may fall slightly outside [0, 1]; range [-0.5, 1.5]):
  ``q = clip(round((c + 0.5) / 2.0 * 65535), 0, 65535)``, ``c = q / 65535 * 2.0 - 0.5``;
  max error 1/65535 inside the range.
* z (relative depth, same scale as x; range [-4, 4)):
  ``q = clip(round(z * 8192), -32768, 32767)``, ``z = q / 8192``; max error 0.5/8192.
* visibility ([0, 1]): ``q = clip(round(v * 255), 0, 255)``, ``v = q / 255``; max error 0.5/255.

Values outside the range are clipped to its edge; NaN is stored as 0 (the value of ``c = 0``)
and infinities as the edges, so a bad measurement never stops the recording.

**File metadata** (Parquet key-value): ``formato`` = ``te-tengo-movimientos``, ``version`` =
``1``, ``camara_id``, ``desde`` and ``hasta`` (ISO-8601 UTC with milliseconds and ``Z``; the file
covers ``[desde, hasta)``) and ``fps_objetivo`` = ``8``.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

import numpy as np
import numpy.typing as npt
import pyarrow as pa
import pyarrow.parquet as pq

from te_tengo_deteccion.clasificacion.estados import Fase, TipoEvento

FORMATO = "te-tengo-movimientos"
VERSION_FORMATO = "1"
FPS_OBJETIVO = 8
NUM_PUNTOS = 33
NIVEL_ZSTD = 3

XY_MIN = -0.5
XY_MAX = 1.5
XY_PASOS = 65535
XY_ERROR_MAX = 1 / 65535
Z_ESCALA = 8192
Z_MIN = -32768 / Z_ESCALA
Z_MAX = 32767 / Z_ESCALA
Z_ERROR_MAX = 0.5 / Z_ESCALA
V_PASOS = 255
V_ERROR_MAX = 0.5 / V_PASOS

VENTANA_MS = 5 * 60 * 1000
VENTANA_MAXIMA_MS = 10 * 60 * 1000
# Two frames further apart than this are not continuous: the next file starts at its first frame.
HUECO_MAXIMO_MS = 2_000

FASES: tuple[str, ...] = tuple(fase.value for fase in Fase)
EVENTOS: tuple[str, ...] = tuple(evento.value for evento in TipoEvento)

Punto = tuple[float, float, float, float]  # x, y, z, visibility (MediaPipe units)
_Flotantes = npt.NDArray[np.float64]


def _columnas_puntos() -> list[tuple[str, pa.DataType]]:
    columnas: list[tuple[str, pa.DataType]] = []
    for i in range(NUM_PUNTOS):
        columnas += [
            (f"x{i:02d}", pa.uint16()),
            (f"y{i:02d}", pa.uint16()),
            (f"z{i:02d}", pa.int16()),
            (f"v{i:02d}", pa.uint8()),
        ]
    return columnas


_COLUMNAS_DELTA = ("t_ms", *(nombre for nombre, _ in _columnas_puntos()))

ESQUEMA = pa.schema(
    [
        pa.field("t_ms", pa.int64(), nullable=False),
        pa.field("pose_presente", pa.bool_(), nullable=False),
        *(pa.field(nombre, tipo) for nombre, tipo in _columnas_puntos()),
        pa.field("theta", pa.float32()),
        pa.field("p", pa.float32()),
        pa.field("v", pa.float32()),
        pa.field("fase", pa.dictionary(pa.int8(), pa.string()), nullable=False),
        pa.field("evento", pa.dictionary(pa.int8(), pa.string())),
    ]
)


@dataclass(frozen=True, slots=True)
class FilaMovimiento:
    """One analyzed frame: the pose (if any) and what the classifier measured and decided."""

    t_ms: int
    landmarks: Sequence[Punto] | None
    theta: float | None = None
    p: float | None = None
    v: float | None = None
    fase: Fase = Fase.NORMAL
    evento: TipoEvento | None = None

    def __post_init__(self) -> None:
        if self.landmarks is not None and len(self.landmarks) != NUM_PUNTOS:
            raise ValueError(f"Se esperaban {NUM_PUNTOS} puntos, hay {len(self.landmarks)}")


# ------------------------------------------------------------------ quantization


def _limpiar(valores: npt.ArrayLike, minimo: float, maximo: float) -> _Flotantes:
    return np.nan_to_num(
        np.asarray(valores, dtype=np.float64), nan=0.0, posinf=maximo, neginf=minimo
    )


def cuantizar_xy(valores: npt.ArrayLike) -> npt.NDArray[np.uint16]:
    c = _limpiar(valores, XY_MIN, XY_MAX)
    q = np.rint((c - XY_MIN) / (XY_MAX - XY_MIN) * XY_PASOS)
    return np.clip(q, 0, XY_PASOS).astype(np.uint16)


def decuantizar_xy(q: npt.ArrayLike) -> _Flotantes:
    return np.asarray(q, dtype=np.float64) / XY_PASOS * (XY_MAX - XY_MIN) + XY_MIN


def cuantizar_z(valores: npt.ArrayLike) -> npt.NDArray[np.int16]:
    q = np.rint(_limpiar(valores, Z_MIN, Z_MAX) * Z_ESCALA)
    return np.clip(q, -32768, 32767).astype(np.int16)


def decuantizar_z(q: npt.ArrayLike) -> _Flotantes:
    return np.asarray(q, dtype=np.float64) / Z_ESCALA


def cuantizar_visibilidad(valores: npt.ArrayLike) -> npt.NDArray[np.uint8]:
    q = np.rint(_limpiar(valores, 0.0, 1.0) * V_PASOS)
    return np.clip(q, 0, V_PASOS).astype(np.uint8)


def decuantizar_visibilidad(q: npt.ArrayLike) -> _Flotantes:
    return np.asarray(q, dtype=np.float64) / V_PASOS


# ------------------------------------------------------------------ writing and reading


def iso_utc(instante: datetime) -> str:
    """``2026-10-10T15:05:00.000Z``; ``instante`` must carry a time zone."""
    if instante.tzinfo is None:
        raise ValueError("El instante debe tener zona horaria")
    return instante.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _diccionario(valores: Sequence[str | None], opciones: tuple[str, ...]) -> pa.DictionaryArray:
    nulos = np.array([valor is None for valor in valores], dtype=bool)
    indices = np.array(
        [0 if valor is None else opciones.index(valor) for valor in valores], dtype=np.int8
    )
    return pa.DictionaryArray.from_arrays(
        pa.array(indices, type=pa.int8(), mask=nulos), pa.array(opciones, type=pa.string())
    )


def escribir_parquet(
    filas: Sequence[FilaMovimiento], camara_id: str, desde: datetime, hasta: datetime
) -> bytes:
    """The Parquet file of ``filas`` (one row group, zstd), with the file metadata."""
    n = len(filas)
    presente = np.array([fila.landmarks is not None for fila in filas], dtype=bool)
    puntos = np.zeros((n, NUM_PUNTOS, 4), dtype=np.float64)
    for indice, fila in enumerate(filas):
        if fila.landmarks is not None:
            puntos[indice] = fila.landmarks
    ausente = ~presente
    qx, qy = cuantizar_xy(puntos[:, :, 0]), cuantizar_xy(puntos[:, :, 1])
    qz, qv = cuantizar_z(puntos[:, :, 2]), cuantizar_visibilidad(puntos[:, :, 3])
    columnas: list[pa.Array] = [
        pa.array([fila.t_ms for fila in filas], type=pa.int64()),
        pa.array(presente, type=pa.bool_()),
    ]
    for i in range(NUM_PUNTOS):
        columnas += [
            pa.array(qx[:, i], type=pa.uint16(), mask=ausente),
            pa.array(qy[:, i], type=pa.uint16(), mask=ausente),
            pa.array(qz[:, i], type=pa.int16(), mask=ausente),
            pa.array(qv[:, i], type=pa.uint8(), mask=ausente),
        ]
    columnas += [
        pa.array([fila.theta for fila in filas], type=pa.float32()),
        pa.array([fila.p for fila in filas], type=pa.float32()),
        pa.array([fila.v for fila in filas], type=pa.float32()),
        _diccionario([fila.fase.value for fila in filas], FASES),
        _diccionario([None if f.evento is None else f.evento.value for f in filas], EVENTOS),
    ]
    metadatos = {
        "formato": FORMATO,
        "version": VERSION_FORMATO,
        "camara_id": camara_id,
        "desde": iso_utc(desde),
        "hasta": iso_utc(hasta),
        "fps_objetivo": str(FPS_OBJETIVO),
    }
    tabla = pa.Table.from_arrays(columnas, schema=ESQUEMA.with_metadata(metadatos))
    salida = pa.BufferOutputStream()
    pq.write_table(
        tabla,
        salida,
        compression="zstd",
        compression_level=NIVEL_ZSTD,
        use_dictionary=["fase", "evento"],
        # Landmarks move little between frames: deltas compress about a third better than plain.
        column_encoding=dict.fromkeys(_COLUMNAS_DELTA, "DELTA_BINARY_PACKED"),
        row_group_size=max(1, n),
        write_statistics=["t_ms"],
    )
    return bytes(salida.getvalue().to_pybytes())


def contar_filas(datos: bytes) -> int:
    """Rows of a movement file, from its footer (``fotogramas`` of the upload, US-37)."""
    return int(pq.ParquetFile(pa.BufferReader(datos)).metadata.num_rows)


def leer_parquet(datos: bytes) -> tuple[dict[str, str], list[FilaMovimiento]]:
    """The file metadata and the rows, with the landmarks decoded to MediaPipe units."""
    tabla = pq.read_table(pa.BufferReader(datos))
    crudos: dict[bytes, bytes] = tabla.schema.metadata or {}
    metadatos = {
        clave.decode(): valor.decode()
        for clave, valor in crudos.items()
        if not clave.startswith(b"ARROW:")
    }
    if metadatos.get("formato") != FORMATO:
        raise ValueError("No es un archivo de movimientos de Te Tengo")

    def numeros(nombre: str) -> npt.NDArray[Any]:
        return np.asarray(tabla.column(nombre).fill_null(0).to_numpy())

    presente = np.asarray(tabla.column("pose_presente").to_numpy(), dtype=bool)
    puntos = np.stack(
        [
            np.stack(
                [
                    decuantizar_xy(numeros(f"x{i:02d}")),
                    decuantizar_xy(numeros(f"y{i:02d}")),
                    decuantizar_z(numeros(f"z{i:02d}")),
                    decuantizar_visibilidad(numeros(f"v{i:02d}")),
                ],
                axis=-1,
            )
            for i in range(NUM_PUNTOS)
        ],
        axis=1,
    )
    t_ms: list[int] = tabla.column("t_ms").to_pylist()
    theta: list[float | None] = tabla.column("theta").to_pylist()
    p: list[float | None] = tabla.column("p").to_pylist()
    v: list[float | None] = tabla.column("v").to_pylist()
    fases: list[str] = tabla.column("fase").to_pylist()
    eventos: list[str | None] = tabla.column("evento").to_pylist()
    filas = [
        FilaMovimiento(
            t_ms=t,
            landmarks=(
                tuple((float(x), float(y), float(z), float(w)) for x, y, z, w in cuerpo)
                if hay_pose
                else None
            ),
            theta=angulo,
            p=proporcion,
            v=velocidad,
            fase=Fase(fase),
            evento=None if evento is None else TipoEvento(evento),
        )
        for t, hay_pose, cuerpo, angulo, proporcion, velocidad, fase, evento in zip(
            t_ms, presente, puntos, theta, p, v, fases, eventos, strict=True
        )
    ]
    return metadatos, filas


# ------------------------------------------------------------------ 5-minute windows


_EPOCA = datetime(1970, 1, 1, tzinfo=UTC)
_UN_MS = timedelta(milliseconds=1)


def instante_ms(t_ms: int) -> datetime:
    """The UTC instant of epoch milliseconds (exact, no float rounding)."""
    return _EPOCA + t_ms * _UN_MS


def a_ms(instante: datetime) -> int:
    """Epoch milliseconds of an aware instant."""
    return (instante - _EPOCA) // _UN_MS


class TramoCerrado(NamedTuple):
    """A finished movement file of one camera, covering ``[desde, hasta)``: the Parquet file
    (``datos``) and the same rows in the light replay format (``ligero``, ``ligero.py``)."""

    desde: datetime
    hasta: datetime
    datos: bytes
    n_filas: int
    ligero: bytes = b""

    @property
    def desde_ms(self) -> int:
        return a_ms(self.desde)

    @property
    def hasta_ms(self) -> int:
        return a_ms(self.hasta)


class TramoMovimientos:
    """Accumulates the rows of one camera and closes a file per window aligned to the UTC clock.

    ``desde`` is the window start when the previous frame was in the previous window and at most
    ``HUECO_MAXIMO_MS`` earlier (continuous capture), otherwise the first frame of the file;
    ``hasta`` is the window end when the next frame continues the capture the same way, otherwise
    just after the last frame. So consecutive files of a continuous capture touch each other, and
    a pause never shows as covered.
    """

    def __init__(self, camara_id: str, ventana_ms: int = VENTANA_MS) -> None:
        if not 0 < ventana_ms <= VENTANA_MAXIMA_MS:
            raise ValueError("La ventana debe durar entre 0 y 10 minutos")
        self._camara_id = camara_id
        self._ventana_ms = ventana_ms
        self._filas: list[FilaMovimiento] = []
        self._ventana = 0  # start of the current window (ms)
        self._desde_ms = 0
        self._ultimo_ms: int | None = None

    @property
    def n_filas(self) -> int:
        return len(self._filas)

    def agregar(self, fila: FilaMovimiento) -> list[TramoCerrado]:
        """Adds a row; returns the file of the previous window when the row starts a new one."""
        ventana = fila.t_ms - fila.t_ms % self._ventana_ms
        cerrados: list[TramoCerrado] = []
        continua = (
            self._ultimo_ms is not None
            and 0 <= fila.t_ms - self._ultimo_ms <= HUECO_MAXIMO_MS
            and ventana == self._ventana + self._ventana_ms
        )
        if self._filas and ventana != self._ventana:
            cerrados = self._cerrar(self._ventana + self._ventana_ms if continua else None)
        if not self._filas:
            self._ventana = ventana
            self._desde_ms = ventana if continua else fila.t_ms
        self._desde_ms = min(self._desde_ms, fila.t_ms)  # a clock that stepped back
        self._filas.append(fila)
        self._ultimo_ms = fila.t_ms
        return cerrados

    def cerrar(self) -> list[TramoCerrado]:
        """Flushes the partial window (nothing when it has no rows)."""
        cerrados = self._cerrar(None)
        self._ultimo_ms = None
        return cerrados

    def _cerrar(self, hasta_ms: int | None) -> list[TramoCerrado]:
        if not self._filas:
            return []
        if hasta_ms is None:
            hasta_ms = max(fila.t_ms for fila in self._filas) + 1
        from te_tengo_captura.almacen.ligero import escribir_ligero  # it imports this module

        desde, hasta = instante_ms(self._desde_ms), instante_ms(hasta_ms)
        datos = escribir_parquet(self._filas, self._camara_id, desde, hasta)
        ligero = escribir_ligero(self._filas, self._desde_ms, hasta_ms)
        cerrado = TramoCerrado(desde, hasta, datos, len(self._filas), ligero)
        self._filas = []
        return [cerrado]
