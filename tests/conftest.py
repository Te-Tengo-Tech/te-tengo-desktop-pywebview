from pathlib import Path

import pytest

from te_tengo_captura import config
from te_tengo_captura.config import Configuracion
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def umbrales() -> Umbrales:
    # The minimum speed is only for the tests: the real value is calibrated (see the spec).
    return Umbrales(velocidad_descenso_min=0.5)


@pytest.fixture
def configuracion() -> Configuracion:
    """The example installation of the prototype (``config.ejemplo.toml``)."""
    return config.cargar(RAIZ / "config.ejemplo.toml")
