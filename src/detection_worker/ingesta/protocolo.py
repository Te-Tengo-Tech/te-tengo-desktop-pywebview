"""Formato de los mensajes que envía el Agente de captura (ver docs/ingestion-protocol.md).

Cada fotograma viaja en un mensaje binario de WebSocket:

    [8 bytes: instante de captura en milisegundos, entero sin signo big-endian][JPEG]
"""

import struct

_CABECERA = struct.Struct(">Q")
_INICIO_JPEG = b"\xff\xd8"


class MensajeInvalidoError(ValueError):
    """El mensaje no respeta el protocolo de ingesta."""


def codificar(instante_ms: int, jpeg: bytes) -> bytes:
    return _CABECERA.pack(instante_ms) + jpeg


def decodificar(mensaje: bytes) -> tuple[int, bytes]:
    """Devuelve ``(instante_ms, jpeg)``."""
    if len(mensaje) <= _CABECERA.size:
        raise MensajeInvalidoError("Mensaje demasiado corto")
    (instante_ms,) = _CABECERA.unpack_from(mensaje)
    jpeg = mensaje[_CABECERA.size :]
    if not jpeg.startswith(_INICIO_JPEG):
        raise MensajeInvalidoError("El contenido no es un JPEG")
    return instante_ms, jpeg
