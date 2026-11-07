from collections.abc import Iterator
from pathlib import Path

import pytest

from te_tengo_captura import config, i18n
from te_tengo_captura.config import Configuracion
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def idioma_espanol() -> Iterator[None]:
    """Every test starts in Spanish (the default) whatever the machine's language, and a test
    that changes the language does not leak it into the next one."""
    i18n.establecer(i18n.ES)
    yield
    i18n.establecer(i18n.ES)


@pytest.fixture
def umbrales() -> Umbrales:
    # The minimum speed is only for the tests: the real value is calibrated (see the spec).
    return Umbrales(velocidad_descenso_min=0.5)


@pytest.fixture
def configuracion() -> Configuracion:
    """The example installation of the prototype (``config.ejemplo.toml``)."""
    return config.cargar_instalacion(RAIZ / "config.ejemplo.toml")
