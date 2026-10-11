"""Encryption at rest: stored files cannot be read outside the app (CA-38.4).

**Key.** One random 256-bit key per PC, kept base64-encoded in the operating system's credential
store (Keychain, Windows Credential Manager, Secret Service) through ``keyring``, under the service
``SERVICIO`` and the user name ``USUARIO``. It is created on first use and never logged.

**File format** (version 1), streamed so large files (10-minute video segments) never touch the
disk in plaintext::

    header  = b"TTG1" || version (1 byte) || chunk size (4 bytes, big-endian) || nonce prefix (8)
    chunk i = AES-256-GCM(key, nonce = prefix || i (4 bytes, big-endian),
                          plaintext_i, aad = header || i (4 bytes) || final flag (1 byte))

Every chunk but the last holds exactly ``chunk size`` plaintext bytes; the last one holds between
0 and ``chunk size`` bytes and carries the final flag 1 (an empty file still has one final, empty
chunk). Binding the header, the counter and the final flag to each tag detects reordering,
truncation (the new last chunk was sealed with flag 0) and appended data (the old last chunk was
sealed with flag 1). Any of them, a wrong key or a damaged header raise ``DatosIlegiblesError``.
"""

import base64
import binascii
import io
import os
import struct
import tempfile
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SERVICIO = "TeTengoCaptura"
USUARIO = "clave-datos"

MAGIA = b"TTG1"
VERSION = 1
TAMANO_CLAVE = 32
TAMANO_BLOQUE = 1 << 20  # 1 MiB of plaintext per chunk
TAMANO_BLOQUE_MAXIMO = 64 << 20  # a larger chunk size in a header means a damaged file
TAMANO_ETIQUETA = 16
_CABECERA = struct.Struct(">4sBI8s")
TAMANO_CABECERA = _CABECERA.size
_MAX_BLOQUES = 1 << 32


class DatosIlegiblesError(Exception):
    """The file was altered, truncated, extended, is not ours or the key is not the right one."""


class ClaveInvalidaError(Exception):
    """The credential store holds something that is not a 256-bit key."""


class AlmacenCredenciales(Protocol):
    """The part of a ``keyring`` backend the key provider uses."""

    def get_password(self, servicio: str, usuario: str, /) -> str | None: ...

    def set_password(self, servicio: str, usuario: str, secreto: str, /) -> None: ...

    def delete_password(self, servicio: str, usuario: str, /) -> None: ...


def almacen_del_sistema() -> AlmacenCredenciales:
    """The operating system's credential store, as ``keyring`` selects it."""
    import keyring

    return keyring.get_keyring()


class ClaveDatos:
    """Provides the data key, creating it in the credential store on first use."""

    def __init__(
        self,
        almacen: AlmacenCredenciales | None = None,
        aleatorio: Callable[[int], bytes] = os.urandom,
    ) -> None:
        self._almacen = almacen
        self._aleatorio = aleatorio
        self._clave: bytes | None = None
        self._candado = threading.Lock()

    def __repr__(self) -> str:  # never show the key
        return "ClaveDatos(<oculta>)"

    def obtener(self) -> bytes:
        with self._candado:
            if self._clave is None:
                almacen = self._usar_almacen()
                guardada = almacen.get_password(SERVICIO, USUARIO)
                if guardada is None:
                    clave = self._aleatorio(TAMANO_CLAVE)
                    almacen.set_password(SERVICIO, USUARIO, base64.b64encode(clave).decode())
                else:
                    clave = _decodificar_clave(guardada)
                self._clave = clave
            return self._clave

    def borrar(self) -> None:
        """Deletes the key: every file encrypted with it becomes unreadable for good."""
        with self._candado:
            self._clave = None
            almacen = self._usar_almacen()
            if almacen.get_password(SERVICIO, USUARIO) is not None:
                almacen.delete_password(SERVICIO, USUARIO)

    def _usar_almacen(self) -> AlmacenCredenciales:
        if self._almacen is None:
            self._almacen = almacen_del_sistema()
        return self._almacen


def _decodificar_clave(texto: str) -> bytes:
    try:
        clave = base64.b64decode(texto, validate=True)
    except (binascii.Error, ValueError):
        raise ClaveInvalidaError("La clave guardada no es base64") from None
    if len(clave) != TAMANO_CLAVE:
        raise ClaveInvalidaError("La clave guardada no tiene 256 bits")
    return clave


class _Sellador:
    """Seals the chunks of one file, in order."""

    def __init__(self, clave: bytes, tamano_bloque: int) -> None:
        if len(clave) != TAMANO_CLAVE:
            raise ValueError("La clave debe tener 32 bytes")
        if not 0 < tamano_bloque <= TAMANO_BLOQUE_MAXIMO:
            raise ValueError("Tamaño de bloque fuera de rango")
        self.tamano_bloque = tamano_bloque
        self._aead = AESGCM(clave)
        self._prefijo = os.urandom(8)
        self.cabecera = _CABECERA.pack(MAGIA, VERSION, tamano_bloque, self._prefijo)
        self._contador = 0

    def sellar(self, bloque: bytes, final: bool) -> bytes:
        if self._contador >= _MAX_BLOQUES:
            raise OverflowError("Demasiados bloques en un archivo")
        contador = self._contador.to_bytes(4, "big")
        self._contador += 1
        aad = self.cabecera + contador + (b"\x01" if final else b"\x00")
        return self._aead.encrypt(self._prefijo + contador, bloque, aad)


def _abrir_flujo(clave: bytes, leer: Callable[[int], bytes]) -> Iterator[bytes]:
    """Yields the plaintext chunks of an encrypted stream, verifying each one.

    A chunk is only yielded after its tag was checked, but a later chunk may still fail: callers
    must treat what they got as unusable when iteration raises ``DatosIlegiblesError``.
    """
    if len(clave) != TAMANO_CLAVE:
        raise ValueError("La clave debe tener 32 bytes")
    cabecera = leer(TAMANO_CABECERA)
    if len(cabecera) != TAMANO_CABECERA:
        raise DatosIlegiblesError("Archivo demasiado corto")
    magia, version, tamano_bloque, prefijo = _CABECERA.unpack(cabecera)
    if magia != MAGIA or version != VERSION:
        raise DatosIlegiblesError("No es un archivo cifrado de Te Tengo")
    if not 0 < tamano_bloque <= TAMANO_BLOQUE_MAXIMO:
        raise DatosIlegiblesError("Cabecera dañada")
    aead = AESGCM(clave)
    tamano_sellado = tamano_bloque + TAMANO_ETIQUETA
    actual = leer(tamano_sellado)
    contador = 0
    while True:
        siguiente = leer(tamano_sellado) if len(actual) == tamano_sellado else b""
        final = not siguiente
        if len(actual) < TAMANO_ETIQUETA or contador >= _MAX_BLOQUES:
            raise DatosIlegiblesError("Archivo truncado")
        indice = contador.to_bytes(4, "big")
        aad = cabecera + indice + (b"\x01" if final else b"\x00")
        try:
            yield aead.decrypt(prefijo + indice, actual, aad)
        except InvalidTag:
            raise DatosIlegiblesError("Archivo alterado, truncado o clave incorrecta") from None
        if final:
            return
        actual = siguiente
        contador += 1


class EscritorCifrado:
    """Write-only binary file that encrypts while it writes, chunk by chunk.

    Plaintext is only held in memory (at most one chunk); the ciphertext goes to a temporary file
    next to ``ruta`` that becomes ``ruta`` atomically on ``close()``. ``abortar()`` (or leaving the
    ``with`` block with an exception) deletes the temporary file. Not seekable, so PyAV writes a
    fragmented MP4 into it; open the PyAV container inside this writer's ``with`` block so the
    container is flushed before the writer seals the last chunk.
    """

    def __init__(self, clave: bytes, ruta: Path, tamano_bloque: int = TAMANO_BLOQUE) -> None:
        self._sellador = _Sellador(clave, tamano_bloque)
        self._ruta = ruta
        descriptor, nombre = tempfile.mkstemp(
            prefix=f".{ruta.name}.", suffix=".tmp", dir=ruta.parent
        )
        self._temporal = Path(nombre)
        self._archivo = os.fdopen(descriptor, "wb")
        self._pendiente = bytearray()
        self._escritos = 0
        self._cerrado = False
        try:
            self._archivo.write(self._sellador.cabecera)
        except BaseException:
            self.abortar()
            raise

    @property
    def ruta(self) -> Path:
        return self._ruta

    @property
    def closed(self) -> bool:
        return self._cerrado

    def writable(self) -> bool:
        return True

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        """Plaintext bytes written so far."""
        return self._escritos

    def flush(self) -> None:
        """Nothing to do: a chunk is only written once it is full or the file is closed."""

    def write(self, datos: bytes | bytearray | memoryview) -> int:
        if self._cerrado:
            raise ValueError("Escritura en un archivo cerrado")
        tamano = self._sellador.tamano_bloque
        try:
            self._pendiente += datos
            # Keep the last (possibly full) chunk in memory: it may turn out to be the final one.
            desde = 0
            while len(self._pendiente) - desde > tamano:
                bloque = bytes(self._pendiente[desde : desde + tamano])
                self._archivo.write(self._sellador.sellar(bloque, final=False))
                desde += tamano
            del self._pendiente[:desde]
        except BaseException:
            self.abortar()
            raise
        escritos = len(datos) if not isinstance(datos, memoryview) else datos.nbytes
        self._escritos += escritos
        return escritos

    def close(self) -> None:
        """Seals the final chunk and moves the file into place (no-op once closed or aborted)."""
        if self._cerrado:
            return
        try:
            self._archivo.write(self._sellador.sellar(bytes(self._pendiente), final=True))
            self._archivo.flush()
            os.fsync(self._archivo.fileno())
            self._archivo.close()
            os.replace(self._temporal, self._ruta)
        except BaseException:
            self.abortar()
            raise
        self._pendiente.clear()
        self._cerrado = True

    def abortar(self) -> None:
        """Discards everything written: no file appears at ``ruta``."""
        if self._cerrado:
            return
        self._cerrado = True
        self._pendiente.clear()
        try:
            self._archivo.close()
        finally:
            self._temporal.unlink(missing_ok=True)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        if tipo is None:
            self.close()
        else:
            self.abortar()


def cifrar_bytes(clave: bytes, datos: bytes, tamano_bloque: int = TAMANO_BLOQUE) -> bytes:
    sellador = _Sellador(clave, tamano_bloque)
    partes = [sellador.cabecera]
    vista = memoryview(datos)
    desde = 0
    while len(datos) - desde > tamano_bloque:
        partes.append(sellador.sellar(bytes(vista[desde : desde + tamano_bloque]), final=False))
        desde += tamano_bloque
    partes.append(sellador.sellar(bytes(vista[desde:]), final=True))
    return b"".join(partes)


def descifrar_bytes(clave: bytes, datos: bytes) -> bytes:
    return b"".join(_abrir_flujo(clave, io.BytesIO(datos).read))


def leer_bloques(clave: bytes, ruta: Path) -> Iterator[bytes]:
    """Yields the plaintext of ``ruta`` chunk by chunk (see ``_abrir_flujo`` on failures)."""
    with ruta.open("rb") as archivo:
        yield from _abrir_flujo(clave, archivo.read)


def abrir_descifrado(clave: bytes, ruta: Path) -> bytes:
    """The whole plaintext of ``ruta``."""
    return b"".join(leer_bloques(clave, ruta))
