"""The light replay format (TTMOV v1) the app draws (US-36, US-39; AGENT_CONTRACT.md, "Light replay
format").

The app cannot read Parquet on every platform, so next to each movement file (``puntos.py``) and
each clip's landmarks the PC writes the same rows in this small binary format, from the same
in-memory rows. The Parquet file stays the source for analysis (US-40).

* **Container:** one gzip member (``MTIME`` 0, no file name) holding the payload.
* **Payload** (little-endian): a 24-byte header ``TTMV``, version, flags, target fps, landmarks
  per pose, ``t0Ms`` (i64), ``duracionMs`` (u32), ``fotogramas`` (u32); then per frame ``dtMs``
  (i32, from the previous frame, the first from ``t0Ms``), ``estado`` (u8: pose, phase, event)
  and, with a pose, the ``x``, ``y`` (u16) and visibility (u8) of the 33 landmarks as deltas from
  the previous frame with a pose (modulo 2^16 / 2^8), plus ``z`` with the ``Z`` flag.
* **Quantization:** the same integers as the Parquet file, so both describe the same frames.
"""

import gzip
import struct
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from te_tengo_captura.almacen.puntos import (
    EVENTOS,
    FASES,
    NUM_PUNTOS,
    FilaMovimiento,
    cuantizar_visibilidad,
    cuantizar_xy,
    cuantizar_z,
)
from te_tengo_deteccion.clasificacion.estados import Fase, TipoEvento

MAGIA = b"TTMV"
VERSION = 1
BANDERA_Z = 0x01
FPS_OBJETIVO = 8
NIVEL_GZIP = 9
EXTENSION = ".ttmov"
CONTENT_TYPE = "application/gzip"

_CABECERA = struct.Struct("<4sBBBBqII")
_FOTOGRAMA = struct.Struct("<iB")
_ESTADO_POSE = 0x01

# The wire values of the phase (bits 1-2) and the event (bits 3-5; 0 is none).
_CODIGO_FASE = {fase: i for i, fase in enumerate(FASES)}
_CODIGO_EVENTO = {evento: i + 1 for i, evento in enumerate(EVENTOS)}
assert FASES == ("normal", "inicio_caida", "en_el_suelo")
assert EVENTOS == (
    "caida",
    "caida_confirmada",
    "movimiento_inestable",
    "recuperacion",
    "deteccion_no_confiable",
)


def ruta_ligera(ruta: str) -> str | None:
    """The light file next to a movement file: ``….parquet.ttg`` → ``….ttmov.ttg`` (``None``
    for any other file)."""
    cabeza, separador, cola = ruta.rpartition(".parquet")
    if not separador or "/" in cola:
        return None
    return f"{cabeza}{EXTENSION}{cola}"


def escribir_ligero(
    filas: Sequence[FilaMovimiento], desde_ms: int, hasta_ms: int, con_z: bool = False
) -> bytes:
    """The light file of ``filas`` covering ``[desde_ms, hasta_ms)``, gzip-compressed."""
    if hasta_ms < desde_ms:
        raise ValueError("hasta_ms debe ser mayor o igual que desde_ms")
    n = len(filas)
    puntos = np.zeros((n, NUM_PUNTOS, 4), dtype=np.float64)
    for indice, fila in enumerate(filas):
        if fila.landmarks is not None:
            puntos[indice] = fila.landmarks
    qx = cuantizar_xy(puntos[:, :, 0]).astype(np.int64)
    qy = cuantizar_xy(puntos[:, :, 1]).astype(np.int64)
    qv = cuantizar_visibilidad(puntos[:, :, 3]).astype(np.int64)
    qz = cuantizar_z(puntos[:, :, 2]).astype(np.int64)

    salida = bytearray(
        _CABECERA.pack(
            MAGIA,
            VERSION,
            BANDERA_Z if con_z else 0,
            FPS_OBJETIVO,
            NUM_PUNTOS,
            desde_ms,
            hasta_ms - desde_ms,
            n,
        )
    )
    cero = np.zeros(NUM_PUNTOS, dtype=np.int64)
    ax, ay, av, az = cero, cero, cero, cero
    anterior_ms = desde_ms
    for i, fila in enumerate(filas):
        pose = fila.landmarks is not None
        salida += _FOTOGRAMA.pack(fila.t_ms - anterior_ms, _estado(fila, pose))
        anterior_ms = fila.t_ms
        if not pose:
            continue
        salida += ((qx[i] - ax) & 0xFFFF).astype("<u2").tobytes()
        salida += ((qy[i] - ay) & 0xFFFF).astype("<u2").tobytes()
        salida += ((qv[i] - av) & 0xFF).astype("u1").tobytes()
        if con_z:
            salida += ((qz[i] - az) & 0xFFFF).astype("<u2").tobytes()
        ax, ay, av, az = qx[i], qy[i], qv[i], qz[i]
    return gzip.compress(bytes(salida), compresslevel=NIVEL_GZIP, mtime=0)


def _estado(fila: FilaMovimiento, pose: bool) -> int:
    evento = 0 if fila.evento is None else _CODIGO_EVENTO[fila.evento.value]
    return (_ESTADO_POSE if pose else 0) | _CODIGO_FASE[fila.fase.value] << 1 | evento << 3


# ------------------------------------------------------------------ reading (tests and tools)


@dataclass(frozen=True, slots=True)
class FotogramaLigero:
    """One decoded frame, with the stored integers (``None`` without a pose)."""

    t_ms: int
    fase: Fase
    evento: TipoEvento | None
    x: npt.NDArray[np.uint16] | None
    y: npt.NDArray[np.uint16] | None
    v: npt.NDArray[np.uint8] | None
    z: npt.NDArray[np.int16] | None


@dataclass(frozen=True, slots=True)
class ArchivoLigero:
    t0_ms: int
    duracion_ms: int
    fps_objetivo: int
    con_z: bool
    fotogramas: list[FotogramaLigero]


def leer_ligero(datos: bytes) -> ArchivoLigero:
    """Decodes a light file; raises ``ValueError`` if it is not one this version understands."""
    try:
        cuerpo = gzip.decompress(datos)
    except (OSError, EOFError) as error:
        raise ValueError("No es un archivo gzip") from error
    if len(cuerpo) < _CABECERA.size:
        raise ValueError("Archivo ligero incompleto")
    magia, version, banderas, fps, puntos, t0_ms, duracion_ms, n = _CABECERA.unpack_from(cuerpo)
    if magia != MAGIA:
        raise ValueError("No es un archivo ligero de movimientos")
    if version != VERSION or banderas & ~BANDERA_Z:
        raise ValueError("Versión del archivo ligero no soportada")
    con_z = bool(banderas & BANDERA_Z)
    tamano_pose = puntos * (5 + (2 if con_z else 0))
    ax = ay = az = np.zeros(puntos, dtype=np.int64)
    av = np.zeros(puntos, dtype=np.int64)
    posicion = _CABECERA.size
    t_ms = t0_ms
    fotogramas: list[FotogramaLigero] = []
    for _ in range(n):
        if posicion + _FOTOGRAMA.size > len(cuerpo):
            raise ValueError("Archivo ligero incompleto")
        dt, estado = _FOTOGRAMA.unpack_from(cuerpo, posicion)
        posicion += _FOTOGRAMA.size
        t_ms += dt
        fase_codigo = (estado >> 1) & 0x03
        evento_codigo = (estado >> 3) & 0x07
        fase = Fase(FASES[fase_codigo]) if fase_codigo < len(FASES) else Fase.NORMAL
        evento = (
            TipoEvento(EVENTOS[evento_codigo - 1]) if 1 <= evento_codigo <= len(EVENTOS) else None
        )
        if not estado & _ESTADO_POSE:
            fotogramas.append(FotogramaLigero(t_ms, fase, evento, None, None, None, None))
            continue
        if posicion + tamano_pose > len(cuerpo):
            raise ValueError("Archivo ligero incompleto")

        def plano(dtype: str, cuantos: int) -> npt.NDArray[np.int64]:
            nonlocal posicion
            valores = np.frombuffer(cuerpo, dtype=dtype, count=puntos, offset=posicion)
            posicion += cuantos
            return valores.astype(np.int64)

        ax = (ax + plano("<u2", puntos * 2)) & 0xFFFF
        ay = (ay + plano("<u2", puntos * 2)) & 0xFFFF
        av = (av + plano("u1", puntos)) & 0xFF
        z = None
        if con_z:
            az = (az + plano("<u2", puntos * 2)) & 0xFFFF
            z = az.astype(np.uint16).view(np.int16)
        fotogramas.append(
            FotogramaLigero(
                t_ms,
                fase,
                evento,
                ax.astype(np.uint16),
                ay.astype(np.uint16),
                av.astype(np.uint8),
                z,
            )
        )
    return ArchivoLigero(t0_ms, duracion_ms, fps, con_z, fotogramas)
