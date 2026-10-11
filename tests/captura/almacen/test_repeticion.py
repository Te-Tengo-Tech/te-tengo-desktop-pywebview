"""«Ver qué pasó» on the PC (US-39): windows, events, stretches without data, poses and video."""

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from te_tengo_captura.almacen.gestor import AlmacenLocal, GrabadorCamara
from te_tengo_captura.almacen.puntos import FilaMovimiento, a_ms
from te_tengo_captura.almacen.repeticion import (
    CONFIRMADA,
    DE_PIE,
    EN_EL_SUELO,
    INESTABLE,
    POSIBLE_CAIDA,
    SE_LEVANTO,
    Repeticion,
)
from te_tengo_captura.backend.modelos import EstadoMovimientos
from te_tengo_captura.captura.bucle import Analisis
from te_tengo_captura.captura.fuentes import Fotograma
from te_tengo_captura.vinculacion.credenciales import LlaveroEnMemoria
from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, Fase, TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

T0 = datetime(2026, 9, 23, 15, 40, tzinfo=UTC)
PUNTO = (0.5, 0.25, 0.0, 0.9)
PERMITIDO = EstadoMovimientos(
    consentimiento_vigente=True, guardar_en_la_pc=True, guardar_en_la_nube=False
)


@pytest.fixture
def almacen(tmp_path: Path) -> Iterator[AlmacenLocal]:
    a = AlmacenLocal(tmp_path / "ajustes", tmp_path / "Datos", LlaveroEnMemoria())
    a.iniciar(lambda: PERMITIDO)
    a.revisar_permiso()
    yield a
    a.detener()


def ms(segundos: float) -> int:
    return a_ms(T0 + timedelta(seconds=segundos))


def fila(segundos: float, persona: bool = True, **campos: object) -> FilaMovimiento:
    return FilaMovimiento(ms(segundos), [PUNTO] * 33 if persona else None, **campos)  # type: ignore[arg-type]


def guardar(almacen: AlmacenLocal, filas: list[FilaMovimiento]) -> None:
    grabador = GrabadorCamara(almacen, "c1")
    for f in filas:
        grabador._cola.put(("fila", f))  # waits: the test wants every row
    grabador.cerrar()


def caida() -> list[FilaMovimiento]:
    """60 s: standing, unstable at 10 s, nobody 20–35 s, a fall at 40 s, up at 52 s."""
    filas = []
    for i in range(60 * 8):
        s = i / 8
        if 20 <= s < 35:
            filas.append(fila(s, persona=False))
            continue
        fase, evento = Fase.NORMAL, None
        if s == 10:
            evento = TipoEvento.MOVIMIENTO_INESTABLE
        if 40 <= s < 41:
            fase = Fase.INICIO_CAIDA
        if 41 <= s < 52:
            fase = Fase.EN_EL_SUELO
        if s == 41:
            evento = TipoEvento.CAIDA
        if s == 46:
            evento = TipoEvento.CAIDA_CONFIRMADA
        if s == 52:
            evento = TipoEvento.RECUPERACION
        filas.append(fila(s, fase=fase, evento=evento))
    return filas


def test_ventana_con_eventos_y_tramos_sin_datos(almacen: AlmacenLocal) -> None:
    guardar(almacen, caida())
    r = Repeticion(almacen, zona=UTC)
    assert r.permitida
    assert r.datos_desde("c1") == ms(0)
    assert r.datos_hasta("c1") == ms(59.875) + 1  # just after the last row
    assert [d.isoformat() for d in r.dias("c1")] == ["2026-09-23"]
    ventana = r.abrir("c1", ms(-30), ms(90))
    assert ventana["hayDatos"] is True
    assert [(e["t"], e["k"], e["l"]) for e in ventana["eventos"]] == [
        (ms(10), "inestable", "Inestable"),
        (ms(41), "caida", "Caída"),
        (ms(52), "calma", "Se levantó"),
    ]
    huecos = [(h["a"], h["b"], h["corto"]) for h in ventana["huecos"]]
    assert huecos[0] == (ms(-30), ms(0), "Sin captura")  # before the file: PC off or paused
    assert (ms(20), ms(35), "Sin persona") in huecos  # CA-39.5
    assert huecos[-1][2] == "Sin captura"
    assert ventana["video"] is False


def test_poses_con_su_fase(almacen: AlmacenLocal) -> None:
    guardar(almacen, caida())
    r = Repeticion(almacen, zona=UTC)
    poses = r.poses("c1", ms(0), ms(60))
    assert poses["claves"][0] == "h"
    assert len(poses["p"][0]) == 26  # 13 joints, x and y
    assert poses["p"][0][:2] == [0.5, 0.25]
    fase = dict(zip(poses["t"], poses["f"], strict=True))
    assert fase[ms(1)] == DE_PIE
    assert fase[ms(10)] == INESTABLE
    assert fase[ms(40)] == POSIBLE_CAIDA
    assert fase[ms(42)] == EN_EL_SUELO
    assert fase[ms(47)] == CONFIRMADA
    assert fase[ms(53)] == SE_LEVANTO
    assert poses["p"][poses["t"].index(ms(25))] is None  # nobody in the image


def test_sin_archivos_no_hay_datos(almacen: AlmacenLocal) -> None:
    r = Repeticion(almacen, zona=UTC)
    assert r.datos_desde("c1") is None
    ventana = r.abrir("c1", ms(0), ms(600))
    assert ventana["hayDatos"] is False
    assert ventana["eventos"] == []
    assert [h["corto"] for h in ventana["huecos"]] == ["Sin captura"]


def test_sin_permiso_no_se_repite(tmp_path: Path) -> None:
    almacen = AlmacenLocal(tmp_path / "ajustes", tmp_path / "Datos", LlaveroEnMemoria())
    almacen.iniciar(None)
    try:
        assert Repeticion(almacen).permitida is False  # CA-39.4
    finally:
        almacen.detener()


def test_fotograma_del_video_guardado(almacen: AlmacenLocal) -> None:
    cv2 = pytest.importorskip("cv2")
    almacen.cambiar(video=True)
    grabador = almacen.para_camara("c1")
    clasificador = ClasificadorCinematico(Umbrales(velocidad_descenso_min=0.5))
    for i in range(20 * 8):
        while grabador._cola.qsize() > 100:  # the test wants every frame
            time.sleep(0.01)
        gris = np.zeros((480, 640, 3), dtype=np.uint8)
        gris[:, i * 4 : i * 4 + 8] = 255  # a white bar that moves 4 px per frame
        grabador.analizado(
            Analisis(
                fotograma=Fotograma(i / 8, b"", gris),
                pose=None,
                clasificador=clasificador,
                eventos=[],
                detectados=[],
                ocurrido_en=T0 + timedelta(seconds=i / 8),
            )
        )
    almacen.soltar_camara("c1")
    r = Repeticion(almacen, zona=UTC)
    assert r.abrir("c1", ms(0), ms(600))["video"] is True
    for segundos in (15.0, 5.0, 12.5):  # forward, back (seek) and forward again
        jpeg = r.fotograma_video("c1", ms(segundos))
        assert jpeg is not None
        imagen = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_GRAYSCALE)
        columnas = np.flatnonzero(imagen.mean(axis=0) > 128)
        cuadro = (float(columnas.mean()) - 3.5) / 4  # the bar's centre
        assert abs(cuadro - segundos * 8) <= 1.5, (segundos, cuadro)
    assert r.fotograma_video("c1", ms(3600)) is None
    r.cerrar()
