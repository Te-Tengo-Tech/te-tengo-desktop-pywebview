from datetime import UTC, datetime, timedelta
from itertools import pairwise

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from te_tengo_captura.almacen.puntos import (
    ESQUEMA,
    FASES,
    NUM_PUNTOS,
    V_ERROR_MAX,
    VENTANA_MS,
    XY_ERROR_MAX,
    XY_MAX,
    XY_MIN,
    Z_ERROR_MAX,
    Z_MAX,
    Z_MIN,
    FilaMovimiento,
    Punto,
    TramoMovimientos,
    a_ms,
    cuantizar_visibilidad,
    cuantizar_xy,
    cuantizar_z,
    decuantizar_visibilidad,
    decuantizar_xy,
    decuantizar_z,
    escribir_parquet,
    instante_ms,
    iso_utc,
    leer_parquet,
)
from te_tengo_deteccion.clasificacion.estados import Fase, TipoEvento

DESDE = datetime(2026, 10, 10, 15, 0, tzinfo=UTC)
HASTA = datetime(2026, 10, 10, 15, 5, tzinfo=UTC)
T0 = a_ms(DESDE)
PASO_MS = 125  # 8 fps


def puntos(rng: np.random.Generator) -> list[Punto]:
    valores = rng.uniform([-0.1, -0.1, -1.0, 0.0], [1.1, 1.1, 1.0, 1.0], (NUM_PUNTOS, 4))
    return [(float(x), float(y), float(z), float(v)) for x, y, z, v in valores]


def fila(t_ms: int, rng: np.random.Generator | None = None, **campos: object) -> FilaMovimiento:
    landmarks = puntos(rng) if rng is not None else None
    return FilaMovimiento(t_ms, landmarks, **campos)  # type: ignore[arg-type]


# ---------------------------------------------------------------------- quantization


def test_error_de_cuantizacion_xy_dentro_del_rango() -> None:
    rng = np.random.default_rng(1)
    c = np.concatenate([rng.uniform(XY_MIN, XY_MAX, 100_000), [XY_MIN, XY_MAX, 0.0, 1.0, 0.5]])
    error = np.abs(decuantizar_xy(cuantizar_xy(c)) - c)
    assert error.max() <= XY_ERROR_MAX + 1e-12


def test_error_de_cuantizacion_z_dentro_del_rango() -> None:
    rng = np.random.default_rng(2)
    z = np.concatenate([rng.uniform(Z_MIN, Z_MAX, 100_000), [Z_MIN, Z_MAX, 0.0, -1.0, 1.0]])
    error = np.abs(decuantizar_z(cuantizar_z(z)) - z)
    assert error.max() <= Z_ERROR_MAX + 1e-12
    assert pytest.approx((-4.0, 4.0), abs=1e-3) == (Z_MIN, Z_MAX)


def test_error_de_cuantizacion_visibilidad() -> None:
    rng = np.random.default_rng(3)
    v = np.concatenate([rng.uniform(0.0, 1.0, 100_000), [0.0, 1.0]])
    error = np.abs(decuantizar_visibilidad(cuantizar_visibilidad(v)) - v)
    assert error.max() <= V_ERROR_MAX + 1e-12


def test_bordes_exactos() -> None:
    assert cuantizar_xy([XY_MIN, XY_MAX]).tolist() == [0, 65535]
    assert decuantizar_xy([0, 65535]).tolist() == [XY_MIN, XY_MAX]
    assert cuantizar_z([0.0, Z_MIN, Z_MAX]).tolist() == [0, -32768, 32767]
    assert cuantizar_visibilidad([0.0, 1.0]).tolist() == [0, 255]


def test_fuera_de_rango_se_recorta_al_borde() -> None:
    rng = np.random.default_rng(4)
    afuera = np.concatenate([rng.uniform(-50, XY_MIN, 1000), rng.uniform(XY_MAX, 50, 1000)])
    q = cuantizar_xy(afuera)
    assert set(q[:1000].tolist()) == {0}
    assert set(q[1000:].tolist()) == {65535}
    assert cuantizar_z([-9.0, 9.0, -1e9]).tolist() == [-32768, 32767, -32768]
    assert cuantizar_visibilidad([-0.3, 1.7]).tolist() == [0, 255]


def test_valores_no_finitos_no_detienen_el_guardado() -> None:
    assert cuantizar_xy([np.nan, np.inf, -np.inf]).tolist() == [cuantizar_xy([0.0])[0], 65535, 0]
    assert cuantizar_z([np.nan, np.inf, -np.inf]).tolist() == [0, 32767, -32768]
    assert cuantizar_visibilidad([np.nan, np.inf, -np.inf]).tolist() == [0, 255, 0]


def test_tipos_enteros() -> None:
    assert cuantizar_xy([0.5]).dtype == np.uint16
    assert cuantizar_z([0.5]).dtype == np.int16
    assert cuantizar_visibilidad([0.5]).dtype == np.uint8


# ---------------------------------------------------------------------- file


def test_ida_y_vuelta() -> None:
    rng = np.random.default_rng(5)
    filas = [
        fila(T0, rng, theta=82.5, p=0.4, v=0.1),
        fila(T0 + 125, rng, theta=30.0, p=1.8, v=1.4, fase=Fase.INICIO_CAIDA),
        fila(T0 + 250, None, fase=Fase.EN_EL_SUELO, evento=TipoEvento.CAIDA),
        fila(T0 + 375, rng, fase=Fase.EN_EL_SUELO, evento=TipoEvento.CAIDA_CONFIRMADA),
    ]
    metadatos, leidas = leer_parquet(escribir_parquet(filas, "cam-1", DESDE, HASTA))
    assert len(leidas) == len(filas)
    for original, leida in zip(filas, leidas, strict=True):
        assert leida.t_ms == original.t_ms
        assert (leida.fase, leida.evento) == (original.fase, original.evento)
        for campo in ("theta", "p", "v"):
            esperado = getattr(original, campo)
            assert getattr(leida, campo) == (None if esperado is None else pytest.approx(esperado))
        if original.landmarks is None:
            assert leida.landmarks is None
            continue
        assert leida.landmarks is not None
        a, b = np.array(original.landmarks), np.array(leida.landmarks)
        assert np.abs(a[:, :2] - b[:, :2]).max() <= XY_ERROR_MAX + 1e-12
        assert np.abs(a[:, 2] - b[:, 2]).max() <= Z_ERROR_MAX + 1e-12
        assert np.abs(a[:, 3] - b[:, 3]).max() <= V_ERROR_MAX + 1e-12
    assert isinstance(leidas[2].fase, Fase)
    assert metadatos["camara_id"] == "cam-1"


def test_columnas_tipos_y_orden() -> None:
    rng = np.random.default_rng(6)
    tabla = pq.read_table(pa.BufferReader(escribir_parquet([fila(T0, rng)], "c", DESDE, HASTA)))
    nombres = tabla.schema.names
    assert nombres[:6] == ["t_ms", "pose_presente", "x00", "y00", "z00", "v00"]
    assert nombres[-9:] == ["x32", "y32", "z32", "v32", "theta", "p", "v", "fase", "evento"]
    assert len(nombres) == 2 + 4 * NUM_PUNTOS + 5
    tipos = {campo.name: str(campo.type) for campo in tabla.schema}
    assert (tipos["t_ms"], tipos["pose_presente"]) == ("int64", "bool")
    assert (tipos["x07"], tipos["y07"], tipos["z07"], tipos["v07"]) == (
        "uint16",
        "uint16",
        "int16",
        "uint8",
    )
    assert (tipos["theta"], tipos["p"], tipos["v"]) == ("float", "float", "float")
    assert tipos["fase"] == tipos["evento"] == "dictionary<values=string, indices=int8, ordered=0>"
    assert tabla.schema.remove_metadata().equals(ESQUEMA)


def test_sin_pose_los_puntos_son_nulos() -> None:
    tabla = pq.read_table(pa.BufferReader(escribir_parquet([fila(T0)], "c", DESDE, HASTA)))
    assert tabla.column("pose_presente").to_pylist() == [False]
    for i in range(NUM_PUNTOS):
        for letra in "xyzv":
            assert tabla.column(f"{letra}{i:02d}").null_count == 1
    assert tabla.column("theta").to_pylist() == [None]
    assert tabla.column("evento").to_pylist() == [None]
    assert tabla.column("fase").to_pylist() == ["normal"]


def test_metadatos_del_archivo() -> None:
    datos = escribir_parquet([], "cam-sala", DESDE, HASTA + timedelta(milliseconds=7))
    metadatos = pq.ParquetFile(pa.BufferReader(datos)).metadata.metadata
    assert metadatos[b"formato"] == b"te-tengo-movimientos"
    assert metadatos[b"version"] == b"1"
    assert metadatos[b"camara_id"] == b"cam-sala"
    assert metadatos[b"desde"] == b"2026-10-10T15:00:00.000Z"
    assert metadatos[b"hasta"] == b"2026-10-10T15:05:00.007Z"
    assert metadatos[b"fps_objetivo"] == b"8"
    leidos, filas = leer_parquet(datos)
    assert filas == []
    assert set(leidos) == {"formato", "version", "camara_id", "desde", "hasta", "fps_objetivo"}


def test_usa_zstd_y_un_solo_grupo_de_filas() -> None:
    rng = np.random.default_rng(8)
    filas = [fila(T0 + k * PASO_MS, rng) for k in range(50)]
    archivo = pq.ParquetFile(pa.BufferReader(escribir_parquet(filas, "c", DESDE, HASTA)))
    assert archivo.metadata.num_row_groups == 1
    grupo = archivo.metadata.row_group(0)
    assert grupo.num_rows == 50
    assert {grupo.column(i).compression for i in range(grupo.num_columns)} == {"ZSTD"}
    assert grupo.column(0).compression == "ZSTD"
    nombres = [grupo.column(i).path_in_schema for i in range(grupo.num_columns)]
    assert "RLE_DICTIONARY" in grupo.column(nombres.index("fase")).encodings


def test_instantes_iso_y_ms() -> None:
    assert iso_utc(datetime(2026, 1, 2, 3, 4, 5, 678_901, tzinfo=UTC)) == "2026-01-02T03:04:05.678Z"
    lima = datetime(2026, 1, 2, 10, 0, tzinfo=UTC).astimezone(datetime.now(UTC).astimezone().tzinfo)
    assert iso_utc(lima) == "2026-01-02T10:00:00.000Z"
    with pytest.raises(ValueError, match="zona horaria"):
        iso_utc(datetime(2026, 1, 2))
    assert a_ms(instante_ms(1_791_234_567_891)) == 1_791_234_567_891


def test_archivo_ajeno_y_puntos_incompletos() -> None:
    salida = pa.BufferOutputStream()
    pq.write_table(pa.table({"a": [1]}), salida)
    with pytest.raises(ValueError, match="movimientos"):
        leer_parquet(salida.getvalue().to_pybytes())
    with pytest.raises(ValueError, match="33"):
        FilaMovimiento(T0, [(0.0, 0.0, 0.0, 0.0)])


def test_fases_y_eventos_validos() -> None:
    assert FASES == ("normal", "inicio_caida", "en_el_suelo")


# ---------------------------------------------------------------------- windows


def test_la_ventana_se_cierra_en_el_limite_de_5_minutos() -> None:
    tramo = TramoMovimientos("cam-1")
    inicio = T0 + 4 * 60_000  # 15:04:00
    cerrados = []
    t = inicio
    while t < T0 + VENTANA_MS + 30_000:  # until 15:05:30
        cerrados += tramo.agregar(fila(t))
        t += PASO_MS
    assert len(cerrados) == 1
    primero = cerrados[0]
    assert (primero.desde, primero.hasta) == (instante_ms(inicio), HASTA)  # started mid-window
    assert primero.n_filas == 60 * 8
    metadatos, filas = leer_parquet(primero.datos)
    assert (metadatos["desde"], metadatos["hasta"]) == (
        "2026-10-10T15:04:00.000Z",
        "2026-10-10T15:05:00.000Z",
    )
    assert all(T0 <= f.t_ms < T0 + VENTANA_MS for f in filas)

    assert tramo.n_filas == 30 * 8
    (segundo,) = tramo.cerrar()
    # Continuous capture: the next file starts where the previous one ended.
    assert segundo.desde == HASTA
    assert segundo.hasta_ms == t - PASO_MS + 1
    assert segundo.n_filas == 30 * 8
    assert segundo.hasta > segundo.desde
    assert tramo.cerrar() == []


def test_ventanas_alineadas_al_reloj_utc() -> None:
    tramo = TramoMovimientos("c")
    cerrados = []
    for k in range(0, 16 * 60 * 8):  # 16 minutes from 15:00:00.000
        cerrados += tramo.agregar(fila(T0 + k * PASO_MS))
    cerrados += tramo.cerrar()
    assert [c.desde.strftime("%H:%M") for c in cerrados] == ["15:00", "15:05", "15:10", "15:15"]
    assert [c.n_filas for c in cerrados] == [2400, 2400, 2400, 480]
    for anterior, siguiente in pairwise(cerrados):
        assert anterior.hasta == siguiente.desde
    assert all(c.hasta_ms - c.desde_ms <= VENTANA_MS for c in cerrados)


def test_ventana_vacia_no_se_emite() -> None:
    assert TramoMovimientos("c").cerrar() == []


def test_una_pausa_no_se_muestra_como_cubierta() -> None:
    tramo = TramoMovimientos("c")
    assert tramo.agregar(fila(T0 + 60_000)) == []
    assert tramo.agregar(fila(T0 + 61_000)) == []
    # Consent paused for an hour: the first file ends after its last frame.
    (cerrado,) = tramo.agregar(fila(T0 + 3_600_000 + 4_000))
    assert (cerrado.desde_ms, cerrado.hasta_ms) == (T0 + 60_000, T0 + 61_001)
    (siguiente,) = tramo.cerrar()
    assert siguiente.desde_ms == T0 + 3_600_000 + 4_000


def test_un_salto_atras_del_reloj_no_rompe_el_tramo() -> None:
    tramo = TramoMovimientos("c")
    tramo.agregar(fila(T0 + 10_000))
    tramo.agregar(fila(T0 + 5_000))  # same window, earlier
    (cerrado,) = tramo.agregar(fila(T0 - 1_000))  # previous window
    assert (cerrado.desde_ms, cerrado.hasta_ms) == (T0 + 5_000, T0 + 10_001)
    (otro,) = tramo.cerrar()
    assert otro.hasta > otro.desde


def test_la_ventana_no_supera_10_minutos() -> None:
    with pytest.raises(ValueError, match="10 minutos"):
        TramoMovimientos("c", ventana_ms=11 * 60_000)
    tramo = TramoMovimientos("c", ventana_ms=10 * 60_000)
    tramo.agregar(fila(T0))
    (cerrado,) = tramo.agregar(fila(T0 + 10 * 60_000))
    assert cerrado.hasta_ms - cerrado.desde_ms <= 10 * 60_000
