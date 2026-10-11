import base64
import io
import logging
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import pytest

from te_tengo_captura.almacen.cifrado import (
    MAGIA,
    SERVICIO,
    TAMANO_BLOQUE,
    TAMANO_CABECERA,
    TAMANO_ETIQUETA,
    USUARIO,
    ClaveDatos,
    ClaveInvalidaError,
    DatosIlegiblesError,
    EscritorCifrado,
    abrir_descifrado,
    cifrar_bytes,
    descifrar_bytes,
    leer_bloques,
)

CLAVE = bytes(range(32))
OTRA_CLAVE = bytes(range(1, 33))
BLOQUE = 64  # small chunks so the tests cross many chunk boundaries


class AlmacenEnMemoria:
    def __init__(self) -> None:
        self.secretos: dict[tuple[str, str], str] = {}
        self.escrituras = 0

    def get_password(self, servicio: str, usuario: str, /) -> str | None:
        return self.secretos.get((servicio, usuario))

    def set_password(self, servicio: str, usuario: str, secreto: str, /) -> None:
        self.escrituras += 1
        self.secretos[(servicio, usuario)] = secreto

    def delete_password(self, servicio: str, usuario: str, /) -> None:
        del self.secretos[(servicio, usuario)]


# ---------------------------------------------------------------------- key


def test_la_clave_se_crea_una_vez_y_se_guarda_en_el_almacen() -> None:
    almacen = AlmacenEnMemoria()
    clave = ClaveDatos(almacen).obtener()
    assert len(clave) == 32
    assert base64.b64decode(almacen.secretos[(SERVICIO, USUARIO)]) == clave
    # A new process (a new provider) reads the same key and does not create another one.
    assert ClaveDatos(almacen).obtener() == clave
    assert almacen.escrituras == 1


def test_borrar_la_clave_vuelve_ilegibles_los_datos() -> None:
    almacen = AlmacenEnMemoria()
    proveedor = ClaveDatos(almacen)
    cifrado = cifrar_bytes(proveedor.obtener(), b"movimientos")
    proveedor.borrar()
    assert almacen.secretos == {}
    proveedor.borrar()  # deleting twice is harmless
    with pytest.raises(DatosIlegiblesError):
        descifrar_bytes(proveedor.obtener(), cifrado)


def test_una_clave_guardada_danada_se_informa() -> None:
    almacen = AlmacenEnMemoria()
    almacen.secretos[(SERVICIO, USUARIO)] = base64.b64encode(b"corta").decode()
    with pytest.raises(ClaveInvalidaError):
        ClaveDatos(almacen).obtener()
    almacen.secretos[(SERVICIO, USUARIO)] = "no es base64!"
    with pytest.raises(ClaveInvalidaError):
        ClaveDatos(almacen).obtener()


def test_la_clave_nunca_aparece_en_repr_ni_en_el_registro(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    almacen = AlmacenEnMemoria()
    proveedor = ClaveDatos(almacen)
    clave = proveedor.obtener()
    texto = almacen.secretos[(SERVICIO, USUARIO)]
    assert texto not in repr(proveedor)
    assert texto not in caplog.text
    assert clave.hex() not in caplog.text


# ---------------------------------------------------------------------- format


@pytest.mark.parametrize("tamano", [0, 1, BLOQUE - 1, BLOQUE, BLOQUE + 1, 3 * BLOQUE, 1000])
def test_ida_y_vuelta_en_memoria(tamano: int) -> None:
    datos = bytes(np.random.default_rng(tamano).integers(0, 256, tamano, dtype=np.uint8))
    cifrado = cifrar_bytes(CLAVE, datos, BLOQUE)
    assert cifrado[:4] == MAGIA
    bloques = max(1, -(-tamano // BLOQUE))
    assert len(cifrado) == TAMANO_CABECERA + tamano + bloques * TAMANO_ETIQUETA
    assert descifrar_bytes(CLAVE, cifrado) == datos


def test_el_texto_no_aparece_en_el_archivo(tmp_path: Path) -> None:
    datos = b"Living room, Mama, 07:15 " * 1000
    ruta = tmp_path / "x.bin"
    with EscritorCifrado(CLAVE, ruta) as escritor:
        escritor.write(datos)
    contenido = ruta.read_bytes()
    assert b"Living room" not in contenido
    assert abrir_descifrado(CLAVE, ruta) == datos


def test_escritor_en_trozos_y_lectura_por_bloques(tmp_path: Path) -> None:
    rng = np.random.default_rng(7)
    datos = bytes(rng.integers(0, 256, 1000, dtype=np.uint8))
    ruta = tmp_path / "x.bin"
    escritor = EscritorCifrado(CLAVE, ruta, BLOQUE)
    assert (escritor.writable(), escritor.seekable(), escritor.readable()) == (True, False, False)
    desde = 0
    for paso in (1, 7, 64, 65, 200, 3):
        escritor.write(memoryview(datos[desde : desde + paso]))
        desde += paso
    escritor.write(datos[desde:])
    assert escritor.tell() == len(datos)
    assert not ruta.exists()  # appears only on close
    escritor.close()
    escritor.close()  # idempotent
    assert escritor.closed
    bloques = list(leer_bloques(CLAVE, ruta))
    assert [len(b) for b in bloques[:-1]] == [BLOQUE] * (len(bloques) - 1)
    assert b"".join(bloques) == datos
    assert list(tmp_path.iterdir()) == [ruta]


def test_un_archivo_vacio_tiene_un_bloque_final(tmp_path: Path) -> None:
    ruta = tmp_path / "vacio.bin"
    with EscritorCifrado(CLAVE, ruta):
        pass
    assert ruta.stat().st_size == TAMANO_CABECERA + TAMANO_ETIQUETA
    assert abrir_descifrado(CLAVE, ruta) == b""


def test_abortar_no_deja_archivos(tmp_path: Path) -> None:
    ruta = tmp_path / "x.bin"
    escritor = EscritorCifrado(CLAVE, ruta, BLOQUE)
    escritor.write(b"a" * 500)
    escritor.abortar()
    escritor.close()  # nothing happens after an abort
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(ValueError, match="cerrado"):
        escritor.write(b"b")


def test_una_excepcion_dentro_del_bloque_with_descarta(tmp_path: Path) -> None:
    ruta = tmp_path / "x.bin"

    def escribir_y_fallar() -> None:
        with EscritorCifrado(CLAVE, ruta) as escritor:
            escritor.write(b"datos")
            raise RuntimeError("fallo al codificar")

    with pytest.raises(RuntimeError):
        escribir_y_fallar()
    assert list(tmp_path.iterdir()) == []


def test_cerrar_reemplaza_un_archivo_anterior(tmp_path: Path) -> None:
    ruta = tmp_path / "x.bin"
    ruta.write_bytes(b"viejo")
    with EscritorCifrado(CLAVE, ruta) as escritor:
        escritor.write(b"nuevo")
    assert abrir_descifrado(CLAVE, ruta) == b"nuevo"


# ---------------------------------------------------------------------- tampering


def _cifrado(bloques: int = 4) -> bytes:
    return cifrar_bytes(CLAVE, bytes(range(256))[: BLOQUE * bloques - 10], BLOQUE)


def _sellado(n: int) -> slice:
    inicio = TAMANO_CABECERA + n * (BLOQUE + TAMANO_ETIQUETA)
    return slice(inicio, inicio + BLOQUE + TAMANO_ETIQUETA)


def test_clave_incorrecta() -> None:
    with pytest.raises(DatosIlegiblesError):
        descifrar_bytes(OTRA_CLAVE, _cifrado())


def test_un_bit_cambiado() -> None:
    for posicion in (TAMANO_CABECERA + 3, len(_cifrado()) - 1, 6):  # chunk, last tag, header
        datos = bytearray(_cifrado())
        datos[posicion] ^= 0x01
        with pytest.raises(DatosIlegiblesError):
            descifrar_bytes(CLAVE, bytes(datos))


def test_bloques_reordenados() -> None:
    datos = _cifrado()
    cambiado = (
        datos[: _sellado(0).start]
        + datos[_sellado(1)]
        + datos[_sellado(0)]
        + datos[_sellado(2).start :]
    )
    assert len(cambiado) == len(datos)
    with pytest.raises(DatosIlegiblesError):
        descifrar_bytes(CLAVE, cambiado)


@pytest.mark.parametrize("bloques_conservados", [1, 2, 3])
def test_truncado_en_el_limite_de_un_bloque(bloques_conservados: int) -> None:
    datos = _cifrado()
    with pytest.raises(DatosIlegiblesError):
        descifrar_bytes(CLAVE, datos[: _sellado(bloques_conservados).start])


def test_truncado_dentro_de_un_bloque_o_en_la_cabecera() -> None:
    datos = _cifrado()
    for largo in (0, 3, TAMANO_CABECERA, TAMANO_CABECERA + 5, len(datos) - 1):
        with pytest.raises(DatosIlegiblesError):
            descifrar_bytes(CLAVE, datos[:largo])


def test_datos_agregados_al_final() -> None:
    datos = _cifrado()
    for extra in (b"x", datos[_sellado(0)], datos[TAMANO_CABECERA:]):
        with pytest.raises(DatosIlegiblesError):
            descifrar_bytes(CLAVE, datos + extra)


def test_bloque_de_otro_archivo() -> None:
    a, b = _cifrado(), _cifrado()  # same key and content, different nonce prefix
    with pytest.raises(DatosIlegiblesError):
        descifrar_bytes(CLAVE, a[: _sellado(1).start] + b[_sellado(1).start :])


def test_no_es_un_archivo_nuestro() -> None:
    with pytest.raises(DatosIlegiblesError):
        descifrar_bytes(CLAVE, b"\x00\x00\x00\x18ftypisom" + bytes(100))
    datos = bytearray(_cifrado())
    datos[5:9] = (0xFFFFFFFF).to_bytes(4, "big")  # absurd chunk size
    with pytest.raises(DatosIlegiblesError):
        descifrar_bytes(CLAVE, bytes(datos))


def test_claves_y_bloques_invalidos() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        cifrar_bytes(b"corta", b"")
    with pytest.raises(ValueError, match="32 bytes"):
        descifrar_bytes(b"corta", _cifrado())
    with pytest.raises(ValueError, match="bloque"):
        cifrar_bytes(CLAVE, b"", tamano_bloque=0)


def test_el_tamano_de_bloque_por_defecto_es_1_mib() -> None:
    assert TAMANO_BLOQUE == 1 << 20
    cifrado = cifrar_bytes(CLAVE, b"x")
    assert int.from_bytes(cifrado[5:9], "big") == 1 << 20


# ---------------------------------------------------------------------- PyAV


def test_pyav_escribe_un_mp4_fragmentado_cifrado(tmp_path: Path) -> None:
    ruta = tmp_path / "tramo.mp4.ttg"
    fps, n = 8, 16
    rng = np.random.default_rng(3)
    with (
        EscritorCifrado(CLAVE, ruta, tamano_bloque=4096) as escritor,
        av.open(
            escritor,
            mode="w",
            format="mp4",
            options={"movflags": "frag_keyframe+empty_moov+default_base_moof"},
        ) as contenedor,
    ):
        flujo = contenedor.add_stream("libx264", rate=Fraction(fps))
        flujo.codec_context.width, flujo.codec_context.height = 64, 48
        flujo.codec_context.pix_fmt = "yuv420p"
        flujo.codec_context.gop_size = fps
        for indice in range(n):
            imagen = rng.integers(0, 256, (48, 64, 3), dtype=np.uint8)
            cuadro = av.VideoFrame.from_ndarray(imagen, format="rgb24")
            cuadro.pts = indice
            contenedor.mux(flujo.encode(cuadro))
        contenedor.mux(flujo.encode(None))
    assert escritor.closed
    assert ruta.exists()
    contenido = ruta.read_bytes()
    assert b"ftyp" not in contenido
    assert b"moof" not in contenido

    mp4 = abrir_descifrado(CLAVE, ruta)
    assert mp4[4:8] == b"ftyp"
    with av.open(io.BytesIO(mp4), mode="r") as entrada:
        cuadros = list(entrada.decode(video=0))
    assert len(cuadros) == n
    assert (cuadros[0].width, cuadros[0].height) == (64, 48)
