"""Local index of the stored files: what is kept, for which camera and time, and its size.

Paths are relative to the data folder (``/``-separated), so the folder can move. The index only
describes files: deleting a file from disk is the caller's job (see ``retencion``).
"""

import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath


class TipoArchivo(StrEnum):
    MOVIMIENTOS = "movimientos"
    VIDEO = "video"
    CLIP = "clip"


_ESQUEMA = """
CREATE TABLE IF NOT EXISTS archivos (
    id INTEGER PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('movimientos', 'video', 'clip')),
    camara_id TEXT NOT NULL,
    desde_ms INTEGER NOT NULL,
    hasta_ms INTEGER NOT NULL,
    ruta TEXT NOT NULL UNIQUE,
    tamano_bytes INTEGER NOT NULL,
    creado_ms INTEGER NOT NULL,
    subido INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NULL
);
CREATE INDEX IF NOT EXISTS archivos_tipo_desde ON archivos (tipo, desde_ms);
CREATE INDEX IF NOT EXISTS archivos_camara_desde ON archivos (camara_id, desde_ms);
"""

_COLUMNAS = "id, tipo, camara_id, desde_ms, hasta_ms, ruta, tamano_bytes, creado_ms, subido, sha256"
_ORDEN = "ORDER BY desde_ms, id"


@dataclass(frozen=True, slots=True)
class Archivo:
    id: int
    tipo: TipoArchivo
    camara_id: str
    desde_ms: int
    hasta_ms: int
    ruta: str
    tamano_bytes: int
    creado_ms: int
    subido: bool
    sha256: str | None


def _archivo(fila: tuple[int, str, str, int, int, str, int, int, int, str | None]) -> Archivo:
    id_, tipo, camara_id, desde_ms, hasta_ms, ruta, tamano, creado_ms, subido, sha256 = fila
    return Archivo(
        id_, TipoArchivo(tipo), camara_id, desde_ms, hasta_ms, ruta, tamano, creado_ms,
        bool(subido), sha256,
    )  # fmt: skip


def _ruta_relativa(ruta: str | PurePosixPath) -> str:
    relativa = PurePosixPath(ruta)
    if relativa.is_absolute() or ".." in relativa.parts or not relativa.parts:
        raise ValueError("La ruta debe ser relativa a la carpeta de datos")
    return relativa.as_posix()


class IndiceArchivos:
    def __init__(self, ruta_db: Path, reloj: Callable[[], float] = time.time) -> None:
        self._reloj = reloj
        self._candado = threading.RLock()
        self._db = sqlite3.connect(ruta_db, check_same_thread=False, isolation_level=None)
        self._db.executescript(_ESQUEMA)

    def cerrar(self) -> None:
        with self._candado:
            self._db.close()

    # ------------------------------------------------------------------ writing

    def registrar(
        self,
        tipo: TipoArchivo,
        camara_id: str,
        desde_ms: int,
        hasta_ms: int,
        ruta: str | PurePosixPath,
        tamano_bytes: int,
        sha256: str | None = None,
    ) -> int:
        """Records a file that is already in place; returns its id."""
        if hasta_ms <= desde_ms:
            raise ValueError("hasta_ms debe ser mayor que desde_ms")
        if tamano_bytes < 0:
            raise ValueError("Tamaño negativo")
        with self._candado:
            cursor = self._db.execute(
                "INSERT INTO archivos (tipo, camara_id, desde_ms, hasta_ms, ruta, tamano_bytes,"
                " creado_ms, sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    TipoArchivo(tipo).value,
                    camara_id,
                    desde_ms,
                    hasta_ms,
                    _ruta_relativa(ruta),
                    tamano_bytes,
                    int(self._reloj() * 1000),
                    sha256,
                ),
            )
            id_ = cursor.lastrowid
        assert id_ is not None
        return id_

    def borrar(self, id_: int) -> None:
        with self._candado:
            self._db.execute("DELETE FROM archivos WHERE id = ?", (id_,))

    def marcar_subido(self, id_: int) -> None:
        with self._candado:
            self._db.execute("UPDATE archivos SET subido = 1 WHERE id = ?", (id_,))

    # ------------------------------------------------------------------ reading

    def obtener(self, id_: int) -> Archivo | None:
        filas = self._consultar(f"SELECT {_COLUMNAS} FROM archivos WHERE id = ?", (id_,))
        return filas[0] if filas else None

    def en_rango(
        self, camara_id: str, tipo: TipoArchivo, desde_ms: int, hasta_ms: int
    ) -> list[Archivo]:
        """Files of the camera that overlap ``[desde_ms, hasta_ms)``, oldest first."""
        return self._consultar(
            f"SELECT {_COLUMNAS} FROM archivos WHERE camara_id = ? AND tipo = ?"
            f" AND desde_ms < ? AND hasta_ms > ? {_ORDEN}",
            (camara_id, TipoArchivo(tipo).value, hasta_ms, desde_ms),
        )

    def mas_antiguos(self, tipo: TipoArchivo, limite: int) -> list[Archivo]:
        return self._consultar(
            f"SELECT {_COLUMNAS} FROM archivos WHERE tipo = ? {_ORDEN} LIMIT ?",
            (TipoArchivo(tipo).value, limite),
        )

    def anteriores_a(self, tipo: TipoArchivo, limite_ms: int) -> list[Archivo]:
        """Files whose whole span ended at or before ``limite_ms``, oldest first."""
        return self._consultar(
            f"SELECT {_COLUMNAS} FROM archivos WHERE tipo = ? AND hasta_ms <= ? {_ORDEN}",
            (TipoArchivo(tipo).value, limite_ms),
        )

    def pendientes_de_subir(self, tipo: TipoArchivo) -> list[Archivo]:
        return self._consultar(
            f"SELECT {_COLUMNAS} FROM archivos WHERE tipo = ? AND subido = 0 {_ORDEN}",
            (TipoArchivo(tipo).value,),
        )

    def disponibles_desde(self, camara_id: str, tipo: TipoArchivo) -> int | None:
        """Start of the oldest file of the camera (epoch ms), or ``None`` when there is none."""
        with self._candado:
            (desde,) = self._db.execute(
                "SELECT MIN(desde_ms) FROM archivos WHERE camara_id = ? AND tipo = ?",
                (camara_id, TipoArchivo(tipo).value),
            ).fetchone()
        return int(desde) if desde is not None else None

    def uso_por_tipo(self) -> dict[TipoArchivo, int]:
        """Bytes used per type (every type present, ``0`` when empty)."""
        uso = dict.fromkeys(TipoArchivo, 0)
        with self._candado:
            filas = self._db.execute(
                "SELECT tipo, SUM(tamano_bytes) FROM archivos GROUP BY tipo"
            ).fetchall()
        for tipo, total in filas:
            uso[TipoArchivo(tipo)] = int(total)
        return uso

    def rutas_conocidas(self) -> set[str]:
        with self._candado:
            filas = self._db.execute("SELECT ruta FROM archivos").fetchall()
        return {ruta for (ruta,) in filas}

    def _consultar(self, sql: str, parametros: tuple[object, ...]) -> list[Archivo]:
        with self._candado:
            filas = self._db.execute(sql, parametros).fetchall()
        return [_archivo(fila) for fila in filas]
