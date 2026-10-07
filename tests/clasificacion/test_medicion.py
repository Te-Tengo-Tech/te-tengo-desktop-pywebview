import pytest

from detection_worker.clasificacion.medicion import MedidorCinematico
from detection_worker.pose.schemas import Landmark, Pose
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
