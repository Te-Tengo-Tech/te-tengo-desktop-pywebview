"""Format of the messages sent by the Capture Agent (see docs/ingestion-protocol.md).

Each frame travels in a binary WebSocket message:

    [8 bytes: capture instant in milliseconds, unsigned big-endian integer][JPEG]
"""

import struct

_CABECERA = struct.Struct(">Q")
_INICIO_JPEG = b"\xff\xd8"


class MensajeInvalidoError(ValueError):
    """The message does not follow the ingestion protocol."""


def codificar(instante_ms: int, jpeg: bytes) -> bytes:
    return _CABECERA.pack(instante_ms) + jpeg


def decodificar(mensaje: bytes) -> tuple[int, bytes]:
    """Returns ``(instante_ms, jpeg)``."""
    if len(mensaje) <= _CABECERA.size:
        raise MensajeInvalidoError("Mensaje demasiado corto")
    (instante_ms,) = _CABECERA.unpack_from(mensaje)
    jpeg = mensaje[_CABECERA.size :]
    if not jpeg.startswith(_INICIO_JPEG):
        raise MensajeInvalidoError("El contenido no es un JPEG")
    return instante_ms, jpeg
