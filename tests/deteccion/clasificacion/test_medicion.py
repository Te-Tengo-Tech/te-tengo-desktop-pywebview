import pytest

from te_tengo_deteccion.clasificacion.medicion import MedidorCinematico
from te_tengo_deteccion.pose.schemas import Landmark, Pose
from tests import fabricas


def medidor() -> MedidorCinematico:
    return MedidorCinematico(separacion_min_s=0.25, ventana_s=1.0, visibilidad_min=0.5)


def test_sin_historial_no_hay_velocidad() -> None:
    assert medidor().medir(0.0, fabricas.DE_PIE).velocidad is None


def test_velocidad_usa_la_mayor_bajada_de_la_ventana() -> None:
    m = medidor()
    m.medir(0.0, fabricas.DE_PIE)  # hip at y = 220
    m.medir(0.5, fabricas.DE_PIE)
    medicion = m.medir(1.0, fabricas.CAYENDO)  # hip at y = 300
    # Possible pairs: with t = 0.5 (Δt 0.5 s) and with t = 0.0 (Δt 1.0 s); the largest drop wins.
    assert medicion.velocidad == pytest.approx(80 / 0.5 / 240)


def test_fotogramas_con_puntos_poco_visibles_no_miden_ni_cuentan() -> None:
    m = medidor()
    m.medir(0.0, fabricas.DE_PIE)
    dudosa = list(fabricas.CAYENDO.landmarks)
    dudosa[0] = Landmark(dudosa[0].x, dudosa[0].y, 0.1)
    assert m.medir(0.5, Pose(tuple(dudosa), 640, 480)).velocidad is None
    # The doubtful pose is not added to the history: the next one is compared only with t = 0.
    assert m.medir(0.6, fabricas.DE_PIE).velocidad == pytest.approx(0.0)


def test_s4_un_salto_de_la_cadera_reinicia_el_historial() -> None:
    m = MedidorCinematico(0.25, 1.0, 0.5, salto_max=1.0)
    m.medir(0.0, fabricas.DE_PIE)
    m.medir(0.5, fabricas.DE_PIE)
    lejos = fabricas.pose(cabeza=(600, 250), cadera=(600, 300), tobillos=(600, 340))
    medicion = m.medir(0.6, lejos)  # 280 px away with a 240 px body: another person
    assert medicion.salto
    assert medicion.velocidad is None
    assert not m.medir(0.7, lejos).salto


def test_s3_sin_tobillos_mide_con_el_tronco_solo_si_esta_activada() -> None:
    def sin_tobillos(pose: Pose, hombros: tuple[float, float]) -> Pose:
        puntos = list(pose.landmarks)
        for i in (11, 12):
            puntos[i] = Landmark(hombros[0] / 640, hombros[1] / 480, 1.0)
        for i in (27, 28):
            puntos[i] = Landmark(puntos[i].x, puntos[i].y, 0.2)
        return Pose(tuple(puntos), 640, 480)

    de_pie = sin_tobillos(fabricas.DE_PIE, (320, 140))
    cayendo = sin_tobillos(fabricas.CAYENDO, (400, 270))
    for activada in (False, True):
        m = MedidorCinematico(0.25, 1.0, 0.5, sin_tobillos=activada)
        m.medir(0.0, de_pie)
        medicion = m.medir(0.5, cayendo)
        assert medicion.sin_tobillos is activada
        if activada:
            # Hip 220 → 300 in 0.5 s; scale 2.2 × 120 px (nose to hip while standing).
            assert medicion.velocidad == pytest.approx(80 / 0.5 / (2.2 * 120))
        else:
            assert medicion.velocidad is None
