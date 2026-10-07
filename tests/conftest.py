import pytest

from te_tengo_deteccion.clasificacion.umbrales import Umbrales


@pytest.fixture
def umbrales() -> Umbrales:
    # The minimum speed is only for the tests: the real value is calibrated (see the spec).
    return Umbrales(velocidad_descenso_min=0.5)
