import pytest

from detection_worker.ingesta import protocolo

JPEG = b"\xff\xd8\xff\xe0contenido"


def test_protocolo_ida_y_vuelta() -> None:
    assert protocolo.decodificar(protocolo.codificar(1_700_000_000_123, JPEG)) == (
        1_700_000_000_123,
        JPEG,
    )


@pytest.mark.parametrize("mensaje", [b"", b"12345678", protocolo.codificar(1, b"no-es-jpeg")])
def test_protocolo_rechaza_mensajes_invalidos(mensaje: bytes) -> None:
    with pytest.raises(protocolo.MensajeInvalidoError):
        protocolo.decodificar(mensaje)
