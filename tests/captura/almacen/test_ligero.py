"""The light replay format TTMOV v1 (AGENT_CONTRACT.md, "Light replay format"; US-36, US-39)."""

import gzip
import json
import struct
from pathlib import Path

import numpy as np
import pytest

from te_tengo_captura.almacen.ligero import (
    EXTENSION,
    escribir_ligero,
    leer_ligero,
    ruta_ligera,
)
from te_tengo_captura.almacen.puntos import (
    FilaMovimiento,
    cuantizar_visibilidad,
    cuantizar_xy,
    cuantizar_z,
    escribir_parquet,
    instante_ms,
    leer_parquet,
)
from te_tengo_deteccion.clasificacion.estados import Fase, TipoEvento

DATOS = Path(__file__).parents[2] / "fixtures"
T0 = 1_791_646_800_000  # 2026-10-10T15:40:00Z


def cuerpo(i: int) -> list[tuple[float, float, float, float]]:
    """33 landmarks that move a little every frame, some outside the image."""
    return [
        (0.1 + 0.02 * k + 0.001 * i, -0.2 + 0.04 * k - 0.002 * i, 0.3 - 0.01 * k, (k % 11) / 10)
        for k in range(33)
    ]


def filas_variadas() -> list[FilaMovimiento]:
    return [
        FilaMovimiento(T0 + 125, cuerpo(0)),
        FilaMovimiento(T0 + 250, None),  # nobody in the image
        FilaMovimiento(T0 + 375, cuerpo(2), fase=Fase.INICIO_CAIDA),
        FilaMovimiento(T0 + 500, cuerpo(3), fase=Fase.EN_EL_SUELO, evento=TipoEvento.CAIDA),
        FilaMovimiento(T0 + 90_000, cuerpo(4), evento=TipoEvento.RECUPERACION),  # a long gap
        FilaMovimiento(T0 + 89_875, cuerpo(5)),  # the clock stepped back
        FilaMovimiento(T0 + 90_000, None, evento=TipoEvento.DETECCION_NO_CONFIABLE),
        FilaMovimiento(
            T0 + 90_125,
            [(float("nan"), 2.0, -9.0, 1.5)] * 33,  # clipped like the Parquet file
            evento=TipoEvento.MOVIMIENTO_INESTABLE,
        ),
    ]


def test_cabecera_y_fotogramas_byte_a_byte() -> None:
    filas = [
        FilaMovimiento(T0 + 125, [(0.5, 0.25, 0.0, 1.0)] * 33),
        FilaMovimiento(T0 + 250, None, fase=Fase.EN_EL_SUELO, evento=TipoEvento.CAIDA_CONFIRMADA),
        FilaMovimiento(T0 + 375, [(0.5, 0.25, 0.0, 0.0)] * 33),
    ]
    datos = escribir_ligero(filas, T0, T0 + 300_000)
    assert datos[:2] == b"\x1f\x8b"  # gzip
    assert datos[4:8] == b"\x00\x00\x00\x00"  # MTIME 0
    carga = gzip.decompress(datos)
    assert carga[:24] == b"TTMV" + bytes([1, 0, 8, 33]) + struct.pack("<qII", T0, 300_000, 3)
    x, y = 32768, 24576  # (0.5 + 0.5) / 2 × 65535 and (0.25 + 0.5) / 2 × 65535, rounded
    primero = struct.pack("<iB", 125, 0b0000_0001)
    primero += struct.pack("<33H", *[x] * 33) + struct.pack("<33H", *[y] * 33) + bytes([255] * 33)
    segundo = struct.pack("<iB", 125, 0b0001_0100)  # no pose, fase 2, evento 2
    tercero = struct.pack("<iB", 125, 0b0000_0001)
    tercero += bytes(66) + bytes(66) + bytes([1] * 33)  # deltas: same x and y, v 255 → 0
    assert carga[24:] == primero + segundo + tercero
    assert len(carga) == 24 + (5 + 33 * 5) * 2 + 5


def test_ida_y_vuelta_con_los_mismos_enteros_que_el_parquet() -> None:
    filas = filas_variadas()
    archivo = leer_ligero(escribir_ligero(filas, T0, T0 + 300_000))
    assert (archivo.t0_ms, archivo.duracion_ms, archivo.fps_objetivo) == (T0, 300_000, 8)
    assert not archivo.con_z
    assert len(archivo.fotogramas) == len(filas)
    for fila, fotograma in zip(filas, archivo.fotogramas, strict=True):
        assert fotograma.t_ms == fila.t_ms
        assert fotograma.fase is fila.fase
        assert fotograma.evento is fila.evento
        assert fotograma.z is None
        if fila.landmarks is None:
            assert fotograma.x is None
            continue
        puntos = np.array(fila.landmarks)
        assert fotograma.x is not None
        assert fotograma.y is not None
        assert fotograma.v is not None
        assert (fotograma.x == cuantizar_xy(puntos[:, 0])).all()
        assert (fotograma.y == cuantizar_xy(puntos[:, 1])).all()
        assert (fotograma.v == cuantizar_visibilidad(puntos[:, 3])).all()


def test_con_z() -> None:
    filas = filas_variadas()
    archivo = leer_ligero(escribir_ligero(filas, T0, T0 + 300_000, con_z=True))
    assert archivo.con_z
    for fila, fotograma in zip(filas, archivo.fotogramas, strict=True):
        if fila.landmarks is not None:
            assert fotograma.z is not None
            assert (fotograma.z == cuantizar_z(np.array(fila.landmarks)[:, 2])).all()


def test_mismas_filas_que_el_parquet_de_un_clip_real() -> None:
    """The committed fixture: a real 12 s clip around a fall (the agent's capture loop over a
    CAUCAFall video), as Parquet; its light file decodes to the same integers."""
    metadatos, filas = leer_parquet((DATOS / "clip_caida.parquet").read_bytes())
    ligero = (DATOS / "clip_caida.ttmov").read_bytes()
    archivo = leer_ligero(ligero)
    assert metadatos["desde"].endswith("Z")
    assert archivo.duracion_ms == 12_000
    assert len(archivo.fotogramas) == len(filas) == 97
    assert [f.evento for f in archivo.fotogramas if f.evento] == [
        TipoEvento.CAIDA,
        TipoEvento.RECUPERACION,
    ]
    assert gzip.decompress(ligero) == gzip.decompress(
        escribir_ligero(filas, archivo.t0_ms, archivo.t0_ms + archivo.duracion_ms)
    )
    for fila, fotograma in zip(filas, archivo.fotogramas, strict=True):
        assert fotograma.t_ms == fila.t_ms
        if fila.landmarks is not None:
            assert fotograma.x is not None
            assert (fotograma.x == cuantizar_xy(np.array(fila.landmarks)[:, 0])).all()


@pytest.mark.parametrize("nombre", ["clip_caida", "clip_caida_z"])
def test_el_json_de_la_app_coincide(nombre: str) -> None:
    """What the app's decoder must return for the fixture (``scripts/fixture_ligero.py``)."""
    esperado = json.loads((DATOS / f"{nombre}.json").read_text(encoding="utf-8"))
    archivo = leer_ligero((DATOS / f"{nombre}.ttmov").read_bytes())
    assert esperado["t0Ms"] == archivo.t0_ms
    assert esperado["conZ"] == archivo.con_z
    for f, g in zip(esperado["fotogramas"], archivo.fotogramas, strict=True):
        assert f["tMs"] == g.t_ms
        assert f["fase"] == g.fase.value
        assert f["x"] == (None if g.x is None else g.x.tolist())


def test_un_archivo_vacio_tambien_es_valido() -> None:
    archivo = leer_ligero(escribir_ligero([], T0, T0))
    assert archivo.fotogramas == []


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        (lambda c: b"XXXX" + c[4:], "No es un archivo ligero"),
        (lambda c: c[:4] + b"\x02" + c[5:], "Versión"),
        (lambda c: c[:5] + b"\x02" + c[6:], "Versión"),  # an unknown flag
        (lambda c: c[:-1], "incompleto"),
        (lambda c: c[:10], "incompleto"),
    ],
)
def test_rechaza_lo_que_no_entiende(cambio: object, mensaje: str) -> None:
    carga = gzip.decompress(escribir_ligero(filas_variadas(), T0, T0 + 300_000))
    with pytest.raises(ValueError, match=mensaje):
        leer_ligero(gzip.compress(cambio(carga), mtime=0))  # type: ignore[operator]
    with pytest.raises(ValueError, match="gzip"):
        leer_ligero(b"PAR1")


def test_ruta_ligera() -> None:
    assert EXTENSION == ".ttmov"
    assert ruta_ligera("movimientos/c1/2026/09/23/154000.parquet.ttg") == (
        "movimientos/c1/2026/09/23/154000.ttmov.ttg"
    )
    assert ruta_ligera("e1.puntos.parquet") == "e1.puntos.ttmov"
    assert ruta_ligera("clips/c1/2026/09/23/e1.mp4.ttg") is None
    assert ruta_ligera("x.parquet/y.mp4") is None


def test_el_tramo_cerrado_trae_su_ligero() -> None:
    filas = filas_variadas()[:4]
    datos = escribir_parquet(filas, "c1", instante_ms(T0), instante_ms(T0 + 1000))
    assert leer_parquet(datos)[1][0].t_ms == T0 + 125
    from te_tengo_captura.almacen.puntos import TramoMovimientos

    tramo = TramoMovimientos("c1")
    for fila in filas:
        assert tramo.agregar(fila) == []
    [cerrado] = tramo.cerrar()
    archivo = leer_ligero(cerrado.ligero)
    assert archivo.t0_ms == cerrado.desde_ms
    assert archivo.t0_ms + archivo.duracion_ms == cerrado.hasta_ms
    assert [f.t_ms for f in archivo.fotogramas] == [f.t_ms for f in filas]
