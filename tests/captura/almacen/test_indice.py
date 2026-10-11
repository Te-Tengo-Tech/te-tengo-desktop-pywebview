import sqlite3
import threading
from pathlib import Path

import pytest

from te_tengo_captura.almacen.indice import IndiceArchivos, TipoArchivo

MIN = 60_000
T0 = 1_791_000_000_000


class Reloj:
    def __init__(self) -> None:
        self.ahora = 1_000.0

    def __call__(self) -> float:
        return self.ahora


@pytest.fixture
def indice(tmp_path: Path) -> IndiceArchivos:
    return IndiceArchivos(tmp_path / "indice.sqlite3", reloj=Reloj())


def registrar(
    indice: IndiceArchivos,
    tipo: TipoArchivo,
    minuto: int,
    camara: str = "cam-1",
    tamano: int = 100,
    duracion_min: int = 5,
) -> int:
    return indice.registrar(
        tipo,
        camara,
        T0 + minuto * MIN,
        T0 + (minuto + duracion_min) * MIN,
        f"{tipo.value}/{camara}/{minuto:04d}.ttg",
        tamano,
    )


def test_registrar_y_leer(indice: IndiceArchivos) -> None:
    id_ = indice.registrar(
        TipoArchivo.CLIP, "cam-1", T0, T0 + 12_000, "clips/a.ttg", 2048, sha256="ab" * 32
    )
    archivo = indice.obtener(id_)
    assert archivo is not None
    assert (archivo.tipo, archivo.camara_id, archivo.ruta) == (
        TipoArchivo.CLIP,
        "cam-1",
        "clips/a.ttg",
    )
    assert (archivo.desde_ms, archivo.hasta_ms, archivo.tamano_bytes) == (T0, T0 + 12_000, 2048)
    assert (archivo.creado_ms, archivo.subido, archivo.sha256) == (1_000_000, False, "ab" * 32)
    assert indice.obtener(id_ + 1) is None


def test_validaciones(indice: IndiceArchivos) -> None:
    for ruta in ("/abs/x.ttg", "../fuera.ttg", "a/../../b", ""):
        with pytest.raises(ValueError, match="relativa"):
            indice.registrar(TipoArchivo.VIDEO, "c", T0, T0 + 1, ruta, 1)
    with pytest.raises(ValueError, match="hasta_ms"):
        indice.registrar(TipoArchivo.VIDEO, "c", T0, T0, "v.ttg", 1)
    with pytest.raises(ValueError, match="negativo"):
        indice.registrar(TipoArchivo.VIDEO, "c", T0, T0 + 1, "v.ttg", -1)
    with pytest.raises(ValueError, match="foto"):
        indice.registrar("foto", "c", T0, T0 + 1, "f.ttg", 1)  # type: ignore[arg-type]
    indice.registrar(TipoArchivo.VIDEO, "c", T0, T0 + 1, "v.ttg", 1)
    with pytest.raises(sqlite3.IntegrityError):
        indice.registrar(TipoArchivo.VIDEO, "c", T0, T0 + 1, "v.ttg", 1)


def test_el_tipo_esta_restringido_en_la_base(tmp_path: Path) -> None:
    IndiceArchivos(tmp_path / "i.sqlite3").cerrar()
    db = sqlite3.connect(tmp_path / "i.sqlite3")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO archivos (tipo, camara_id, desde_ms, hasta_ms, ruta, tamano_bytes,"
            " creado_ms) VALUES ('foto', 'c', 0, 1, 'x', 1, 0)"
        )
    indices = {fila[1] for fila in db.execute("PRAGMA index_list('archivos')")}
    assert {"archivos_tipo_desde", "archivos_camara_desde"} <= indices


def test_en_rango_devuelve_los_que_se_superponen(indice: IndiceArchivos) -> None:
    for minuto in (0, 5, 10, 15):
        registrar(indice, TipoArchivo.MOVIMIENTOS, minuto)
    registrar(indice, TipoArchivo.MOVIMIENTOS, 5, camara="cam-2")
    registrar(indice, TipoArchivo.VIDEO, 0, duracion_min=10)
    encontrados = indice.en_rango("cam-1", TipoArchivo.MOVIMIENTOS, T0 + 7 * MIN, T0 + 10 * MIN)
    assert [a.desde_ms for a in encontrados] == [T0 + 5 * MIN]  # [10, 15) only touches the end
    encontrados = indice.en_rango("cam-1", TipoArchivo.MOVIMIENTOS, T0 + 4 * MIN, T0 + 11 * MIN)
    assert [a.desde_ms for a in encontrados] == [T0, T0 + 5 * MIN, T0 + 10 * MIN]
    assert indice.en_rango("cam-3", TipoArchivo.MOVIMIENTOS, T0, T0 + 60 * MIN) == []


def test_mas_antiguos_y_anteriores_a(indice: IndiceArchivos) -> None:
    for minuto in (20, 0, 10):
        registrar(indice, TipoArchivo.VIDEO, minuto, duracion_min=10)
    registrar(indice, TipoArchivo.CLIP, -100, duracion_min=1)
    assert [a.desde_ms for a in indice.mas_antiguos(TipoArchivo.VIDEO, 2)] == [T0, T0 + 10 * MIN]
    anteriores = indice.anteriores_a(TipoArchivo.VIDEO, T0 + 20 * MIN)
    assert [a.desde_ms for a in anteriores] == [T0, T0 + 10 * MIN]  # ended at or before
    assert indice.anteriores_a(TipoArchivo.VIDEO, T0 + 19 * MIN) == anteriores[:1]


def test_uso_por_tipo(indice: IndiceArchivos) -> None:
    assert indice.uso_por_tipo() == dict.fromkeys(TipoArchivo, 0)
    registrar(indice, TipoArchivo.VIDEO, 0, tamano=1_000)
    registrar(indice, TipoArchivo.VIDEO, 10, tamano=500)
    registrar(indice, TipoArchivo.CLIP, 0, tamano=30)
    assert indice.uso_por_tipo() == {
        TipoArchivo.MOVIMIENTOS: 0,
        TipoArchivo.VIDEO: 1_500,
        TipoArchivo.CLIP: 30,
    }


def test_subidas_pendientes(indice: IndiceArchivos) -> None:
    a = registrar(indice, TipoArchivo.MOVIMIENTOS, 0)
    b = registrar(indice, TipoArchivo.MOVIMIENTOS, 5)
    registrar(indice, TipoArchivo.VIDEO, 0)
    assert [x.id for x in indice.pendientes_de_subir(TipoArchivo.MOVIMIENTOS)] == [a, b]
    indice.marcar_subido(a)
    assert [x.id for x in indice.pendientes_de_subir(TipoArchivo.MOVIMIENTOS)] == [b]
    archivo = indice.obtener(a)
    assert archivo is not None
    assert archivo.subido


def test_disponibles_desde_y_borrar(indice: IndiceArchivos) -> None:
    assert indice.disponibles_desde("cam-1", TipoArchivo.MOVIMIENTOS) is None
    a = registrar(indice, TipoArchivo.MOVIMIENTOS, 0)
    registrar(indice, TipoArchivo.MOVIMIENTOS, 5)
    registrar(indice, TipoArchivo.MOVIMIENTOS, -50, camara="cam-2")
    assert indice.disponibles_desde("cam-1", TipoArchivo.MOVIMIENTOS) == T0
    indice.borrar(a)
    assert indice.disponibles_desde("cam-1", TipoArchivo.MOVIMIENTOS) == T0 + 5 * MIN
    assert indice.rutas_conocidas() == {"movimientos/cam-1/0005.ttg", "movimientos/cam-2/-050.ttg"}


def test_sobrevive_a_un_reinicio(tmp_path: Path) -> None:
    primero = IndiceArchivos(tmp_path / "i.sqlite3")
    registrar(primero, TipoArchivo.VIDEO, 0)
    primero.cerrar()
    segundo = IndiceArchivos(tmp_path / "i.sqlite3")
    assert segundo.rutas_conocidas() == {"video/cam-1/0000.ttg"}


def test_uso_desde_varios_hilos(indice: IndiceArchivos) -> None:
    def trabajar(camara: str) -> None:
        for minuto in range(0, 100, 5):
            registrar(indice, TipoArchivo.MOVIMIENTOS, minuto, camara=camara, tamano=1)
            indice.uso_por_tipo()

    hilos = [threading.Thread(target=trabajar, args=(f"cam-{n}",)) for n in range(4)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert indice.uso_por_tipo()[TipoArchivo.MOVIMIENTOS] == 80
