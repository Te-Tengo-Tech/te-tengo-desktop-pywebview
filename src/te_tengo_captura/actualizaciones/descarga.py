"""Downloads the Windows installer and checks its SHA-256 (US-43, CA-43.2).

* **Space first:** before downloading, the folder's disk must hold the installer plus
  ``RESERVA_BYTES`` (implementation choice: room for the files the installer writes). Otherwise
  nothing is downloaded and the window says how much to free («Libera 90 MB en el disco C:.»).
* **Download:** streamed to ``<name>.part`` with its progress; «Cancelar» stops it.
* **Verify:** the SHA-256 of the whole file on disk against the ``sha256`` of ``GET
  /api/versiones``. Only a match renames it to the installer's name.

Every failure (no internet, the download failed, a mismatch, a full disk, cancelled) deletes
the partial or bad file: nothing is installed and the current version stays.
"""

import errno
import hashlib
import logging
import shutil
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RESERVA_BYTES = 100 * 2**20
BLOQUE = 2**20
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
MIB = 2**20


class Resultado(StrEnum):
    LISTA = "lista"
    SIN_INTERNET = "net"
    FALLO = "fail"
    ALTERADA = "bad"
    SIN_ESPACIO = "disk"
    CANCELADA = "cancelada"


@dataclass(frozen=True, slots=True)
class Descarga:
    resultado: Resultado
    archivo: Path | None = None
    faltan_bytes: int = 0  # SIN_ESPACIO: what has to be freed


UsoDisco = Callable[[Path], Any]  # shutil.disk_usage: an object with ``free``


def espacio_faltante(directorio: Path, tamano: int, uso: UsoDisco = shutil.disk_usage) -> int:
    """Bytes to free on the folder's disk before downloading ``tamano`` bytes (0: enough)."""
    try:
        libre = int(uso(directorio).free)
    except OSError:
        return 0  # unknown: try, and a full disk is caught while writing
    return max(0, tamano + RESERVA_BYTES - libre)


def megas(bytes_: int) -> int:
    """MB as the prototype shows them («86 MB» for 90 177 536 bytes): MiB, rounded up."""
    return -(-bytes_ // MIB)


def sha256_de(archivo: Path) -> str:
    suma = hashlib.sha256()
    with archivo.open("rb") as entrada:
        while bloque := entrada.read(BLOQUE):
            suma.update(bloque)
    return suma.hexdigest()


def descargar(
    url: str,
    sha256: str,
    destino: Path,
    tamano: int | None = None,
    al_progreso: Callable[[int], None] = lambda _pct: None,
    al_verificar: Callable[[], None] = lambda: None,
    cancelada: threading.Event | None = None,
    transporte: httpx.BaseTransport | None = None,
    uso: UsoDisco = shutil.disk_usage,
) -> Descarga:
    """Downloads ``url`` to ``destino`` and verifies it; never leaves a partial or bad file."""
    cancelada = cancelada or threading.Event()
    destino.parent.mkdir(parents=True, exist_ok=True)
    if tamano:
        faltan = espacio_faltante(destino.parent, tamano, uso)
        if faltan:
            logger.warning("Falta espacio para la descarga: %d MB", megas(faltan))
            return Descarga(Resultado.SIN_ESPACIO, faltan_bytes=faltan)
    parcial = destino.with_name(destino.name + ".part")
    try:
        resultado = _bajar(url, parcial, tamano, al_progreso, cancelada, transporte)
    except OSError as error:
        parcial.unlink(missing_ok=True)
        if error.errno == errno.ENOSPC:
            faltan = espacio_faltante(destino.parent, tamano or 0, uso) or (tamano or 0)
            logger.warning("Disco lleno durante la descarga")
            return Descarga(Resultado.SIN_ESPACIO, faltan_bytes=faltan)
        logger.warning("No se pudo escribir la descarga: %s", error)
        return Descarga(Resultado.FALLO)
    if resultado is not Resultado.LISTA:
        parcial.unlink(missing_ok=True)
        return Descarga(resultado)
    al_verificar()
    try:
        calculada = sha256_de(parcial)
    except OSError as error:
        parcial.unlink(missing_ok=True)
        logger.warning("No se pudo leer la descarga: %s", error)
        return Descarga(Resultado.FALLO)
    if calculada.lower() != sha256.strip().lower():
        parcial.unlink(missing_ok=True)
        logger.warning("La suma SHA-256 de la descarga no coincide: se borró el archivo")
        return Descarga(Resultado.ALTERADA)
    parcial.replace(destino)
    logger.info("Descarga verificada (SHA-256): %s", destino.name)
    return Descarga(Resultado.LISTA, destino)


def _bajar(
    url: str,
    parcial: Path,
    tamano: int | None,
    al_progreso: Callable[[int], None],
    cancelada: threading.Event,
    transporte: httpx.BaseTransport | None,
) -> Resultado:
    try:
        with (
            httpx.Client(timeout=TIMEOUT, transport=transporte, follow_redirects=True) as http,
            http.stream("GET", url) as respuesta,
        ):
            if respuesta.is_error:
                logger.warning("No se pudo descargar la versión: HTTP %d", respuesta.status_code)
                return Resultado.FALLO
            total = int(respuesta.headers.get("Content-Length") or tamano or 0)
            recibidos, ultimo = 0, -1
            with parcial.open("wb") as salida:
                for bloque in respuesta.iter_bytes(BLOQUE):
                    if cancelada.is_set():
                        logger.info("Descarga cancelada")
                        return Resultado.CANCELADA
                    salida.write(bloque)
                    recibidos += len(bloque)
                    pct = min(100, recibidos * 100 // total) if total else 0
                    if pct != ultimo:
                        ultimo = pct
                        al_progreso(pct)
            if cancelada.is_set():
                return Resultado.CANCELADA
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as error:
        logger.warning("Sin internet para descargar la versión: %s", type(error).__name__)
        return Resultado.SIN_INTERNET
    except httpx.HTTPError as error:
        logger.warning("No se pudo descargar la versión: %s", type(error).__name__)
        return Resultado.FALLO
    return Resultado.LISTA
