import pytest

from detection_worker.ingesta import protocolo
from detection_worker.ingesta.buffer import BufferClip

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


def test_clip_incluye_6_s_antes_y_6_s_despues() -> None:
    buffer = BufferClip()
    clips = []
    for i in range(41):  # 0 a 20 s, cada 0,5 s
        t = i * 0.5
        if t == 10.0:
            buffer.marcar_evento("evento-1", t)
        clips += buffer.agregar(t, JPEG)
    assert len(clips) == 1
    instantes = [t for t, _ in clips[0].fotogramas]
    assert instantes[0] == 4.0
    assert instantes[-1] == 16.0
    assert clips[0].evento_id == "evento-1"


def test_buffer_descarta_fotogramas_antiguos() -> None:
    buffer = BufferClip()
    for i in range(100):
        buffer.agregar(float(i), JPEG)
    buffer.marcar_evento("e", 99.0)
    clip = next(iter(c for t in range(100, 106) for c in buffer.agregar(float(t), JPEG)))
    assert clip.fotogramas[0][0] == 93.0
