import math

import pytest

from detection_worker.clasificacion import parametros
from detection_worker.pose.schemas import Landmark, Pose, Punto
from tests import fabricas


def test_angulo_de_pie_es_90_grados() -> None:
    assert parametros.angulo_linea_central(fabricas.DE_PIE) == pytest.approx(90.0)


def test_angulo_tendido_es_0_grados() -> None:
    assert parametros.angulo_linea_central(fabricas.TENDIDA) == pytest.approx(0.0)


def test_angulo_a_45_grados() -> None:
    pose = fabricas.pose(cabeza=(400, 100), cadera=(350, 150), tobillos=(300, 200))
    assert parametros.angulo_linea_central(pose) == pytest.approx(45.0)


def test_linea_central_usa_punto_medio_de_los_tobillos() -> None:
    pose = fabricas.pose(cabeza=(320, 100), cadera=(320, 220), tobillos=(320, 340))
    cabeza, pies = parametros.extremos_linea_central(pose)
    assert cabeza == Punto(320, 100)
    assert pies == Punto(320, 340)
    assert parametros.longitud_linea_central(pose) == pytest.approx(240.0)


def test_centro_de_cadera() -> None:
    assert parametros.centro_cadera(fabricas.CAYENDO) == Punto(330, 300)


def test_razon_ancho_alto() -> None:
    assert parametros.razon_ancho_alto(fabricas.DE_PIE, 0.5) < 1
    assert parametros.razon_ancho_alto(fabricas.CAYENDO, 0.5) == pytest.approx(120 / 90)
    assert parametros.razon_ancho_alto(fabricas.TENDIDA, 0.5) == math.inf


def test_razon_ignora_landmarks_poco_visibles() -> None:
    base = fabricas.DE_PIE
    oculto = list(base.landmarks)
    oculto[15] = Landmark(0.99, 0.5, 0.1)  # distant but poorly visible wrist
    pose = Pose(tuple(oculto), base.ancho, base.alto)
    assert parametros.razon_ancho_alto(pose, 0.5) == parametros.razon_ancho_alto(base, 0.5)


def test_velocidad_positiva_al_bajar_y_negativa_al_subir() -> None:
    assert parametros.velocidad_descenso(220, 300, 0.25, 240) == pytest.approx(80 / 0.25 / 240)
    assert parametros.velocidad_descenso(300, 220, 0.25, 240) == pytest.approx(-80 / 0.25 / 240)


def test_cabeza_bajo_pies() -> None:
    assert not parametros.cabeza_bajo_pies(fabricas.DE_PIE)
    assert parametros.cabeza_bajo_pies(
        fabricas.pose(cabeza=(320, 420), cadera=(320, 360), tobillos=(320, 300))
    )


@pytest.mark.parametrize(("dt", "escala"), [(0, 1), (-1, 1), (1, 0)])
def test_velocidad_rechaza_valores_invalidos(dt: float, escala: float) -> None:
    with pytest.raises(ValueError, match="positiv"):
        parametros.velocidad_descenso(0, 1, dt, escala)


def test_en_pixeles_respeta_imagen_no_cuadrada() -> None:
    assert fabricas.DE_PIE.en_pixeles(0) == Punto(320, 100)


def test_puntos_clave_visibles() -> None:
    assert parametros.puntos_clave_visibles(fabricas.DE_PIE, 0.5)
    oculto = list(fabricas.DE_PIE.landmarks)
    oculto[0] = Landmark(oculto[0].x, oculto[0].y, 0.2)  # poorly visible nose
    assert not parametros.puntos_clave_visibles(Pose(tuple(oculto), 640, 480), 0.5)
